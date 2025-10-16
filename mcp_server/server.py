"""
MCP Server for Wildfire Risk Monitoring System

Provides tools for fetching fire data, enriching with weather/AQI/PurpleAir,
and generating visualizations.
"""

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import mcp.types as types
from pathlib import Path
import sys
import os

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp_server.tools import (
    fetch_fires_tool,
    enrich_weather_tool,
    enrich_aqi_tool,
    enrich_purpleair_tool,
    visualize_fires_tool,
    get_fire_stats_tool,
)


# Create server instance
server = Server("wildfire-risk-mcp")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools for wildfire monitoring.

    Returns tools for:
    - Fetching fire data from NASA FIRMS
    - Enriching with NOAA weather data
    - Enriching with EPA AirNow AQI data
    - Enriching with PurpleAir sensor data
    - Generating visualizations
    - Getting fire statistics
    """
    return [
        types.Tool(
            name="fetch_fires",
            description=(
                "Fetch active fire data from NASA FIRMS for a specified region with optional enrichment. "
                "Can include weather, AQI, and PM2.5 data in a single call. "
                "Optionally filters out industrial heat sources. "
                "Returns fire count and stores data in database."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Region to fetch fires for (e.g., 'california', 'colorado', 'conus')",
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Number of days to look back (default: 2)",
                        "default": 2,
                    },
                    "filter_industrial": {
                        "type": "boolean",
                        "description": "Filter out industrial heat sources (default: true)",
                        "default": True,
                    },
                    "use_weather": {
                        "type": "boolean",
                        "description": "Include NOAA weather data (default: false, slow for large datasets)",
                        "default": False,
                    },
                    "use_aqi": {
                        "type": "boolean",
                        "description": "Include EPA AirNow air quality data (default: false)",
                        "default": False,
                    },
                    "use_purpleair": {
                        "type": "boolean",
                        "description": "Include PurpleAir PM2.5 sensor data (default: false)",
                        "default": False,
                    },
                },
                "required": ["region"],
            },
        ),
        types.Tool(
            name="enrich_weather",
            description=(
                "Enrich existing fire data with NOAA weather information. "
                "Fetches temperature, humidity, wind, precipitation for each fire location. "
                "Updates risk scores with weather data. SLOW: ~1-2 sec per fire."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of fires to enrich (default: all)",
                        "default": None,
                    },
                },
            },
        ),
        types.Tool(
            name="enrich_aqi",
            description=(
                "Enrich existing fire data with EPA AirNow air quality index (AQI). "
                "Finds nearest AQI monitoring station within 50km. "
                "Returns AQI value, category, and pollutant parameter."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of fires to enrich (default: all)",
                        "default": None,
                    },
                },
            },
        ),
        types.Tool(
            name="enrich_purpleair",
            description=(
                "Enrich existing fire data with PurpleAir PM2.5 sensor data. "
                "Averages readings from nearby sensors within 50km radius. "
                "Returns PM2.5 concentration, sensor count, and average distance."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of fires to enrich (default: all)",
                        "default": None,
                    },
                    "radius_km": {
                        "type": "number",
                        "description": "Search radius in kilometers (default: 50)",
                        "default": 50.0,
                    },
                },
            },
        ),
        types.Tool(
            name="visualize_fires",
            description=(
                "Generate interactive map visualizations of fire data. "
                "Creates Plotly HTML maps showing fires, risk zones, and air quality heatmaps. "
                "Returns paths to generated HTML files."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "map_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Types of maps to generate: 'basic', 'risk_heatmap', "
                            "'brightness', 'buffers', 'combined', 'aqi', 'purpleair'. "
                            "Default: all available based on data"
                        ),
                        "default": ["all"],
                    },
                },
            },
        ),
        types.Tool(
            name="get_fire_stats",
            description=(
                "Get summary statistics about current fire data. "
                "Returns counts by risk category, date range, data enrichment status, "
                "and geographic extent."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    """
    if arguments is None:
        arguments = {}

    if name == "fetch_fires":
        result = await fetch_fires_tool(arguments)
    elif name == "enrich_weather":
        result = await enrich_weather_tool(arguments)
    elif name == "enrich_aqi":
        result = await enrich_aqi_tool(arguments)
    elif name == "enrich_purpleair":
        result = await enrich_purpleair_tool(arguments)
    elif name == "visualize_fires":
        result = await visualize_fires_tool(arguments)
    elif name == "get_fire_stats":
        result = await get_fire_stats_tool(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")

    return [types.TextContent(type="text", text=result)]


async def main():
    """Run the MCP server using stdio transport."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="wildfire-risk-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
