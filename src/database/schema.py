# src/database/schema.py
"""Database schema definitions."""

import duckdb


def create_tables(conn: duckdb.DuckDBPyConnection):
    """Create all database tables."""

    conn.execute("""
        CREATE TABLE IF NOT EXISTS fires (
            fire_id VARCHAR PRIMARY KEY,
            latitude DOUBLE,
            longitude DOUBLE,
            geom GEOMETRY,
            brightness DOUBLE,
            confidence VARCHAR,
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create spatial indexes for performance
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_fires_geom
        ON fires USING RTREE (geom)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_fires_date
        ON fires (acq_date)
    """)
