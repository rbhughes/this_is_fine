"""Debug script to see what columns FIRMS actually returns."""

import os
from dotenv import load_dotenv
import httpx
import pandas as pd
from io import StringIO

_ = load_dotenv()

api_key = os.getenv("FIRMS_API_KEY")
bbox = (-125, 24, -66, 49)  # Continental US
days = 10
source = "VIIRS_NOAA20_NRT"

url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{api_key}/{source}/{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}/{days}"

print(f"Fetching from: {url}\n")

client = httpx.Client(timeout=30.0)
response = client.get(url)

print(f"Status: {response.status_code}")
print(f"Response length: {len(response.text)} chars\n")

# Show first 500 chars of response
print("First 500 chars of response:")
print(response.text[:500])
print("\n" + "=" * 80 + "\n")

# Parse as CSV
df = pd.read_csv(StringIO(response.text))

print(f"DataFrame shape: {df.shape}")
print(f"\nColumn names:")
for i, col in enumerate(df.columns, 1):
    print(f"  {i}. {col}")

print(f"\nFirst few rows:")
print(df.head())

print(f"\nData types:")
print(df.dtypes)
