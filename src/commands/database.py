"""Database management commands - MCP and CLI compatible."""

import os
from typing import Dict, Any
from pathlib import Path
import duckdb
from dotenv import load_dotenv

load_dotenv()


def get_database_stats() -> Dict[str, Any]:
    """
    Get statistics about the fire database.

    MCP-compatible function that returns current database state.

    Returns:
        Dictionary with database stats:
        {
            "success": bool,
            "total_fires": int,
            "total_buffers": int,
            "date_range": tuple or None,
            "geographic_extent": dict,
            "message": str
        }
    """
    db_path = os.getenv("DATABASE_PATH", "data/wildfire.duckdb")

    if not Path(db_path).exists():
        return {
            "success": False,
            "total_fires": 0,
            "total_buffers": 0,
            "date_range": None,
            "geographic_extent": None,
            "message": f"Database not found: {db_path}",
        }

    try:
        conn = duckdb.connect(db_path)
        conn.install_extension("spatial")
        conn.load_extension("spatial")

        # Get fire count and date range
        fire_stats = conn.execute("""
            SELECT
                COUNT(*) as total,
                MIN(acq_date) as earliest,
                MAX(acq_date) as latest
            FROM fires
        """).fetchone()

        # Get buffer count
        buffer_count = conn.execute("SELECT COUNT(*) FROM fire_buffers").fetchone()[0]

        # Get geographic extent
        extent = conn.execute("""
            SELECT
                MIN(longitude) as west,
                MIN(latitude) as south,
                MAX(longitude) as east,
                MAX(latitude) as north
            FROM fires
        """).fetchone()

        conn.close()

        date_range = None
        if fire_stats[1] is not None and fire_stats[2] is not None:
            date_range = (str(fire_stats[1]), str(fire_stats[2]))

        geographic_extent = None
        if extent[0] is not None:
            geographic_extent = {
                "west": extent[0],
                "south": extent[1],
                "east": extent[2],
                "north": extent[3],
            }

        return {
            "success": True,
            "total_fires": fire_stats[0],
            "total_buffers": buffer_count,
            "date_range": date_range,
            "geographic_extent": geographic_extent,
            "message": f"Database contains {fire_stats[0]:,} fires and {buffer_count:,} buffers",
        }

    except Exception as e:
        return {
            "success": False,
            "total_fires": 0,
            "total_buffers": 0,
            "date_range": None,
            "geographic_extent": None,
            "message": f"Error reading database: {str(e)}",
        }


def clear_database(confirm: bool = False) -> Dict[str, Any]:
    """
    Clear all fire data from the database.

    MCP-compatible function to reset the database.

    Args:
        confirm: Must be True to actually clear data (safety check)

    Returns:
        Dictionary with result:
        {
            "success": bool,
            "fires_deleted": int,
            "buffers_deleted": int,
            "message": str
        }
    """
    if not confirm:
        return {
            "success": False,
            "fires_deleted": 0,
            "buffers_deleted": 0,
            "message": "Confirmation required. Set confirm=True to proceed.",
        }

    db_path = os.getenv("DATABASE_PATH", "data/wildfire.duckdb")

    if not Path(db_path).exists():
        return {
            "success": False,
            "fires_deleted": 0,
            "buffers_deleted": 0,
            "message": f"Database not found: {db_path}",
        }

    try:
        conn = duckdb.connect(db_path)
        conn.install_extension("spatial")
        conn.load_extension("spatial")

        # Get counts before deletion
        fire_count = conn.execute("SELECT COUNT(*) FROM fires").fetchone()[0]
        buffer_count = conn.execute("SELECT COUNT(*) FROM fire_buffers").fetchone()[0]

        # Clear tables
        conn.execute("DELETE FROM fire_buffers")
        conn.execute("DELETE FROM fires")
        conn.commit()
        conn.close()

        return {
            "success": True,
            "fires_deleted": fire_count,
            "buffers_deleted": buffer_count,
            "message": f"Deleted {fire_count:,} fires and {buffer_count:,} buffers",
        }

    except Exception as e:
        return {
            "success": False,
            "fires_deleted": 0,
            "buffers_deleted": 0,
            "message": f"Error clearing database: {str(e)}",
        }


def clear_date_range(
    start_date: str, end_date: str | None = None, confirm: bool = False
) -> Dict[str, Any]:
    """
    Clear fire data for a specific date range.

    MCP-compatible function to selectively clear data.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (defaults to start_date)
        confirm: Must be True to actually delete data

    Returns:
        Dictionary with result:
        {
            "success": bool,
            "fires_deleted": int,
            "buffers_deleted": int,
            "date_range": tuple,
            "message": str
        }
    """
    if not confirm:
        return {
            "success": False,
            "fires_deleted": 0,
            "buffers_deleted": 0,
            "date_range": (start_date, end_date or start_date),
            "message": "Confirmation required. Set confirm=True to proceed.",
        }

    if end_date is None:
        end_date = start_date

    db_path = os.getenv("DATABASE_PATH", "data/wildfire.duckdb")

    try:
        conn = duckdb.connect(db_path)
        conn.install_extension("spatial")
        conn.load_extension("spatial")

        # Count fires to delete
        fire_count = conn.execute(
            "SELECT COUNT(*) FROM fires WHERE acq_date BETWEEN ? AND ?",
            [start_date, end_date],
        ).fetchone()[0]

        # Delete fires
        conn.execute(
            "DELETE FROM fires WHERE acq_date BETWEEN ? AND ?",
            [start_date, end_date],
        )

        # Delete orphaned buffers
        conn.execute("""
            DELETE FROM fire_buffers
            WHERE fire_id NOT IN (SELECT fire_id FROM fires)
        """)

        buffer_count = conn.get_table_names()  # Simplified for now
        conn.commit()
        conn.close()

        return {
            "success": True,
            "fires_deleted": fire_count,
            "buffers_deleted": 0,  # Would need to track this separately
            "date_range": (start_date, end_date),
            "message": f"Deleted {fire_count:,} fires from {start_date} to {end_date}",
        }

    except Exception as e:
        return {
            "success": False,
            "fires_deleted": 0,
            "buffers_deleted": 0,
            "date_range": (start_date, end_date),
            "message": f"Error: {str(e)}",
        }
