# flows/etl_flow.py
from prefect import flow, task
from prefect.tasks import task_input_hash
from datetime import timedelta
import geopandas as gpd
from pathlib import Path
import os
from dotenv import load_dotenv

from src.ingestion.firms_client import FIRMSClient
from src.ingestion.noaa_client import NOAAWeatherClient
from src.ingestion.airnow_client import AirNowClient
from src.ingestion.purpleair_client import PurpleAirClient
from src.analysis.risk_calculator import FireRiskCalculator
from src.database import init_database, save_fires_to_db
from src.database.operations import save_buffers_to_db
from src.filters.industrial_filter import IndustrialHeatFilter

# Load environment variables from .env file
_ = load_dotenv()


@task
def clear_database_task(db_path: str):
    """Clear existing fire data from database before new ETL run."""
    conn = init_database(db_path)
    conn.execute("DELETE FROM fire_buffers")
    conn.execute("DELETE FROM fires")
    conn.commit()
    # Don't close - using singleton pattern
    print("✓ Cleared previous fire data from database")


@task(cache_key_fn=task_input_hash, cache_expiration=timedelta(hours=3))
def fetch_active_fires(
    api_key: str, days: int = 1, bbox: tuple[float, float, float, float] | None = None
) -> gpd.GeoDataFrame:
    """
    Fetch active fires from FIRMS.

    Args:
        api_key: FIRMS API key
        days: Days to look back
        bbox: Bounding box (west, south, east, north). If None, uses continental US.
    """
    client = FIRMSClient(api_key)
    if bbox is None:
        return client.get_continental_us_fires(days)
    else:
        return client.get_active_fires(bbox, days)


@task
def filter_industrial_sources(
    fires_gdf: gpd.GeoDataFrame, db_path: str
) -> gpd.GeoDataFrame:
    """Filter out persistent industrial heat sources."""
    filter_obj = IndustrialHeatFilter(db_path)

    # Try to load existing persistent locations first
    persistent = filter_obj.load_persistent_locations()

    # If no existing data, identify from historical data with adaptive threshold
    if persistent is None or len(persistent) == 0:
        # Identify persistent anomalies from historical data
        # Use lower threshold (2 days) to work with limited historical data
        persistent = filter_obj.identify_persistent_anomalies(
            lookback_days=30, detection_threshold=2, grid_size_km=0.4
        )

    if len(persistent) > 0:
        print(
            f"Filtering {len(fires_gdf)} fires against {len(persistent)} known industrial sources..."
        )
        # Filter fires near persistent locations (1km buffer to account for sensor drift)
        filtered_fires, excluded_fires = filter_obj.filter_fires(
            fires_gdf, buffer_km=1.0, persistent_locations=persistent
        )

        print(f"  Excluded {len(excluded_fires)} industrial heat sources")
        print(f"  Retained {len(filtered_fires)} actual fire detections")

        # Save persistent locations for reference
        filter_obj.save_persistent_locations()

        return filtered_fires
    else:
        print("No persistent anomalies found - returning all fires")
        return fires_gdf


@task
def enrich_with_weather(fires_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Enrich fires with NOAA weather data."""
    with NOAAWeatherClient() as noaa:
        return noaa.enrich_fires_with_weather(fires_gdf)


@task
def enrich_with_aqi(fires_gdf: gpd.GeoDataFrame, api_key: str) -> gpd.GeoDataFrame:
    """Enrich fires with AirNow air quality data."""
    airnow = AirNowClient(api_key)
    return airnow.enrich_fires_with_aqi(fires_gdf)


@task
def enrich_with_purpleair(
    fires_gdf: gpd.GeoDataFrame, api_key: str
) -> gpd.GeoDataFrame:
    """Enrich fires with PurpleAir sensor data."""
    purpleair = PurpleAirClient(api_key)
    return purpleair.enrich_fires_with_purpleair(fires_gdf)


@task
def calculate_risk_scores(
    fires_gdf: gpd.GeoDataFrame, use_weather: bool = True
) -> gpd.GeoDataFrame:
    """Calculate risk scores for fires."""
    calculator = FireRiskCalculator(use_weather=use_weather)

    if use_weather:
        return calculator.calculate_enhanced_risk(fires_gdf)
    else:
        return calculator.calculate_base_risk(fires_gdf)


@task
def create_buffers(
    fires_gdf: gpd.GeoDataFrame, buffer_km: float = 5.0, dissolve: bool = False
) -> gpd.GeoDataFrame:
    """
    Create risk buffer zones.

    Args:
        fires_gdf: GeoDataFrame with fire detections
        buffer_km: Buffer radius in kilometers (default 5km)
        dissolve: If True, merge overlapping buffers by risk category.
                 Set to False (default) for individual fire buffers.
    """
    calculator = FireRiskCalculator()
    return calculator.create_risk_buffers(fires_gdf, buffer_km, dissolve=dissolve)


# @task
# def save_to_database(fires_gdf: gpd.GeoDataFrame, db_path: str):
#     """Save processed data to DuckDB."""
#     conn = init_database(db_path)
#     save_fires_to_db(conn, fires_gdf)
#     conn.close()


@task
def save_to_database(fires_gdf: gpd.GeoDataFrame, db_path: str):
    """Save processed data to DuckDB."""
    conn = init_database(db_path)
    save_fires_to_db(conn, fires_gdf)


@task
def save_buffers_to_database(
    buffers_gdf: gpd.GeoDataFrame, db_path: str, buffer_km: float
):
    """Save buffer zones to DuckDB."""
    conn = init_database(db_path)
    save_buffers_to_db(conn, buffers_gdf, buffer_km)


@task
def export_for_visualization(
    fires_gdf: gpd.GeoDataFrame,
    buffers_gdf: gpd.GeoDataFrame,
    output_dir: str,
    bbox: tuple[float, float, float, float] | None = None,
):
    """Export GeoJSON for kepler.gl."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Export fires
    fires_gdf.to_file(f"{output_dir}/active_fires.geojson", driver="GeoJSON")

    # Export buffers
    if not buffers_gdf.empty:
        buffers_gdf.to_file(f"{output_dir}/fire_buffers.geojson", driver="GeoJSON")

    # Save region metadata for visualization
    import json

    metadata = {
        "bbox": bbox if bbox else None,
        "fire_count": len(fires_gdf),
        "buffer_count": len(buffers_gdf),
    }
    with open(f"{output_dir}/region_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)


@flow(name="Wildfire Risk Monitor ETL")
def wildfire_etl_flow(
    days_back: int = 1,
    buffer_km: float = 5.0,
    use_weather: bool = True,
    use_aqi: bool = False,
    use_purpleair: bool = False,
    filter_industrial: bool = True,
    bbox: tuple[float, float, float, float] | None = None,
    dissolve_buffers: bool = True,
) -> gpd.GeoDataFrame | None:
    """
    Main ETL flow for wildfire monitoring.

    Args:
        days_back: Number of days to look back for fire data (1-10)
        buffer_km: Buffer radius in kilometers for risk zones (default 5km)
                  Typical values: 2-5km for immediate risk, 10-20km for extended risk
        use_weather: If True, enrich fires with NOAA weather data (slower but more accurate)
        use_aqi: If True, enrich fires with AirNow air quality data
        use_purpleair: If True, enrich fires with PurpleAir sensor data (real-time PM2.5)
        filter_industrial: If True, filter out persistent industrial heat sources
        bbox: Optional bounding box (west, south, east, north) to limit geographic area.
              If None, uses continental US (-125, 24, -66, 49).
              Example: California: (-124.5, 32.5, -114, 42)
        dissolve_buffers: If True (default), merge overlapping buffers by risk category (creates risk zones).
                         If False, keep individual fire buffers (one per fire detection).
    """
    # Load config
    api_key = os.getenv("FIRMS_API_KEY")
    airnow_api_key = os.getenv("AIRNOW_API_KEY")
    purpleair_api_key = os.getenv("PURPLEAIR_API_KEY")
    db_path = os.getenv("DATABASE_PATH", "data/wildfire.duckdb")

    # Clear database before new ETL run to keep data fresh
    _ = clear_database_task(db_path)

    # Fetch data
    fires: gpd.GeoDataFrame = fetch_active_fires(api_key, days_back, bbox)  # pyright: ignore[reportAssignmentType]

    if len(fires) == 0:
        print("No fires detected")
        return None

    # Filter industrial sources if requested
    if filter_industrial:
        print(f"Filtering industrial heat sources from {len(fires)} detections...")
        fires = filter_industrial_sources(fires, db_path)  # type: ignore[assignment]

        if len(fires) == 0:
            print("No fires remaining after filtering industrial sources")
            return None

    # Enrich with weather data if requested
    if use_weather:
        print(f"Enriching {len(fires)} fires with NOAA weather data...")
        fires = enrich_with_weather(fires)  # type: ignore[assignment]

    # Enrich with AQI data if requested
    if use_aqi:
        if not airnow_api_key:
            print(
                "Warning: AIRNOW_API_KEY not set in .env file, skipping AQI enrichment"
            )
        else:
            print(f"Enriching {len(fires)} fires with AirNow AQI data...")
            fires = enrich_with_aqi(fires, airnow_api_key)  # type: ignore[assignment]

    # Enrich with PurpleAir data if requested
    if use_purpleair:
        if not purpleair_api_key:
            print(
                "Warning: PURPLEAIR_API_KEY not set in .env file, skipping PurpleAir enrichment"
            )
            print("  Get a free API key at https://develop.purpleair.com/")
        else:
            print(f"Enriching {len(fires)} fires with PurpleAir sensor data...")
            fires = enrich_with_purpleair(fires, purpleair_api_key)  # type: ignore[assignment]

    # Process data
    fires_with_risk: gpd.GeoDataFrame = calculate_risk_scores(
        fires, use_weather=use_weather
    )  # type: ignore[assignment]
    buffers: gpd.GeoDataFrame = create_buffers(
        fires_with_risk, buffer_km, dissolve_buffers
    )  # type: ignore[assignment]

    # Save results
    _ = save_to_database(fires_with_risk, db_path)
    _ = save_buffers_to_database(buffers, db_path, buffer_km)
    _ = export_for_visualization(fires_with_risk, buffers, "data/processed", bbox)

    weather_msg = "with weather data" if use_weather else "without weather data"
    print(
        f"Processed {len(fires_with_risk)} fires {weather_msg} with {buffer_km}km buffers"
    )
    return fires_with_risk


# NOTE: FIRMS API has ~24hr processing delay, use days_back=2 for recent fires
# NOTE: setting more than 10 days back will return nothing from FIRMS API
if __name__ == "__main__":
    # Default to 2 days to account for FIRMS processing delay
    # use_weather=False by default for faster processing (enable for detailed analysis)
    # filter_industrial=True to exclude steel plants, refineries, etc.
    wildfire_etl_flow(days_back=2, use_weather=True, filter_industrial=True)
