#!/usr/bin/env python3
"""
Test script to verify Kepler.gl map view configuration.
Run this to see what the notebook SHOULD be doing.
"""

from pathlib import Path
import geopandas as gpd
import pandas as pd
import json

data_dir = Path("../data/processed")
fires_gdf = gpd.read_file(data_dir / "active_fires.geojson")
buffers_gdf = gpd.read_file(data_dir / "fire_buffers.geojson")

print(f"✓ Loaded {len(fires_gdf)} fires, {len(buffers_gdf)} buffers")

# Load region metadata
metadata_path = data_dir / "region_metadata.json"
region_bbox = None

if metadata_path.exists():
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
        region_bbox = metadata.get("bbox")
        print(f"✓ Found region metadata: {region_bbox}")
else:
    print("✗ No region metadata found!")

# Determine bounding box
if region_bbox:
    bounds = region_bbox
    print(f"✓ Using region bbox: {bounds}")
else:
    print("✗ Falling back to data bounds (THIS IS THE PROBLEM)")
    bounds = fires_gdf.total_bounds.tolist()

# Calculate view
center_lon = (bounds[0] + bounds[2]) / 2
center_lat = (bounds[1] + bounds[3]) / 2
lon_diff = bounds[2] - bounds[0]
lat_diff = bounds[3] - bounds[1]
max_diff = max(lon_diff, lat_diff)

if max_diff > 5:
    zoom = 6
elif max_diff > 2:
    zoom = 7
else:
    zoom = 8

print(f"\n{'=' * 60}")
print("EXPECTED MAP VIEW:")
print(f"  Center: ({center_lat:.2f}, {center_lon:.2f})")
print(f"  Zoom: {zoom}")
print(f"  Extent: {lon_diff:.1f}° × {lat_diff:.1f}°")
print(f"{'=' * 60}")

# Show the config that should be passed to Kepler
config = {"mapState": {"latitude": center_lat, "longitude": center_lon, "zoom": zoom}}

print("\nKepler config:")
print(json.dumps(config, indent=2))

# Compare to fire data extent
fire_bounds = fires_gdf.total_bounds
fire_extent = fire_bounds[2] - fire_bounds[0]
print(f"\nFire data extent: {fire_extent:.2f}° (without padding)")
print(f"Region extent: {lon_diff:.1f}°")

if fire_extent < 1 and lon_diff > 5:
    print("\n✓ CORRECT: Using full region bbox, not just fire locations")
else:
    print("\n✗ PROBLEM: Not using region bbox properly")
