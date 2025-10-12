# src/database/__init__.py
import duckdb
from pathlib import Path


def init_database(db_path: str = "data/wildfire.duckdb"):
    """Initialize DuckDB with spatial extension."""

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(db_path)

    # Install and load spatial extension
    conn.execute("INSTALL spatial")
    conn.execute("LOAD spatial")

    # Create tables
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fires (
            fire_id VARCHAR PRIMARY KEY,
            latitude DOUBLE,
            longitude DOUBLE,
            geom GEOMETRY,
            brightness DOUBLE,
            confidence INTEGER,
            frp DOUBLE,
            acq_date DATE,
            acq_time TIME,
            acq_datetime TIMESTAMP,
            daynight VARCHAR,
            satellite VARCHAR,
            risk_score DOUBLE,
            risk_category VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS fire_buffers (
            buffer_id VARCHAR PRIMARY KEY,
            fire_id VARCHAR,
            buffer_km DOUBLE,
            geom GEOMETRY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (fire_id) REFERENCES fires(fire_id)
        )
    """)

    return conn


def save_fires_to_db(conn: duckdb.DuckDBPyConnection, fires_gdf: gpd.GeoDataFrame):
    """Save fire detections to database."""

    # Create unique fire ID
    fires_gdf["fire_id"] = (
        fires_gdf["acq_date"].astype(str)
        + "_"
        + fires_gdf["latitude"].astype(str)
        + "_"
        + fires_gdf["longitude"].astype(str)
    )

    # Convert to WKT for DuckDB
    fires_gdf["geom_wkt"] = fires_gdf.geometry.to_wkt()

    # Insert or replace
    conn.execute("""
        INSERT OR REPLACE INTO fires
        SELECT
            fire_id,
            latitude,
            longitude,
            ST_GeomFromText(geom_wkt) as geom,
            bright_ti4 as brightness,
            confidence,
            frp,
            acq_date::DATE,
            acq_time::TIME,
            acq_datetime,
            daynight,
            satellite,
            risk_score,
            risk_category,
            CURRENT_TIMESTAMP
        FROM fires_gdf
    """)
