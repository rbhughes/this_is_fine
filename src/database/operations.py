# src/database/operations.py
"""Database operations for fire data."""

import duckdb
import geopandas as gpd
from typing import Optional, Tuple
from datetime import date


def save_fires_to_db(conn: duckdb.DuckDBPyConnection, fires_gdf: gpd.GeoDataFrame):
    """
    Save fire detections to database.

    Args:
        conn: DuckDB connection
        fires_gdf: GeoDataFrame with fire data
    """
    if fires_gdf.empty:
        return

    # Create unique fire ID
    fires_gdf = fires_gdf.copy()
    fires_gdf["fire_id"] = (
        fires_gdf["acq_date"].astype(str)
        + "_"
        + fires_gdf["latitude"].round(4).astype(str)
        + "_"
        + fires_gdf["longitude"].round(4).astype(str)
    )

    # Convert geometry to WKT
    fires_gdf["geom_wkt"] = fires_gdf.geometry.to_wkt()

    # Create a regular DataFrame (drop geometry column for DuckDB)
    df_for_db = fires_gdf.drop(columns=["geometry"]).copy()

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
            (substr(lpad(acq_time::VARCHAR, 4, '0'), 1, 2) || ':' || substr(lpad(acq_time::VARCHAR, 4, '0'), 3, 2) || ':00')::TIME as acq_time,
            acq_datetime,
            daynight,
            satellite,
            risk_score,
            risk_category::VARCHAR,
            CURRENT_TIMESTAMP
        FROM df_for_db
    """)

    conn.commit()


def save_buffers_to_db(
    conn: duckdb.DuckDBPyConnection, buffers_gdf: gpd.GeoDataFrame, buffer_km: float
):
    """
    Save fire buffer zones to database.

    Args:
        conn: DuckDB connection
        buffers_gdf: GeoDataFrame with buffer polygons (can be dissolved or individual)
        buffer_km: Buffer radius in kilometers
    """
    if buffers_gdf.empty:
        return

    # Create buffers DataFrame
    buffers_gdf = buffers_gdf.copy()

    # Check if this is dissolved buffers (grouped by risk_category) or individual buffers
    if "fire_id" not in buffers_gdf.columns:
        # Dissolved buffers - create buffer_id from risk_category
        if "risk_category" in buffers_gdf.columns:
            buffers_gdf["buffer_id"] = (
                buffers_gdf["risk_category"].astype(str) + f"_buffer_{buffer_km}km"
            )
            buffers_gdf["fire_id"] = (
                buffers_gdf["risk_category"].astype(str) + "_zone"
            )  # Placeholder
        else:
            # Individual buffers without fire_id - create it
            buffers_gdf["fire_id"] = (
                buffers_gdf["acq_date"].astype(str)
                + "_"
                + buffers_gdf["latitude"].round(4).astype(str)
                + "_"
                + buffers_gdf["longitude"].round(4).astype(str)
            )
            buffers_gdf["buffer_id"] = buffers_gdf["fire_id"] + f"_buffer_{buffer_km}km"
    else:
        # Individual buffers with fire_id already present
        buffers_gdf["buffer_id"] = buffers_gdf["fire_id"] + f"_buffer_{buffer_km}km"

    buffers_gdf["buffer_km"] = buffer_km

    # Convert geometry to WKT
    buffers_gdf["geom_wkt"] = buffers_gdf.geometry.to_wkt()

    # Create a regular DataFrame (drop geometry column for DuckDB)
    df_for_db = buffers_gdf[["buffer_id", "fire_id", "buffer_km", "geom_wkt"]].copy()

    # Insert or replace
    conn.execute("""
        INSERT OR REPLACE INTO fire_buffers
        SELECT
            buffer_id,
            fire_id,
            buffer_km,
            ST_GeomFromText(geom_wkt) as geom,
            CURRENT_TIMESTAMP
        FROM df_for_db
    """)

    conn.commit()


def get_fires_by_date(
    conn: duckdb.DuckDBPyConnection, start_date: date, end_date: Optional[date] = None
) -> gpd.GeoDataFrame:
    """
    Retrieve fires within date range.

    Args:
        conn: DuckDB connection
        start_date: Start date
        end_date: End date (defaults to start_date)

    Returns:
        GeoDataFrame with fires
    """
    if end_date is None:
        end_date = start_date

    result = conn.execute(
        """
        SELECT
            fire_id,
            latitude,
            longitude,
            ST_AsText(geom) as geometry,
            brightness,
            confidence,
            frp,
            acq_date,
            acq_datetime,
            risk_score,
            risk_category
        FROM fires
        WHERE acq_date BETWEEN ? AND ?
        ORDER BY risk_score DESC
    """,
        [start_date, end_date],
    ).fetchdf()

    if result.empty:
        return gpd.GeoDataFrame()

    # Convert to GeoDataFrame
    from shapely import wkt

    result["geometry"] = result["geometry"].apply(wkt.loads)  # pyright: ignore
    return gpd.GeoDataFrame(result, geometry="geometry", crs="EPSG:4326")


def get_fires_in_bbox(
    conn: duckdb.DuckDBPyConnection, bbox: Tuple[float, float, float, float]
) -> gpd.GeoDataFrame:
    """
    Get fires within bounding box.

    Args:
        conn: DuckDB connection
        bbox: (west, south, east, north) in WGS84

    Returns:
        GeoDataFrame with fires
    """
    west, south, east, north = bbox

    result = conn.execute(
        """
        SELECT
            fire_id,
            latitude,
            longitude,
            ST_AsText(geom) as geometry,
            brightness,
            confidence,
            frp,
            acq_date,
            acq_datetime,
            risk_score,
            risk_category
        FROM fires
        WHERE latitude BETWEEN ? AND ?
          AND longitude BETWEEN ? AND ?
        ORDER BY risk_score DESC
    """,
        [south, north, west, east],
    ).fetchdf()

    if result.empty:
        return gpd.GeoDataFrame()

    from shapely import wkt

    result["geometry"] = result["geometry"].apply(wkt.loads)  # pyright: ignore
    return gpd.GeoDataFrame(result, geometry="geometry", crs="EPSG:4326")
