# FIRMS: Fire Information for Resource Management System

## What is FIRMS?

FIRMS (Fire Information for Resource Management System) is a NASA-funded system that provides near real-time active fire data from multiple satellite sources. Developed in 2007 by the University of Maryland with funding from NASA's Applied Sciences Program and the UN Food and Agriculture Organization, FIRMS distributes thermal anomaly and active fire location data within 1-3 hours of satellite observation globally.

## Purpose and Applications

FIRMS serves natural resource managers, emergency responders, fire managers, humanitarian organizations, and government agencies worldwide. The system enables:

- **Fire location tracking** - Real-time monitoring of active fires globally
- **Resource allocation decisions** - Data-driven deployment of firefighting resources
- **Impact assessment** - Evaluating fire distribution and extent
- **Infrastructure protection** - Safeguarding human life and critical infrastructure
- **Humanitarian response** - Supporting disaster response organizations

## Satellite Sensors

FIRMS aggregates data from multiple satellite-based thermal sensors:

### MODIS (Moderate Resolution Imaging Spectroradiometer)
- **Satellites**: Terra (since 2000), Aqua (since 2002)
- **Spatial Resolution**: 1 km × 1 km
- **Coverage**: Global, multiple daily overpasses
- **Characteristics**: Long-term historical record, well-validated algorithm

### VIIRS (Visible Infrared Imaging Radiometer Suite)
- **Satellites**: Suomi NPP (since 2012), NOAA-20, NOAA-21
- **Spatial Resolution**: 375 m × 375 m
- **Coverage**: Global coverage
- **Advantages**: Higher resolution, improved nighttime detection, better small fire detection

### Geostationary Sensors
- **Systems**: GOES (Americas), Meteosat (Europe/Africa), Himawari (Asia/Pacific)
- **Spatial Resolution**: ~2 km at sub-satellite point
- **Advantage**: Continuous monitoring (no gaps between polar orbiter passes)

## How Thermal Detection Works

### Detection Principle
FIRMS uses thermal infrared sensors to detect "thermal anomalies" - areas that are significantly hotter than their surroundings. The system identifies:
- Wildfires
- Agricultural burns
- Volcanic activity
- Industrial heat sources
- Other intense heat anomalies

### Technical Process
1. **Mid-Infrared Scanning**: Satellites measure thermal radiation in mid-infrared wavelengths
2. **Contextual Algorithm**: Each pixel is examined for fire signatures by comparing its temperature to surrounding pixels
3. **Threshold Detection**: If the temperature difference exceeds a predetermined threshold, the pixel is flagged as an active fire or "hot spot"
4. **Validation**: Confidence levels are assigned based on detection certainty

### Detection Capabilities
- **Minimum Fire Size**: Can detect fires as small as 1,000 m² (0.25 acres) under ideal conditions
- **Sensitivity**: VIIRS detects smaller and cooler fires than MODIS due to higher spatial resolution
- **Temporal Coverage**: Provides "snapshot" of fires at satellite overpass time

## Data Fields Provided

FIRMS provides the following key data fields for each fire detection:

| Field | Description |
|-------|-------------|
| **Latitude/Longitude** | Fire location in WGS84 coordinates |
| **Brightness Temperature** | Temperature in Kelvin measured in thermal infrared band (typically 300-400K for fires) |
| **Fire Radiative Power (FRP)** | Heat energy released by fire in megawatts (MW), indicating fire intensity |
| **Confidence** | Detection confidence: Low/Nominal/High (VIIRS) or 0-100% (MODIS) |
| **Acquisition Date/Time** | When the satellite observed the fire |
| **Day/Night Flag** | Whether detection occurred during day or night |
| **Satellite** | Which sensor made the detection (e.g., VIIRS_NOAA20_NRT) |
| **Scan/Track** | Pixel size and viewing angle information |

### Key Metrics

**Fire Radiative Power (FRP)**
- Measures the rate of radiant heat energy released
- Typical range: 0-500+ MW
- Higher values indicate more intense fires
- Used to estimate smoke emissions and fire severity

**Brightness Temperature (bright_ti4)**
- Surface temperature in mid-infrared band
- Normal land surface: ~280-310K
- Active fires: 320-400K+
- Extremely hot fires: 400K+

## Data Latency

FIRMS provides multiple data streams based on latency requirements:

- **Ultra Real-Time (URT)**: Within minutes of observation
- **Real-Time (RT)**: Within 1 hour (US/Canada only)
- **Near Real-Time (NRT)**: 1-3 hours globally
- **Standard Processing**: Higher quality, longer latency

## Limitations and Considerations

### Detection Limitations
1. **Temporal Gaps**: Fires can start and end between satellite passes
2. **Cloud/Smoke Obscuration**: Dense clouds or heavy smoke can block thermal sensors
3. **Pixel-Level Data**: Fire location represents pixel center, not exact fire boundaries
4. **Multiple Fires**: A single pixel may contain multiple small fires
5. **Size Ambiguity**: Cannot precisely determine fire size from single pixel

### False Positives
Thermal anomalies can be triggered by:
- Gas flares and industrial facilities
- Volcanoes and geothermal features
- Highly reflective surfaces (metal roofs, solar panels)
- Very hot industrial processes

### Spatial Resolution Trade-offs
- **MODIS (1km)**: May miss small fires but provides longer historical record
- **VIIRS (375m)**: Better small fire detection but shorter data archive
- **Geostationary**: Continuous monitoring but coarser resolution

## API Access

FIRMS provides free API access for downloading active fire data:

### Bounding Box Query
```
https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{source}/{bbox}/{days}
```

Parameters:
- `MAP_KEY`: Your FIRMS API key
- `source`: Satellite source (VIIRS_NOAA20_NRT, MODIS_NRT, etc.)
- `bbox`: west,south,east,north in WGS84 decimal degrees
- `days`: Number of days to look back (1-10)

### Coverage
- **Global**: Worldwide coverage available
- **US/Canada**: Real-time data available within 1 hour
- **Historical**: Archive available dating back to 2000 (MODIS) and 2012 (VIIRS)

## Use in this Project

This wildfire monitoring system uses FIRMS data to:
1. Fetch active fire detections from VIIRS satellites
2. Calculate risk scores based on FRP, brightness, and detection confidence
3. Create spatial buffer zones for risk assessment
4. Store and query fire data in a geospatial database
5. Export visualizations for mapping tools

The system primarily uses the **VIIRS_NOAA20_NRT** source for its superior spatial resolution and small fire detection capabilities.

## References

- [NASA FIRMS Homepage](https://firms.modaps.eosdis.nasa.gov/)
- [FIRMS FAQ](https://www.earthdata.nasa.gov/data/tools/firms/faq)
- [FIRMS User Guide](https://www.earthdata.nasa.gov/data/tools/firms)
