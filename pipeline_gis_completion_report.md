# Pipeline GIS Completion Report

## 1. Introduction

This report documents the final GIS feature audit and verification of the Historical Analysis Ready Dataset (ARD) v2.

## 2. Feature Verification Details

- **Elevation**: Extracted from USGS SRTM GL1 (30m scale). Values range between 8.00m and 885.00m, representing the spatial distribution of active monitors.
- **Land Cover**: Extracted from ESA WorldCover (10m scale). Station land cover types were validated against the official ESA classifications (trees, grassland, built-up, water, etc.).
- **Distance to Coast**: Geodesic distances (in kilometers) computed from each monitor's canonical latitude and longitude to the nearest coastline using the Natural Earth 110m physical coastline dataset. Distances range from 10.53 km to 932.25 km.

## 3. Core Verification Statistics

| Feature | Min | Max | Mean | Median | Std Dev | Missing % |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Elevation (m)** | 8.00 | 885.00 | 146.83 | 9.00 | 217.50 | 0.00% |
| **Land Cover Code** | 10.00 | 50.00 | 35.52 | 50.00 | 19.22 | 0.00% |
| **Distance to Coast (km)** | 10.53 | 932.25 | 251.74 | 87.10 | 347.33 | 0.00% |


## 4. Range and Type Checks

1. **Elevation**: Range is within physical limits (-100m to 9000m). No impossible negative or out-of-bounds elevation values detected.
2. **Land Cover Code**: All land cover codes belong to the valid ESA WorldCover classes. Description fields match the respective code classes exactly.
3. **Distance to Coast**: Values are non-negative and properly represented in kilometers. The distance range (approx. 10.53 km to 932.25 km) is geographically sound for the Indian subcontinent.

## 5. Conclusion

All required GIS features are fully integrated, populated, and successfully validated in the historical pipeline.
