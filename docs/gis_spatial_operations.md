# GIS Spatial Operations - ArcGIS Workflow Mapping

This document maps the spatial operations used in the wildfire risk monitoring system to their ArcGIS equivalents, providing a reference for GIS professionals familiar with ArcGIS workflows.

## Overview

The system uses **GeoPandas** and **Shapely** for spatial operations, which provide Python-native equivalents to ArcGIS geoprocessing tools. All operations are performed in-memory with vector data (points, polygons).

---

## Core Spatial Operations

| GeoPandas/Shapely | ArcGIS Tool | Location in Code | Purpose |
|-------------------|-------------|------------------|---------|
| `geometry.buffer(distance)` | **Buffer** | `risk_calculator.py:191`<br>`industrial_filter.py:164` | Create 10km risk zones around fires<br>Create 1km buffer around industrial sites |
| `.dissolve(by="field")` | **Dissolve** | `risk_calculator.py:196` | Merge overlapping buffers by risk category (Low/Moderate/High) |
| `.to_crs("EPSG:code")` | **Project** | Throughout | Reproject between WGS84 (4326) and Albers Equal Area (5070) |
| `.geometry.within(polygon)` | **Select by Location** (within) | `industrial_filter.py:167` | Find fires within industrial buffer zones |
| `.unary_union` | **Union** | `industrial_filter.py:164` | Merge all industrial buffers into single geometry |
| `Point(lon, lat)` | **XY to Point** | `firms_client.py`<br>`purpleair_client.py` | Convert lat/lon coordinates to point geometry |

---

## Data Management Operations

| GeoPandas | ArcGIS Tool | Location | Purpose |
|-----------|-------------|----------|---------|
| `gpd.GeoDataFrame(df, geometry=...)` | **XY Table to Point** | `firms_client.py`<br>`industrial_filter.py:116` | Create spatial layer from CSV/DataFrame |
| `gdf.to_file("file.geojson")` | **Feature Class to Feature Class** (Export) | Throughout ETL | Export to GeoJSON format |
| `gpd.read_file("file.geojson")` | **Add Data** / **Import Feature Class** | Throughout | Load spatial data |
| `gdf[condition]` | **Select by Attribute** | `industrial_filter.py:171` | Filter features by attribute query |

---

## Coordinate System Operations

| Operation | ArcGIS Equivalent | Code Location | Details |
|-----------|-------------------|---------------|---------|
| WGS84 (EPSG:4326) | Geographic Coordinate System | Input/Output CRS | Standard lat/lon for web mapping |
| Albers Equal Area (EPSG:5070) | **USA Contiguous Albers Equal Area Conic** | Buffer operations | Accurate distance calculations in meters |
| `.to_crs("EPSG:5070")` | **Project** tool | Before buffering | Required for metric buffers |
| `.to_crs("EPSG:4326")` | **Project** tool | After buffering | Return to web-friendly CRS |

### Why Project Before Buffering?

**Problem:** WGS84 uses degrees, not meters. A 10km buffer in decimal degrees varies by latitude.

**Solution:** 
1. Project to equal-area projection (Albers EPSG:5070)
2. Buffer in meters (10km = 10,000m)
3. Project back to WGS84 for display

**ArcGIS Equivalent:**
```
1. Project (WGS84 → Albers Equal Area Conic)
2. Buffer (10 kilometers)
3. Project (Albers → WGS84)
```

---

## Analysis Workflows

### Workflow 1: Risk Buffer Creation

**File:** `src/analysis/risk_calculator.py:170-209`

**ArcGIS ModelBuilder Equivalent:**
```
Input: Fire Points (WGS84)
  ↓
[1. Project] → Albers Equal Area EPSG:5070
  ↓
[2. Buffer] → 10km radius, FULL option
  ↓
[3. Dissolve] → Dissolve by risk_category field, FIRST statistics
  ↓
[4. Project] → WGS84 EPSG:4326
  ↓
Output: Risk Zone Polygons (WGS84)
```

**Python Code:**
```python
def create_risk_buffers(fires_gdf, buffer_km=10, dissolve=False):
    # 1. Project to Albers Equal Area
    fires_proj = fires_gdf.to_crs("EPSG:5070")
    
    # 2. Buffer (convert km to meters)
    fires_proj["geometry"] = fires_proj.geometry.buffer(buffer_km * 1000)
    
    # 3. Dissolve by risk category
    if dissolve:
        dissolved = fires_proj.dissolve(by="risk_category", aggfunc="first")
        dissolved = dissolved.reset_index()
        
        # 4. Project back to WGS84
        return dissolved.to_crs("EPSG:4326")
    
    return fires_proj.to_crs("EPSG:4326")
```

**Key Parameters:**
- `buffer_km`: Buffer radius (default 10km)
- `dissolve`: Merge overlapping buffers (True/False)
- `aggfunc="first"`: Keep first value when dissolving (like FIRST statistic in ArcGIS)

---

### Workflow 2: Industrial Heat Source Filtering

**File:** `src/filters/industrial_filter.py:134-177`

**ArcGIS ModelBuilder Equivalent:**
```
Input 1: Fire Points (WGS84)
Input 2: Industrial Sites (WGS84)
  ↓
[1. Project] → Both layers to Albers EPSG:5070
  ↓
[2. Buffer] → Industrial sites by 1km
  ↓
[3. Union] → Merge all industrial buffers (Dissolve with "All" option)
  ↓
[4. Select by Location] → Select fires WITHIN industrial buffer
  ↓
[5. Split] → Create two feature classes:
            - Filtered fires (NOT selected)
            - Excluded fires (selected)
  ↓
[6. Project] → Both outputs to WGS84
  ↓
Output 1: Filtered Fires (actual wildfires)
Output 2: Excluded Fires (industrial sources)
```

**Python Code:**
```python
def filter_fires(fires_gdf, buffer_km=1.0, persistent_locations=None):
    # 1. Project to Albers Equal Area
    fires_proj = fires_gdf.to_crs("EPSG:5070")
    persistent_proj = persistent_locations.to_crs("EPSG:5070")
    
    # 2. Buffer industrial sites
    buffer_m = buffer_km * 1000
    
    # 3. Union - merge all buffers into single geometry
    persistent_buffer = persistent_proj.geometry.buffer(buffer_m).unary_union
    
    # 4. Select by Location - identify fires within buffer
    fires_proj["is_industrial"] = fires_proj.geometry.within(persistent_buffer)
    
    # 5. Split based on selection
    filtered_fires = fires_proj[~fires_proj["is_industrial"]]  # NOT selected
    excluded_fires = fires_proj[fires_proj["is_industrial"]]   # Selected
    
    # 6. Project back to WGS84
    filtered_fires = filtered_fires.to_crs("EPSG:4326")
    excluded_fires = excluded_fires.to_crs("EPSG:4326")
    
    return filtered_fires, excluded_fires
```

**Key Differences from ArcGIS:**
- `.within()` is equivalent to "WITHIN" spatial relationship
- `.unary_union` merges all geometries (like Dissolve with no field)
- Boolean indexing `~` means NOT (inverts selection)

---

### Workflow 3: Complete Fire Risk ETL

**File:** `flows/etl_flow.py`

**Full ArcGIS Workflow:**
```
[1. Make XY Event Layer]
    Input: NASA FIRMS CSV (lat, lon, brightness, frp, etc.)
    Output: Fire Points (temporary)
    
[2. Copy Features]
    Input: Fire Points (temporary)
    Output: Fire Points (WGS84 geodatabase)
    
[3. Calculate Field]
    Field: risk_score
    Expression: weighted_risk_formula(brightness, frp, confidence, daynight)
    
[4. Calculate Field]
    Field: risk_category
    Expression: categorize_risk(risk_score)
    
[5. Select by Location]
    Layer: Fire Points
    Relationship: WITHIN
    Selecting Features: Industrial Buffer Zones
    Selection Type: NEW_SELECTION
    
[6. Switch Selection]
    (Keep fires NOT in industrial zones)
    
[7. Copy Features]
    Input: Fire Points (selected)
    Output: Filtered_Fires
    
[8. Project]
    Input: Filtered_Fires
    Output CRS: Albers Equal Area EPSG:5070
    
[9. Buffer]
    Input: Filtered_Fires (Albers)
    Distance: 10 kilometers
    Output: Fire_Buffers_Albers
    
[10. Dissolve]
    Input: Fire_Buffers_Albers
    Dissolve Field: risk_category
    Statistics: risk_score FIRST
    Output: Dissolved_Buffers_Albers
    
[11. Project]
    Input: Dissolved_Buffers_Albers
    Output CRS: WGS84 EPSG:4326
    Output: Fire_Risk_Zones
    
[12. Features to JSON]
    Input: Filtered_Fires, Fire_Risk_Zones
    Output: active_fires.geojson, fire_buffers.geojson
```

---

## Geometry Types

| Shapely Type | ArcGIS Geometry | Usage in Project |
|--------------|-----------------|------------------|
| `Point` | Point Feature | Fire locations, air quality sensors |
| `Polygon` | Polygon Feature | Individual fire buffers (undissolved) |
| `MultiPolygon` | Multipart Polygon | Dissolved risk zones (multiple disconnected areas) |

**Creating Point Geometry:**
```python
# GeoPandas/Shapely
from shapely.geometry import Point
geometry = [Point(lon, lat) for lon, lat in zip(df['longitude'], df['latitude'])]
gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

# ArcGIS Equivalent
arcpy.management.XYTableToPoint(
    in_table="fires.csv",
    out_feature_class="fires_points",
    x_field="longitude",
    y_field="latitude",
    coordinate_system=arcpy.SpatialReference(4326)
)
```

---

## Spatial Predicates

| GeoPandas Method | ArcGIS Spatial Relationship | Description | Usage |
|------------------|------------------------------|-------------|-------|
| `.within(geometry)` | **WITHIN** | Feature entirely inside | `fires.geometry.within(industrial_buffer)` |
| `.intersects(geometry)` | **INTERSECT** | Features overlap | Not currently used |
| `.contains(geometry)` | **CONTAINS** | Feature entirely contains | Not currently used |
| `.touches(geometry)` | **BOUNDARY_TOUCHES** | Features share boundary | Not currently used |

**Example - Select by Location:**
```python
# GeoPandas
fires["is_inside"] = fires.geometry.within(buffer_zone)
selected_fires = fires[fires["is_inside"]]

# ArcGIS Equivalent
arcpy.management.SelectLayerByLocation(
    in_layer="fires",
    overlap_type="WITHIN",
    select_features="buffer_zone",
    selection_type="NEW_SELECTION"
)
```

---

## Database Spatial Operations

| DuckDB Spatial Function | ArcGIS Tool | Location | Purpose |
|-------------------------|-------------|----------|---------|
| `ST_GeomFromText(wkt)` | Geometry from WKT | `database/operations.py` | Convert WKT string to geometry |
| `ST_AsText(geometry)` | Geometry to WKT | `database/operations.py` | Convert geometry to WKT string |
| Spatial index | **Add Spatial Index** | `database/__init__.py:36` | Fast spatial queries |

**DuckDB Spatial Extension:**
```sql
-- Install spatial extension
INSTALL spatial;
LOAD spatial;

-- Create table with geometry
CREATE TABLE fires (
    fire_id VARCHAR PRIMARY KEY,
    latitude DOUBLE,
    longitude DOUBLE,
    geometry GEOMETRY
);

-- Create spatial index
CREATE INDEX fires_geom_idx ON fires USING RTREE (geometry);

-- Spatial query example
SELECT * FROM fires 
WHERE ST_Within(
    geometry, 
    ST_GeomFromText('POLYGON((...))')
);
```

**ArcGIS Equivalent:**
- Feature Class with Geometry field (automatic)
- Spatial Index created automatically
- Select by Location tool for spatial queries

---

## Common GIS Workflow Patterns

### Pattern 1: Point-to-Buffer Analysis
```python
# 1. Load points
fires = gpd.read_file("fires.geojson")

# 2. Project to metric CRS
fires_proj = fires.to_crs("EPSG:5070")

# 3. Create buffers
fires_proj["geometry"] = fires_proj.geometry.buffer(10000)  # 10km

# 4. Project back
buffers = fires_proj.to_crs("EPSG:4326")
```

**ArcGIS Equivalent:**
```
Project → Buffer → Project
```

### Pattern 2: Spatial Selection and Split
```python
# 1. Perform spatial query
selection = fires.geometry.within(exclusion_zone)

# 2. Split data based on selection
selected = fires[selection]
not_selected = fires[~selection]
```

**ArcGIS Equivalent:**
```
Select by Location → Switch Selection → Export both
```

### Pattern 3: Dissolve with Statistics
```python
# Dissolve by category, keep first risk_score value
dissolved = gdf.dissolve(by="risk_category", aggfunc="first")
dissolved = dissolved.reset_index()  # Make risk_category a column again
```

**ArcGIS Equivalent:**
```
Dissolve (risk_category field, risk_score FIRST statistic)
```

---

## Key Differences from ArcGIS

| Concept | ArcGIS | GeoPandas |
|---------|--------|-----------|
| **Coordinate Systems** | Stored in layer properties, persists | Must specify per operation with `.to_crs()` |
| **Buffering** | Single tool with unit dropdown | Requires projection to metric CRS first |
| **Dissolve** | Creates new feature class | Returns modified GeoDataFrame (in-memory) |
| **Selection** | Creates selection set on layer | Boolean indexing returns new GeoDataFrame |
| **Geometry Storage** | Proprietary geodatabase formats | Standard formats (GeoJSON, Shapefile, GeoPackage) |
| **Processing** | Tool-by-tool workflow | Python functions, can chain operations |
| **Performance** | Optimized for disk-based data | Optimized for in-memory operations |

---

## Spatial Functions Available But Not Currently Used

These common ArcGIS tools aren't currently used but could be added:

| GeoPandas/Shapely | ArcGIS Equivalent | Potential Use Case |
|-------------------|-------------------|-------------------|
| `gpd.clip(gdf, mask)` | **Clip** | Clip fires to state boundaries |
| `gpd.overlay(how='intersection')` | **Intersect** | Find fire-forest overlap areas |
| `gpd.sjoin(gdf1, gdf2)` | **Spatial Join** | Join fires to counties |
| `.distance(point)` | **Near** | Distance to nearest fire station |
| `.convex_hull` | **Minimum Bounding Geometry** (Convex Hull) | Overall fire extent |
| `.centroid` | **Feature to Point** (Centroid) | Find center of fire cluster |
| `.boundary` | **Feature to Line** | Convert polygon to line |
| `.simplify(tolerance)` | **Simplify Polygon** | Reduce vertex count |
| `gpd.overlay(how='union')` | **Union** | Combine multiple risk zones |
| `gpd.overlay(how='difference')` | **Erase** | Remove protected areas from analysis |

### Example: Spatial Join

**GeoPandas:**
```python
# Join fires to counties
fires_with_county = gpd.sjoin(
    fires,           # Target features
    counties,        # Join features
    how="left",      # Keep all fires
    predicate="within"  # Spatial relationship
)
```

**ArcGIS Equivalent:**
```
Spatial Join (fires, counties, JOIN_ONE_TO_ONE, KEEP_ALL, WITHIN)
```

### Example: Clip to Study Area

**GeoPandas:**
```python
# Clip fires to California boundary
ca_fires = gpd.clip(fires, california_boundary)
```

**ArcGIS Equivalent:**
```
Clip (fires, california_boundary, ca_fires)
```

---

## Performance Considerations

### GeoPandas vs ArcGIS

**GeoPandas Advantages:**
- Fast for small to medium datasets (< 1M features)
- In-memory operations (no disk I/O)
- Easy to chain operations
- Free and open source

**ArcGIS Advantages:**
- Better for very large datasets (> 1M features)
- Advanced topology tools
- Raster analysis capabilities
- Enterprise geodatabase support

### Optimization Tips

**For Large Datasets:**
```python
# 1. Use spatial index (automatic with GeoDataFrame)
fires.sindex  # Generates R-tree spatial index

# 2. Filter data early
fires_subset = fires[fires['risk_score'] > 50]

# 3. Use appropriate CRS for analysis
fires_proj = fires.to_crs("EPSG:5070")  # Equal area for buffers

# 4. Dissolve before complex operations
simplified = buffers.dissolve(by='risk_category')
```

---

## References

- **GeoPandas Documentation:** https://geopandas.org/
- **Shapely Documentation:** https://shapely.readthedocs.io/
- **ArcGIS Geoprocessing Tools:** https://pro.arcgis.com/en/pro-app/latest/tool-reference/
- **EPSG:4326 (WGS84):** https://epsg.io/4326
- **EPSG:5070 (Albers Equal Area):** https://epsg.io/5070
- **DuckDB Spatial Extension:** https://duckdb.org/docs/extensions/spatial.html

---

## Quick Reference Table

| Need to... | GeoPandas | ArcGIS |
|------------|-----------|--------|
| Load spatial data | `gpd.read_file()` | Add Data / Import |
| Create points from XY | `gpd.GeoDataFrame(geometry=Point())` | XY Table to Point |
| Buffer features | `.buffer(distance)` | Buffer |
| Merge features | `.dissolve()` | Dissolve |
| Change projection | `.to_crs()` | Project |
| Spatial selection | `.within()`, `.intersects()` | Select by Location |
| Attribute selection | `gdf[gdf['field'] > value]` | Select by Attribute |
| Export data | `.to_file()` | Export / Features to JSON |
| Join tables | `.merge()` | Join Field |
| Spatial join | `gpd.sjoin()` | Spatial Join |
| Clip to boundary | `gpd.clip()` | Clip |

---

*Generated for the wildfire risk monitoring system - GeoPandas/Shapely implementation with ArcGIS equivalents*
