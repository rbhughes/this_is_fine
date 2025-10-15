# Bounding Box Reference

Common bounding boxes for limiting FIRMS/NOAA data fetching to specific regions.

Format: `(west, south, east, north)` in decimal degrees (WGS84)

## Important Notes

**Bounding boxes are rectangular** - they may include areas outside state boundaries:
- California's eastern border is irregular (follows the Colorado River and state line)
- A rectangular bbox will include parts of Nevada near Lake Mead
- Use "tight" bboxes to exclude border areas, or "loose" to include nearby regions
- For precise state boundaries, filter the results after fetching

## Continental US
```python
bbox = (-125, 24, -66, 49)  # Default - entire CONUS
```

## US States

### Western States
```python
# California (very tight - excludes Lake Mead/NV)
bbox = (-124.5, 32.5, -114.04, 42.0)

# California (standard - may include Lake Mead area fires)
# bbox = (-124.5, 32.5, -114.5, 42.0)

# Oregon
bbox = (-124.6, 41.9, -116.5, 46.3)

# Washington
bbox = (-124.8, 45.5, -116.9, 49.0)

# Nevada
bbox = (-120.0, 35.0, -114.0, 42.0)

# Arizona
bbox = (-114.8, 31.3, -109.0, 37.0)

# New Mexico
bbox = (-109.0, 31.3, -103.0, 37.0)

# Colorado
bbox = (-109.1, 37.0, -102.0, 41.0)

# Montana
bbox = (-116.1, 44.4, -104.0, 49.0)

# Idaho
bbox = (-117.2, 41.9, -111.0, 49.0)

# Wyoming
bbox = (-111.1, 41.0, -104.0, 45.0)
```

### Southern States
```python
# Texas
bbox = (-106.7, 25.8, -93.5, 36.5)

# Oklahoma
bbox = (-103.0, 33.6, -94.4, 37.0)

# Louisiana
bbox = (-94.1, 28.9, -88.8, 33.0)

# Mississippi
bbox = (-91.7, 30.2, -88.1, 35.0)

# Alabama
bbox = (-88.5, 30.2, -84.9, 35.0)

# Florida
bbox = (-87.6, 24.5, -80.0, 31.0)

# Georgia
bbox = (-85.6, 30.4, -80.8, 35.0)
```

### Midwest States
```python
# Indiana
bbox = (-88.1, 37.8, -84.8, 41.8)

# Illinois
bbox = (-91.5, 37.0, -87.5, 42.5)

# Ohio
bbox = (-84.8, 38.4, -80.5, 42.0)

# Michigan
bbox = (-90.4, 41.7, -82.4, 48.3)

# Wisconsin
bbox = (-92.9, 42.5, -86.8, 47.1)

# Minnesota
bbox = (-97.2, 43.5, -89.5, 49.4)

# Iowa
bbox = (-96.6, 40.4, -90.1, 43.5)

# Missouri
bbox = (-95.8, 36.0, -89.1, 40.6)
```

### Eastern States
```python
# North Carolina
bbox = (-84.3, 33.8, -75.4, 36.6)

# Virginia
bbox = (-83.7, 36.5, -75.2, 39.5)

# Pennsylvania
bbox = (-80.5, 39.7, -74.7, 42.3)

# New York
bbox = (-79.8, 40.5, -71.9, 45.0)
```

## US Regions

### Pacific Northwest (WA, OR, ID)
```python
bbox = (-124.8, 41.9, -111.0, 49.0)
```

### Southwest (CA, NV, AZ)
```python
bbox = (-124.5, 31.3, -109.0, 42.0)
```

### Rocky Mountains (MT, WY, CO, ID)
```python
bbox = (-117.2, 37.0, -102.0, 49.0)
```

### Great Plains (ND, SD, NE, KS, OK)
```python
bbox = (-104.0, 33.6, -96.4, 49.0)
```

### Southeast (FL, GA, AL, MS, LA, SC, NC)
```python
bbox = (-94.1, 24.5, -75.4, 36.6)
```

## Major Metropolitan Areas (with 100km radius)

```python
# Los Angeles
bbox = (-119.0, 33.0, -117.0, 35.0)

# San Francisco Bay Area
bbox = (-123.0, 37.0, -121.0, 39.0)

# Portland, OR
bbox = (-123.5, 44.5, -121.5, 46.5)

# Seattle
bbox = (-123.0, 46.5, -121.0, 48.5)

# Phoenix
bbox = (-113.0, 32.5, -111.0, 34.5)

# Denver
bbox = (-106.0, 39.0, -104.0, 41.0)

# Houston
bbox = (-96.5, 29.0, -94.5, 31.0)

# Dallas
bbox = (-97.5, 32.0, -95.5, 34.0)

# Atlanta
bbox = (-85.5, 33.0, -83.5, 35.0)

# Miami
bbox = (-81.0, 25.0, -79.0, 27.0)
```

## Usage Examples

### Python
```python
from flows.etl_flow import wildfire_etl_flow

# California only
wildfire_etl_flow(
    days_back=2,
    bbox=(-124.5, 32.5, -114.0, 42.0),
    use_weather=True
)

# Pacific Northwest
wildfire_etl_flow(
    days_back=2,
    bbox=(-124.8, 41.9, -111.0, 49.0),
    buffer_km=3.0
)

# Around specific city (Phoenix + 100km)
wildfire_etl_flow(
    days_back=1,
    bbox=(-113.0, 32.5, -111.0, 34.5),
    buffer_km=2.0,
    use_weather=False  # Faster for small areas
)
```

### Command Line
```bash
# California fires with weather
uv run python -c "from flows.etl_flow import wildfire_etl_flow; wildfire_etl_flow(bbox=(-124.5, 32.5, -114.0, 42.0), use_weather=True)"

# Pacific Northwest, fast (no weather)
uv run python -c "from flows.etl_flow import wildfire_etl_flow; wildfire_etl_flow(bbox=(-124.8, 41.9, -111.0, 49.0), use_weather=False)"
```

## Finding Your Own Bounding Box

### Online Tools
1. **http://bboxfinder.com/** - Draw a box and get coordinates
2. **https://boundingbox.klokantech.com/** - Similar tool with multiple formats

### From GeoJSON/Shapefile
```python
import geopandas as gpd

# Load your area of interest
gdf = gpd.read_file('my_region.geojson')

# Get bounding box
bounds = gdf.total_bounds  # (minx, miny, maxx, maxy)
bbox = (bounds[0], bounds[1], bounds[2], bounds[3])
print(f"Bounding box: {bbox}")
```

## Performance Tips

- **Smaller bbox = faster processing**: 
  - California (~200k km²): ~50-200 fires/day
  - Continental US (~8M km²): ~1000-3000 fires/day

- **Weather enrichment impact**:
  - 10 fires: ~10-20 seconds
  - 100 fires: ~2-3 minutes
  - 1000 fires: ~20-30 minutes

- **Recommended for development**:
  - Use small bbox (1-2 states)
  - Disable weather: `use_weather=False`
  - Short lookback: `days_back=1`
