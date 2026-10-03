# Google Earth Engine Data Pipeline

This documentation outlines the design and modules of the **Google Earth Engine (GEE)** data pipeline package developed under Soumyadeb's scope for the **VAYU-DRISHTI** (AKASH) project.

---

## 📁 Package Layout

All files are stored in the modular package [data_collection_pipeline/earth_engine/](file:///Users/soumyadebtripathy/Downloads/StockSphere_Project/Akaash/data_collection_pipeline/earth_engine/):

* **`config.py`**: Bounding boxes, environment keys, default ranges.
* **`initializer.py`**: Authentication helper supporting user keys & service accounts.
* **`dataset_catalog.py`**: Mapping of standard pollutant and climate collection catalog IDs, native resolution meters, and target bands.
* **`analysis_grid.py`**: Generator for the 5 km common grid system over India or target bounding geometries.
* **`base_loader.py`**: Base class definition standardizing spatial/temporal filtering and metadata queries.
* **`tropomi.py`**: Sentinel-5P TROPOMI column loaders ($HCHO$, $NO_2$, $SO_2$, $CO$, $O_3$) with custom QA/cloud fraction masking.
* **`modis.py`**: MODIS MCD19A2 MAIAC daily 1km AOD loader with QA-bitmask filtering.
* **`era5.py`**: ERA5 Land hourly atmospheric data loader supporting daily downsampling aggregation.
* **`viirs.py`**: VIIRS active fire hotspots loader with confidence-based anomaly filtering.
* **`export.py`**: Abstract interfaces/stubs for image exports (Drive, GEE Assets, GCS).
* **`utils.py`**: Sensory cloud masking algorithms and coordinate parsing helpers.

---

## ⚙️ Authentication & Setup

To use the Earth Engine pipeline, ensure the Google Earth Engine Python library (`earthengine-api`) is installed. Add it to [requirements.txt](file:///Users/soumyadebtripathy/Downloads/StockSphere_Project/Akaash/data_collection_pipeline/requirements.txt):

```text
earthengine-api>=0.1.350
```

### 1. Interactive Authentication
If running on a local desktop or development machine:
```bash
earthengine authenticate
```

### 2. Headless/Service Account Initialization
If running inside automated server environments, specify the environment variables:
```env
EE_SA_KEY_PATH=/path/to/service-account.json
EE_PROJECT=your-gcp-project-id
```

The initializer module will automatically pick these up on startup.

---

## 🛰️ Supported Datasets

| Alias | Collection ID | Native Resolution | Bands Selected |
| :--- | :--- | :---: | :--- |
| **`TROPOMI_HCHO`** | `COPERNICUS/S5P/OFFL/L3_HCHO` | 5.5 km | `HCHO_tropospheric_column_amount` |
| **`TROPOMI_NO2`** | `COPERNICUS/S5P/OFFL/L3_NO2` | 5.5 km | `NO2_column_number_density` |
| **`MODIS_MAIAC_AOD`** | `MODIS/061/MCD19A2_GRANULES` | 1 km | `Optical_Depth_047`, `Optical_Depth_055` |
| **`ERA5_LAND_HOURLY`** | `ECMWF/ERA5_LAND/HOURLY` | 11.1 km | `temperature_2m`, `u_component_of_wind_10m`, etc. |
| **`VIIRS_ACTIVE_FIRE`**| `NASA/LANCE/SNPP_VIIRS/C2` | 375 m | `T21`, `confidence`, `fire` |

---

## 🗺️ 5 km Common Grid Utility

The common grid system creates spatial anchors to match satellite readings with ground station observations.
```python
from data_collection_pipeline.earth_engine import AnalysisGrid
from data_collection_pipeline.earth_engine.config import INDIA_BBOX

# Initialize a 5 km grid over India
grid = AnalysisGrid(bbox=INDIA_BBOX, resolution_km=5.0)

# Generate offline coordinate list of centroids
coords = grid.generate_python_grid_coords()
print(f"Generated {len(coords)} grid centroids.")

# Get GEE FeatureCollection
gee_feature_collection = grid.to_gee_feature_collection()
```
