# src/analysis/risk_calculator.py
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import numpy as np


class FireRiskCalculator:
    """Calculate fire risk scores based on multiple factors."""

    def __init__(self):
        self.weights = {
            "brightness": 0.3,  # Fire intensity
            "confidence": 0.2,  # Detection confidence
            "frp": 0.3,  # Fire radiative power
            "daynight": 0.2,  # Time of detection
        }

    def calculate_base_risk(self, fires_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Calculate base risk score for each fire.

        Args:
            fires_gdf: GeoDataFrame with fire detections

        Returns:
            GeoDataFrame with added 'risk_score' column
        """
        df = fires_gdf.copy()

        # Normalize brightness (typically 300-400K)
        df["brightness_norm"] = (df["bright_ti4"] - 300) / 100
        df["brightness_norm"] = df["brightness_norm"].clip(0, 1)

        # Normalize confidence
        # VIIRS uses categorical: 'l' (low), 'n' (nominal), 'h' (high)
        # MODIS uses numeric: 0-100
        if df["confidence"].dtype == "object":
            # Categorical confidence (VIIRS)
            confidence_map = {"l": 0.33, "n": 0.66, "h": 1.0}
            df["confidence_norm"] = df["confidence"].map(confidence_map)
        else:
            # Numeric confidence (MODIS)
            df["confidence_norm"] = df["confidence"] / 100

        # Normalize FRP (Fire Radiative Power, 0-500+ MW)
        df["frp_norm"] = (df["frp"] / 500).clip(0, 1)

        # Day/night factor (nighttime fires more concerning)
        df["daynight_norm"] = df["daynight"].map({"D": 0.5, "N": 1.0})

        # Calculate weighted risk score (0-100)
        df["risk_score"] = (
            df["brightness_norm"] * self.weights["brightness"]
            + df["confidence_norm"] * self.weights["confidence"]
            + df["frp_norm"] * self.weights["frp"]
            + df["daynight_norm"] * self.weights["daynight"]
        ) * 100

        # Categorize risk
        df["risk_category"] = pd.cut(
            df["risk_score"], bins=[0, 30, 60, 100], labels=["Low", "Moderate", "High"]
        )

        return df

    def create_risk_buffers(
        self, fires_gdf: gpd.GeoDataFrame, buffer_km: float = 10, dissolve: bool = False
    ) -> gpd.GeoDataFrame:
        """
        Create buffer zones around fires.

        Args:
            fires_gdf: GeoDataFrame with fires
            buffer_km: Buffer radius in kilometers
            dissolve: If True, merge overlapping buffers by risk_category

        Returns:
            GeoDataFrame with buffer polygons
        """
        # Project to appropriate CRS for buffering (meters)
        # Using Albers Equal Area for CONUS
        fires_proj = fires_gdf.to_crs("EPSG:5070")

        # Create buffers (convert km to meters)
        fires_proj["geometry"] = fires_proj.geometry.buffer(buffer_km * 1000)

        # Dissolve overlapping buffers by risk category if requested
        if dissolve and "risk_category" in fires_proj.columns:
            # Group by risk category and merge overlapping polygons
            dissolved = fires_proj.dissolve(by="risk_category", aggfunc="first")

            # Reset index to make risk_category a column again
            dissolved = dissolved.reset_index()

            # Convert back to WGS84 for display
            return dissolved.to_crs("EPSG:4326")

        # Convert back to WGS84 for display
        return fires_proj.to_crs("EPSG:4326")
