# Analytical Data Collection Processing Report (v2)

*Completed at: 2026-07-17 15:33:46*
*Total pipeline execution time: 738.42 seconds*

## 1. Pipeline Architecture Summary
This historical ingestion pipeline sequentially processes, validates, and consolidates multi-year ground observations and atmospheric predictors.

| Ingestion Step | Target Data / Platform | Storage format | Status | Cache / Resume |
| :--- | :--- | :---: | :---: | :---: |
| 1. Metadata Registry | CPCB & OpenAQ Master List | CSV | SUCCESS | Yes |
| 2. GEE Static features | ESA WorldCover & SRTM elevation | CSV | SUCCESS | Yes (Mock fallback) |
| 3. Ground observations | CPCB & OpenAQ Historical observations (2025) | Parquet | SUCCESS | Yes |
| 4. ERA5 Meteorology | ECMWF Single-levels Hourly (2023-2025) | Parquet | SUCCESS | Yes (Month-by-month cache) |
| 5. Sentinel-5P Columns | TROPOMI NO2, HCHO, CO Columns (2023-2025) | Parquet | SUCCESS | Yes (Daily QA filtered) |
| 6. MODIS AOD | MAIAC Daily 1km Optical Depth (2023-2025) | Parquet | SUCCESS | Yes (QA bitmask filtered) |
| 7. Analytical Merger | Consolidated Multi-source Join | Parquet & CSV | SUCCESS | Output: `analysis_ready_dataset_v2` |

## 2. Predictor Resolution & Variables
* **Meteorology (ERA5)**: Hourly Temperature, Relative Humidity, Boundary Layer Height, Surface Pressure, Wind Speed, Wind Direction.
* **Sentinel-5P TROPOMI**: Tropospheric NO2 Column, HCHO Column, CO Column.
* **MODIS MAIAC**: Aerosol Optical Depth (AOD) at 550nm and 470nm.
* **Static Terrain features**: Elevation (meters) and land cover class (e.g. Trees, Shrubland, Built-up).

## 3. Future Spatial Extension Points Design
The v2 dataset includes placeholder extension columns mapped for:
1. **Population Density (`ext_population_density`)**: Extracted from Gridded Population of the World (GPW v4) at station point buffers.
2. **Road Density (`ext_road_density`)**: Sum of OpenStreetMap highway feature lengths divided by point buffer areas.
3. **Distance to Coast (`ext_distance_to_coast`)**: Calculated spherical distance (meters) to the nearest maritime coastline vector.
4. **Nighttime Lights (`ext_nighttime_lights`)**: Averaged NOAA VIIRS daily/monthly nighttime radiance profiles.
5. **Distance to Industrial Zone (`ext_distance_to_industrial`)**: Distance to closest classified industrial polygon.
