# src/database/connection.py
"""Database connection management."""

import duckdb
from pathlib import Path
from typing import Optional

_connection: Optional[duckdb.DuckDBPyConnection] = None


def get_connection(db_path: str = "data/wildfire.duckdb") -> duckdb.DuckDBPyConnection:
    """
    Get or create database connection (singleton pattern).

    Args:
        db_path: Path to DuckDB database file

    Returns:
        DuckDB connection
    """
    global _connection

    if _connection is None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _connection = duckdb.connect(db_path)

        # Install and load spatial extension
        _connection.execute("INSTALL spatial")
        _connection.execute("LOAD spatial")

    return _connection


def init_database(db_path: str = "data/wildfire.duckdb") -> duckdb.DuckDBPyConnection:
    """
    Initialize database with schema.

    Args:
        db_path: Path to DuckDB database file

    Returns:
        Initialized DuckDB connection
    """
    from .schema import create_tables

    conn = get_connection(db_path)
    create_tables(conn)

    return conn


def close_connection():
    """Close the database connection."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
