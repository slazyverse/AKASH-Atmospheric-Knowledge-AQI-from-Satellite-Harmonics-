import unittest
import pandas as pd
import numpy as np

class TestValidationFixes(unittest.TestCase):
    def test_no_duplicate_primary_keys(self):
        # Verify the final ARD doesn't have duplicate primary keys
        df = pd.read_parquet("d:\\AKASH\\data_collection_pipeline\\processed_data\\analysis_ready_dataset_v2.parquet")
        duplicates = df.duplicated(subset=['station_id', 'timestamp_utc']).sum()
        self.assertEqual(duplicates, 0, f"Expected 0 duplicates, found {duplicates}")

    def test_no_invalid_coordinates(self):
        # Verify there are no 0.0, 0.0 or out of bounds coordinates
        df = pd.read_parquet("d:\\AKASH\\data_collection_pipeline\\processed_data\\analysis_ready_dataset_v2.parquet")
        
        zero_coords = df[(df['latitude'] == 0.0) & (df['longitude'] == 0.0)]
        self.assertEqual(len(zero_coords), 0, f"Found {len(zero_coords)} rows with 0.0, 0.0 coordinates")
        
        out_of_bounds = df[
            (df['latitude'] < 8.0) | (df['latitude'] > 38.0) | 
            (df['longitude'] < 68.0) | (df['longitude'] > 98.0)
        ]
        self.assertEqual(len(out_of_bounds), 0, f"Found {len(out_of_bounds)} rows with out of bounds coordinates")

    def test_missing_coordinates_quarantined(self):
        # Verify that quarantined stations (missing coordinates) are not present in ARD
        ard_df = pd.read_parquet("d:\\AKASH\\data_collection_pipeline\\processed_data\\analysis_ready_dataset_v2.parquet")
        meta_df = pd.read_csv("d:\\AKASH\\data_collection_pipeline\\metadata\\station_metadata.csv")
        
        missing_stations = meta_df[meta_df['coordinate_status'] == 'MISSING']['station_id'].unique()
        stations_in_ard = ard_df['station_id'].unique()
        
        overlap = set(missing_stations).intersection(set(stations_in_ard))
        self.assertEqual(len(overlap), 0, f"Found {len(overlap)} quarantined stations in the ARD")

    def test_timestamp_normalization(self):
        # Verify alignment strategy for HH:30 -> HH:00 floor
        cpcb_ts = pd.to_datetime("2025-01-01T00:30:00")
        era5_ts = pd.to_datetime("2025-01-01T00:00:00")
        
        # Applying floor('h') should align CPCB to ERA5 hour
        aligned_ts = cpcb_ts.floor('h')
        self.assertEqual(aligned_ts, era5_ts, "Floor alignment strategy failed")

        # Test mixing timezone-aware (OpenAQ) and timezone-naive parsing standard
        parsed_utc = pd.to_datetime("2026-07-13T19:00:00+00:00", format='mixed', utc=True)
        self.assertIsNotNone(parsed_utc.tzinfo, "Parsed timestamp should be timezone-aware")

    def test_station_mapping(self):
        # Verify the station mapping report is generated and contains required columns
        mapping_df = pd.read_csv("d:\\AKASH\\station_mapping_report.csv")
        required_cols = [
            'canonical_station_id', 'cpcb_station_id', 
            'openaq_station_id', 'legacy_station_id', 'hashed_station_id'
        ]
        for col in required_cols:
            self.assertIn(col, mapping_df.columns, f"Required column {col} missing from mapping report")
            
        # Verify Anand Vihar mapping is present and correct
        av_row = mapping_df[mapping_df['legacy_station_id'] == 'STN_080']
        self.assertFalse(av_row.empty, "Anand Vihar legacy ID STN_080 not found in mapping report")
        self.assertEqual(av_row['canonical_station_id'].iloc[0], 'ST_86a1774d', "Anand Vihar canonical station ID mismatch")

    def test_openaq_parsing_utc_time(self):
        # Verify the openaq timestamp validation report contains zero NaT
        validation_df = pd.read_csv("d:\\AKASH\\openaq_timestamp_validation.csv")
        self.assertIn('is_nat', validation_df.columns)
        
        # Check that there are zero NaT timestamps verified
        nat_count = validation_df['is_nat'].sum()
        self.assertEqual(nat_count, 0, f"Found {nat_count} NaT values in OpenAQ timestamp validation")

        # Check all validation statuses are PASS
        status_fails = (validation_df['validation_status'] != 'PASS').sum()
        self.assertEqual(status_fails, 0, f"Found {status_fails} validation failures in OpenAQ timestamp validation")

    def test_feature_completeness_after_repair(self):
        # Verify feature completeness is restored for meteorology and satellite columns
        df = pd.read_parquet("d:\\AKASH\\data_collection_pipeline\\processed_data\\analysis_ready_dataset_v2.parquet")
        
        # Check that Temperature (meteorology) has non-zero completeness
        temp_null_pct = df['Temperature'].isna().mean() * 100
        self.assertLess(temp_null_pct, 10.0, f"Temperature feature completeness degraded: {temp_null_pct}% null")

        # Check that HCHO (satellite) has non-zero completeness
        hcho_null_pct = df['HCHO'].isna().mean() * 100
        self.assertLess(hcho_null_pct, 10.0, f"HCHO feature completeness degraded: {hcho_null_pct}% null")

        # Check that AOD (satellite) has non-zero completeness (allows for expected cloud masking)
        aod_null_pct = df['AOD'].isna().mean() * 100
        self.assertLess(aod_null_pct, 50.0, f"AOD feature completeness degraded: {aod_null_pct}% null")

    def test_gis_feature_presence_and_completeness(self):
        # Verify GIS features exist in the final ARD and are 100% complete
        df = pd.read_parquet("d:\\AKASH\\data_collection_pipeline\\processed_data\\analysis_ready_dataset_v2.parquet")
        
        for feat in ['elevation', 'land_cover_code', 'land_cover_desc', 'distance_to_coast']:
            self.assertIn(feat, df.columns, f"GIS feature '{feat}' missing from ARD")
            missing_pct = df[feat].isna().mean() * 100
            self.assertEqual(missing_pct, 0.0, f"GIS feature '{feat}' is not 100% complete: {missing_pct}% missing")

    def test_gis_feature_ranges_and_types(self):
        # Verify physical ranges and types of GIS features in ARD
        df = pd.read_parquet("d:\\AKASH\\data_collection_pipeline\\processed_data\\analysis_ready_dataset_v2.parquet")
        
        # Elevation check
        self.assertTrue(np.issubdtype(df['elevation'].dtype, np.number), "Elevation should be numeric")
        self.assertTrue((df['elevation'] >= -100).all() and (df['elevation'] <= 9000).all(), "Elevation contains impossible values")
        
        # Land Cover check
        valid_classes = {10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100}
        unique_codes = set(df['land_cover_code'].unique())
        self.assertTrue(unique_codes.issubset(valid_classes), f"Invalid land cover codes detected: {unique_codes - valid_classes}")
        
        # Distance to Coast check
        self.assertTrue(np.issubdtype(df['distance_to_coast'].dtype, np.number), "Distance to coast should be numeric")
        self.assertTrue((df['distance_to_coast'] >= 0.0).all(), "Distance to coast contains negative values")
        self.assertTrue((df['distance_to_coast'] <= 5000.0).all(), "Distance to coast contains unreasonably large values (>5000km)")

if __name__ == '__main__':
    unittest.main()


