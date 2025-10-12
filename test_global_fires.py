"""Test script to check for fires in various regions."""

import os
from dotenv import load_dotenv
from src.ingestion.firms_client import FIRMSClient

load_dotenv()

api_key = os.getenv("FIRMS_API_KEY")
client = FIRMSClient(api_key)

# Define regions to check (west, south, east, north)
regions = {
    "Continental US": (-125, 24, -66, 49),
    "Australia": (113, -44, 154, -10),
    "Amazon (Brazil)": (-74, -16, -47, 5),
    "Southeast Asia": (95, -10, 141, 20),
    "Southern Europe": (-10, 36, 45, 47),
    "Sub-Saharan Africa": (15, -35, 52, 15),
    "California": (-125, 32, -114, 42),
}

print("Checking for active fires worldwide (last 24 hours):\n")

total_fires = 0
for region_name, bbox in regions.items():
    try:
        fires = client.get_active_fires(bbox, days=1)
        count = len(fires)
        total_fires += count
        status = "🔥" if count > 0 else "  "
        print(f"{status} {region_name:25} {count:5} fires")

        if count > 0 and count <= 5:
            print(
                f"     Locations: {list(zip(fires['latitude'].values, fires['longitude'].values))}"
            )
    except Exception as e:
        print(f"   {region_name:25} ERROR: {e}")

print(f"\nTotal fires detected worldwide: {total_fires}")
