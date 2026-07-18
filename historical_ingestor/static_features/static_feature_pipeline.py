import os
import pandas as pd
import logging
from .landcover import extract_landcover
from .elevation import extract_elevation
from data_collection_pipeline.sentinel5p_collector import _try_import_ee, _authenticate_gee

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StaticFeaturePipeline")

def generate_static_features(metadata_csv_path: str, output_csv_path: str):
    logger.info("Starting static feature extraction pipeline...")
    
    if not os.path.exists(metadata_csv_path):
        logger.error(f"Metadata file not found: {metadata_csv_path}")
        return
        
    df = pd.read_csv(metadata_csv_path)
    if 'latitude' not in df.columns or 'longitude' not in df.columns or 'station_id' not in df.columns:
        logger.error("Metadata missing required columns (station_id, latitude, longitude)")
        return
        
    ee = _try_import_ee()
    _authenticate_gee(ee)
    
    results = []
    
    for _, row in df.iterrows():
        sid = row['station_id']
        lat = row['latitude']
        lon = row['longitude']
        
        logger.info(f"Processing station: {sid} at ({lat}, {lon})")
        
        lc_data = extract_landcover(lat, lon)
        elev_data = extract_elevation(lat, lon)
        
        record = {
            'station_id': sid,
            'latitude': lat,
            'longitude': lon,
            **lc_data,
            **elev_data
        }
        results.append(record)
        
    df_out = pd.DataFrame(results)
    
    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
    df_out.to_csv(output_csv_path, index=False)
    logger.info(f"Static features generated and saved to {output_csv_path}")

if __name__ == "__main__":
    meta_path = os.path.join("d:\\AKASH", "data_collection_pipeline", "metadata", "station_metadata.csv")
    out_path = os.path.join("d:\\AKASH", "historical_data", "static_features", "station_static_features.csv")
    generate_static_features(meta_path, out_path)
