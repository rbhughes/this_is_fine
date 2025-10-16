"""
MCP Tool Implementations for Wildfire Risk Monitoring
"""

import json
from pathlib import Path
from typing import Any, Dict
import geopandas as gpd
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import project modules
from src.commands.fetch_fires import fetch_fires_for_region
from src.ingestion.noaa_client import NOAAWeatherClient
from src.ingestion.airnow_client import AirNowClient
from src.ingestion.purpleair_client import PurpleAirClient


def log(message: str):
    """Print timestamped log message to stderr for visibility."""
    from datetime import datetime

    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", file=sys.stderr, flush=True)


async def fetch_fires_tool(args: Dict[str, Any]) -> str:
    """
    Fetch fire data from NASA FIRMS with optional enrichment.

    Args:
        region: Region name (e.g., 'california', 'colorado', 'conus')
        days_back: Number of days to look back (default: 2)
        filter_industrial: Filter industrial heat sources (default: True)
        use_weather: Include NOAA weather data (default: False, slow for large datasets)
        use_aqi: Include EPA AirNow air quality data (default: False)
        use_purpleair: Include PurpleAir PM2.5 sensor data (default: False)

    Returns:
        JSON string with fire count and summary statistics
    """
    region = args.get("region", "conus")
    days_back = args.get("days_back", 2)
    filter_industrial = args.get("filter_industrial", True)
    use_weather = args.get("use_weather", False)
    use_aqi = args.get("use_aqi", False)
    use_purpleair = args.get("use_purpleair", False)

    enrichments = []
    if use_weather:
        enrichments.append("weather")
    if use_aqi:
        enrichments.append("AQI")
    if use_purpleair:
        enrichments.append("PM2.5")

    enrich_msg = f" with {', '.join(enrichments)}" if enrichments else ""
    log(f"🔥 Fetching fires for {region} (last {days_back} days){enrich_msg}...")

    # Fetch fires using existing command
    result = fetch_fires_for_region(
        region=region,
        days_back=days_back,
        buffer_km=5.0,
        use_weather=use_weather,
        use_aqi=use_aqi,
        use_purpleair=use_purpleair,
        filter_industrial=filter_industrial,
        dissolve_buffers=True,
    )

    # Format response (handle both old and new key names)
    fires_count = result.get("fires_processed", result.get("fires_count", 0))
    industrial_filtered = result.get("industrial_filtered", 0)

    # Count buffers from the actual file
    data_dir = Path("data/processed")
    buffers_count = 0
    if (data_dir / "fire_buffers.geojson").exists():
        import geopandas as gpd

        buffers_gdf = gpd.read_file(data_dir / "fire_buffers.geojson")
        buffers_count = len(buffers_gdf)

    log(f"✓ Found {fires_count} fires ({industrial_filtered} industrial filtered)")

    response = {
        "status": "success",
        "region": region,
        "fires_count": fires_count,
        "buffers_count": buffers_count,
        "industrial_filtered": industrial_filtered,
        "days_back": days_back,
        "message": f"Fetched {fires_count} fires from {region} "
        f"({industrial_filtered} industrial sources filtered)",
    }

    return json.dumps(response, indent=2)


async def enrich_weather_tool(args: Dict[str, Any]) -> str:
    """
    Enrich fire data with NOAA weather information.

    Args:
        limit: Maximum number of fires to enrich (default: all)

    Returns:
        JSON string with enrichment statistics
    """
    limit = args.get("limit")

    log("🌤️  Loading fire data for weather enrichment...")

    # Load fires from database
    data_dir = Path("data/processed")
    fires_gdf = gpd.read_file(data_dir / "active_fires.geojson")

    if limit:
        fires_gdf = fires_gdf.head(limit)
        log(f"   Limiting to first {limit} fires")

    log(f"   Processing {len(fires_gdf)} fires")

    # Get NOAA API token
    noaa_token = os.getenv("NOAA_API_TOKEN")
    if not noaa_token:
        log("❌ NOAA_API_TOKEN not found in .env")
        return json.dumps(
            {
                "status": "error",
                "message": "NOAA_API_TOKEN not found in environment variables",
            }
        )

    log("   Fetching weather data from NOAA NWS API...")
    log("   ⚠️  This may take 1-2 seconds per fire")

    # Enrich with weather data
    noaa_client = NOAAWeatherClient()
    enriched_gdf = noaa_client.enrich_fires_with_weather(fires_gdf)

    log("   Saving enriched data...")

    # Save back to database
    enriched_gdf.to_file(data_dir / "active_fires.geojson", driver="GeoJSON")

    # Count enriched fires
    weather_count = enriched_gdf["temperature_c"].notna().sum()

    log(f"✓ Added weather data to {weather_count}/{len(enriched_gdf)} fires")

    response = {
        "status": "success",
        "fires_enriched": int(weather_count),
        "total_fires": len(enriched_gdf),
        "message": f"Enriched {weather_count}/{len(enriched_gdf)} fires with weather data",
    }

    return json.dumps(response, indent=2)


async def enrich_aqi_tool(args: Dict[str, Any]) -> str:
    """
    Enrich fire data with EPA AirNow AQI data.

    Args:
        limit: Maximum number of fires to enrich (default: all)

    Returns:
        JSON string with enrichment statistics
    """
    limit = args.get("limit")

    log("💨 Loading fire data for AQI enrichment...")

    # Load fires from database
    data_dir = Path("data/processed")
    fires_gdf = gpd.read_file(data_dir / "active_fires.geojson")

    if limit:
        fires_gdf = fires_gdf.head(limit)
        log(f"   Limiting to first {limit} fires")

    log(f"   Processing {len(fires_gdf)} fires")

    # Get AirNow API key
    airnow_key = os.getenv("AIRNOW_API_KEY")
    if not airnow_key:
        log("❌ AIRNOW_API_KEY not found in .env")
        return json.dumps(
            {
                "status": "error",
                "message": "AIRNOW_API_KEY not found in environment variables",
            }
        )

    log("   Fetching AQI data from EPA AirNow API...")

    # Enrich with AQI data
    airnow_client = AirNowClient(airnow_key)
    enriched_gdf = airnow_client.enrich_fires_with_aqi(fires_gdf)

    log("   Saving enriched data...")

    # Save back to database
    enriched_gdf.to_file(data_dir / "active_fires.geojson", driver="GeoJSON")

    # Count enriched fires
    aqi_count = enriched_gdf["aqi"].notna().sum()

    log(f"✓ Added AQI data to {aqi_count}/{len(enriched_gdf)} fires")

    response = {
        "status": "success",
        "fires_enriched": int(aqi_count),
        "total_fires": len(enriched_gdf),
        "message": f"Enriched {aqi_count}/{len(enriched_gdf)} fires with AQI data",
    }

    return json.dumps(response, indent=2)


async def enrich_purpleair_tool(args: Dict[str, Any]) -> str:
    """
    Enrich fire data with PurpleAir PM2.5 sensor data.

    Args:
        limit: Maximum number of fires to enrich (default: all)
        radius_km: Search radius in km (default: 50)

    Returns:
        JSON string with enrichment statistics
    """
    limit = args.get("limit")
    radius_km = args.get("radius_km", 50.0)

    log(f"🟣 Loading fire data for PurpleAir enrichment (radius: {radius_km}km)...")

    # Load fires from database
    data_dir = Path("data/processed")
    fires_gdf = gpd.read_file(data_dir / "active_fires.geojson")

    if limit:
        fires_gdf = fires_gdf.head(limit)
        log(f"   Limiting to first {limit} fires")

    log(f"   Processing {len(fires_gdf)} fires")

    # Get PurpleAir API key
    purpleair_key = os.getenv("PURPLEAIR_API_KEY")
    if not purpleair_key:
        log("❌ PURPLEAIR_API_KEY not found in .env")
        return json.dumps(
            {
                "status": "error",
                "message": "PURPLEAIR_API_KEY not found in environment variables",
            }
        )

    log("   Fetching PM2.5 data from PurpleAir sensors...")

    # Enrich with PurpleAir data
    purpleair_client = PurpleAirClient(purpleair_key)
    enriched_gdf = purpleair_client.enrich_fires_with_purpleair(
        fires_gdf, radius_km=radius_km
    )

    log("   Saving enriched data...")

    # Save back to database
    enriched_gdf.to_file(data_dir / "active_fires.geojson", driver="GeoJSON")

    # Count enriched fires
    pa_count = enriched_gdf["pa_pm25"].notna().sum()

    log(f"✓ Added PurpleAir data to {pa_count}/{len(enriched_gdf)} fires")

    response = {
        "status": "success",
        "fires_enriched": int(pa_count),
        "total_fires": len(enriched_gdf),
        "radius_km": radius_km,
        "message": f"Enriched {pa_count}/{len(enriched_gdf)} fires with PurpleAir data",
    }

    return json.dumps(response, indent=2)


async def visualize_fires_tool(args: Dict[str, Any]) -> str:
    """
    Generate interactive map visualizations.

    Args:
        map_types: List of map types to generate (default: all)

    Returns:
        JSON string with paths to generated HTML files
    """
    import plotly.express as px
    import plotly.graph_objects as go

    map_types = args.get("map_types", ["all"])
    if "all" in map_types:
        map_types = ["basic", "risk_heatmap", "brightness", "buffers", "combined"]

    log(f"🗺️  Generating {len(map_types)} map visualizations...")

    # Load data
    data_dir = Path("data/processed")
    log("   Loading fire data...")
    fires_gdf = gpd.read_file(data_dir / "active_fires.geojson")
    buffers_gdf = gpd.read_file(data_dir / "fire_buffers.geojson")

    fires_df = fires_gdf.copy()
    fires_df["lon"] = fires_df.geometry.x
    fires_df["lat"] = fires_df.geometry.y

    center_lat = fires_df["lat"].mean()
    center_lon = fires_df["lon"].mean()

    map_style = "carto-positron"
    generated_maps = []

    # Generate basic map
    if "basic" in map_types:
        log("   Creating basic fire map...")
        fig = px.scatter_map(
            fires_df,
            lat="lat",
            lon="lon",
            color="risk_category",
            color_discrete_map={"Low": "yellow", "Moderate": "orange", "High": "red"},
            hover_data=["risk_score", "confidence", "bright_ti4", "frp"],
            zoom=6,
            center={"lat": center_lat, "lon": center_lon},
            title="Active Fire Detections",
            map_style=map_style,
        )
        fig.update_layout(height=600)
        output_path = data_dir / "fires_basic_map.html"
        fig.write_html(output_path)
        generated_maps.append(str(output_path))

    # Generate risk heatmap
    if "risk_heatmap" in map_types:
        log("   Creating risk heatmap...")
        fig = px.density_map(
            fires_df,
            lat="lat",
            lon="lon",
            z="risk_score",
            radius=15,
            zoom=6,
            center={"lat": center_lat, "lon": center_lon},
            color_continuous_scale="YlOrRd",
            title="Fire Risk Heatmap",
            map_style=map_style,
        )
        fig.update_layout(
            height=600,
            margin=dict(l=0, r=0, t=30, b=0),
            autosize=True,
        )
        output_path = data_dir / "fires_risk_heatmap.html"
        fig.write_html(output_path)
        generated_maps.append(str(output_path))

    # Check for AQI data
    if "aqi" in map_types or "all" in args.get("map_types", []):
        fires_aqi = fires_df[fires_df["aqi"].notna()]
        if len(fires_aqi) > 0:
            log(f"   Creating AQI heatmap ({len(fires_aqi)} fires with AQI data)...")
            fig = px.density_map(
                fires_aqi,
                lat="lat",
                lon="lon",
                z="aqi",
                radius=15,
                zoom=6,
                center={"lat": center_lat, "lon": center_lon},
                color_continuous_scale="YlOrRd",
                title="AQI Density Heatmap",
                map_style=map_style,
            )
            fig.update_layout(
                height=600,
                margin=dict(l=0, r=0, t=30, b=0),
                autosize=True,
            )
            output_path = data_dir / "fires_aqi.html"
            fig.write_html(output_path)
            generated_maps.append(str(output_path))

    # Check for PurpleAir data
    if "purpleair" in map_types or "all" in args.get("map_types", []):
        fires_pa = fires_df[fires_df["pa_pm25"].notna()]
        if len(fires_pa) > 0:
            log(
                f"   Creating PurpleAir heatmap ({len(fires_pa)} fires with PM2.5 data)..."
            )
            fig = px.density_map(
                fires_pa,
                lat="lat",
                lon="lon",
                z="pa_pm25",
                radius=15,
                zoom=6,
                center={"lat": center_lat, "lon": center_lon},
                color_continuous_scale="YlOrRd",
                title="PM2.5 Heatmap (PurpleAir)",
                map_style=map_style,
            )
            fig.update_layout(
                height=600,
                margin=dict(l=0, r=0, t=30, b=0),
                autosize=True,
            )
            output_path = data_dir / "fires_purpleair_heatmap.html"
            fig.write_html(output_path)
            generated_maps.append(str(output_path))

    log(f"✓ Generated {len(generated_maps)} map visualizations")

    response = {
        "status": "success",
        "maps_generated": len(generated_maps),
        "output_files": generated_maps,
        "message": f"Generated {len(generated_maps)} map visualizations",
    }

    return json.dumps(response, indent=2)


async def get_fire_stats_tool(args: Dict[str, Any]) -> str:
    """
    Get summary statistics about fire data.

    Returns:
        JSON string with fire statistics
    """
    log("📊 Calculating fire statistics...")

    # Load data
    data_dir = Path("data/processed")
    fires_gdf = gpd.read_file(data_dir / "active_fires.geojson")

    # Calculate statistics
    total_fires = len(fires_gdf)
    risk_counts = fires_gdf["risk_category"].value_counts().to_dict()

    # Check enrichment status
    has_weather = (
        fires_gdf["temperature_c"].notna().sum() if "temperature_c" in fires_gdf else 0
    )
    has_aqi = fires_gdf["aqi"].notna().sum() if "aqi" in fires_gdf else 0
    has_purpleair = fires_gdf["pa_pm25"].notna().sum() if "pa_pm25" in fires_gdf else 0

    # Get date range
    if "acq_date" in fires_gdf:
        dates = fires_gdf["acq_date"].unique()
        date_range = f"{min(dates)} to {max(dates)}"
    else:
        date_range = "Unknown"

    # Get geographic extent
    bounds = fires_gdf.total_bounds  # [minx, miny, maxx, maxy]

    log(
        f"✓ Stats: {total_fires} fires, {has_weather} with weather, {has_aqi} with AQI, {has_purpleair} with PM2.5"
    )

    response = {
        "status": "success",
        "total_fires": int(total_fires),
        "risk_breakdown": {k: int(v) for k, v in risk_counts.items()},
        "enrichment_status": {
            "weather": int(has_weather),
            "aqi": int(has_aqi),
            "purpleair": int(has_purpleair),
        },
        "date_range": date_range,
        "geographic_extent": {
            "west": float(bounds[0]),
            "south": float(bounds[1]),
            "east": float(bounds[2]),
            "north": float(bounds[3]),
        },
    }

    return json.dumps(response, indent=2)
