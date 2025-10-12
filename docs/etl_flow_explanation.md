# ETL Flow Execution Guide

This document describes exactly what happens step-by-step when `wildfire_etl_flow()` executes.

## Step-by-Step Execution of `wildfire_etl_flow()`

### **Step 1: Configuration Loading**
```python
api_key = os.getenv("FIRMS_API_KEY")
db_path = os.getenv("DATABASE_PATH", "data/wildfire.duckdb")
```
- Reads `FIRMS_API_KEY` from environment variables (from your `.env` file)
- Reads `DATABASE_PATH` or defaults to `"data/wildfire.duckdb"`
- These are just strings at this point, no API calls or file operations yet

### **Step 2: Fetch Active Fires (Prefect Task)**
```python
fires = fetch_active_fires(api_key, days_back)
```
**What happens inside `fetch_active_fires()` task:**
1. Creates a `FIRMSClient` instance with your API key
2. Calls `client.get_continental_us_fires(days=1)` (or whatever `days_back` is)
3. Inside that method:
   - Constructs bounding box: `(-125, 24, -66, 49)` (continental US)
   - Builds URL: `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{api_key}/VIIRS_NOAA20_NRT/-125,24,-66,49/1`
   - Makes HTTP GET request with 30 second timeout
   - Parses CSV response into pandas DataFrame
   - If empty → returns empty GeoDataFrame
   - If data exists → converts to GeoDataFrame with Point geometries, adds `acq_datetime` column
4. **This task is cached for 3 hours** (same inputs = cached result)
5. Returns GeoDataFrame with columns: `latitude`, `longitude`, `geometry`, `acq_date`, `acq_time`, `acq_datetime`, `brightness`, `confidence`, `frp`, `daynight`, `satellite`, etc.

### **Step 3: Early Exit Check**
```python
if fires.empty:
    print("No fires detected")
    return
```
- Checks if the GeoDataFrame has any rows
- If empty: prints "No fires detected" and returns immediately
- Nothing saved to database, no files exported
- Flow execution stops here

---

### **Steps 4-7 (Only execute when fires are detected):**

### **Step 4: Calculate Risk Scores**
```python
fires_with_risk = calculate_risk_scores(fires)
```
**Inside `calculate_risk_scores()` task:**
1. Creates `FireRiskCalculator` instance
2. Calls `calculator.calculate_base_risk(fires_gdf)`
3. Normalizes fire attributes:
   - `brightness_norm` = (bright_ti4 - 300) / 100, clipped to [0,1]
   - `confidence_norm` = confidence / 100
   - `frp_norm` = frp / 500, clipped to [0,1]
   - `daynight_norm` = 0.5 for day fires, 1.0 for night fires
4. Calculates weighted `risk_score` (0-100):
   - 30% brightness + 20% confidence + 30% FRP + 20% day/night
5. Categorizes into: "Low" (0-30), "Moderate" (30-60), "High" (60-100)
6. Returns GeoDataFrame with added `risk_score` and `risk_category` columns

### **Step 5: Create Buffer Zones**
```python
buffers = create_buffers(fires_with_risk, buffer_km)
```
**Inside `create_buffers()` task:**
1. Creates another `FireRiskCalculator` instance
2. Calls `calculator.create_risk_buffers(fires_gdf, buffer_km=10)`
3. Re-projects from WGS84 (EPSG:4326) to Albers Equal Area (EPSG:5070)
4. Creates 10km buffers (converted to 10,000 meters)
5. Re-projects back to WGS84
6. Returns GeoDataFrame with **polygon** geometries instead of points
7. **Note:** This result (`buffers`) is calculated but **never used** - it's not saved anywhere!

### **Step 6: Save to Database**
```python
save_to_database(fires_with_risk, db_path)
```
**Inside `save_to_database()` task:**
1. Calls `init_database(db_path)`:
   - Creates `data/` directory if needed
   - Connects to DuckDB at `data/wildfire.duckdb`
   - Installs and loads spatial extension
   - Calls `create_tables()` to create `fires` and `fire_buffers` tables with spatial indexes
2. Calls `save_fires_to_db(conn, fires_gdf)`:
   - Creates unique `fire_id` from date + lat + lon
   - Converts geometry to WKT format
   - Executes SQL `INSERT OR REPLACE` into `fires` table
   - Commits transaction
3. **Note:** Connection is NOT closed (potential resource leak - uses singleton pattern)

### **Step 7: Export Visualization Files**
```python
export_for_visualization(fires_with_risk, "data/processed")
```
**Inside `export_for_visualization()` task:**
1. Creates `data/processed/` directory
2. Exports `active_fires.geojson` file with all fire data

### **Step 8: Final Output**
```python
print(f"Processed {len(fires_with_risk)} fires")
return fires_with_risk
```
- Prints count
- Returns GeoDataFrame (Prefect captures this as flow result)

---

## Execution Paths

### When No Fires Detected:
1. ✓ Load environment variables
2. ✓ Make FIRMS API call 
3. ✓ Get empty result
4. ✓ Print "No fires detected"
5. ✓ Exit early

### When Fires Are Detected:
1. ✓ Load environment variables
2. ✓ Make FIRMS API call
3. ✓ Calculate risk scores for all fires
4. ✓ Create buffer zones (not saved)
5. ✓ Initialize DuckDB with schema
6. ✓ Save fires to database
7. ✓ Export GeoJSON file
8. ✓ Print count and return GeoDataFrame

## Known Issues

1. **Buffer zones are calculated but never saved** - The `buffers` variable in step 5 is not used
2. **Database connection not explicitly closed** - Uses singleton pattern in `connection.py`
3. **No error handling for missing API key** - Will fail if `FIRMS_API_KEY` is not set
