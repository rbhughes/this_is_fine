#!/usr/bin/env python3
"""
CLI for the wildfire risk monitoring system.

This CLI wraps discrete command functions that are also used by the MCP server,
ensuring consistency between CLI and programmatic access.
"""

import click
from typing import Optional
import json

from src.commands.fetch_fires import (
    fetch_fires_for_region,
    fetch_fires_for_bbox,
    get_fires_summary,
)
from src.commands.database import (
    get_database_stats,
    clear_database,
    clear_date_range,
)
from src.commands.industrial import (
    analyze_industrial_sources,
    get_persistent_locations,
)
from src.commands.regions import get_region_names, get_region_bbox


@click.group()
@click.version_option(version="0.1.0", prog_name="wildfire")
def cli():
    """
    Wildfire Risk Monitoring System CLI.

    A tool for fetching, analyzing, and visualizing wildfire data from NASA FIRMS
    with intelligent industrial heat source filtering.
    """
    pass


@cli.command()
@click.option(
    "--region",
    "-r",
    help="Region name (e.g., california, indiana, pacific-northwest)",
)
@click.option(
    "--bbox",
    "-b",
    help="Custom bounding box: west,south,east,north (e.g., -124.5,32.5,-114,42)",
)
@click.option(
    "--days",
    "-d",
    default=2,
    type=int,
    help="Days to look back (1-10, default: 2)",
)
@click.option(
    "--buffer",
    default=5.0,
    type=float,
    help="Buffer radius in km (default: 5.0)",
)
@click.option(
    "--fires",
    is_flag=True,
    default=True,
    help="Fetch FIRMS fire data (default: enabled)",
)
@click.option(
    "--weather",
    is_flag=True,
    default=False,
    help="Enrich with NOAA weather data (slower but more accurate)",
)
@click.option(
    "--aqi",
    is_flag=True,
    default=False,
    help="Enrich with AirNow air quality data",
)
@click.option(
    "--purpleair",
    is_flag=True,
    default=False,
    help="Enrich with PurpleAir sensor data (real-time PM2.5)",
)
@click.option(
    "--filter-industrial/--no-filter-industrial",
    default=True,
    help="Filter out industrial heat sources (default: enabled)",
)
@click.option(
    "--dissolve/--no-dissolve",
    default=True,
    help="Merge overlapping buffers by risk category (default: enabled)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON",
)
def fetch(
    region: Optional[str],
    bbox: Optional[str],
    days: int,
    buffer: float,
    fires: bool,
    weather: bool,
    aqi: bool,
    purpleair: bool,
    filter_industrial: bool,
    dissolve: bool,
    output_json: bool,
):
    """
    Fetch and process fire data for a region or bounding box.

    Data Sources:
      --fires      FIRMS satellite fire detections (default: enabled)
      --weather    NOAA weather enrichment (slow: ~1-2 sec/fire)
      --aqi        AirNow official air quality (sparse coverage)
      --purpleair  PurpleAir sensors (dense real-time PM2.5)

    Examples:

      # Just fires (fast, default)
      wildfire fetch --region indiana

      # Fires + weather data
      wildfire fetch --region california --weather

      # Fires + PurpleAir smoke tracking
      wildfire fetch --region colorado --purpleair

      # Fires + both air quality sources
      wildfire fetch --region california --aqi --purpleair

      # All data sources
      wildfire fetch --region pnw --weather --aqi --purpleair

      # Custom bounding box around Phoenix
      wildfire fetch --bbox -113,32.5,-111,34.5 --buffer 3
    """
    if not region and not bbox:
        click.echo("Error: Must specify either --region or --bbox", err=True)
        click.echo("Use 'wildfire regions' to see available regions", err=True)
        raise click.Abort()

    if region and bbox:
        click.echo("Error: Cannot specify both --region and --bbox", err=True)
        raise click.Abort()

    # Fetch fires
    if region:
        result = fetch_fires_for_region(
            region=region,
            days_back=days,
            buffer_km=buffer,
            use_weather=weather,
            use_aqi=aqi,
            use_purpleair=purpleair,
            filter_industrial=filter_industrial,
            dissolve_buffers=dissolve,
        )
    else:
        # Parse bbox
        try:
            bbox_parts = [float(x.strip()) for x in bbox.split(",")]
            if len(bbox_parts) != 4:
                raise ValueError("Bounding box must have 4 values")
            bbox_tuple = tuple(bbox_parts)
        except (ValueError, AttributeError) as e:
            click.echo(f"Error: Invalid bounding box format: {e}", err=True)
            click.echo(
                "Expected: west,south,east,north (e.g., -124.5,32.5,-114,42)", err=True
            )
            raise click.Abort()

        result = fetch_fires_for_bbox(
            bbox=bbox_tuple,
            days_back=days,
            buffer_km=buffer,
            use_weather=weather,
            use_aqi=aqi,
            use_purpleair=purpleair,
            filter_industrial=filter_industrial,
            dissolve_buffers=dissolve,
        )

    # Output results
    if output_json:
        click.echo(json.dumps(result, indent=2))
    else:
        if result["success"]:
            click.echo(f"✓ {result['message']}")
            if result["fires_processed"] > 0:
                click.echo(f"\nOutput files:")
                for f in result["output_files"]:
                    click.echo(f"  • {f}")
        else:
            click.echo(f"✗ {result['message']}", err=True)
            raise click.Abort()


@cli.command()
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def summary(output_json: bool):
    """
    Show summary of currently processed fire data.

    Displays statistics from the latest processed fires and buffers.
    """
    result = get_fires_summary()

    if output_json:
        click.echo(json.dumps(result, indent=2))
    else:
        if result["success"]:
            click.echo(f"Fire Data Summary")
            click.echo(f"─" * 40)
            click.echo(f"Total fires: {result['total_fires']:,}")
            click.echo(f"Total buffers: {result['total_buffers']:,}")

            if result["date_range"]:
                click.echo(
                    f"Date range: {result['date_range'][0]} to {result['date_range'][1]}"
                )

            if result["risk_breakdown"]:
                click.echo(f"\nRisk breakdown:")
                for category, count in result["risk_breakdown"].items():
                    click.echo(f"  {category}: {count:,}")
        else:
            click.echo(f"✗ {result['message']}", err=True)


@cli.command()
def regions():
    """
    List all available region presets.

    Shows predefined regions that can be used with the --region flag.
    """
    regions_list = get_region_names()

    # Group by category
    states = [r for r in regions_list if len(r) <= 3 or "-" not in r]
    multi_region = [r for r in regions_list if "-" in r and len(r) > 3]

    click.echo("Available Regions")
    click.echo("=" * 50)

    click.echo("\nUS States (full name or abbreviation):")
    click.echo("─" * 50)
    for i in range(0, len(states), 4):
        row = states[i : i + 4]
        click.echo("  " + "  ".join(f"{r:15}" for r in row))

    click.echo("\nMulti-State Regions:")
    click.echo("─" * 50)
    for region in multi_region:
        bbox = get_region_bbox(region)
        click.echo(f"  {region:20} {bbox}")


@cli.command()
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def db_stats(output_json: bool):
    """
    Show database statistics.

    Displays information about fires and buffers stored in DuckDB.
    """
    result = get_database_stats()

    if output_json:
        click.echo(json.dumps(result, indent=2))
    else:
        if result["success"]:
            click.echo("Database Statistics")
            click.echo("─" * 40)
            click.echo(f"Total fires: {result['total_fires']:,}")
            click.echo(f"Total buffers: {result['total_buffers']:,}")

            if result["date_range"]:
                click.echo(
                    f"Date range: {result['date_range'][0]} to {result['date_range'][1]}"
                )

            if result["geographic_extent"]:
                ext = result["geographic_extent"]
                click.echo(f"\nGeographic extent:")
                click.echo(f"  West: {ext['west']:.2f}")
                click.echo(f"  South: {ext['south']:.2f}")
                click.echo(f"  East: {ext['east']:.2f}")
                click.echo(f"  North: {ext['north']:.2f}")
        else:
            click.echo(f"✗ {result['message']}", err=True)


@cli.command()
@click.confirmation_option(prompt="Are you sure you want to clear all fire data?")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def clear(output_json: bool):
    """
    Clear all fire data from the database.

    ⚠️  This will delete all fires and buffers. Use with caution!
    """
    result = clear_database(confirm=True)

    if output_json:
        click.echo(json.dumps(result, indent=2))
    else:
        if result["success"]:
            click.echo(f"✓ {result['message']}")
        else:
            click.echo(f"✗ {result['message']}", err=True)


@cli.command()
@click.option(
    "--days",
    "-d",
    default=30,
    type=int,
    help="Days of history to analyze (default: 30)",
)
@click.option(
    "--threshold",
    "-t",
    default=5,
    type=int,
    help="Minimum detections to flag as persistent (default: 5)",
)
@click.option(
    "--grid-size",
    "-g",
    default=0.4,
    type=float,
    help="Grid cell size in km (default: 0.4)",
)
@click.option(
    "--no-save",
    is_flag=True,
    help="Don't save results to file",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def analyze_industrial(
    days: int,
    threshold: int,
    grid_size: float,
    no_save: bool,
    output_json: bool,
):
    """
    Identify persistent industrial heat sources.

    Analyzes historical fire data to find locations with repeated thermal
    detections (steel plants, refineries, gas flares, etc.).

    Examples:

      # Standard analysis (30 days, 5+ detections)
      wildfire analyze-industrial

      # More sensitive (catch sources with fewer detections)
      wildfire analyze-industrial --days 14 --threshold 3

      # Coarser grid for broader analysis
      wildfire analyze-industrial --grid-size 1.0
    """
    result = analyze_industrial_sources(
        lookback_days=days,
        detection_threshold=threshold,
        grid_size_km=grid_size,
        save=not no_save,
    )

    if output_json:
        click.echo(json.dumps(result, indent=2))
    else:
        if result["success"]:
            click.echo(f"✓ {result['message']}")
            if result["persistent_locations_found"] > 0:
                click.echo(
                    f"\nFound {result['persistent_locations_found']} persistent locations:"
                )
                click.echo(f"  Lookback: {days} days")
                click.echo(f"  Threshold: {threshold}+ detections")
                click.echo(f"  Grid size: {grid_size} km")

                if result["output_file"]:
                    click.echo(f"\n✓ Saved to: {result['output_file']}")

                # Show sample locations
                if len(result["locations"]) > 0:
                    click.echo(f"\nTop persistent sources:")
                    for loc in sorted(
                        result["locations"],
                        key=lambda x: x["detection_count"],
                        reverse=True,
                    )[:5]:
                        click.echo(
                            f"  Lat: {loc['latitude']:.4f}, "
                            f"Lon: {loc['longitude']:.4f}, "
                            f"Detections: {loc['detection_count']} "
                            f"({loc['detections_per_day']:.1f}/day)"
                        )
        else:
            click.echo(f"✗ {result['message']}", err=True)


@cli.command()
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def show_industrial(output_json: bool):
    """
    Show current persistent industrial heat source locations.

    Displays the saved list of known industrial sources that are
    filtered out during fire detection.
    """
    result = get_persistent_locations()

    if output_json:
        click.echo(json.dumps(result, indent=2))
    else:
        if result["success"]:
            click.echo(f"Persistent Industrial Locations")
            click.echo("─" * 60)
            click.echo(f"Total locations: {result['total_locations']}\n")

            # Show all locations
            for i, loc in enumerate(result["locations"], 1):
                click.echo(
                    f"{i:3}. Lat: {loc['latitude']:7.4f}, "
                    f"Lon: {loc['longitude']:8.4f}, "
                    f"Detections: {loc['detection_count']:3} over {loc['unique_days']:2} days"
                )
        else:
            click.echo(f"✗ {result['message']}", err=True)


if __name__ == "__main__":
    cli()
