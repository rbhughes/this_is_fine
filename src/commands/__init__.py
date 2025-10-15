"""Command functions for CLI and MCP tools."""

from .fetch_fires import fetch_fires_for_region, fetch_fires_for_bbox
from .database import clear_database, get_database_stats
from .industrial import analyze_industrial_sources

__all__ = [
    "fetch_fires_for_region",
    "fetch_fires_for_bbox",
    "clear_database",
    "get_database_stats",
    "analyze_industrial_sources",
]
