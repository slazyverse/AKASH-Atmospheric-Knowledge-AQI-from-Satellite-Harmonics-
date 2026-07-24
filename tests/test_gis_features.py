import unittest
import os
import pandas as pd
import numpy as np
from pathlib import Path

# Ensure GEE_PROJECT_ID env var is set for importing configs
os.environ['GEE_PROJECT_ID'] = 'aqi-satellite'

from data_collection_pipeline.static_features import _compute_coastline_distances
from data_collection_pipeline import config

class TestGISRegression(unittest.TestCase):
    
    def setUp(self):
        self.ard_path = Path("D:/AKASH/data_collection_pipeline/processed_data/analysis_ready_dataset_v2.parquet")
        self.static_csv_path = Path("D:/AKASH/data_collection_pipeline/processed_data/station_static_features.csv")
        self.meta_path = Path("D:/AKASH/data_collection_pipeline/metadata/station_metadata.csv")
        self.bridge_path = Path("D:/AKASH/data_collection_pipeline/metadata/station_id_bridge.csv")

    def test_distance_to_coast_computation(self):
        """Test distance to coast geodesic calculation for known coastal/inland coordinates."""
        # Mumbai vs Delhi
        df_stations = pd.DataFrame({
            "Station ID": ["STN_MUM", "STN_DEL"],
            "Latitude": [18.9220, 28.6139],
            "Longitude": [72.8347, 77.2090]
        })
        
        distances = _compute_coastline_distances(df_stations)
        
        if distances:
            mumbai_dist = distances.get("STN_MUM", float('inf'))
            delhi_dist = distances.get("STN_DEL", float('-inf'))
            
            # Mumbai is coastal: distance to coast should be low (< 50 km)
            self.assertLess(mumbai_dist, 50.0, f"Mumbai distance {mumbai_dist} km is too large.")
            # Delhi is inland: distance to coast should be high (> 500 km)
            self.assertGreater(delhi_dist, 500.0, f"Delhi distance {delhi_dist} km is too small.")
            self.assertTrue(mumbai_dist >= 0.0)
            self.assertTrue(delhi_dist >= 0.0)

    def test_static_features_file_contents(self):
        """Verify the generated station_static_features.csv structure and data limits."""
        self.assertTrue(self.static_csv_path.exists(), "station_static_features.csv does not exist.")
        df = pd.read_csv(self.static_csv_path)
        
        # Verify required columns exist
        required_cols = {'station_id', 'elevation', 'land_cover_code', 'land_cover_desc', 'distance_to_coast'}
        self.assertTrue(required_cols.issubset(df.columns), f"Missing columns in static features: {required_cols - set(df.columns)}")
        
        # Check completeness (no nulls)
        self.assertEqual(df['elevation'].isna().sum(), 0, "Null values found in elevation.")
        self.assertEqual(df['land_cover_code'].isna().sum(), 0, "Null values found in land_cover_code.")
        self.assertEqual(df['distance_to_coast'].isna().sum(), 0, "Null values found in distance_to_coast.")
        
        # Check numeric ranges
        self.assertTrue((df['elevation'] >= -100).all() and (df['elevation'] <= 9000).all(), "Elevation out of physical bounds.")
        self.assertTrue((df['distance_to_coast'] >= 0.0).all(), "Distance to coast contains negative values.")
        
        valid_classes = {10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100}
        self.assertTrue(set(df['land_cover_code'].dropna().unique()).issubset(valid_classes), "Invalid ESA land cover classes found.")

    def test_ard_propagation(self):
        """Verify that GIS features are fully propagated and merged into the ARD v2 Parquet dataset."""
        self.assertTrue(self.ard_path.exists(), "analysis_ready_dataset_v2.parquet does not exist.")
        df = pd.read_parquet(self.ard_path)
        
        # Verify columns exist
        for col in ['elevation', 'land_cover_code', 'land_cover_desc', 'distance_to_coast']:
            self.assertIn(col, df.columns, f"Column {col} was not propagated into the ARD.")
            
        # Verify completeness (0% missing in final ARD)
        self.assertEqual(df['elevation'].isna().sum(), 0, "Null values propagated to elevation in ARD.")
        self.assertEqual(df['land_cover_code'].isna().sum(), 0, "Null values propagated to land_cover_code in ARD.")
        self.assertEqual(df['distance_to_coast'].isna().sum(), 0, "Null values propagated to distance_to_coast in ARD.")

    def test_validation_reports(self):
        """Verify that validation reports and statistics are generated correctly."""
        validation_report = Path("D:/AKASH/validation_report_v2.md")
        self.assertTrue(validation_report.exists(), "validation_report_v2.md does not exist.")
        
        # Read the report and check that all three GIS features are included
        with open(validation_report, 'r', encoding='utf-8') as f:
            content = f.read()
            
        self.assertIn("Elevation Validation", content)
        self.assertIn("Land Cover Code Validation", content)
        self.assertIn("Distance to Coast Validation", content)
        self.assertIn("All ARD stations in static features: True", content)

if __name__ == '__main__':
    unittest.main()
