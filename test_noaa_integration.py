"""Test script for NOAA weather integration."""

from src.ingestion.noaa_client import NOAAWeatherClient
import pandas as pd


def test_point_weather():
    """Test getting weather for a single point."""
    print("=" * 80)
    print("Testing NOAA NWS API Integration")
    print("=" * 80)

    # Test locations (various fire-prone areas)
    test_locations = [
        (39.7456, -97.0892, "Kansas (Central US)"),
        (34.0522, -118.2437, "Los Angeles, CA"),
        (45.5231, -122.6765, "Portland, OR"),
    ]

    with NOAAWeatherClient() as client:
        for lat, lon, name in test_locations:
            print(f"\n📍 Testing location: {name} ({lat}, {lon})")
            print("-" * 80)

            try:
                weather = client.get_fire_weather_for_point(lat, lon)

                if weather:
                    print(f"✓ Successfully retrieved weather data")
                    print(
                        f"  Grid: {weather.get('grid_id')} ({weather.get('grid_x')}, {weather.get('grid_y')})"
                    )
                    print(f"  Temperature: {weather.get('temperature_c')}°C")
                    print(f"  Humidity: {weather.get('relative_humidity')}%")
                    print(f"  Wind Speed: {weather.get('wind_speed_kmh')} km/h")
                    print(f"  Wind Direction: {weather.get('wind_direction_deg')}°")
                    print(f"  Precip Probability: {weather.get('precip_probability')}%")

                    fire_danger = weather.get("fire_danger_index")
                    red_flag = weather.get("red_flag_index")

                    if fire_danger is not None:
                        print(f"  🔥 Fire Danger Index: {fire_danger}")
                    if red_flag is not None:
                        print(f"  🚩 Red Flag Threat Index: {red_flag}")
                else:
                    print(f"✗ No weather data available for this location")

            except Exception as e:
                print(f"✗ Error: {e}")


def test_fire_enrichment():
    """Test enriching fire data with weather."""
    print("\n" + "=" * 80)
    print("Testing Fire Data Enrichment with Weather")
    print("=" * 80)

    # Create sample fire data
    import geopandas as gpd
    from shapely.geometry import Point

    sample_fires = pd.DataFrame(
        {
            "latitude": [34.0522, 36.7783, 37.7749],
            "longitude": [-118.2437, -119.4179, -122.4194],
            "brightness": [350, 380, 340],
            "frp": [25.5, 45.2, 18.3],
            "acq_date": ["2025-10-12", "2025-10-12", "2025-10-12"],
        }
    )

    # Convert to GeoDataFrame
    geometry = [Point(xy) for xy in zip(sample_fires.longitude, sample_fires.latitude)]
    fires_gdf = gpd.GeoDataFrame(sample_fires, geometry=geometry, crs="EPSG:4326")

    print(f"\nEnriching {len(fires_gdf)} sample fires with weather data...")
    print("(This may take 30-60 seconds due to API rate limits)")

    with NOAAWeatherClient() as client:
        try:
            enriched = client.enrich_fires_with_weather(fires_gdf)

            print(f"\n✓ Successfully enriched fire data")
            print(f"\nEnriched columns:")
            weather_cols = [
                "temperature_c",
                "relative_humidity",
                "wind_speed_kmh",
                "precip_probability",
                "fire_danger_index",
            ]

            for col in weather_cols:
                if col in enriched.columns:
                    non_null = enriched[col].notna().sum()
                    print(f"  {col}: {non_null}/{len(enriched)} fires have data")

            # Show sample
            print(f"\nSample enriched fire data:")
            print(
                enriched[
                    [
                        "latitude",
                        "longitude",
                        "temperature_c",
                        "relative_humidity",
                        "wind_speed_kmh",
                    ]
                ].head()
            )

        except Exception as e:
            print(f"✗ Error during enrichment: {e}")


if __name__ == "__main__":
    test_point_weather()

    # Uncomment to test fire enrichment (slower due to multiple API calls)
    # test_fire_enrichment()

    print("\n" + "=" * 80)
    print("✓ NOAA Integration Testing Complete")
    print("=" * 80)
