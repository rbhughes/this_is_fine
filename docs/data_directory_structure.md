# Data Directory Structure

## Overview

The `data/` directory contains both static reference data and dynamically processed outputs from the ETL pipeline.

```
data/
├── static/                          # Static reference data (can be version controlled)
│   ├── persistent_anomalies.geojson # Known industrial heat sources
│   └── persistent_anomalies.csv     # Same data in CSV format
├── processed/                       # Dynamic output (generated per ETL run)
│   ├── active_fires.geojson        # Current fire detections (filtered)
│   ├── fire_buffers.geojson        # Risk buffer zones (dissolved by risk_category)
│   ├── excluded_industrial_fires.geojson  # Fires filtered out (if running analysis script)
│   ├── fires_*.html                # Plotly visualizations (generated on demand)
│   └── region_metadata.json        # Metadata about current dataset
├── wildfire.duckdb                 # Main database (all historical data)
└── wildfire.duckdb.wal             # Write-Ahead Log (transaction safety)
```

---

## Static Reference Data (`data/static/`)

### Purpose
Contains manually curated or infrequently updated reference data that defines the baseline for filtering and analysis.

### Files

#### `persistent_anomalies.geojson`
- **Type:** GeoJSON FeatureCollection
- **Purpose:** Known industrial heat sources identified through temporal persistence analysis
- **Generation:** Run `uv run python scripts/analyze_industrial_sources.py`
- **Update frequency:** Weekly/monthly, or when new industrial facilities are observed
- **Version control:** Can be committed to git if desired (currently gitignored but can be included)
- **Fields:**
  - `latitude`, `longitude`: Location
  - `detection_count`: Total detections in lookback period
  - `unique_days`: Number of days with detections
  - `detections_per_day`: Average frequency
  - `first_detection`, `last_detection`: Date range
  - `geometry`: Point location

#### `persistent_anomalies.csv`
- **Type:** CSV
- **Purpose:** Same data as GeoJSON for spreadsheet review and manual verification
- **Usage:** Open in Excel/Google Sheets to review suspected industrial sources

### When to Update
- After accumulating 30+ days of new historical data
- When visual inspection reveals new industrial facilities
- When fire detections consistently appear at new persistent locations
- Quarterly/seasonally for facilities with variable operations

---

## Processed Data (`data/processed/`)

### Purpose
Contains outputs from each ETL run - dynamically generated and overwritten with fresh data.

### Files

#### `active_fires.geojson`
- **Type:** GeoJSON FeatureCollection
- **Purpose:** Current fire detections after industrial filtering
- **Generation:** Every ETL run via `wildfire_etl_flow()`
- **Overwritten:** Yes, with each run
- **Contains:**
  - Fire locations (lat/lon)
  - Satellite metadata (brightness, FRP, confidence)
  - Risk scores and categories
  - Weather data (if `use_weather=True`)
- **Use case:** Load into Kepler.gl for visualization

#### `fire_buffers.geojson`
- **Type:** GeoJSON FeatureCollection with MultiPolygon geometries
- **Purpose:** Dissolved 10km buffer zones grouped by risk category
- **Generation:** Every ETL run
- **Features:** Typically 3 polygons (Low, Moderate, High risk zones)
- **Use case:** Visualize risk zones and evacuation areas

#### `excluded_industrial_fires.geojson`
- **Type:** GeoJSON FeatureCollection
- **Purpose:** Fire detections that were filtered out as industrial sources
- **Generation:** Only when running `scripts/analyze_industrial_sources.py`
- **Use case:** Manual review to verify filtering accuracy

#### `fires_*.html`
- **Type:** HTML files with embedded Plotly visualizations
- **Purpose:** Interactive maps for fire visualization (basic, risk heatmap, AQI, PurpleAir)
- **Generation:** Created by `visualize_fires` tool or Gradio interface
- **Use case:** View maps in any web browser

#### `region_metadata.json`
- **Type:** JSON metadata file
- **Purpose:** Stores information about the current dataset (bbox, fire count, buffer count)
- **Generation:** Created by ETL flow on each run
- **Use case:** Track what region was last processed

---

## Database (`data/*.duckdb`)

### `wildfire.duckdb`
- **Type:** DuckDB database with spatial extension
- **Purpose:** Historical fire data storage with spatial indexing
- **Tables:**
  - `fires`: All fire detections (latitude, longitude, brightness, FRP, risk_score, etc.)
  - `fire_buffers`: Dissolved buffer zones per ETL run
- **Retention:** Accumulates data over time (not overwritten)
- **Size:** Grows with historical data (~1MB per 1000 fires)

### `wildfire.duckdb.wal`
- **Type:** Write-Ahead Log
- **Purpose:** Transaction safety for DuckDB
- **Management:** Automatically created/removed by DuckDB

---

## .gitignore Configuration

```gitignore
data/*.duckdb          # Database files (too large, user-specific)
data/*.duckdb.wal      # WAL files (transient)
data/processed/*.geojson  # Generated outputs (change frequently)
data/raw/*             # Raw API responses (if caching)

# Note: data/static/persistent_anomalies.* can be committed if desired
```

**Rationale:**
- `data/static/` is **not** gitignored - persistent anomalies can be version controlled
- Dynamic outputs in `data/processed/` are gitignored (regenerated each run)
- Database files are too large and user-specific

---

## Workflow

### Initial Setup (Day 1-7)
1. Run ETL without industrial filtering to accumulate data:
   ```bash
   wildfire_etl_flow(filter_industrial=False)
   ```
2. Data goes into `data/wildfire.duckdb`
3. No persistent anomalies identified yet (insufficient history)

### Establishing Baseline (Day 7-30)
1. Continue running ETL to build historical database
2. After 7-14 days, run analysis:
   ```bash
   uv run python scripts/analyze_industrial_sources.py
   ```
3. Review generated `data/static/persistent_anomalies.*` files
4. Verify locations using Google Maps links provided in output
5. Adjust detection threshold if needed

### Production Operation (Day 30+)
1. Run ETL with filtering enabled (default):
   ```bash
   wildfire_etl_flow(filter_industrial=True)
   ```
2. Industrial sources automatically filtered using `data/static/persistent_anomalies.geojson`
3. Clean fire data exported to `data/processed/active_fires.geojson`
4. Update persistent anomalies monthly or as needed

---

## File Sizes

**Example sizes (based on test data):**
- `persistent_anomalies.geojson`: ~25 KB (69 locations)
- `persistent_anomalies.csv`: ~6 KB
- `active_fires.geojson`: ~560 KB (1000 fires)
- `fire_buffers.geojson`: ~1.3 MB (3 dissolved polygons)
- `wildfire.duckdb`: ~600 KB (30 days of data)

---

## Best Practices

### Version Control
- **Commit** `data/static/persistent_anomalies.*` if you want to share baseline across team
- **Don't commit** processed outputs or database files

### Backup
- Back up `data/wildfire.duckdb` periodically (contains all historical data)
- Persistent anomalies can be regenerated from database if lost

### Maintenance
- Review and update persistent anomalies quarterly
- Check for new industrial facilities appearing in data
- Archive old database files if disk space becomes an issue

### Performance
- Database query time: ~1-2 seconds for 30 days of data
- GeoJSON load time in Kepler.gl: <5 seconds for typical datasets
- ETL with filtering: +2 seconds overhead vs no filtering

---

## Troubleshooting

### "No persistent anomalies found"
**Cause:** Insufficient historical data in database  
**Solution:** Run ETL for 7-14 days to accumulate data, then run analysis script

### "persistent_anomalies.geojson not found"
**Cause:** Analysis script hasn't been run yet  
**Solution:** Run `uv run python scripts/analyze_industrial_sources.py` to generate files

### "Too many fires filtered out"
**Cause:** Detection threshold too aggressive  
**Solution:** Regenerate with higher threshold: `detection_threshold=7` instead of `5`

### "Known industrial source not filtered"
**Cause:** Not enough detections at that location yet  
**Solution:** Wait for more historical data or manually add to exclusion list

---

*Last updated: 2025-10-13*
