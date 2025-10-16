# NOAA Weather Integration

## Overview

The wildfire risk monitoring system incorporates real-time weather data from NOAA's National Weather Service (NWS) API to enhance fire risk assessments.

**Current Implementation:**
- **Tier 1:** NOAA NWS API (Real-time) - Implemented
- **Tier 2:** Enhanced Risk Model with GHCN-Daily (Recent History) - Future enhancement
- **Tier 3:** Advanced Analysis (Multi-day forecasts + Historical patterns) - Future enhancement

## Real-time Weather Integration

### What's Implemented

**`src/ingestion/noaa_client.py`** - NOAA NWS API Client
- Fetches real-time weather conditions for any lat/lon coordinate
- Retrieves fire-specific indices (Fire Danger Index, Red Flag Threat Index)
- Enriches fire data with current weather conditions
- No API key required, free public service

**`src/analysis/risk_calculator.py`** - Enhanced Risk Calculation
- `calculate_enhanced_risk()` method incorporates weather data
- Adjusted weighting system when weather data is available
- Falls back to base calculation if weather unavailable

### Weather Data Retrieved

For each fire location, the system fetches:

| Field | Description | How It Affects Risk |
|-------|-------------|---------------------|
| **Temperature** | Current temperature (°C) | Indirectly via fire indices |
| **Relative Humidity** | Humidity percentage (0-100%) | Lower = Higher risk (15% weight) |
| **Wind Speed** | Wind speed (km/h) | Higher = Higher risk (10% weight) |
| **Wind Direction** | Wind direction (degrees) | Future: Spread prediction |
| **Precipitation Probability** | Chance of rain (0-100%) | Lower = Higher risk (5% weight) |
| **Fire Danger Index** | NOAA grassland fire danger (0-100) | Direct risk indicator (5% weight) |
| **Red Flag Threat Index** | Red flag warning threat level | Future: Alert prioritization |

### Risk Calculation Models

#### Base Model (Satellite Data Only)
Used when weather data is unavailable:
- **30%** Brightness (fire intensity)
- **20%** Confidence (detection confidence)
- **30%** FRP (Fire Radiative Power)
- **20%** Day/Night (time of detection)

#### Enhanced Model (With Weather Data)
Used when NOAA weather data is available:
- **20%** Brightness (fire intensity)
- **15%** Confidence (detection confidence)
- **20%** FRP (Fire Radiative Power)
- **10%** Day/Night (time of detection)
- **15%** Humidity (inverted: low humidity = high risk)
- **10%** Wind Speed (high wind = high risk)
- **5%** Precipitation Probability (inverted: low precip = high risk)
- **5%** Fire Danger Index (NOAA's fire danger metric)

### How It Works

```python
from src.ingestion.noaa_client import NOAAWeatherClient
from src.analysis.risk_calculator import FireRiskCalculator

# 1. Fetch fires from FIRMS
fires = firms_client.get_continental_us_fires(days=1)

# 2. Enrich with weather data (optional)
with NOAAWeatherClient() as noaa:
    fires_with_weather = noaa.enrich_fires_with_weather(fires)

# 3. Calculate enhanced risk
calculator = FireRiskCalculator(use_weather=True)
fires_with_risk = calculator.calculate_enhanced_risk(fires_with_weather)
```

### API Details

**Base URL:** `https://api.weather.gov`

**Key Endpoints Used:**
1. `/points/{lat},{lon}` - Get grid coordinates for location
2. `/gridpoints/{wfo}/{x},{y}` - Get forecast data including fire indices
3. `/stations/{id}/observations/latest` - Get station observations

**Rate Limits:**
- Not publicly documented, but "generous"
- System automatically handles rate limit errors
- For large datasets, consider caching or batching

**Requirements:**
- Must include User-Agent header (automatically set)
- No API key required
- Free for all uses

### Performance Considerations

**Current Implementation:**
- Sequential API calls (one per fire location)
- ~1-2 seconds per fire location
- For 100 fires: ~2-3 minutes total

**Optimization Strategies:**
1. **Caching:** Cache weather data by grid coordinates (multiple fires may share grids)
2. **Batching:** Group fires by grid cell to reduce API calls
3. **Sampling:** For dense fire clusters, sample representative points
4. **Async:** Use async HTTP for parallel requests (future enhancement)

### Testing

Run the test script to verify NOAA integration:

```bash
uv run python test_noaa_integration.py
```

Expected output:
- Successfully retrieves weather for test locations
- Shows temperature, humidity, wind, precipitation data
- Displays fire danger and red flag indices when available

### Usage in ETL Flow

**Option 1: Always use weather (slower but more accurate)**
```python
# In flows/etl_flow.py
@task
def enrich_with_weather(fires_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Enrich fires with NOAA weather data."""
    with NOAAWeatherClient() as noaa:
        return noaa.enrich_fires_with_weather(fires_gdf)

# Then in the flow:
fires = fetch_active_fires(api_key, days_back)
fires_with_weather = enrich_with_weather(fires)
fires_with_risk = calculate_risk_scores(fires_with_weather)
```

**Option 2: Weather on demand (faster, use when needed)**
```python
# Keep current flow as-is for speed
# Add separate analysis script for detailed weather-enhanced assessment
```

### Limitations

1. **Coverage:** NWS API primarily covers US and territories
2. **Granularity:** Weather data is grid-based (~2.5km resolution)
3. **Latency:** Real-time data updated every 1-6 hours depending on location
4. **Performance:** Sequential API calls can be slow for large datasets
5. **Availability:** Some fire-specific indices may not be available in all regions

### Future Enhancements (Tier 2 & 3)

**Tier 2: Historical Weather Context**
- NOAA GHCN-Daily for recent precipitation history
- Drought indices (Palmer Drought Index, PDSI)
- Multi-day temperature/humidity trends
- Requires separate API key from NCDC

**Tier 3: Advanced Analytics**
- 7-day weather forecasts for spread prediction
- Seasonal fire risk patterns
- Climate indices (El Niño/La Niña effects)
- Integration with vegetation/fuel moisture models

## References

- [NOAA NWS API Documentation](https://www.weather.gov/documentation/services-web-api)
- [NWS API GitHub](https://github.com/weather-gov/api)
- [OpenAPI Specification](https://api.weather.gov/openapi.json)
- [Fire Weather Services](https://www.weather.gov/fire/)

## Examples

### Example 1: Get Weather for Single Fire

```python
from src.ingestion.noaa_client import NOAAWeatherClient

with NOAAWeatherClient() as client:
    weather = client.get_fire_weather_for_point(34.05, -118.24)
    
    if weather:
        print(f"Temperature: {weather['temperature_c']}°C")
        print(f"Humidity: {weather['relative_humidity']}%")
        print(f"Wind: {weather['wind_speed_kmh']} km/h")
        print(f"Fire Danger: {weather['fire_danger_index']}")
```

### Example 2: Enhanced Risk Calculation

```python
from src.analysis.risk_calculator import FireRiskCalculator

# With weather data
calculator = FireRiskCalculator(use_weather=True)
enhanced_risk = calculator.calculate_enhanced_risk(fires_with_weather)

# Without weather data (falls back to base model)
base_risk = calculator.calculate_enhanced_risk(fires_without_weather)
```

### Example 3: Compare Risk Scores

```python
# Calculate both base and enhanced risk
base_calc = FireRiskCalculator(use_weather=False)
enhanced_calc = FireRiskCalculator(use_weather=True)

base_scores = base_calc.calculate_base_risk(fires)
enhanced_scores = enhanced_calc.calculate_enhanced_risk(fires_with_weather)

# Compare
comparison = pd.DataFrame({
    'fire_id': base_scores['fire_id'],
    'base_risk': base_scores['risk_score'],
    'enhanced_risk': enhanced_scores['risk_score'],
    'difference': enhanced_scores['risk_score'] - base_scores['risk_score']
})
```

## Troubleshooting

**Issue:** Weather data not available for location
- **Cause:** Location outside NWS coverage area or data temporarily unavailable
- **Solution:** System automatically falls back to base risk calculation

**Issue:** Slow performance with many fires
- **Cause:** Sequential API calls (1-2 seconds each)
- **Solution:** Consider implementing caching or batching (see Performance Considerations)

**Issue:** `HTTPError: 500 Internal Server Error`
- **Cause:** NWS API temporary outage
- **Solution:** Implement retry logic or skip weather enrichment for this run

**Issue:** Fire danger index always `None`
- **Cause:** Not all grid locations provide fire-specific indices
- **Solution:** Normal behavior - risk calculation handles missing data gracefully
