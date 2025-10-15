#!/usr/bin/env python3
"""
Minimal test to verify Kepler.gl config is working.
"""

import geopandas as gpd
from keplergl import KeplerGl
from pathlib import Path

# Load data
data_dir = Path("../data/processed")
fires_gdf = gpd.read_file(data_dir / "active_fires.geojson")

print(f"Loaded {len(fires_gdf)} fires")
print(f"Fire bounds: {fires_gdf.total_bounds}")

# Set Colorado center and zoom explicitly
config = {"mapState": {"latitude": 39.0, "longitude": -105.55, "zoom": 6}}

print(f"\nCreating map with config:")
print(f"  Center: (39.0, -105.55)")
print(f"  Zoom: 6")
print(f"\nExpected view: Full Colorado state")

# Create map
map_viz = KeplerGl(height=600, config=config)
map_viz.add_data(data=fires_gdf, name="fires")

# Check if config was applied
print(f"\nMap config keys: {map_viz.config.keys()}")

# Save to HTML to test
map_viz.save_to_html(file_name="../test_colorado_map.html")
print("\n✓ Saved to test_colorado_map.html")
print("Open this file in a browser to see if zoom/center are correct")
