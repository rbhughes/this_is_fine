"""Fetch fire data commands - MCP and CLI compatible."""

import os
from typing import Dict, Any, Tuple
from pathlib import Path
import geopandas as gpd
from dotenv import load_dotenv

from flows.etl_flow import wildfire_etl_flow
from .regions import get_region_bbox

load_dotenv()


def fetch_fires_for_region(
    region: str,
    days_back: int = 2,
    buffer_km: float = 5.0,
    use_weather: bool = False,
    use_aqi: bool = False,
    use_purpleair: bool = False,
    filter_industrial: bool = True,
    dissolve_buffers: bool = True,
) -> Dict[str, Any]:
    """
    Fetch fire data for a named region.

    MCP-compatible function that fetches and processes fire data for
    predefined regions (states, multi-state areas).

    Args:
        region: Region name (e.g., "california", "indiana", "pacific-northwest")
        days_back: Number of days to look back (1-10, default 2)
        buffer_km: Buffer radius in km (default 5.0)
        use_weather: Enrich with NOAA weather data (default False, slower)
        use_aqi: Enrich with AirNow air quality data (default False)
        use_purpleair: Enrich with PurpleAir sensor data (default False)
        filter_industrial: Filter industrial heat sources (default True)
        dissolve_buffers: Merge overlapping buffers by risk category (default True)

    Returns:
        Dictionary with results:
        {
            "success": bool,
            "fires_processed": int,
            "region": str,
            "bbox": tuple,
            "output_files": list,
            "message": str
        }

    Example:
        >>> result = fetch_fires_for_region("indiana", days_back=2)
        >>> print(f"Processed {result['fires_processed']} fires")
    """
    bbox = get_region_bbox(region)

    if bbox is None:
        return {
            "success": False,
            "fires_processed": 0,
            "region": region,
            "bbox": None,
            "output_files": [],
            "message": f"Unknown region: {region}. Use list_regions() to see available regions.",
        }

    return fetch_fires_for_bbox(
        bbox=bbox,
        days_back=days_back,
        buffer_km=buffer_km,
        use_weather=use_weather,
        use_aqi=use_aqi,
        use_purpleair=use_purpleair,
        filter_industrial=filter_industrial,
        dissolve_buffers=dissolve_buffers,
        region_name=region,
    )


def fetch_fires_for_bbox(
    bbox: Tuple[float, float, float, float],
    days_back: int = 2,
    buffer_km: float = 5.0,
    use_weather: bool = False,
    use_aqi: bool = False,
    use_purpleair: bool = False,
    filter_industrial: bool = True,
    dissolve_buffers: bool = True,
    region_name: str | None = None,
) -> Dict[str, Any]:
    """
    Fetch fire data for a custom bounding box.

    MCP-compatible function that fetches and processes fire data for
    any geographic bounding box.

    Args:
        bbox: Bounding box (west, south, east, north) in WGS84 decimal degrees
        days_back: Number of days to look back (1-10, default 2)
        buffer_km: Buffer radius in km (default 5.0)
        use_weather: Enrich with NOAA weather data (default False, slower)
        use_aqi: Enrich with AirNow air quality data (default False)
        use_purpleair: Enrich with PurpleAir sensor data (default False)
        filter_industrial: Filter industrial heat sources (default True)
        dissolve_buffers: Merge overlapping buffers by risk category (default True)
        region_name: Optional name for this region (for reporting)

    Returns:
        Dictionary with results:
        {
            "success": bool,
            "fires_processed": int,
            "region": str or None,
            "bbox": tuple,
            "output_files": list,
            "message": str
        }

    Example:
        >>> result = fetch_fires_for_bbox(
        ...     bbox=(-124.5, 32.5, -114.13, 42.0),
        ...     days_back=1,
        ...     use_weather=False
        ... )
    """
    try:
        # Run the ETL flow
        result = wildfire_etl_flow(
            days_back=days_back,
            buffer_km=buffer_km,
            use_weather=use_weather,
            use_aqi=use_aqi,
            use_purpleair=use_purpleair,
            filter_industrial=filter_industrial,
            bbox=bbox,
            dissolve_buffers=dissolve_buffers,
        )

        if result is None or len(result) == 0:
            return {
                "success": True,
                "fires_processed": 0,
                "region": region_name,
                "bbox": bbox,
                "output_files": [],
                "message": "No fires detected in this area/timeframe",
            }

        # Check output files
        output_dir = Path("data/processed")
        output_files = []
        if (output_dir / "active_fires.geojson").exists():
            output_files.append(str(output_dir / "active_fires.geojson"))
        if (output_dir / "fire_buffers.geojson").exists():
            output_files.append(str(output_dir / "fire_buffers.geojson"))

        weather_msg = "with weather data" if use_weather else "without weather data"
        filter_msg = (
            "with industrial filtering" if filter_industrial else "no filtering"
        )

        return {
            "success": True,
            "fires_processed": len(result),
            "region": region_name,
            "bbox": bbox,
            "output_files": output_files,
            "message": f"Processed {len(result)} fires {weather_msg}, {filter_msg}",
        }

    except Exception as e:
        return {
            "success": False,
            "fires_processed": 0,
            "region": region_name,
            "bbox": bbox,
            "output_files": [],
            "message": f"Error: {str(e)}",
        }


def get_fires_summary() -> Dict[str, Any]:
    """
    Get summary of currently processed fire data.

    Returns summary statistics from the latest GeoJSON exports.

    Returns:
        Dictionary with summary stats:
        {
            "success": bool,
            "total_fires": int,
            "total_buffers": int,
            "date_range": tuple or None,
            "risk_breakdown": dict,
            "message": str
        }
    """
    try:
        fires_path = Path("data/processed/active_fires.geojson")
        buffers_path = Path("data/processed/fire_buffers.geojson")

        if not fires_path.exists():
            return {
                "success": False,
                "total_fires": 0,
                "total_buffers": 0,
                "date_range": None,
                "risk_breakdown": {},
                "message": "No processed fire data found. Run fetch_fires_for_region() first.",
            }

        fires = gpd.read_file(fires_path)
        buffers = gpd.read_file(buffers_path) if buffers_path.exists() else None

        # Get risk breakdown
        risk_breakdown = {}
        if "risk_category" in fires.columns:
            risk_breakdown = fires["risk_category"].value_counts().to_dict()

        # Get date range
        date_range = None
        if "acq_date" in fires.columns:
            date_range = (
                str(fires["acq_date"].min()),
                str(fires["acq_date"].max()),
            )

        return {
            "success": True,
            "total_fires": len(fires),
            "total_buffers": len(buffers) if buffers is not None else 0,
            "date_range": date_range,
            "risk_breakdown": risk_breakdown,
            "message": f"Found {len(fires)} fires across {len(risk_breakdown)} risk categories",
        }

    except Exception as e:
        return {
            "success": False,
            "total_fires": 0,
            "total_buffers": 0,
            "date_range": None,
            "risk_breakdown": {},
            "message": f"Error reading fire data: {str(e)}",
        }
