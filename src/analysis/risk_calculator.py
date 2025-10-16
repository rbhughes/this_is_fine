# src/analysis/risk_calculator.py
import geopandas as gpd
import pandas as pd


class FireRiskCalculator:
    """Calculate fire risk scores based on multiple factors."""

    def __init__(self, use_weather: bool = False):
        """
        Initialize FireRiskCalculator.

        Args:
            use_weather: If True, incorporate weather data into risk calculations
        """
        self.use_weather: bool = use_weather

        # Base weights (used when weather data unavailable)
        self.weights: dict[str, float] = {
            "brightness": 0.3,  # Fire intensity
            "confidence": 0.2,  # Detection confidence
            "frp": 0.3,  # Fire radiative power
            "daynight": 0.2,  # Time of detection
        }

        # Enhanced weights (used when weather data available)
        self.enhanced_weights: dict[str, float] = {
            "brightness": 0.20,  # Fire intensity
            "confidence": 0.15,  # Detection confidence
            "frp": 0.20,  # Fire radiative power
            "daynight": 0.10,  # Time of detection
            "humidity": 0.15,  # Low humidity increases risk
            "wind": 0.10,  # High wind increases risk
            "precipitation": 0.05,  # Low precip probability increases risk
            "fire_danger": 0.05,  # NOAA fire danger index
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
        df["brightness_norm"] = df["brightness_norm"].clip(lower=0.0, upper=1.0)

        # Normalize confidence
        # VIIRS uses categorical: 'l' (low), 'n' (nominal), 'h' (high)
        # MODIS uses numeric: 0-100
        if df["confidence"].dtype == "object":
            # Categorical confidence (VIIRS)
            confidence_map: dict[str, float] = {"l": 0.33, "n": 0.66, "h": 1.0}
            df["confidence_norm"] = df["confidence"].map(confidence_map)  # type: ignore[arg-type]
        else:
            # Numeric confidence (MODIS)
            df["confidence_norm"] = df["confidence"] / 100

        # Normalize FRP (Fire Radiative Power, 0-500+ MW)
        df["frp_norm"] = (df["frp"] / 500).clip(lower=0.0, upper=1.0)

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

    def calculate_enhanced_risk(self, fires_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Calculate enhanced risk score incorporating weather data.

        Args:
            fires_gdf: GeoDataFrame with fire detections and weather data

        Returns:
            GeoDataFrame with enhanced 'risk_score' and 'risk_category' columns
        """
        df = fires_gdf.copy()

        # Check if weather data is available
        has_weather = all(
            col in df.columns
            for col in ["relative_humidity", "wind_speed_kmh", "precip_probability"]
        )

        if not has_weather:
            # Fall back to base risk calculation
            return self.calculate_base_risk(df)

        # Normalize fire satellite data (same as base)
        df["brightness_norm"] = ((df["bright_ti4"] - 300) / 100).clip(
            lower=0.0, upper=1.0
        )

        if df["confidence"].dtype == "object":
            confidence_map: dict[str, float] = {"l": 0.33, "n": 0.66, "h": 1.0}
            df["confidence_norm"] = df["confidence"].map(confidence_map)  # type: ignore[arg-type]
        else:
            df["confidence_norm"] = df["confidence"] / 100

        df["frp_norm"] = (df["frp"] / 500).clip(lower=0.0, upper=1.0)
        df["daynight_norm"] = df["daynight"].map({"D": 0.5, "N": 1.0})

        # Normalize weather data
        # Humidity: Lower is worse (invert so 0% humidity = 1.0 risk)
        df["humidity_norm"] = (
            1 - (df["relative_humidity"].fillna(50.0).astype(float) / 100)
        ).clip(lower=0.0, upper=1.0)

        # Wind: Higher is worse (normalize to 0-60 km/h range)
        df["wind_norm"] = (df["wind_speed_kmh"].fillna(0.0).astype(float) / 60).clip(
            lower=0.0, upper=1.0
        )

        # Precipitation: Lower probability is worse (invert)
        df["precip_norm"] = (
            1 - (df["precip_probability"].fillna(0.0).astype(float) / 100)
        ).clip(lower=0.0, upper=1.0)

        # Fire danger index: Normalize if available (0-100 scale)
        if "fire_danger_index" in df.columns:
            df["fire_danger_norm"] = (
                df["fire_danger_index"].fillna(0.0).astype(float) / 100
            ).clip(lower=0.0, upper=1.0)
        else:
            df["fire_danger_norm"] = 0.5  # Neutral value if unavailable

        # Calculate weighted enhanced risk score (0-100)
        w = self.enhanced_weights
        df["risk_score"] = (
            df["brightness_norm"] * w["brightness"]
            + df["confidence_norm"] * w["confidence"]
            + df["frp_norm"] * w["frp"]
            + df["daynight_norm"] * w["daynight"]
            + df["humidity_norm"] * w["humidity"]
            + df["wind_norm"] * w["wind"]
            + df["precip_norm"] * w["precipitation"]
            + df["fire_danger_norm"] * w["fire_danger"]
        ) * 100

        # Categorize risk
        df["risk_category"] = pd.cut(
            df["risk_score"], bins=[0, 30, 60, 100], labels=["Low", "Moderate", "High"]
        )

        # Add flag indicating enhanced calculation was used
        df["uses_weather_data"] = True

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
        # Make a copy to avoid modifying original
        fires_copy = fires_gdf.copy()

        # Project to appropriate CRS for buffering (meters)
        # Using Albers Equal Area for CONUS
        fires_proj = fires_copy.to_crs("EPSG:5070")

        # Create buffers (convert km to meters)
        fires_proj["geometry"] = fires_proj.geometry.buffer(buffer_km * 1000)

        # Dissolve overlapping buffers by risk category if requested
        if dissolve and "risk_category" in fires_proj.columns:
            # Group by risk category and merge overlapping polygons
            dissolved = fires_proj.dissolve(by="risk_category", aggfunc="first")

            # Reset index to make risk_category a column again
            dissolved = dissolved.reset_index()

            # Keep only relevant columns for dissolved buffers
            buffer_cols = ["risk_category", "geometry"]
            if "fire_id" in dissolved.columns:
                buffer_cols.insert(0, "fire_id")

            dissolved = dissolved[buffer_cols]

            # Convert back to WGS84 for display
            return dissolved.to_crs("EPSG:4326")

        # For individual buffers, keep key attributes but remove detailed fire data
        # Keep: fire_id, latitude, longitude, risk_score, risk_category, acq_date
        buffer_cols = ["geometry", "risk_category"]
        optional_cols = [
            "fire_id",
            "latitude",
            "longitude",
            "risk_score",
            "acq_date",
            "frp",
            "brightness",
        ]

        for col in optional_cols:
            if col in fires_proj.columns:
                buffer_cols.append(col)

        fires_proj = fires_proj[buffer_cols]

        # Convert back to WGS84 for display
        return fires_proj.to_crs("EPSG:4326")
