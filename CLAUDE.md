# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Instructions for Claude Code

**IMPORTANT - Verify Currency of Advice:**
- Today's date is available in the `<env>` context (check "Today's date" field)
- Before providing advice about external APIs, libraries, or services, use WebSearch to verify the information is current
- APIs and libraries change frequently - always check if syntax, function names, or service requirements have changed
- When suggesting code that uses external services (Plotly, Mapbox, PurpleAir, etc.), search for recent examples or documentation
- If giving advice about deprecations or migrations, verify the current status (e.g., "Plotly Mapbox migration 2025")
- When in doubt, search first before answering

## Project Overview

"this-is-fine" is a wildfire risk monitoring system that ingests active fire data from NASA FIRMS (Fire Information for Resource Management System), filters out industrial heat sources, calculates risk scores with optional weather enrichment, and provides APIs for visualization and querying. The system uses geospatial analysis to track fires and create risk buffer zones.

**Key technologies:**
- Python 3.12+ managed with uv
- DuckDB with spatial extension for geospatial data storage
- GeoPandas/Shapely for spatial operations
- Prefect for ETL orchestration
- Flask/Flask-CORS for REST API
- Kepler.gl and Plotly+MapLibre for interactive geospatial visualization
- MCP (Model Context Protocol) server for tool integration
- Gradio web UI with local LLM (Qwen2.5:14b via Ollama)

**Key features:**
- Industrial heat source filtering (steel plants, refineries, etc.)
- Optional NOAA weather data enrichment for enhanced risk scoring
- Optional air quality enrichment (EPA AirNow + PurpleAir sensors)
- Dissolved buffer zones grouped by risk category
- Real-time fire detection with ~24hr FIRMS API lag
- Natural language interface via local LLM (no API keys required)

## Development Commands

### Running the Application

**Primary CLI (Recommended):**
```bash
# Fetch fires for a region (fast, default: fires only)
uv run wildfire fetch --region indiana
uv run wildfire fetch --region california

# Fetch with weather enrichment (slower but more accurate)
uv run wildfire fetch --region california --weather

# Fetch with official air quality data (AQI from EPA AirNow)
uv run wildfire fetch --region colorado --aqi

# Fetch with real-time smoke tracking (PurpleAir sensors)
uv run wildfire fetch --region colorado --purpleair

# Fetch with both air quality sources
uv run wildfire fetch --region california --aqi --purpleair

# Fetch with all data sources (fires + weather + both AQ sources)
uv run wildfire fetch --region california --weather --aqi --purpleair

# Custom bounding box
uv run wildfire fetch --bbox -124.5,32.5,-114.13,42.0

# Advanced options
uv run wildfire fetch --region pnw --days 5 --buffer 3 --weather

# View available regions
uv run wildfire regions

# Show summary of current data
uv run wildfire summary

# Database management
uv run wildfire db-stats
uv run wildfire clear  # Clears all data (with confirmation)

# Industrial source analysis
uv run wildfire analyze-industrial
uv run wildfire show-industrial
```

**Legacy Python API (still supported):**
```bash
# Direct ETL flow execution
uv run python -m flows.etl_flow

# Custom parameters
uv run python -c "from flows.etl_flow import wildfire_etl_flow; wildfire_etl_flow(days_back=2, use_weather=False)"
```

**Web Interface (New!):**
```bash
# Launch Gradio web UI with LLM chat interface
uv run python web/gradio_app.py
# Access at http://localhost:7860
```

**Other Services:**
```bash
# Start Flask API server
uv run api/app.py

# Start MCP server (stdio mode)
uv run python mcp_server/server.py
```

### Visualization
```bash
# Open Jupyter notebook for interactive Kepler.gl visualization
uv run jupyter notebook notebooks/kepler.ipynb

# Or use JupyterLab
uv run jupyter lab notebooks/kepler.ipynb

# If you see "Kernel does not exist" errors, clean stale sessions:
uv run python scripts/clean_jupyter_kernels.py
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_risk_calculator.py

# Run with verbose output
uv run pytest -v

# Run type checking
uv run basedpyright
```

### Dependency Management
```bash
# Add a new dependency
uv add <package-name>

# Add a development dependency
uv add --dev <package-name>

# Sync dependencies
uv sync
```

### Environment Setup
The project requires a `.env` file with:
```
FIRMS_API_KEY=<your-nasa-firms-api-key>
AIRNOW_API_KEY=<your-epa-airnow-api-key>      # Optional: for official AQI data
PURPLEAIR_API_KEY=<your-purpleair-api-key>    # Optional: for real-time PM2.5 data
MAPBOX_TOKEN=<your-mapbox-token>              # Optional: for Plotly visualizations with Mapbox
DATABASE_PATH=data/wildfire.duckdb
```

**Getting API Keys:**
- **FIRMS API Key** (required): Register at https://firms.modaps.eosdis.nasa.gov/api/area/
- **AirNow API Key** (optional): Register at https://docs.airnowapi.org/account/request/
- **PurpleAir API Key** (optional): Register at https://develop.purpleair.com/ (free for personal/research use)
- **Mapbox Token** (optional, not needed for Plotly): Only needed if you want custom Mapbox tiles. Plotly uses free CARTO maps by default.

## Architecture

### Data Pipeline (Prefect ETL)
The ETL flow (`flows/etl_flow.py`) orchestrates the data pipeline:
1. **Ingestion**: Fetch active fire data from NASA FIRMS API (default: 2 days lookback)
2. **Industrial Filtering**: Identify and exclude persistent heat sources using temporal persistence analysis
3. **Weather Enrichment** (optional): Fetch NOAA NWS weather data for each fire location
4. **AQI Enrichment** (optional): Fetch EPA AirNow official air quality index for each fire location
5. **PurpleAir Enrichment** (optional): Fetch real-time PM2.5 data from nearby PurpleAir sensors
6. **Risk Calculation**: Calculate risk scores using weighted factors
7. **Spatial Processing**: Create dissolved buffer zones grouped by risk category (default 5km)
8. **Storage**: Save processed data to DuckDB with spatial indexing
9. **Export**: Generate GeoJSON files for visualization tools (e.g., kepler.gl)

Tasks are cached for 3 hours to avoid redundant API calls.

**Data Source Flags:**
- `--fires`: FIRMS satellite fire data (always enabled, default data source)
- `--weather`: NOAA weather enrichment (optional, slow: ~1-2 sec per fire)
- `--aqi`: AirNow official air quality (optional, requires AIRNOW_API_KEY, sparse coverage)
- `--purpleair`: PurpleAir sensor network (optional, requires PURPLEAIR_API_KEY, searches 50km radius for sensors)

**Important notes:**
- FIRMS API has ~24hr processing delay - use `days_back=2` for recent data
- Industrial filtering uses saved persistent locations (data/static/persistent_anomalies.geojson)
  - Uses 1km buffer around persistent locations to account for satellite sensor drift
  - Falls back to identifying from historical data with threshold of 2+ detections
  - Run analyze_industrial_sources.py to update the persistent locations
- Weather enrichment is slow (~1-2 sec per fire) - disable for large datasets
- AQI enrichment requires AIRNOW_API_KEY in .env file
- Buffer radius: default 5km (2-5km for immediate risk, 10-20km for extended planning)

### Core Modules

**`src/ingestion/`**
- `firms_client.py`: NASA FIRMS API client supporting VIIRS and MODIS satellite data
- `noaa_client.py`: NOAA NWS weather data integration
- `airnow_client.py`: EPA AirNow official air quality/AQI data (sparse, authoritative)
- `purpleair_client.py`: PurpleAir crowdsourced sensor network (dense, real-time PM2.5)
- `enrichment.py`: Additional data enrichment logic (placeholder)

**`src/analysis/`**
- `risk_calculator.py`: Fire risk scoring algorithm with weighted factors (brightness: 30%, confidence: 20%, FRP: 30%, day/night: 20%). Outputs risk scores (0-100) and categories (Low/Moderate/High)
- `spatial_ops.py`: Geospatial utility functions

**`src/database/`**
- `__init__.py`: DuckDB initialization with spatial extension, table schema for `fires` and `fire_buffers`
- `queries.py`: Common database queries

**`api/`**
- `app.py`: Flask REST API for querying fire data and risk assessments

**`mcp_server/`**
- MCP server implementation for external integrations
- `server.py`: Server setup and configuration
- `tools.py`: Tool definitions for the MCP protocol

### Database Schema
- **fires table**: Core fire detections with geometry, satellite data, risk scores
- **fire_buffers table**: Risk buffer zones linked to fire records

### Coordinate Systems
- Input/output: WGS84 (EPSG:4326)
- Buffering operations: Albers Equal Area for CONUS (EPSG:5070) for accurate distance calculations

## Data Sources
- **NASA FIRMS**: Real-time active fire data from VIIRS (Visible Infrared Imaging Radiometer Suite) and MODIS satellites
- **NOAA NWS**: Weather data for fire risk enrichment (optional)
- **EPA AirNow**: Official air quality monitoring from ~2,500 regulatory stations (optional)
- **PurpleAir**: Crowdsourced air quality from 20,000+ sensors for real-time smoke tracking (optional)
- Default area: Continental US (-125, 24, -66, 49)
- Custom areas: See `docs/bounding_boxes.md` for state/region coordinates

### Geographic Filtering
You can limit data fetching to specific regions for faster processing:

```python
# Fetch data for California only
wildfire_etl_flow(bbox=(-124.5, 32.5, -114.13, 42.0))

# Pacific Northwest (WA, OR, ID)
wildfire_etl_flow(bbox=(-124.8, 41.9, -111.0, 49.0))
```

**Performance benefits:**
- Smaller area = fewer API calls to FIRMS and NOAA
- California: ~50-200 fires/day vs CONUS: ~1000-3000 fires/day
- Weather enrichment: 10 fires = 10-20 sec, 1000 fires = 20-30 min

See `docs/bounding_boxes.md` for common regions and how to find your own.

## Web Interface (Gradio + LLM)

**NEW:** Natural language interface powered by local LLM (Qwen2.5:14b).

**Quick Start:**
```bash
# 1. Install Ollama: https://ollama.ai
# 2. Pull the model
ollama pull qwen2.5:14b

# 3. Launch the web interface
uv run python web/gradio_app.py
# Access at http://localhost:7860
```

**Features:**
- 💬 **Natural language chat** - Ask questions or give commands in plain English
- 🗺️ **Real-time maps** - Interactive Plotly visualizations updated automatically
- 🤖 **Local LLM** - No API keys, runs entirely on your Mac (24GB RAM recommended)
- 🔧 **Full MCP access** - All tools available via conversation

**Example Interactions:**
```
You: "Fetch fires in California from the last 2 days"
Assistant: [Executes fetch_fires] "Found 150 fires (23 industrial filtered)"

You: "Add PurpleAir air quality data"
Assistant: [Executes enrich_purpleair] "Added PM2.5 to 87/150 fires"

You: "Show me a PM2.5 heatmap"
[Map switches to PurpleAir density visualization]
```

**LLM Requirements:**
- **Recommended**: Qwen2.5:14b (~10-12GB RAM, good quality)
- **Alternatives**: llama3.2:11b, qwen2.5:7b, mistral:7b
- **Hardware**: M1/M2/M3 MacBook Air with 24GB RAM is perfect

See `docs/gradio_web_interface.md` for detailed documentation.

## Visualization Options

The project includes two visualization approaches:

### 1. Plotly + MapLibre (Recommended - Fully Programmatic)

**Location:** `notebooks/plotly_visualization.ipynb`

**Features:**
- **Complete programmatic control** - define all styling in code
- **Modern MapLibre rendering** - uses CARTO maps (free, no API key)
- **Density heatmaps** - PM2.5 smoke tracking
- **Multi-layer maps** - fires, buffers, AQI, PM2.5
- **Statistics dashboards** - charts and graphs
- **Export to HTML** - standalone files for sharing

**Map Styles (No API Key Required):**
- `carto-positron` - Light theme (default)
- `carto-darkmatter` - Dark theme
- `carto-voyager` - Colorful theme
- `open-street-map` - Classic OpenStreetMap

**Quick Start:**
```bash
# No API key needed! Uses free CARTO maps

# Run the ETL
uv run wildfire fetch --region colorado --aqi --purpleair

# Open the visualization notebook
uv run jupyter notebook notebooks/plotly_visualization.ipynb
```

**Note:** As of Plotly 5.24+ (2024), Plotly switched from Mapbox to MapLibre. Built-in styles now use CARTO (free) instead of requiring Mapbox tokens. Mapbox can still be used via custom raster tile configuration if needed.

**Available Visualizations:**
1. Fire points map (colored by risk score)
2. Risk buffer zones (polygons by category)
3. AQI impact map (official EPA data)
4. PM2.5 density heatmap (PurpleAir sensors)
5. Combined multi-layer map (all data sources)
6. Statistics dashboard (charts and metrics)

### 2. Kepler.gl Interactive Maps

**Location:** `notebooks/kepler.ipynb`

**Features:**
- Automatic styling - no manual configuration needed
- Multiple visualization methods (auto-style, saved configs, HTML export)
- Support for loading data from GeoJSON files or DuckDB
- GeoArrow support for fast rendering of large datasets
- Air quality visualization (AQI and PM2.5 heatmaps)

**Quick Start:**
```bash
# Run the ETL with air quality data
uv run wildfire fetch --region colorado --aqi --purpleair

# Open the visualization notebook
uv run jupyter notebook notebooks/kepler.ipynb
```

**Notebook Sections:**
1. **Quick Visualization**: Auto-styled maps with zero configuration
2. **Export Configuration**: Save custom styling for reuse
3. **Load with Saved Config**: Apply consistent styling across sessions
4. **Export to HTML**: Create standalone web maps
5. **Database Loading**: Load data directly from DuckDB
6. **GeoArrow Performance**: Fast rendering for large datasets
7. **Air Quality Visualization**: AQI and PM2.5 heatmaps

**Useful Columns for Visualization:**
- Fire points: `risk_score`, `risk_category`, `frp`, `bright_ti4`, `confidence`, `acq_date`
- Buffer zones: `risk_category`, `geometry`
- Air quality (AirNow): `aqi`, `aqi_category`, `aqi_parameter`
- Air quality (PurpleAir): `pa_pm25`, `pa_pm25_60min`, `pa_sensor_count`

**Visualization Options:**
- **Fire Risk Map**: Points colored by risk score, buffers by risk category
- **AQI Impact Map**: Points colored by AQI value showing air quality impact
- **PM2.5 Heatmap**: Heatmap layer showing PurpleAir smoke concentrations
- **Multi-Layer Map**: Combined view with fires, buffers, AQI, and PM2.5

**Export Options:**
- Save configuration as JSON for programmatic reuse
- Export interactive HTML maps (no Python required to view)
- Share standalone visualizations with stakeholders

## CLI Reference

The `wildfire` CLI provides a clean interface for all operations. All commands support `--help` for detailed information.

### Quick Reference

```bash
# Fetch fires (data sources: --fires --weather --aqi --purpleair)
wildfire fetch --region <name>                      # Just fires (fast, default)
wildfire fetch --region ca --weather                # Fires + weather data
wildfire fetch --region ca --aqi                    # Fires + official AQI
wildfire fetch --region ca --purpleair              # Fires + real-time PM2.5
wildfire fetch --region ca --aqi --purpleair        # Fires + both AQ sources
wildfire fetch --region ca --weather --aqi --purpleair  # All data sources
wildfire fetch --bbox W,S,E,N                       # Custom bounding box
wildfire fetch --region ca --days 5                 # Custom lookback
wildfire fetch --region ca --buffer 10              # Custom buffer radius

# View data
wildfire summary                            # Current fire summary
wildfire db-stats                           # Database statistics
wildfire regions                            # List available regions

# Database management
wildfire clear                              # Clear all data (with confirmation)

# Industrial filtering
wildfire analyze-industrial                 # Identify industrial sources
wildfire analyze-industrial --days 14 --threshold 3  # Custom parameters
wildfire show-industrial                    # Show current industrial locations
```

### Region Names

Use abbreviated or full state names:
- **States**: `california` or `ca`, `indiana` or `in`, `texas` or `tx`
- **Regions**: `pacific-northwest` or `pnw`, `southwest` or `sw`
- **Full CONUS**: `conus` or `continental-us`

Run `wildfire regions` to see all available regions.

### MCP Integration

All CLI commands are backed by discrete functions in `src/commands/` that are designed for MCP tool integration:

- `fetch_fires_for_region(region, days_back, buffer_km, use_weather, use_aqi, use_purpleair, filter_industrial)`
- `fetch_fires_for_bbox(bbox, days_back, buffer_km, use_weather, use_aqi, use_purpleair, filter_industrial)`
- `get_database_stats()` - Returns database statistics
- `clear_database(confirm=True)` - Clear all data
- `analyze_industrial_sources(lookback_days, detection_threshold, grid_size_km)`
- `get_persistent_locations()` - Get industrial source list

**Data Source Parameters:**
- `use_weather`: Enable NOAA weather enrichment (default: False)
- `use_aqi`: Enable AirNow official air quality enrichment (default: False, requires AIRNOW_API_KEY)
- `use_purpleair`: Enable PurpleAir sensor enrichment (default: False, requires PURPLEAIR_API_KEY)

These functions return structured dictionaries suitable for both CLI display and MCP responses.

## Troubleshooting

### Jupyter Kernel Errors
If you see errors like "Kernel does not exist: <kernel-id>" when running Jupyter:

**Quick fix:**
```bash
# Run the cleanup utility
uv run python scripts/clean_jupyter_kernels.py

# Then restart Jupyter
jupyter notebook stop
uv run jupyter notebook
```

**Manual fix:**
1. Stop all Jupyter processes (Ctrl+C or `jupyter notebook stop`)
2. Clear runtime directory:
   - macOS: `rm -rf ~/Library/Jupyter/runtime/*`
   - Linux: `rm -rf ~/.local/share/jupyter/runtime/*`
3. Restart Jupyter: `uv run jupyter notebook`
4. In the notebook: Kernel → Restart & Clear Output

**Root cause:** These errors occur when Jupyter has stale kernel session references from previous runs. The cleanup utility or manual clearing removes these orphaned session files.

### Industrial Filtering Not Working
If industrial heat sources (steel mills, refineries) are still showing in results:

**Most common cause:** Database contains old unfiltered data from previous ETL runs.

**Solution:**
```bash
# 1. Clear the database
uv run python scripts/clear_database.py

# 2. Re-run ETL with industrial filtering enabled (default)
uv run python -c "from flows.etl_flow import wildfire_etl_flow; wildfire_etl_flow(bbox=(-88.1, 37.8, -84.8, 41.8))"

# 3. Verify in notebook
uv run jupyter notebook notebooks/kepler.ipynb
```

**Why this happens:** The ETL uses `INSERT OR REPLACE` which:
- Updates existing fires with the same fire_id
- But doesn't delete old fires from previous runs
- The notebook reads all fires from the database, including old unfiltered data

**Other checks:**
1. Verify persistent locations file exists: `data/static/persistent_anomalies.geojson`
2. If missing or outdated, run: `uv run python scripts/analyze_industrial_sources.py`
3. The analyzer needs 7-30 days of historical data to identify persistent sources

### Buffer Zones Appearance
Buffer zones are dissolved by risk category by default, creating merged risk zones:

- **Default behavior:** `dissolve_buffers=True` merges all buffers of the same risk category into combined polygons
- **For individual buffers:** Use `dissolve_buffers=False` to see one buffer per fire
- **CLI:** Use `--no-dissolve` flag to disable merging
- **Example:** `wildfire fetch --region california --no-dissolve`

### Type Checking Warnings
If you see basedpyright warnings about pandas/geopandas:

- Most warnings are from incomplete type stubs in pandas/geopandas libraries
- Critical errors have been resolved with appropriate type annotations
- Safe to ignore warnings like "reportAttributeAccessIssue" for known pandas methods

### NOAA Weather Data Slow
Weather enrichment can take 1-2 seconds per fire:

- **For testing:** Disable weather: `wildfire_etl_flow(use_weather=False)`
- **For production:** Use geographic filtering to reduce fire count: `wildfire_etl_flow(bbox=<region>)`
- **Typical times:** 10 fires = 10-20 sec, 100 fires = 2-3 min, 1000 fires = 20-30 min
