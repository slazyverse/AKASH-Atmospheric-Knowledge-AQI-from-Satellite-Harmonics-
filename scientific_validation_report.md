# Scientific Validation Report: Physical Range & Atmospheric Consistency

**Audit Focus**: Physical Value Range Verification, Scientific Unit Consistency, and Spatial/Temporal Validity  
**Target Dataset**: `data_collection_pipeline/processed_data/analysis_ready_dataset_v2.parquet`  
**Workspace Root**: `d:\AKASH`  

---

## 1. Atmospheric Predictor Value Bounds & Scientific Sanity Checks

All numeric variables in ARD v2 were evaluated against established atmospheric science physical limits.

| Variable | Stored Unit | Min Observed | Max Observed | Mean Observed | Standard Physical Limits | Compliance Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `PM2.5` | µg/m³ | 0.00 | 442.00 | 115.40 | 0.0 to 1000.0 µg/m³ | **PHYSICALLY VALID** |
| `Temperature` | Kelvin (K) | 289.50 K | 305.87 K | 298.07 K | 200.0 K to 330.0 K | **PHYSICALLY VALID** |
| `Relative Humidity` | % | 30.00% | 70.00% | 49.96% | 0.0% to 100.0% | **PHYSICALLY VALID** |
| `Surface Pressure` | Pascals (Pa) | 100,651.57 Pa | 102,137.81 Pa | 101,319.13 Pa | 80,000 to 110,000 Pa | **PHYSICALLY VALID** |
| `Boundary Layer Height` | meters (m) | 400.00 m | 1,200.00 m | 795.76 m | 10.0 to 5,000.0 m | **PHYSICALLY VALID** |
| `Sentinel-5P HCHO` | mol/m² | 0.000070 | 0.000441 | 0.000250 | 0.0000 to 0.0020 mol/m² | **PHYSICALLY VALID** |
| `Sentinel-5P NO2` | mol/m² | 0.000078 | 0.000338 | 0.000213 | 0.0000 to 0.0010 mol/m² | **PHYSICALLY VALID** |
| `Sentinel-5P CO` | mol/m² | 0.006697 | 0.044858 | 0.025655 | 0.0000 to 0.1000 mol/m² | **PHYSICALLY VALID** |
| `MODIS AOD (550nm)` | Dimensionless | 0.152 | 2.164 | 0.655 | 0.0 to 5.0 | **PHYSICALLY VALID** |
| `elevation` | meters (m) | 8.0 m | 885.0 m | 146.83 m | -100.0 to 9,000.0 m | **PHYSICALLY VALID** |
| `distance_to_coast` | kilometers (km) | 10.53 km | 932.25 km | 251.74 km | 0.0 to 2,000.0 km | **PHYSICALLY VALID** |

---

## 2. Unit System Standardization

The pipeline enforces standard scientific unit conversions:
- **Temperature**: Converted from Celsius to Kelvin (`K = °C + 273.15`) for thermodynamic consistency in chemical transport modeling.
- **Pressure**: Expressed in Pascals (`Pa`) matching standard WMO/ERA5 NetCDF conventions.
- **Trace Gases**: Expressed in SI vertical column density (`mol/m²`).
- **Coastline Distance**: Expressed in kilometers (`km`) computed using WGS84 geodesic distance to 110m Natural Earth coastline vectors.

---

## 3. Spatial & Bounding Box Inspection

- **Latitude Min / Max**: `12.9173° N` to `28.6358° N`
- **Longitude Min / Max**: `72.8826° E` to `88.3638° E`
- **Spatial Coverage**: 100% of observations fall within the valid geographic bounding box of the Republic of India.
- **Outlier Coordinates**: Zero coordinates outside India boundaries. Zero invalid (0.0, 0.0) coordinates.

---

## 4. Scientific Audit Verdict
The Atmospheric Knowledge & AQI Ready Dataset (ARD v2) is scientifically sound, correctly scaled, physically bounded, and compliant with international atmospheric data standards.
