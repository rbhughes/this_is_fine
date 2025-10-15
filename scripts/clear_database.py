#!/usr/bin/env python3
"""
Clear fire data from the DuckDB database.

This script clears the fires and fire_buffers tables, useful when:
- Switching between different geographic regions
- Changing filtering settings (industrial vs. no industrial)
- Starting fresh with new ETL parameters

Usage:
    uv run python scripts/clear_database.py
"""

import duckdb
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def clear_database(db_path: str | None = None) -> None:
    """
    Clear all fire and buffer data from database.

    Args:
        db_path: Path to DuckDB database (defaults to env DATABASE_PATH)
    """
    if db_path is None:
        db_path = os.getenv("DATABASE_PATH", "data/wildfire.duckdb")

    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return

    print(f"📁 Database: {db_path}")

    # Connect and check current data
    conn = duckdb.connect(db_path)
    conn.install_extension("spatial")
    conn.load_extension("spatial")

    # Get current counts
    fires_count = conn.execute("SELECT COUNT(*) FROM fires").fetchone()[0]
    buffers_count = conn.execute("SELECT COUNT(*) FROM fire_buffers").fetchone()[0]

    print(f"\nCurrent data:")
    print(f"  Fires: {fires_count:,}")
    print(f"  Buffers: {buffers_count:,}")

    if fires_count == 0 and buffers_count == 0:
        print("\n✅ Database is already empty")
        conn.close()
        return

    # Confirm deletion
    print()
    response = input("🗑️  Delete all fire and buffer data? (y/N): ").strip().lower()

    if response == "y":
        # Clear tables
        conn.execute("DELETE FROM fire_buffers")
        conn.execute("DELETE FROM fires")
        conn.commit()

        print("\n✅ Database cleared successfully!")
        print("\nNext steps:")
        print("  1. Run ETL with your desired parameters:")
        print(
            '     uv run python -c "from flows.etl_flow import wildfire_etl_flow; wildfire_etl_flow(bbox=(-88.1, 37.8, -84.8, 41.8))"'
        )
        print("  2. Open Jupyter notebook to visualize:")
        print("     uv run jupyter notebook notebooks/kepler.ipynb")
    else:
        print("\n❌ Deletion cancelled")

    conn.close()


def clear_date_range(start_date: str, end_date: str | None = None) -> None:
    """
    Clear fire data for a specific date range.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format (defaults to start_date)
    """
    db_path = os.getenv("DATABASE_PATH", "data/wildfire.duckdb")

    if end_date is None:
        end_date = start_date

    conn = duckdb.connect(db_path)
    conn.install_extension("spatial")
    conn.load_extension("spatial")

    # Check what will be deleted
    count = conn.execute(
        "SELECT COUNT(*) FROM fires WHERE acq_date BETWEEN ? AND ?",
        [start_date, end_date],
    ).fetchone()[0]

    print(f"📅 Date range: {start_date} to {end_date}")
    print(f"   Fires to delete: {count}")

    if count == 0:
        print("✅ No fires found in this date range")
        conn.close()
        return

    response = input("\n🗑️  Delete these fires? (y/N): ").strip().lower()

    if response == "y":
        # Delete fires
        conn.execute(
            "DELETE FROM fires WHERE acq_date BETWEEN ? AND ?", [start_date, end_date]
        )

        # Delete orphaned buffers
        conn.execute("""
            DELETE FROM fire_buffers
            WHERE fire_id NOT IN (SELECT fire_id FROM fires)
        """)

        conn.commit()
        print("✅ Date range cleared successfully!")
    else:
        print("❌ Deletion cancelled")

    conn.close()


def main() -> None:
    """Main entry point."""
    print("=" * 60)
    print("DuckDB Fire Database Cleanup Utility")
    print("=" * 60)
    print()

    print("Options:")
    print("  1. Clear all data (full reset)")
    print("  2. Clear specific date range")
    print("  3. Exit")
    print()

    choice = input("Select option (1-3): ").strip()

    if choice == "1":
        clear_database()
    elif choice == "2":
        start = input("Start date (YYYY-MM-DD): ").strip()
        end = input("End date (YYYY-MM-DD, or press Enter for same as start): ").strip()
        if not end:
            end = start
        clear_date_range(start, end)
    else:
        print("Exiting...")


if __name__ == "__main__":
    main()
