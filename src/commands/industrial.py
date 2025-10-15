"""Industrial heat source analysis commands - MCP and CLI compatible."""

import os
from typing import Dict, Any
from pathlib import Path
import geopandas as gpd
from dotenv import load_dotenv

from src.filters.industrial_filter import IndustrialHeatFilter

load_dotenv()


def analyze_industrial_sources(
    lookback_days: int = 30,
    detection_threshold: int = 5,
    grid_size_km: float = 0.4,
    save: bool = True,
) -> Dict[str, Any]:
    """
    Identify persistent industrial heat sources from historical fire data.

    MCP-compatible function that analyzes the database to find locations
    with repeated thermal detections (steel plants, refineries, etc.).

    Args:
        lookback_days: Days of history to analyze (default 30)
        detection_threshold: Minimum detections to flag as persistent (default 5)
        grid_size_km: Grid cell size in km (default 0.4 = 400m)
        save: Save results to data/static/persistent_anomalies.geojson (default True)

    Returns:
        Dictionary with results:
        {
            "success": bool,
            "persistent_locations_found": int,
            "output_file": str or None,
            "locations": list of dicts,
            "message": str
        }

    Example:
        >>> result = analyze_industrial_sources(lookback_days=14, threshold=3)
        >>> print(f"Found {result['persistent_locations_found']} industrial sources")
    """
    db_path = os.getenv("DATABASE_PATH", "data/wildfire.duckdb")

    if not Path(db_path).exists():
        return {
            "success": False,
            "persistent_locations_found": 0,
            "output_file": None,
            "locations": [],
            "message": f"Database not found: {db_path}. Run fetch_fires_for_region() first.",
        }

    try:
        filter_obj = IndustrialHeatFilter(db_path)

        # Identify persistent anomalies
        persistent = filter_obj.identify_persistent_anomalies(
            lookback_days=lookback_days,
            detection_threshold=detection_threshold,
            grid_size_km=grid_size_km,
        )

        if len(persistent) == 0:
            return {
                "success": True,
                "persistent_locations_found": 0,
                "output_file": None,
                "locations": [],
                "message": f"No persistent sources found with threshold {detection_threshold} over {lookback_days} days",
            }

        # Convert to list of dicts for MCP
        locations = []
        for idx, row in persistent.iterrows():
            locations.append(
                {
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "detection_count": int(row["detection_count"]),
                    "unique_days": int(row["unique_days"]),
                    "first_detection": str(row["first_detection"]),
                    "last_detection": str(row["last_detection"]),
                    "detections_per_day": float(row["detections_per_day"]),
                }
            )

        # Save if requested
        output_file = None
        if save:
            filter_obj.save_persistent_locations()
            output_file = "data/static/persistent_anomalies.geojson"

        return {
            "success": True,
            "persistent_locations_found": len(persistent),
            "output_file": output_file,
            "locations": locations,
            "message": f"Identified {len(persistent)} persistent thermal anomalies",
        }

    except Exception as e:
        return {
            "success": False,
            "persistent_locations_found": 0,
            "output_file": None,
            "locations": [],
            "message": f"Error: {str(e)}",
        }


def get_persistent_locations() -> Dict[str, Any]:
    """
    Load saved persistent industrial heat source locations.

    MCP-compatible function to retrieve the current persistent locations
    without re-analyzing the database.

    Returns:
        Dictionary with locations:
        {
            "success": bool,
            "total_locations": int,
            "locations": list of dicts,
            "message": str
        }
    """
    persistent_file = Path("data/static/persistent_anomalies.geojson")

    if not persistent_file.exists():
        return {
            "success": False,
            "total_locations": 0,
            "locations": [],
            "message": "No persistent locations file found. Run analyze_industrial_sources() first.",
        }

    try:
        gdf = gpd.read_file(persistent_file)

        locations = []
        for idx, row in gdf.iterrows():
            locations.append(
                {
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "detection_count": int(row["detection_count"]),
                    "unique_days": int(row["unique_days"]),
                    "first_detection": str(row["first_detection"]),
                    "last_detection": str(row["last_detection"]),
                }
            )

        return {
            "success": True,
            "total_locations": len(gdf),
            "locations": locations,
            "message": f"Loaded {len(gdf)} persistent locations",
        }

    except Exception as e:
        return {
            "success": False,
            "total_locations": 0,
            "locations": [],
            "message": f"Error reading persistent locations: {str(e)}",
        }
