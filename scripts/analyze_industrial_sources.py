#!/usr/bin/env python3
"""
Analyze and identify persistent industrial heat sources in fire detection data.

This script helps you:
1. Identify locations with repeated fire detections (likely industrial)
2. Export them for manual review
3. Visualize them alongside actual fires
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.filters.industrial_filter import IndustrialHeatFilter
import geopandas as gpd


def main():
    """Analyze persistent anomalies in fire detection data."""

    print("=" * 60)
    print("Industrial Heat Source Analysis")
    print("=" * 60)

    # Initialize filter
    filter_obj = IndustrialHeatFilter("data/wildfire.duckdb")

    # Identify persistent anomalies with different thresholds
    print("\n1. Analyzing with conservative threshold (5+ detections over 30 days)...")
    persistent = filter_obj.identify_persistent_anomalies(
        lookback_days=30, detection_threshold=5, grid_size_km=0.4
    )

    if len(persistent) == 0:
        print("\nNo persistent anomalies found with current threshold.")
        print("This could mean:")
        print("  - Not enough historical data (need 30+ days)")
        print("  - Detection threshold too high (try threshold=3)")
        print("  - No industrial sources in your area")
        return

    # Display summary statistics
    print("\n" + "=" * 60)
    print("PERSISTENT ANOMALY SUMMARY")
    print("=" * 60)
    print(f"\nTotal persistent locations: {len(persistent)}")
    print(f"\nTop 10 by detection count:")
    print(
        persistent[
            [
                "latitude",
                "longitude",
                "detection_count",
                "unique_days",
                "detections_per_day",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    # Save to file (static reference data)
    print("\n2. Saving persistent anomalies...")
    filter_obj.save_persistent_locations("data/static/persistent_anomalies.geojson")

    # Also save as CSV for easy review
    persistent_csv = persistent.drop(columns=["geometry"])
    persistent_csv.to_csv("data/static/persistent_anomalies.csv", index=False)
    print("   - GeoJSON: data/static/persistent_anomalies.geojson")
    print("   - CSV: data/static/persistent_anomalies.csv")

    # Categorize by persistence
    print("\n3. Categorizing by persistence level...")
    persistent["persistence_level"] = "Unknown"
    persistent.loc[persistent["detections_per_day"] >= 2.0, "persistence_level"] = (
        "Very High (likely industrial)"
    )
    persistent.loc[
        (persistent["detections_per_day"] >= 1.0)
        & (persistent["detections_per_day"] < 2.0),
        "persistence_level",
    ] = "High (likely industrial)"
    persistent.loc[
        (persistent["detections_per_day"] >= 0.5)
        & (persistent["detections_per_day"] < 1.0),
        "persistence_level",
    ] = "Moderate (review needed)"
    persistent.loc[persistent["detections_per_day"] < 0.5, "persistence_level"] = (
        "Low (possibly legitimate fire)"
    )

    print("\nPersistence Breakdown:")
    for level in [
        "Very High (likely industrial)",
        "High (likely industrial)",
        "Moderate (review needed)",
        "Low (possibly legitimate fire)",
    ]:
        count = len(persistent[persistent["persistence_level"] == level])
        if count > 0:
            print(f"   {level}: {count} locations")

    # Manual review suggestions
    print("\n" + "=" * 60)
    print("NEXT STEPS FOR MANUAL REVIEW")
    print("=" * 60)
    print("\n1. Load persistent_anomalies.geojson into Kepler.gl or QGIS")
    print("2. Review high-persistence locations using satellite imagery:")
    print("   - Google Maps: Look for industrial facilities")
    print("   - Sentinel Hub: Check for gas flares, thermal activity")
    print("3. Locations to investigate first (very high persistence):")

    very_high = persistent[
        persistent["persistence_level"] == "Very High (likely industrial)"
    ].head(5)
    for _, row in very_high.iterrows():
        google_maps_url = (
            f"https://www.google.com/maps/@{row['latitude']},{row['longitude']},15z"
        )
        print(f"\n   Location: {row['latitude']:.4f}, {row['longitude']:.4f}")
        print(
            f"   Detections: {row['detection_count']} over {row['unique_days']} days ({row['detections_per_day']:.2f}/day)"
        )
        print(f"   View: {google_maps_url}")

    # Test filtering with recent fires
    print("\n" + "=" * 60)
    print("TESTING FILTER WITH RECENT FIRES")
    print("=" * 60)

    try:
        recent_fires = gpd.read_file("data/processed/active_fires.geojson")
        print(f"\nCurrent fire count: {len(recent_fires)}")

        filtered, excluded = filter_obj.filter_fires(
            recent_fires, buffer_km=0.5, persistent_locations=persistent
        )

        print(
            f"After filtering: {len(filtered)} fires (excluded {len(excluded)} near persistent sources)"
        )

        if len(excluded) > 0:
            print(f"\nExcluded fire locations (likely industrial):")
            print(
                excluded[["latitude", "longitude", "bright_ti4", "frp"]]
                .head(10)
                .to_string(index=False)
            )

            # Save excluded fires for review
            excluded.to_file(
                "data/processed/excluded_industrial_fires.geojson", driver="GeoJSON"
            )
            print("\n   Saved to: data/processed/excluded_industrial_fires.geojson")
    except FileNotFoundError:
        print("\nNo active_fires.geojson found - run ETL flow first to test filtering")

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print("\nFiles created:")
    print("  - data/static/persistent_anomalies.geojson (static reference data)")
    print("  - data/static/persistent_anomalies.csv (for spreadsheet review)")
    print(
        "  - data/processed/excluded_industrial_fires.geojson (fires that would be filtered)"
    )
    print("\nTo use filtering in ETL flow:")
    print("  wildfire_etl_flow(filter_industrial=True)")


if __name__ == "__main__":
    main()
