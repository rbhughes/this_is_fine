# Kepler.gl Visualization Guide

## Quick Start

### 1. Load Data into Kepler.gl

**Using kepler.gl web app (https://kepler.gl/demo)**
1. Open https://kepler.gl/demo
2. Click "Add Data" button (or drag and drop)
3. Upload both GeoJSON files:
   - `data/processed/active_fires.geojson`
   - `data/processed/fire_buffers.geojson`
4. Kepler.gl will automatically create layers for each dataset

**Note:** The `kepler_config.json` file is provided as a reference for manual styling. In the current Kepler.gl interface, you'll need to manually configure the styling using the layer panels (see Manual Configuration section below).

---

## Manual Configuration Steps

After loading your GeoJSON files, follow these steps to style your map:

### Configure Fire Points Layer

1. **Find the active_fires layer** in the left panel
2. **Click the layer** to expand settings
3. **Basic tab:**
   - Layer Type: Should auto-detect as "Point"
   - Fill Color: Click color picker → Select "risk_category" from dropdown
   - Color Palette: Choose custom colors or use the palette dropdown:
     - Low → `#FFD700` (Gold)
     - Moderate → `#FF8C00` (Dark Orange)
     - High → `#FF0000` (Red)
   - Radius: Click "Radius Based On" → Select "frp"
   - Radius Range: Set to 5-50 pixels
   - Opacity: Set to 0.8 (80%)
   - Stroke: Enable outline
   - Stroke Color: White `#FFFFFF`
   - Stroke Width: 2px

4. **Interaction tab:**
   - Enable tooltips
   - Select fields to show:
     - risk_category
     - risk_score
     - bright_ti4
     - frp
     - confidence
     - relative_humidity (if available)
     - wind_speed_kmh (if available)
     - acq_datetime

### Configure Fire Buffers Layer

1. **Find the fire_buffers layer** in the left panel
2. **Click the layer** to expand settings
3. **Basic tab:**
   - Layer Type: Should auto-detect as "Polygon" or "GeoJSON"
   - Fill Color: Click color picker → Select "risk_category"
   - Color Palette: Match fire points (Gold/Orange/Red)
   - Fill Opacity: Set to 0.25 (25%)
   - Stroke: Enable
   - Stroke Color: Select "risk_category" (same as fill)
   - Stroke Opacity: Set to 0.8 (80%)
   - Stroke Width: 2-3 pixels

4. **Interaction tab:**
   - Enable tooltips
   - Select fields:
     - risk_category
     - risk_score

### Adjust Map Style

1. **Click the map icon** in the bottom-left corner
2. **Select "Dark Matter"** (recommended) or your preferred base map
3. **Toggle map features** as needed:
   - Labels: On
   - Roads: On
   - Water: On
   - Buildings: Optional

### Set Initial View

1. **Navigate to your area of interest** (pan and zoom)
2. Your view will be saved when you export the map

---

### 2. Understanding the Layers

#### **Layer 1: Active Fire Points**
- **Display:** Colored circles representing individual fire detections
- **Color Coding:**
  - 🟡 **Gold (#FFD700):** Low Risk (0-30)
  - 🟠 **Orange (#FF8C00):** Moderate Risk (30-60)
  - 🔴 **Red (#FF0000):** High Risk (60-100)
- **Size:** Scaled by Fire Radiative Power (FRP) - larger circles = more intense fires
- **Opacity:** 80% to see overlapping fires clearly

#### **Layer 2: Fire Risk Zones (Buffers)**
- **Display:** Dissolved 10km buffer polygons around fire clusters
- **Color Coding:** Same as fire points (Gold/Orange/Red)
- **Opacity:** 25% fill, 80% stroke - semi-transparent to see underlying map
- **Purpose:** Shows areas of potential fire spread and evacuation zones

---

## Color Scheme Rationale

### Fire Risk Color Scale
```
Low Risk      Moderate Risk    High Risk
#FFD700  →    #FF8C00     →    #FF0000
 Gold          Dark Orange      Red
```

**Why these colors?**
- **Universal recognition:** Red = danger, yellow = caution
- **Heat association:** Warm colors represent fire intensity
- **Colorblind-friendly:** Works for deuteranopia and protanopia
- **High contrast:** Stands out on dark background

---

## Map Style Recommendations

### Best Base Maps for Fire Visualization

1. **Dark Matter (Default)** ⭐ RECOMMENDED
   - Best contrast for bright fire colors
   - Red/orange fires pop dramatically
   - Professional appearance for presentations

2. **Satellite**
   - Real terrain and land cover context
   - See forests, grasslands, urban areas
   - Useful for understanding fire environment

3. **Light**
   - Clean, minimal for printed reports
   - Good for daytime viewing
   - Lower eye strain

**To Change:** Click map icon in bottom-left → Select base map

---

## Tooltip Configuration

### Fire Points - Shows:
- **risk_category:** Low/Moderate/High
- **risk_score:** 0-100 (1 decimal)
- **bright_ti4:** Brightness temperature (Kelvin)
- **frp:** Fire Radiative Power (MW)
- **confidence:** Detection confidence (l/n/h)
- **relative_humidity:** % (if weather data available)
- **wind_speed_kmh:** km/h (if weather data available)
- **acq_datetime:** Detection date/time

### Buffer Zones - Shows:
- **risk_category:** Zone classification
- **risk_score:** Representative risk score

**To Customize:** Hover over layer → Click ⚙️ → Interaction tab

---

## Advanced Styling Options

### 3D Visualization

Enable 3D mode to show fire intensity as height:

1. **For Fire Points:**
   - Click fire_points layer → Elevation tab
   - Set Height Based On: `risk_score` or `frp`
   - Height Multiplier: 10000-50000 (adjust for dramatic effect)
   - Enable "Show Elevation"

2. **Camera Controls:**
   - Pitch: 45-60° for best 3D perspective
   - Bearing: Rotate to match prevailing wind direction
   - Zoom: Adjust to see 3D effect

3. **Buffer Zones in 3D:**
   - Keep buffers flat (height = 0) for "ground zones"
   - OR slight elevation (1000-5000m) to show containment boundaries

**Enable 3D:** Click 3D icon in top-right corner

### Time Animation (if using temporal data)

If your data includes multiple days:

1. Add Time Filter:
   - Click Filters → Add Filter
   - Select `acq_datetime` field
   - Enable playback controls

2. Animation Settings:
   - Speed: 1x (adjust as needed)
   - Window: 1-6 hours to show recent activity
   - Trail: Show fire progression over time

---

## Layer Customization

### Adjusting Fire Point Size

```
Layer: fire_points → Basic tab
├─ Radius: Fixed vs Dynamic
│  ├─ Fixed: All fires same size (5-15 pixels)
│  └─ Dynamic: Size by FRP (recommended)
│     └─ Radius Range: [5, 50] pixels
│
└─ Opacity: 0.6-0.9 (0.8 default)
```

### Adjusting Buffer Opacity

```
Layer: fire_buffers → Basic tab
├─ Fill Opacity: 0.15-0.35 (0.25 default)
├─ Stroke Opacity: 0.6-0.9 (0.8 default)
└─ Stroke Width: 1-4 pixels (2 default)
```

### Color Palette Alternatives

If you want different colors:

**Option 1: Blue → Red (temperature scale)**
```
Low:      #3288BD (Blue)
Moderate: #FEE08B (Yellow)
High:     #D53E4F (Red)
```

**Option 2: Green → Red (traffic light)**
```
Low:      #00FF00 (Green)
Moderate: #FFFF00 (Yellow)
High:     #FF0000 (Red)
```

**To Change:**
- Layer → Basic → Color → Custom Palette
- Enter hex codes for Low/Moderate/High

---

## Filter Options

### Filter by Risk Category

1. Click **Filters** (top panel)
2. **Add Filter** → Select `risk_category`
3. Check/uncheck categories to show/hide:
   - ☑ Low
   - ☑ Moderate
   - ☑ High

### Filter by Fire Intensity (FRP)

1. **Add Filter** → Select `frp`
2. Drag slider to show only high-intensity fires
3. Example: Show only FRP > 10 MW

### Filter by Confidence

1. **Add Filter** → Select `confidence`
2. Show only high-confidence detections: `h`
3. Hide low-confidence: uncheck `l`

### Filter by Date/Time

1. **Add Filter** → Select `acq_datetime`
2. Drag time slider to show specific time windows
3. Useful for tracking fire progression

---

## Export & Sharing

### Export Map Image

1. Click **Share** (or menu icon) in top-right corner
2. Select **Export Image**
3. Configure settings:
   - Resolution: 1920×1080 or higher (for presentations)
   - Ratio: Keep current viewport or select custom (e.g., 16:9)
   - Legend: Check to include
   - Scale bar: Check to include
4. Click **Download**
5. Image will save as PNG file

### Export Map Configuration

Save your customized styling to reload later:

1. Click menu icon (☰) in top-right
2. Select **Export Map**
3. Choose **JSON** format
4. This saves both:
   - **dataset:** Your fire and buffer data
   - **config:** All layer styling, filters, and map settings
5. Click **Download**

**To reload later:**
1. Go to https://kepler.gl/demo
2. Click **Add Data**
3. Select **Load Map from URL** or upload your saved JSON file
4. All styling and data will be restored

### Export as HTML

Create a standalone interactive map:

1. Click menu icon (☰) → **Export Map**
2. Select **HTML** format
3. Downloads a single HTML file containing:
   - All map data
   - All styling configuration
   - Interactive functionality
4. Share the HTML file or host on a web server
5. Anyone can open it in a browser (no Kepler.gl account needed)

### Export Data

Export processed data as CSV:

1. Click menu icon (☰) → **Export Data**
2. Select dataset (active_fires or fire_buffers)
3. Choose:
   - **Filtered Data:** Only currently visible fires
   - **Entire Dataset:** All data regardless of filters
4. Downloads as CSV file

### Share via URL (Dropbox)

1. Click **Share** button
2. Select **Share Map URL**
3. Authenticate with Dropbox (if first time)
4. Map is uploaded to your Dropbox
5. Copy the generated permalink to share
6. **Note:** Recipients will load data from your Dropbox, so keep files accessible

---

## Performance Tips

### For Large Datasets (1000+ fires)

1. **Reduce point size:** Smaller radius = faster rendering
2. **Lower opacity:** Less GPU overhead
3. **Disable 3D:** Use 2D view for better performance
4. **Use filters:** Show only high-risk fires
5. **Simplify buffers:** Dissolved buffers (3 polygons) already optimized

### Browser Recommendations

- **Chrome/Edge:** Best performance (WebGL 2.0)
- **Firefox:** Good performance
- **Safari:** Acceptable, may be slower with large datasets

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + Z` | Undo |
| `Cmd/Ctrl + Y` | Redo |
| `Cmd/Ctrl + S` | Save/Export |
| `Cmd/Ctrl + D` | Duplicate layer |
| `Delete` | Remove selected layer |
| `←/→` | Rotate map (if 3D enabled) |

---

## Troubleshooting

### "No data shown"
- Check layer visibility (eye icon should be visible)
- Verify correct data IDs: `active_fires` and `fire_buffers`
- Check if filters are too restrictive

### "Colors not matching"
- Ensure `risk_category` field exists in both datasets
- Check that values are exactly: "Low", "Moderate", "High"
- Verify custom color palette is applied

### "Performance issues"
- Reduce point count with filters
- Lower opacity and radius
- Disable 3D mode
- Use Chrome/Edge browser

### "Buffers not visible"
- Increase buffer opacity (try 0.4-0.5)
- Change buffer stroke color to white
- Zoom out to see full extent
- Check if buffers overlap with fires (lower layer order)

---

## Example Use Cases

### 1. Emergency Response Dashboard
```
Settings:
├─ Base Map: Satellite
├─ Fire Points: Size by FRP, Color by risk
├─ Buffers: 25% opacity, visible
├─ Filters: Show only High + Moderate risk
└─ Tooltips: Show all weather data
```

### 2. Public Information Map
```
Settings:
├─ Base Map: Dark Matter
├─ Fire Points: Fixed size, Color by risk
├─ Buffers: 35% opacity, prominent
├─ Filters: Show all fires
└─ 3D: Disabled (easier for public to understand)
```

### 3. Scientific Analysis
```
Settings:
├─ Base Map: Light
├─ Fire Points: Size by FRP, Color by confidence
├─ Buffers: 15% opacity, subtle
├─ Filters: FRP > 5 MW, confidence = 'h'
└─ 3D: Height by risk_score
```

---

## Data Fields Reference

### Fire Points Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `latitude` | float | Latitude (WGS84) | 34.05 |
| `longitude` | float | Longitude (WGS84) | -118.24 |
| `bright_ti4` | float | Brightness temp (K) | 350.2 |
| `frp` | float | Fire Radiative Power (MW) | 45.2 |
| `confidence` | string | Detection confidence | 'h', 'n', 'l' |
| `risk_score` | float | Calculated risk (0-100) | 67.5 |
| `risk_category` | string | Risk classification | 'High' |
| `acq_datetime` | datetime | Detection time | 2025-10-13T06:10 |
| `relative_humidity` | float | Humidity % (NOAA) | 25.0 |
| `wind_speed_kmh` | float | Wind speed (NOAA) | 35.0 |
| `fire_danger_index` | float | NOAA fire danger (0-100) | 75.0 |

### Buffer Zone Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `risk_category` | string | Zone classification | 'Moderate' |
| `risk_score` | float | Representative risk | 45.3 |
| `geometry` | MultiPolygon | Dissolved buffer zone | [polygons] |

---

## Additional Resources

- **Kepler.gl Documentation:** https://docs.kepler.gl/
- **GeoJSON Specification:** https://geojson.org/
- **Color Picker Tool:** https://colorbrewer2.org/
- **NASA FIRMS Info:** https://firms.modaps.eosdis.nasa.gov/

---

## Support

For issues with this visualization:
1. Check this guide's Troubleshooting section
2. Verify GeoJSON files are valid
3. Review the ETL flow logs for data issues
4. Test with a subset of data (filter to 10-50 fires)

Generated for wildfire risk monitoring system using NASA FIRMS + NOAA NWS data.
