# src/ingestion/noaa_client.py
"""Client for NOAA National Weather Service API."""

import httpx
from typing import Any, Dict, Optional, Tuple
import pandas as pd
import geopandas as gpd
from datetime import datetime


class NOAAWeatherClient:
    """Client for NOAA NWS API to fetch real-time weather data."""

    BASE_URL = "https://api.weather.gov"

    # User-Agent is required by NWS API
    HEADERS = {
        "User-Agent": "(WildfireRiskMonitor, contact@example.com)",
        "Accept": "application/geo+json",
    }

    def __init__(self, timeout: float = 30.0):
        """
        Initialize NOAA Weather client.

        Args:
            timeout: Request timeout in seconds
        """
        self.client = httpx.Client(
            timeout=timeout, headers=self.HEADERS, follow_redirects=True
        )

    def get_point_metadata(self, latitude: float, longitude: float) -> dict[str, Any]:
        """
        Get metadata for a geographic point.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees

        Returns:
            Dictionary with point metadata including forecast URLs and grid info
        """
        url = f"{self.BASE_URL}/points/{latitude:.4f},{longitude:.4f}"
        response = self.client.get(url)
        response.raise_for_status()
        return response.json()

    def get_gridpoint_forecast(
        self, wfo: str, grid_x: int, grid_y: int
    ) -> dict[str, Any]:
        """
        Get detailed gridpoint forecast data including fire weather indices.

        Args:
            wfo: Weather Forecast Office identifier (e.g., 'TOP')
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate

        Returns:
            Dictionary with forecast data including temperature, humidity, wind,
            grasslandFireDangerIndex, and redFlagThreatIndex
        """
        url = f"{self.BASE_URL}/gridpoints/{wfo}/{grid_x},{grid_y}"
        response = self.client.get(url)
        response.raise_for_status()
        return response.json()

    def get_station_observation(self, station_id: str) -> dict[str, Any]:
        """
        Get latest observation from a weather station.

        Args:
            station_id: Station identifier (e.g., 'KTOPK')

        Returns:
            Dictionary with current conditions including temperature, humidity, wind
        """
        url = f"{self.BASE_URL}/stations/{station_id}/observations/latest"
        response = self.client.get(url)
        response.raise_for_status()
        return response.json()

    def get_fire_weather_for_point(
        self, latitude: float, longitude: float
    ) -> dict[str, Any] | None:
        """
        Get fire-relevant weather data for a specific point.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees

        Returns:
            Dictionary with fire weather data or None if unavailable
        """
        try:
            # Step 1: Get point metadata to find grid coordinates
            point_data = self.get_point_metadata(latitude, longitude)
            properties = point_data.get("properties", {})

            # Extract grid information
            grid_id = properties.get("gridId")
            grid_x = properties.get("gridX")
            grid_y = properties.get("gridY")

            if not all([grid_id, grid_x, grid_y]):
                return None

            # Step 2: Get gridpoint forecast with fire indices
            forecast_data = self.get_gridpoint_forecast(grid_id, grid_x, grid_y)
            properties = forecast_data.get("properties", {})

            # Extract fire-relevant data
            result = {
                "latitude": latitude,
                "longitude": longitude,
                "grid_id": grid_id,
                "grid_x": grid_x,
                "grid_y": grid_y,
                "update_time": properties.get("updateTime"),
            }

            # Extract current/first values from time series data
            def get_current_value(data_dict):
                """Extract the first (current) value from a time series."""
                if not data_dict or "values" not in data_dict:
                    return None
                values = data_dict["values"]
                if not values or len(values) == 0:
                    return None
                return values[0].get("value")

            # Temperature (convert from Celsius if needed)
            temp_data = properties.get("temperature", {})
            result["temperature_c"] = get_current_value(temp_data)

            # Relative Humidity
            humidity_data = properties.get("relativeHumidity", {})
            result["relative_humidity"] = get_current_value(humidity_data)

            # Wind Speed (convert from km/h if needed)
            wind_speed_data = properties.get("windSpeed", {})
            result["wind_speed_kmh"] = get_current_value(wind_speed_data)

            # Wind Direction
            wind_dir_data = properties.get("windDirection", {})
            result["wind_direction_deg"] = get_current_value(wind_dir_data)

            # Precipitation Probability
            precip_data = properties.get("probabilityOfPrecipitation", {})
            result["precip_probability"] = get_current_value(precip_data)

            # Fire Weather Indices (if available)
            fire_danger_data = properties.get("grasslandFireDangerIndex", {})
            result["fire_danger_index"] = get_current_value(fire_danger_data)

            red_flag_data = properties.get("redFlagThreatIndex", {})
            result["red_flag_index"] = get_current_value(red_flag_data)

            return result

        except (httpx.HTTPError, KeyError, ValueError) as e:
            # Return None if data unavailable for this location
            return None

    def enrich_fires_with_weather(
        self, fires_gdf: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """
        Enrich fire data with current weather conditions from NOAA.

        Args:
            fires_gdf: GeoDataFrame with fire locations

        Returns:
            GeoDataFrame with added weather columns
        """
        fires_gdf = fires_gdf.copy()

        # Initialize weather columns
        weather_columns = [
            "temperature_c",
            "relative_humidity",
            "wind_speed_kmh",
            "wind_direction_deg",
            "precip_probability",
            "fire_danger_index",
            "red_flag_index",
        ]

        for col in weather_columns:
            fires_gdf[col] = None

        # Fetch weather for each fire location
        # Note: This can be slow for many fires - consider batching/caching
        for idx, row in fires_gdf.iterrows():
            weather = self.get_fire_weather_for_point(row["latitude"], row["longitude"])

            if weather:
                for col in weather_columns:
                    if col in weather and weather[col] is not None:
                        fires_gdf.at[idx, col] = weather[col]  # pyright: ignore

        return fires_gdf

    def get_weather_summary_for_bbox(
        self, bbox: Tuple[float, float, float, float], sample_points: int = 5
    ) -> pd.DataFrame:
        """
        Get weather summary for a bounding box by sampling points.

        Args:
            bbox: Bounding box (west, south, east, north)
            sample_points: Number of points to sample in each direction

        Returns:
            DataFrame with weather conditions across the region
        """
        west, south, east, north = bbox

        # Create sample grid
        import numpy as np

        lats = np.linspace(south, north, sample_points)
        lons = np.linspace(west, east, sample_points)

        results = []
        for lat in lats:
            for lon in lons:
                weather = self.get_fire_weather_for_point(lat, lon)
                if weather:
                    results.append(weather)

        return pd.DataFrame(results)

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
