"""
PurpleAir API client for real-time air quality sensor data.

PurpleAir is a crowdsourced air quality monitoring network with 20,000+ sensors
worldwide. It provides real-time PM2.5 (particulate matter) measurements that are
especially useful for tracking wildfire smoke.

API Documentation: https://api.purpleair.com/
API Key: **REQUIRED** - Register at https://develop.purpleair.com/
         As of 2024, PurpleAir requires an API key for all requests.

Rate Limits:
- Free tier: Generous limits for personal/research use
- Recommended: Cache data and use request delays

Data Notes:
- Real-time updates every ~2 minutes
- Consumer-grade sensors (less accurate than regulatory monitors)
- Data can be noisy - sensors may drift or malfunction
- Best for hyperlocal smoke tracking and spatial coverage
- PM2.5 is the primary metric for wildfire smoke
"""

import httpx
from typing import Dict, List, Optional, Any
import geopandas as gpd
from shapely.geometry import Point
from datetime import datetime, timedelta
import time
import pandas as pd


class PurpleAirClient:
    """
    Client for fetching air quality data from PurpleAir sensors.

    Provides methods to fetch real-time PM2.5 measurements from nearby sensors
    with spatial queries and caching.
    """

    BASE_URL = "https://api.purpleair.com/v1/sensors"

    def __init__(self, api_key: str, cache_minutes: float = 10.0):
        """
        Initialize PurpleAir API client.

        Args:
            api_key: PurpleAir API key (required - get from https://develop.purpleair.com/)
            cache_minutes: Minutes to cache responses (default 10.0)

        Raises:
            ValueError: If api_key is None or empty
        """
        if not api_key:
            raise ValueError(
                "PurpleAir API key is required. "
                "Get one at https://develop.purpleair.com/ "
                "and set PURPLEAIR_API_KEY in your .env file"
            )
        self.api_key = api_key
        self.cache_minutes = cache_minutes
        self._cache: Dict[str, tuple[datetime, Any]] = {}

    def _get_cache_key(self, lat: float, lon: float, radius_km: float) -> str:
        """Generate cache key for a location query."""
        return f"{lat:.4f},{lon:.4f},{radius_km}"

    def _is_cache_valid(self, cache_time: datetime) -> bool:
        """Check if cached data is still valid."""
        age = datetime.now() - cache_time
        return age < timedelta(minutes=self.cache_minutes)

    def get_sensors_near_location(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 10.0,
    ) -> List[Dict[str, Any]]:
        """
        Get PurpleAir sensors near a location.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            radius_km: Search radius in kilometers (default 10.0)

        Returns:
            List of sensor dictionaries with PM2.5 and location data:
            [
                {
                    'sensor_index': 12345,
                    'name': 'Sensor Name',
                    'latitude': 37.7749,
                    'longitude': -122.4194,
                    'pm2.5': 15.2,
                    'pm2.5_60min': 14.8,
                    'humidity': 45,
                    'temperature': 68,
                    'confidence': 100,
                    'last_seen': 1697234567
                }
            ]
        """
        # Check cache first
        cache_key = self._get_cache_key(latitude, longitude, radius_km)
        if cache_key in self._cache:
            cache_time, cached_data = self._cache[cache_key]
            if self._is_cache_valid(cache_time):
                return cached_data

        # Prepare API request
        # Convert km to miles for PurpleAir API (it uses miles)
        radius_miles = radius_km * 0.621371

        # Fields to retrieve from API
        fields = [
            "name",
            "latitude",
            "longitude",
            "pm2.5",
            "pm2.5_60minute",
            "humidity",
            "temperature",
            "confidence",
            "last_seen",
        ]

        params = {
            "fields": ",".join(fields),
            "location_type": "0",  # 0 = outside sensors only
            "max_age": "3600",  # Only sensors updated in last hour
        }

        # Add bounding box (more efficient than radius for API)
        # Calculate approximate bounding box (simple lat/lon offset)
        lat_offset = radius_km / 111.0  # 1 degree lat ≈ 111 km
        lon_offset = radius_km / (
            111.0 * abs(float(f"{latitude:.6f}".replace("-", "0.01")))
        )  # Adjust for latitude

        params["nwlat"] = latitude + lat_offset
        params["nwlng"] = longitude - lon_offset
        params["selat"] = latitude - lat_offset
        params["selng"] = longitude + lon_offset

        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        try:
            response = httpx.get(
                self.BASE_URL, params=params, headers=headers, timeout=10.0
            )
            response.raise_for_status()

            data = response.json()

            # Parse response
            sensors = []
            if "data" in data and data["data"]:
                fields_list = data.get("fields", [])
                for sensor_data in data["data"]:
                    sensor_dict = dict(zip(fields_list, sensor_data))
                    sensors.append(sensor_dict)

            # Cache the result
            self._cache[cache_key] = (datetime.now(), sensors)

            return sensors

        except httpx.HTTPError as e:
            print(f"Error fetching PurpleAir data for ({latitude}, {longitude}): {e}")
            return []

    def enrich_fires_with_purpleair(
        self,
        fires_gdf: gpd.GeoDataFrame,
        radius_km: float = 50.0,
        delay_seconds: float = 0.2,
    ) -> gpd.GeoDataFrame:
        """
        Enrich fire data with nearby PurpleAir sensor readings.

        Args:
            fires_gdf: GeoDataFrame with fire detections (must have latitude, longitude)
            radius_km: Search radius in km for nearby sensors (default 50.0 for rural areas)
            delay_seconds: Delay between API calls to respect rate limits (default 0.2)

        Returns:
            GeoDataFrame with added PurpleAir columns:
            - pa_pm25: Current PM2.5 reading (μg/m³)
            - pa_pm25_60min: 60-minute average PM2.5
            - pa_sensor_count: Number of sensors found nearby
            - pa_avg_distance_km: Average distance to sensors
        """
        if fires_gdf.empty:
            return fires_gdf

        fires_enriched = fires_gdf.copy()

        # Initialize new columns
        fires_enriched["pa_pm25"] = None
        fires_enriched["pa_pm25_60min"] = None
        fires_enriched["pa_sensor_count"] = 0
        fires_enriched["pa_avg_distance_km"] = None

        total_fires = len(fires_enriched)
        import sys

        print(
            f"Enriching {total_fires} fires with PurpleAir sensor data...",
            file=sys.stderr,
            flush=True,
        )

        for idx, row in fires_enriched.iterrows():
            lat = row["latitude"]
            lon = row["longitude"]

            # Get nearby sensors
            sensors = self.get_sensors_near_location(lat, lon, radius_km)

            if sensors:
                # Calculate average PM2.5 from nearby sensors
                # Convert to float to ensure numeric types
                pm25_values = [
                    float(s.get("pm2.5")) for s in sensors if s.get("pm2.5") is not None
                ]
                pm25_60min_values = [
                    float(s.get("pm2.5_60minute"))
                    for s in sensors
                    if s.get("pm2.5_60minute") is not None
                ]

                if pm25_values:
                    fires_enriched.at[idx, "pa_pm25"] = float(
                        sum(pm25_values) / len(pm25_values)
                    )
                    fires_enriched.at[idx, "pa_sensor_count"] = int(len(sensors))

                if pm25_60min_values:
                    fires_enriched.at[idx, "pa_pm25_60min"] = float(
                        sum(pm25_60min_values) / len(pm25_60min_values)
                    )

                # Calculate average distance to sensors
                distances = []
                for sensor in sensors:
                    sensor_lat = sensor.get("latitude")
                    sensor_lon = sensor.get("longitude")
                    if sensor_lat and sensor_lon:
                        # Simple distance calculation (approximation)
                        dist = (
                            (lat - sensor_lat) ** 2 + (lon - sensor_lon) ** 2
                        ) ** 0.5 * 111.0
                        distances.append(dist)

                if distances:
                    fires_enriched.at[idx, "pa_avg_distance_km"] = float(
                        sum(distances) / len(distances)
                    )

            # Respect rate limits - delay between requests
            if idx < total_fires - 1:  # Don't delay after last request
                time.sleep(delay_seconds)

            # Progress indicator
            if (idx + 1) % 10 == 0 or (idx + 1) == 1 or (idx + 1) == total_fires:
                print(
                    f"  [{idx + 1}/{total_fires}] Processing PurpleAir data...",
                    file=sys.stderr,
                    flush=True,
                )

        # Count how many fires got PurpleAir data
        pa_count = fires_enriched["pa_pm25"].notna().sum()
        print(
            f"✓ Added PurpleAir data to {pa_count}/{total_fires} fires",
            file=sys.stderr,
            flush=True,
        )

        return fires_enriched

    def get_sensors_for_heatmap(
        self, bbox: tuple[float, float, float, float]
    ) -> gpd.GeoDataFrame:
        """
        Get all PurpleAir sensors in a bounding box for heatmap visualization.

        Args:
            bbox: Bounding box (west, south, east, north) in WGS84 decimal degrees

        Returns:
            GeoDataFrame with sensor locations and PM2.5 readings suitable for heatmap
        """
        west, south, east, north = bbox

        # Fields to retrieve
        fields = [
            "name",
            "latitude",
            "longitude",
            "pm2.5",
            "pm2.5_60minute",
            "humidity",
            "temperature",
            "confidence",
            "last_seen",
        ]

        params = {
            "fields": ",".join(fields),
            "location_type": "0",  # Outside sensors only
            "max_age": "3600",  # Last hour
            "nwlat": north,
            "nwlng": west,
            "selat": south,
            "selng": east,
        }

        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        try:
            response = httpx.get(
                self.BASE_URL, params=params, headers=headers, timeout=10.0
            )
            response.raise_for_status()

            data = response.json()

            # Parse sensors into GeoDataFrame
            sensors = []
            if "data" in data and data["data"]:
                fields_list = data.get("fields", [])
                for sensor_data in data["data"]:
                    sensor_dict = dict(zip(fields_list, sensor_data))
                    sensors.append(sensor_dict)

            if not sensors:
                print("No PurpleAir sensors found in bounding box")
                return gpd.GeoDataFrame()

            # Create GeoDataFrame
            df = pd.DataFrame(sensors)
            geometry = [
                Point(lon, lat) for lon, lat in zip(df["longitude"], df["latitude"])
            ]
            gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

            print(f"Found {len(gdf)} PurpleAir sensors in region")
            return gdf

        except httpx.HTTPError as e:
            print(f"Error fetching PurpleAir sensors for bbox {bbox}: {e}")
            return gpd.GeoDataFrame()
