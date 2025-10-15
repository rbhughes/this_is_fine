"""
Filter industrial heat sources from fire detection data.

This module identifies and filters out persistent thermal anomalies that are likely
from industrial sources (steel plants, refineries, gas flares, etc.) rather than
actual wildfires.
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timedelta
import duckdb


class IndustrialHeatFilter:
    """
    Filter out persistent thermal anomalies from industrial sources.

    Uses temporal persistence analysis to identify locations that repeatedly
    show fire detections over extended periods, which are likely industrial
    facilities rather than wildfires.
    """

    def __init__(self, db_path: str = "data/wildfire.duckdb"):
        """
        Initialize the industrial heat filter.

        Args:
            db_path: Path to DuckDB database containing historical fire data
        """
        self.db_path = db_path
        self.persistent_locations = None

    def identify_persistent_anomalies(
        self,
        lookback_days: int = 30,
        detection_threshold: int = 5,
        grid_size_km: float = 0.4,
    ) -> gpd.GeoDataFrame:
        """
        Identify persistent thermal anomalies from historical data.

        Uses a grid-based approach similar to NASA's STA layer:
        - Summarize detections on a grid (default 400m ~ 0.4km)
        - Identify cells with multiple detections over time period
        - Flag these as likely industrial sources

        Args:
            lookback_days: Days of history to analyze (default 30)
            detection_threshold: Minimum detections to flag as persistent (default 5)
            grid_size_km: Grid cell size in kilometers (default 0.4 = 400m)

        Returns:
            GeoDataFrame with persistent anomaly locations
        """
        try:
            conn = duckdb.connect(self.db_path)
            conn.install_extension("spatial")
            conn.load_extension("spatial")

            # Calculate date threshold
            start_date = (datetime.now() - timedelta(days=lookback_days)).strftime(
                "%Y-%m-%d"
            )

            # Query historical fires and snap to grid
            query = f"""
            WITH gridded_fires AS (
                SELECT
                    FLOOR(latitude / {grid_size_km}) * {grid_size_km} as grid_lat,
                    FLOOR(longitude / {grid_size_km}) * {grid_size_km} as grid_lon,
                    COUNT(*) as detection_count,
                    AVG(latitude) as avg_lat,
                    AVG(longitude) as avg_lon,
                    MIN(acq_date) as first_detection,
                    MAX(acq_date) as last_detection,
                    COUNT(DISTINCT acq_date) as unique_days
                FROM fires
                WHERE acq_date >= '{start_date}'
                GROUP BY grid_lat, grid_lon
                HAVING COUNT(*) >= {detection_threshold}
            )
            SELECT
                grid_lat,
                grid_lon,
                avg_lat as latitude,
                avg_lon as longitude,
                detection_count,
                unique_days,
                first_detection,
                last_detection,
                ROUND(detection_count::FLOAT / unique_days, 2) as detections_per_day
            FROM gridded_fires
            ORDER BY detection_count DESC
            """

            result = conn.execute(query).fetchdf()
            conn.close()

            if len(result) == 0:
                print(
                    f"No persistent anomalies found with threshold {detection_threshold} over {lookback_days} days"
                )
                return gpd.GeoDataFrame()

            # Convert to GeoDataFrame
            from shapely.geometry import Point

            geometry = [
                Point(lon, lat)
                for lon, lat in zip(result["longitude"], result["latitude"])
            ]

            gdf = gpd.GeoDataFrame(result, geometry=geometry, crs="EPSG:4326")

            # Store for filtering
            self.persistent_locations = gdf

            print(f"Identified {len(gdf)} persistent thermal anomalies:")
            print(f"  - Lookback: {lookback_days} days")
            print(f"  - Detection threshold: {detection_threshold}+")
            print(f"  - Grid size: {grid_size_km}km")

            return gdf

        except Exception as e:
            print(f"Error identifying persistent anomalies: {e}")
            return gpd.GeoDataFrame()

    def filter_fires(
        self,
        fires_gdf: gpd.GeoDataFrame,
        buffer_km: float = 0.5,
        persistent_locations: Optional[gpd.GeoDataFrame] = None,
    ) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
        """
        Filter out fires near persistent anomaly locations.

        Args:
            fires_gdf: GeoDataFrame with current fire detections
            buffer_km: Buffer distance around persistent locations (default 0.5km)
            persistent_locations: Optional pre-computed persistent locations

        Returns:
            Tuple of (filtered_fires, excluded_fires)
        """
        if persistent_locations is None:
            persistent_locations = self.persistent_locations

        if persistent_locations is None or len(persistent_locations) == 0:
            print(
                "No persistent locations to filter. Run identify_persistent_anomalies() first."
            )
            return fires_gdf, gpd.GeoDataFrame()

        # Project to meters for accurate buffering
        fires_proj = fires_gdf.to_crs("EPSG:5070")
        persistent_proj = persistent_locations.to_crs("EPSG:5070")

        # Create buffer around persistent locations
        buffer_m = buffer_km * 1000
        persistent_buffer = persistent_proj.geometry.buffer(buffer_m).unary_union

        # Identify fires within buffer (likely industrial)
        fires_proj["is_industrial"] = fires_proj.geometry.within(persistent_buffer)

        # Split into filtered and excluded
        filtered_fires = (
            fires_proj[~fires_proj["is_industrial"]].to_crs("EPSG:4326").copy()
        )
        excluded_fires = (
            fires_proj[fires_proj["is_industrial"]].to_crs("EPSG:4326").copy()
        )

        # Remove temporary column
        filtered_fires = filtered_fires.drop(columns=["is_industrial"])
        excluded_fires = excluded_fires.drop(columns=["is_industrial"])

        print(f"Filtered {len(excluded_fires)} likely industrial heat sources")
        print(f"Retained {len(filtered_fires)} probable wildland fires")

        return filtered_fires, excluded_fires

    def save_persistent_locations(
        self, output_path: str = "data/static/persistent_anomalies.geojson"
    ):
        """
        Save identified persistent anomalies to file.

        This is static reference data that defines known industrial heat sources.

        Args:
            output_path: Path to save GeoJSON file (default: data/static/)
        """
        if self.persistent_locations is None or len(self.persistent_locations) == 0:
            print(
                "No persistent locations to save. Run identify_persistent_anomalies() first."
            )
            return

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        self.persistent_locations.to_file(output_path, driver="GeoJSON")
        print(
            f"Saved {len(self.persistent_locations)} persistent anomalies to {output_path}"
        )

    def load_persistent_locations(
        self, input_path: str = "data/static/persistent_anomalies.geojson"
    ) -> Optional[gpd.GeoDataFrame]:
        """
        Load previously identified persistent anomalies from file.

        Args:
            input_path: Path to GeoJSON file (default: data/static/)

        Returns:
            GeoDataFrame with persistent locations or None if file not found
        """
        try:
            self.persistent_locations = gpd.read_file(input_path)
            print(
                f"Loaded {len(self.persistent_locations)} persistent anomalies from {input_path}"
            )
            return self.persistent_locations
        except Exception as e:
            print(f"Could not load persistent locations from {input_path}: {e}")
            self.persistent_locations = None
            return None


def create_industrial_exclusion_zone(
    facilities_csv: str, buffer_km: float = 1.0
) -> gpd.GeoDataFrame:
    """
    Create exclusion zones around known industrial facilities.

    Use this function if you have a CSV/database of known industrial facilities
    (steel plants, refineries, power plants, etc.)

    Args:
        facilities_csv: Path to CSV with columns: name, latitude, longitude, type
        buffer_km: Buffer radius around each facility

    Returns:
        GeoDataFrame with buffered exclusion zones

    Example CSV format:
        name,latitude,longitude,type
        "US Steel Gary Works",41.5933,-87.3403,steel_plant
        "BP Whiting Refinery",41.6764,-87.4995,refinery
    """
    from shapely.geometry import Point

    # Load facilities
    df = pd.read_csv(facilities_csv)

    # Create GeoDataFrame
    geometry = [Point(lon, lat) for lon, lat in zip(df["longitude"], df["latitude"])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    # Buffer in projected CRS
    gdf_proj = gdf.to_crs("EPSG:5070")
    gdf_proj["geometry"] = gdf_proj.geometry.buffer(buffer_km * 1000)

    # Convert back
    return gdf_proj.to_crs("EPSG:4326")
