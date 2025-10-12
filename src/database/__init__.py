# src/database/__init__.py
"""Database package for wildfire monitoring."""

from .connection import get_connection, init_database
from .operations import save_fires_to_db, get_fires_by_date, get_fires_in_bbox
from .schema import create_tables

__all__ = [
    "get_connection",
    "init_database",
    "save_fires_to_db",
    "get_fires_by_date",
    "get_fires_in_bbox",
    "create_tables",
]
