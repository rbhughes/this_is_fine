"""Test script to check FIRMS API connection."""

import os
from dotenv import load_dotenv
from src.ingestion.firms_client import FIRMSClient

_ = load_dotenv()

api_key = os.getenv("FIRMS_API_KEY")

if not api_key:
    print("ERROR: FIRMS_API_KEY not found in environment")
    exit(1)

print(f"API Key found: {api_key[:10]}...")

client = FIRMSClient(api_key)

print("\nFetching fires from continental US (last 24 hours)...")
try:
    fires = client.get_continental_us_fires(days=1)
    print(f"✓ API call successful")
    print(f"  Fires detected: {len(fires)}")

    if not fires.empty:
        print(f"\n  Columns: {list(fires.columns)}")
        print(f"\n  First few fires:")
        print(
            fires[
                ["latitude", "longitude", "brightness", "confidence", "acq_date"]
            ].head()
        )
    else:
        print("\n  No fires detected in the last 24 hours")

except Exception as e:
    print(f"✗ API call failed: {e}")
