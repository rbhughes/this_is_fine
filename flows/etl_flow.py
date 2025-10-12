# flows/etl_flow.py
from prefect import flow, task
from prefect.tasks import task_input_hash
from datetime import timedelta
import geopandas as gpd
from pathlib import Path
import os

from src.ingestion.firms_client import FIRMSClient
from src.analysis.risk_calculator import FireRiskCalculator
from src.database import init_database, save_fires_to_db


@task(cache_key_fn=task_input_hash, cache_expiration=timedelta(hours=3))
def fetch_active_fires(api_key: str, days: int = 1) -> gpd.GeoDataFrame:
    """Fetch active fires from FIRMS."""
    client = FIRMSClient(api_key)
    return client.get_continental_us_fires(days)


@task
def calculate_risk_scores(fires_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Calculate risk scores for fires."""
    calculator = FireRiskCalculator()
    return calculator.calculate_base_risk(fires_gdf)


@task
def create_buffers(
    fires_gdf: gpd.GeoDataFrame, buffer_km: float = 10
) -> gpd.GeoDataFrame:
    """Create risk buffer zones."""
    calculator = FireRiskCalculator()
    return calculator.create_risk_buffers(fires_gdf, buffer_km)


@task
def save_to_database(fires_gdf: gpd.GeoDataFrame, db_path: str):
    """Save processed data to DuckDB."""
    conn = init_database(db_path)
    save_fires_to_db(conn, fires_gdf)
    conn.close()


@task
def export_for_visualization(fires_gdf: gpd.GeoDataFrame, output_dir: str):
    """Export GeoJSON for kepler.gl."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Export fires
    fires_gdf.to_file(f"{output_dir}/active_fires.geojson", driver="GeoJSON")


@flow(name="Wildfire Risk Monitor ETL")
def wildfire_etl_flow(days_back: int = 1, buffer_km: float = 10):
    """Main ETL flow for wildfire monitoring."""

    # Load config
    api_key = os.getenv("FIRMS_API_KEY")
    db_path = os.getenv("DATABASE_PATH", "data/wildfire.duckdb")

    # Fetch data
    fires = fetch_active_fires(api_key, days_back)

    if fires.empty:
        print("No fires detected")
        return

    # Process data
    fires_with_risk = calculate_risk_scores(fires)
    buffers = create_buffers(fires_with_risk, buffer_km)

    # Save results
    save_to_database(fires_with_risk, db_path)
    export_for_visualization(fires_with_risk, "data/processed")

    print(f"Processed {len(fires_with_risk)} fires")
    return fires_with_risk


if __name__ == "__main__":
    wildfire_etl_flow()
