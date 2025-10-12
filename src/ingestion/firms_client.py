# src/ingestion/firms_client.py
import httpx
from datetime import datetime, timedelta
from typing import Dict, List
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point


class FIRMSClient:
    """Client for NASA FIRMS active fire data."""

    BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)

    def get_active_fires(
        self,
        bbox: tuple,  # (west, south, east, north)
        days: int = 1,
        source: str = "VIIRS_NOAA20_NRT",  # or MODIS_NRT
    ) -> gpd.GeoDataFrame:
        """
        Fetch active fire detections.

        Args:
            bbox: Bounding box (west, south, east, north) in WGS84
            days: Number of days to look back (1-10)
            source: Satellite source (VIIRS_NOAA20_NRT or MODIS_NRT)

        Returns:
            GeoDataFrame with fire detections
        """
        url = f"{self.BASE_URL}/{self.api_key}/{source}/{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}/{days}"

        response = self.client.get(url)
        response.raise_for_status()

        # Parse CSV response
        from io import StringIO

        df = pd.read_csv(StringIO(response.text))

        if df.empty:
            return gpd.GeoDataFrame()

        # Convert to GeoDataFrame
        geometry = [Point(xy) for xy in zip(df.longitude, df.latitude)]
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

        # Add timestamp
        gdf["acq_datetime"] = pd.to_datetime(
            gdf["acq_date"] + " " + gdf["acq_time"].astype(str).str.zfill(4),
            format="%Y-%m-%d %H%M",
        )

        return gdf

    def get_continental_us_fires(self, days: int = 1) -> gpd.GeoDataFrame:
        """Get all fires in continental US."""
        # Continental US bounding box
        bbox = (-125, 24, -66, 49)
        return self.get_active_fires(bbox, days)
