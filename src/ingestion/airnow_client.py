"""
EPA AirNow API client for real-time air quality data.

The AirNow API provides real-time air quality observations from 2,500+ monitoring
stations across the United States, Canada, and Mexico. Data includes AQI (Air
Quality Index) and pollutant concentrations like PM2.5, PM10, and Ozone.

API Documentation: https://docs.airnowapi.org/
API Key: Register at https://docs.airnowapi.org/account/request/

Rate Limits:
- 500 requests per hour
- Observations updated hourly
- Recommended: Cache data and update no more than twice per hour

Data Notes:
- Data is preliminary and not fully validated
- Subject to change and should not be used for regulatory purposes
- Suitable for informational and fire risk assessment purposes
"""

import httpx
from typing import Dict, List, Optional, Any
import geopandas as gpd
from datetime import datetime, timedelta
import time


class AirNowClient:
    """
    Client for fetching air quality data from EPA AirNow API.

    Provides methods to fetch current air quality observations by location
    (latitude/longitude) with caching to respect API rate limits.
    """

    BASE_URL = "https://www.airnowapi.org/aq"

    def __init__(self, api_key: str, cache_hours: float = 1.0):
        """
        Initialize AirNow API client.

        Args:
            api_key: AirNow API key (get from https://docs.airnowapi.org/)
            cache_hours: Hours to cache responses (default 1.0, respects hourly updates)
        """
        self.api_key = api_key
        self.cache_hours = cache_hours
        self._cache: Dict[str, tuple[datetime, Any]] = {}

    def _get_cache_key(self, lat: float, lon: float, distance: int) -> str:
        """Generate cache key for a location query."""
        return f"{lat:.4f},{lon:.4f},{distance}"

    def _is_cache_valid(self, cache_time: datetime) -> bool:
        """Check if cached data is still valid."""
        age = datetime.now() - cache_time
        return age < timedelta(hours=self.cache_hours)

    def get_current_observation(
        self,
        latitude: float,
        longitude: float,
        distance: int = 25,
    ) -> Optional[Dict[str, Any]]:
        """
        Get current air quality observation for a location.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            distance: Search radius in miles (default 25)

        Returns:
            Dictionary with air quality data or None if no data available:
            {
                'DateObserved': '2025-10-14',
                'HourObserved': 12,
                'LocalTimeZone': 'MST',
                'ReportingArea': 'Phoenix',
                'StateCode': 'AZ',
                'Latitude': 33.4484,
                'Longitude': -112.0740,
                'ParameterName': 'PM2.5',
                'AQI': 42,
                'Category': {'Number': 1, 'Name': 'Good'}
            }
        """
        # Check cache first
        cache_key = self._get_cache_key(latitude, longitude, distance)
        if cache_key in self._cache:
            cache_time, cached_data = self._cache[cache_key]
            if self._is_cache_valid(cache_time):
                return cached_data

        # Make API request
        url = f"{self.BASE_URL}/observation/latLong/current/"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "distance": distance,
            "format": "application/json",
            "API_KEY": self.api_key,
        }

        # Retry logic for rate limiting
        max_retries = 3
        retry_delay = 2.0  # Start with 2 seconds

        for attempt in range(max_retries):
            try:
                response = httpx.get(url, params=params, timeout=10.0)
                response.raise_for_status()

                data = response.json()

                # API returns a list of observations (one per parameter)
                # Return the first observation if available
                result = data[0] if isinstance(data, list) and len(data) > 0 else None

                # Cache the result
                self._cache[cache_key] = (datetime.now(), result)

                return result

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit exceeded
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2**attempt)  # Exponential backoff
                        print(
                            f"Rate limited (429). Waiting {wait_time:.1f}s before retry {attempt + 1}/{max_retries}..."
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        print(
                            f"Rate limit exceeded after {max_retries} retries for ({latitude}, {longitude})"
                        )
                        return None
                else:
                    print(
                        f"HTTP error fetching AirNow data for ({latitude}, {longitude}): {e}"
                    )
                    return None
            except httpx.HTTPError as e:
                print(f"Error fetching AirNow data for ({latitude}, {longitude}): {e}")
                return None

        return None

    def enrich_fires_with_aqi(
        self,
        fires_gdf: gpd.GeoDataFrame,
        distance: int = 25,
        delay_seconds: float = 0.5,
    ) -> gpd.GeoDataFrame:
        """
        Enrich fire data with current AQI from nearby air quality monitors.

        Args:
            fires_gdf: GeoDataFrame with fire detections (must have latitude, longitude)
            distance: Search radius in miles for nearby monitors (default 25)
            delay_seconds: Delay between API calls to respect rate limits (default 0.5)

        Returns:
            GeoDataFrame with added AQI columns:
            - aqi: Air Quality Index value
            - aqi_parameter: Pollutant measured (PM2.5, PM10, Ozone)
            - aqi_category: Category name (Good, Moderate, Unhealthy, etc.)
            - aqi_category_number: Category number (1-6)
        """
        if fires_gdf.empty:
            return fires_gdf

        fires_enriched = fires_gdf.copy()

        # Initialize new columns
        fires_enriched["aqi"] = None
        fires_enriched["aqi_parameter"] = None
        fires_enriched["aqi_category"] = None
        fires_enriched["aqi_category_number"] = None

        total_fires = len(fires_enriched)
        import sys

        print(
            f"Enriching {total_fires} fires with AirNow AQI data...",
            file=sys.stderr,
            flush=True,
        )

        for idx, row in fires_enriched.iterrows():
            lat = row["latitude"]
            lon = row["longitude"]

            # Get AQI data
            aqi_data = self.get_current_observation(lat, lon, distance)

            if aqi_data:
                # Ensure numeric types for AQI values
                aqi_value = aqi_data.get("AQI")
                fires_enriched.at[idx, "aqi"] = (
                    float(aqi_value) if aqi_value is not None else None
                )
                fires_enriched.at[idx, "aqi_parameter"] = aqi_data.get("ParameterName")

                category = aqi_data.get("Category", {})
                fires_enriched.at[idx, "aqi_category"] = category.get("Name")
                cat_number = category.get("Number")
                fires_enriched.at[idx, "aqi_category_number"] = (
                    int(cat_number) if cat_number is not None else None
                )

            # Respect rate limits - delay between requests
            if idx < total_fires - 1:  # Don't delay after last request
                time.sleep(delay_seconds)

            # Progress indicator
            if (idx + 1) % 10 == 0 or (idx + 1) == 1 or (idx + 1) == total_fires:
                print(
                    f"  [{idx + 1}/{total_fires}] Processing AQI data...",
                    file=sys.stderr,
                    flush=True,
                )

        # Count how many fires got AQI data
        aqi_count = fires_enriched["aqi"].notna().sum()
        print(
            f"✓ Added AQI data to {aqi_count}/{total_fires} fires",
            file=sys.stderr,
            flush=True,
        )

        return fires_enriched

    def get_aqi_forecast(
        self,
        latitude: float,
        longitude: float,
        date: Optional[str] = None,
        distance: int = 25,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get AQI forecast for a location.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            date: Forecast date in YYYY-MM-DD format (default: today)
            distance: Search radius in miles (default 25)

        Returns:
            List of forecast dictionaries or None if no data available
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        url = f"{self.BASE_URL}/forecast/latLong/"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "date": date,
            "distance": distance,
            "format": "application/json",
            "API_KEY": self.api_key,
        }

        try:
            response = httpx.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Error fetching AirNow forecast for ({latitude}, {longitude}): {e}")
            return None
