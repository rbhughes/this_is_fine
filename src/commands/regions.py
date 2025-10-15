"""Region presets for common geographic areas."""

from typing import Dict, Tuple

# Bounding box format: (west, south, east, north)
REGIONS: Dict[str, Tuple[float, float, float, float]] = {
    # Full coverage
    "conus": (-125, 24, -66, 49),
    "continental-us": (-125, 24, -66, 49),
    # Western states
    "california": (-124.5, 32.5, -114.13, 42.0),
    "ca": (-124.5, 32.5, -114.13, 42.0),
    "oregon": (-124.6, 41.9, -116.5, 46.3),
    "or": (-124.6, 41.9, -116.5, 46.3),
    "washington": (-124.8, 45.5, -116.9, 49.0),
    "wa": (-124.8, 45.5, -116.9, 49.0),
    "nevada": (-120.0, 35.0, -114.0, 42.0),
    "nv": (-120.0, 35.0, -114.0, 42.0),
    "arizona": (-114.8, 31.3, -109.0, 37.0),
    "az": (-114.8, 31.3, -109.0, 37.0),
    "new-mexico": (-109.0, 31.3, -103.0, 37.0),
    "nm": (-109.0, 31.3, -103.0, 37.0),
    "colorado": (-109.1, 37.0, -102.0, 41.0),
    "co": (-109.1, 37.0, -102.0, 41.0),
    "montana": (-116.1, 44.4, -104.0, 49.0),
    "mt": (-116.1, 44.4, -104.0, 49.0),
    "idaho": (-117.2, 41.9, -111.0, 49.0),
    "id": (-117.2, 41.9, -111.0, 49.0),
    "wyoming": (-111.1, 41.0, -104.0, 45.0),
    "wy": (-111.1, 41.0, -104.0, 45.0),
    # Midwest states
    "indiana": (-88.1, 37.8, -84.8, 41.8),
    "in": (-88.1, 37.8, -84.8, 41.8),
    "illinois": (-91.5, 37.0, -87.5, 42.5),
    "il": (-91.5, 37.0, -87.5, 42.5),
    "ohio": (-84.8, 38.4, -80.5, 42.0),
    "oh": (-84.8, 38.4, -80.5, 42.0),
    "michigan": (-90.4, 41.7, -82.4, 48.3),
    "mi": (-90.4, 41.7, -82.4, 48.3),
    "wisconsin": (-92.9, 42.5, -86.8, 47.1),
    "wi": (-92.9, 42.5, -86.8, 47.1),
    "minnesota": (-97.2, 43.5, -89.5, 49.4),
    "mn": (-97.2, 43.5, -89.5, 49.4),
    "iowa": (-96.6, 40.4, -90.1, 43.5),
    "ia": (-96.6, 40.4, -90.1, 43.5),
    "missouri": (-95.8, 36.0, -89.1, 40.6),
    "mo": (-95.8, 36.0, -89.1, 40.6),
    # Southern states
    "texas": (-106.7, 25.8, -93.5, 36.5),
    "tx": (-106.7, 25.8, -93.5, 36.5),
    "oklahoma": (-103.0, 33.6, -94.4, 37.0),
    "ok": (-103.0, 33.6, -94.4, 37.0),
    "louisiana": (-94.1, 28.9, -88.8, 33.0),
    "la": (-94.1, 28.9, -88.8, 33.0),
    "mississippi": (-91.7, 30.2, -88.1, 35.0),
    "ms": (-91.7, 30.2, -88.1, 35.0),
    "alabama": (-88.5, 30.2, -84.9, 35.0),
    "al": (-88.5, 30.2, -84.9, 35.0),
    "florida": (-87.6, 24.5, -80.0, 31.0),
    "fl": (-87.6, 24.5, -80.0, 31.0),
    "georgia": (-85.6, 30.4, -80.8, 35.0),
    "ga": (-85.6, 30.4, -80.8, 35.0),
    # Eastern states
    "north-carolina": (-84.3, 33.8, -75.4, 36.6),
    "nc": (-84.3, 33.8, -75.4, 36.6),
    "virginia": (-83.7, 36.5, -75.2, 39.5),
    "va": (-83.7, 36.5, -75.2, 39.5),
    "pennsylvania": (-80.5, 39.7, -74.7, 42.3),
    "pa": (-80.5, 39.7, -74.7, 42.3),
    "new-york": (-79.8, 40.5, -71.9, 45.0),
    "ny": (-79.8, 40.5, -71.9, 45.0),
    # Regions
    "pacific-northwest": (-124.8, 41.9, -111.0, 49.0),
    "pnw": (-124.8, 41.9, -111.0, 49.0),
    "southwest": (-124.5, 31.3, -109.0, 42.0),
    "sw": (-124.5, 31.3, -109.0, 42.0),
    "rocky-mountains": (-117.2, 37.0, -102.0, 49.0),
    "rockies": (-117.2, 37.0, -102.0, 49.0),
    "great-plains": (-104.0, 33.6, -96.4, 49.0),
    "southeast": (-94.1, 24.5, -75.4, 36.6),
    "se": (-94.1, 24.5, -75.4, 36.6),
}


def get_region_bbox(region: str) -> Tuple[float, float, float, float] | None:
    """
    Get bounding box for a named region.

    Args:
        region: Region name (e.g., "california", "ca", "indiana")

    Returns:
        Bounding box (west, south, east, north) or None if not found
    """
    return REGIONS.get(region.lower())


def list_regions() -> Dict[str, Tuple[float, float, float, float]]:
    """
    Get all available region presets.

    Returns:
        Dictionary mapping region names to bounding boxes
    """
    return REGIONS.copy()


def get_region_names() -> list[str]:
    """
    Get list of all region names.

    Returns:
        List of region name strings
    """
    return sorted(REGIONS.keys())
