# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

"this-is-fine" is a wildfire risk monitoring system that ingests active fire data from NASA FIRMS (Fire Information for Resource Management System), calculates risk scores, and provides APIs for visualization and querying. The system uses geospatial analysis to track fires and create risk buffer zones.

**Key technologies:**
- Python 3.12+ managed with uv
- DuckDB with spatial extension for geospatial data storage
- GeoPandas/Shapely for spatial operations
- Prefect for ETL orchestration
- Flask/Flask-CORS for REST API
- MCP (Model Context Protocol) server for integration

## Development Commands

### Running the Application
```bash
# Main entry point
uv run main.py

# Run ETL flow (requires FIRMS_API_KEY env var)
uv run flows/etl_flow.py

# Start Flask API server
uv run api/app.py

# Start MCP server
uv run mcp_server/server.py
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_risk_calculator.py

# Run with verbose output
uv run pytest -v
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
DATABASE_PATH=data/wildfire.duckdb
```

## Architecture

### Data Pipeline (Prefect ETL)
The ETL flow (`flows/etl_flow.py`) orchestrates the data pipeline:
1. **Ingestion**: Fetch active fire data from NASA FIRMS API for continental US
2. **Risk Calculation**: Calculate risk scores based on brightness, FRP (Fire Radiative Power), confidence, and time of day
3. **Spatial Processing**: Create buffer zones around fires (default 10km radius)
4. **Storage**: Save processed data to DuckDB with spatial indexing
5. **Export**: Generate GeoJSON files for visualization tools (e.g., kepler.gl)

Tasks are cached for 3 hours to avoid redundant API calls.

### Core Modules

**`src/ingestion/`**
- `firms_client.py`: NASA FIRMS API client supporting VIIRS and MODIS satellite data
- `noaa_client.py`: Weather data integration (if needed)
- `enrichment.py`: Additional data enrichment logic

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
- Continental US bounding box: (-125, 24, -66, 49) in lon/lat
