# Industrial Heat Source Filtering

## Overview

NASA FIRMS detects all thermal anomalies from satellites, including not just wildfires but also:
- Steel plants and foundries
- Oil refineries and petrochemical facilities
- Gas flares
- Cement plants
- Power plants
- Waste incinerators
- Other persistent industrial heat sources

This module filters out these false positives to focus on actual wildland fires.

---

## How It Works

### Temporal Persistence Analysis

The filtering uses a **grid-based temporal persistence approach** inspired by NASA's Static Thermal Anomalies (STA) layer:

1. **Grid Analysis (400m cells)**
   - Fire detections are summarized on a 400m grid
   - Each grid cell is analyzed over a 30-day lookback period

2. **Persistence Detection**
   - Grid cells with 5+ detections are flagged as "persistent"
   - Industrial sources show up daily/nightly, wildfires do not

3. **Spatial Filtering**
   - Current fire detections within 500m of persistent locations are excluded
   - Remaining fires are considered probable wildland fires

### Key Parameters

```python
lookback_days=30           # Analyze 30 days of history
detection_threshold=5      # 5+ detections = persistent
grid_size_km=0.4          # 400m grid cells
buffer_km=0.5             # 500m exclusion radius
```

---

## Usage

### Automatic Filtering in ETL Flow

The simplest approach - filtering runs automatically:

```python
from flows.etl_flow import wildfire_etl_flow

# Filter industrial sources by default
wildfire_etl_flow(
    days_back=2,
    use_weather=True,
    filter_industrial=True  # Default: True
)
```

**Results:**
- Persistent anomalies identified from historical data
- Current fires near these locations excluded
- Filtered fires used for risk analysis and visualization

### Manual Analysis

Identify and review persistent anomalies before filtering:

```bash
# Run analysis script
uv run python scripts/analyze_industrial_sources.py
```

**Output:**
```
Identified 69 persistent thermal anomalies:
  - Lookback: 30 days
  - Detection threshold: 5+
  - Grid size: 0.4km

Top 10 by detection count:
 latitude  longitude  detection_count  unique_days  detections_per_day
43.281366 -79.808087               37            2                18.5
29.731501 -95.079475               34            2                17.0
...

Current fire count: 1423
After filtering: 1267 fires (excluded 156 near persistent sources)
```

**Files Created:**
- `data/static/persistent_anomalies.geojson` - Static reference data for mapping
- `data/static/persistent_anomalies.csv` - Spreadsheet review
- `data/processed/excluded_industrial_fires.geojson` - Filtered detections (per run)

### Programmatic Usage

Use the filter in your own scripts:

```python
from src.filters.industrial_filter import IndustrialHeatFilter
import geopandas as gpd

# Initialize filter
filter_obj = IndustrialHeatFilter("data/wildfire.duckdb")

# Identify persistent anomalies
persistent = filter_obj.identify_persistent_anomalies(
    lookback_days=30,
    detection_threshold=5,
    grid_size_km=0.4
)

# Load current fires
fires = gpd.read_file("data/processed/active_fires.geojson")

# Filter out industrial sources
filtered_fires, excluded_fires = filter_obj.filter_fires(
    fires, 
    buffer_km=0.5,
    persistent_locations=persistent
)

print(f"Kept: {len(filtered_fires)} fires")
print(f"Excluded: {len(excluded_fires)} industrial sources")
```

---

## Validation and Review

### Visual Review in Kepler.gl

1. Load three layers:
   - `data/processed/active_fires.geojson` (current fires)
   - `data/static/persistent_anomalies.geojson` (industrial locations - static)
   - `data/processed/excluded_industrial_fires.geojson` (filtered fires - per run)

2. Style persistent anomalies:
   - Color: Purple/Gray (distinct from fire colors)
   - Size: Large circles to see overlap
   - Opacity: 50%

3. Check that excluded fires overlap with persistent anomalies

### Satellite Imagery Verification

The analysis script provides Google Maps URLs for top persistent locations:

```
Location: 43.2814, -79.8081
Detections: 37 over 2 days (18.50/day)
View: https://www.google.com/maps/@43.2814,-79.8081,15z
```

**What to look for:**
- Large industrial facilities
- Smokestacks or cooling towers
- Gas flare structures
- Rail yards with visible steel/metal processing
- Refineries with complex pipe networks

### Example Verified Locations

From our test data, these persistent anomalies correspond to known industrial sites:

| Latitude | Longitude | Detections/Day | Likely Facility |
|----------|-----------|----------------|-----------------|
| 43.28 | -79.81 | 18.5 | Hamilton Steel Mills (Stelco/ArcelorMittal) |
| 29.73 | -95.08 | 17.0 | Houston Petrochemical Complex |
| 41.65 | -87.40 | 33.0 | South Chicago Steel District |
| 41.46 | -81.68 | 14.0 | Cleveland Manufacturing |
| 42.81 | -80.10 | 13.0 | Nanticoke Steel Plant |

---

## Tuning Parameters

### Detection Threshold

**Higher threshold (7-10):** More conservative, fewer false positives
- Use when you have abundant historical data
- Filters only very persistent sources
- Risk: May miss some industrial facilities

**Lower threshold (3-4):** More aggressive, catches more industrial
- Use with limited historical data
- Filters moderately persistent sources
- Risk: May exclude legitimate multi-day wildfires

**Default (5):** Balanced approach
- Good for most use cases
- Matches NASA's methodology

### Lookback Period

**Longer (60-90 days):** Better for seasonal operations
- Captures facilities that operate intermittently
- Requires longer historical database
- More robust identification

**Shorter (14-30 days):** Faster, requires less data
- Good for getting started
- May miss seasonal facilities
- Default: 30 days

**Very short (7 days):** Quick test
- Useful for initial testing
- Will miss many industrial sources
- Not recommended for production

### Buffer Distance

**Larger buffer (1-2km):** More aggressive filtering
- Catches nearby detections
- Risk: May exclude legitimate fires near facilities
- Use in dense industrial areas

**Smaller buffer (0.3-0.5km):** Precise filtering
- Only excludes very close detections
- Better for mixed urban/wildland areas
- Default: 0.5km (500m)

### Grid Size

**Larger grid (1km+):** Coarse spatial grouping
- Faster processing
- May group unrelated fires
- Not recommended

**Smaller grid (0.2-0.4km):** Fine spatial resolution
- More precise location identification
- Default: 0.4km matches NASA STA
- Recommended for most use cases

---

## Performance Impact

### Database Requirements

- Requires historical fire data in DuckDB
- Minimum: 7-14 days of data
- Recommended: 30+ days
- Query time: 1-2 seconds for 30 days

### ETL Flow Impact

**Without filtering:**
```
Fetch: 1.5s
Process: 0.5s
Save: 0.3s
Total: 2.3s (1423 fires)
```

**With filtering:**
```
Fetch: 1.5s
Filter: 2.0s (identify + filter)
Process: 0.5s
Save: 0.3s
Total: 4.3s (1267 fires)
```

**Trade-off:** +2 seconds processing time, -11% false positive fires

---

## Limitations

### 1. Requires Historical Data

- Cannot filter on first run (no history)
- Need 7-14 days minimum for reasonable results
- More history = better identification

**Solution:** Run ETL without filtering for first 2 weeks, then enable

### 2. New Industrial Facilities

- Recently started operations won't be flagged
- Takes time to build up detection history

**Solution:** Use lower detection threshold (3-4) to catch faster

### 3. Long-Duration Wildfires

- Large fires burning for weeks could be flagged as "persistent"
- Risk: Legitimate fire excluded

**Solution:** 
- Review excluded fires manually
- Check for movement (wildfires spread, industrial sources don't)
- Use higher detection threshold

### 4. Seasonal Facilities

- Some facilities operate only certain months
- May not show up in 30-day window

**Solution:** Use 60-90 day lookback during startup

---

## Future Enhancements

### NASA Static Thermal Anomalies Integration

Once NASA releases downloadable STA data:

```python
# Future capability
filter_obj.load_nasa_sta_layer("path/to/nasa_sta.geojson")
```

### Third-Party Industrial Database

Integrate known facility locations:

```python
from src.filters.industrial_filter import create_industrial_exclusion_zone

# Load facilities database
exclusion_zones = create_industrial_exclusion_zone(
    facilities_csv="data/static/industrial_facilities.csv",
    buffer_km=1.0
)
```

**CSV Format:**
```csv
name,latitude,longitude,type
"US Steel Gary Works",41.5933,-87.3403,steel_plant
"BP Whiting Refinery",41.6764,-87.4995,refinery
```

### Movement Detection

Track fire location changes over time:
- Industrial sources: stationary
- Wildfires: move/spread
- Use velocity to distinguish

---

## Troubleshooting

### "No persistent anomalies found"

**Causes:**
- Insufficient historical data (< 7 days)
- Detection threshold too high
- No industrial sources in your area

**Solutions:**
```python
# Try lower threshold
persistent = filter_obj.identify_persistent_anomalies(
    detection_threshold=3  # Instead of 5
)

# Check available history
import duckdb
conn = duckdb.connect("data/wildfire.duckdb")
result = conn.execute("SELECT MIN(acq_date), MAX(acq_date), COUNT(*) FROM fires").fetchone()
print(f"Data range: {result[0]} to {result[1]} ({result[2]} fires)")
```

### "Too many fires excluded"

**Causes:**
- Threshold too low
- Buffer too large
- Large active wildfire complex

**Solutions:**
```python
# Use higher threshold
filter_obj.identify_persistent_anomalies(detection_threshold=7)

# Reduce buffer
filter_obj.filter_fires(fires, buffer_km=0.3)

# Review excluded fires manually
excluded.to_file("review_excluded.geojson")
```

### "Known industrial source not filtered"

**Causes:**
- New facility (not in historical data)
- Intermittent operation
- Not enough detections yet

**Solutions:**
- Wait for more historical data
- Manually add to exclusion list
- Use third-party facility database

---

## Command Reference

### Run Analysis
```bash
uv run python scripts/analyze_industrial_sources.py
```

### ETL with Filtering
```bash
uv run python -m flows.etl_flow  # filter_industrial=True by default
```

### ETL without Filtering
```python
from flows.etl_flow import wildfire_etl_flow
wildfire_etl_flow(filter_industrial=False)
```

### Custom Parameters
```python
from src.filters.industrial_filter import IndustrialHeatFilter

filter_obj = IndustrialHeatFilter("data/wildfire.duckdb")

# Aggressive filtering
persistent = filter_obj.identify_persistent_anomalies(
    lookback_days=60,
    detection_threshold=3,
    grid_size_km=0.4
)

filtered, excluded = filter_obj.filter_fires(
    fires,
    buffer_km=1.0,
    persistent_locations=persistent
)
```

---

## References

- [NASA FIRMS Static Thermal Anomalies](https://www.earthdata.nasa.gov/news/blog/firms-releases-new-features-identify-active-fires-type)
- [FIRMS FAQ](https://www.earthdata.nasa.gov/data/tools/firms/faq)
- Methodology based on NASA's 2023 STA layer approach

---

*Last updated: 2025-10-13*
