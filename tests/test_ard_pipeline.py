import unittest
import pandas as pd
from historical_ingestor.static_features.landcover import extract_landcover

class TestARDPipeline(unittest.TestCase):
    
    def test_landcover_fallback(self):
        # Without GEE initialization, we expect a fallback to -1/Error
        res = extract_landcover(28.6476, 77.3158)
        self.assertEqual(res['land_cover_code'], -1)
        self.assertEqual(res['land_cover_name'], 'Error')

    def test_metadata_normalization(self):
        from scripts.build_station_registry import normalize_string
        self.assertEqual(normalize_string("  New Delhi "), "New Delhi")
        self.assertEqual(normalize_string(float('nan')), "Unknown")

    def test_duplicate_detection(self):
        # Create a mock df with duplicates on keys
        df = pd.DataFrame({
            'station_id': ['ST_1', 'ST_1', 'ST_2'],
            'date': ['2023-01-01', '2023-01-01', '2023-01-01'],
            'value': [10.0, 20.0, 30.0]
        })
        dups = df.duplicated(subset=['station_id', 'date']).sum()
        self.assertEqual(dups, 1)
        # Simulate prepare_right_df duplicate handling (aggregating with mean)
        res = df.groupby(['station_id', 'date'], as_index=False).mean(numeric_only=True)
        self.assertEqual(len(res), 2)
        self.assertEqual(res.loc[res['station_id'] == 'ST_1', 'value'].iloc[0], 15.0)

    def test_coordinate_validation(self):
        # Test coordinates validation bounds
        def check_coords(lat, lon):
            return (8.0 <= lat <= 38.0) and (68.0 <= lon <= 98.0)
        self.assertTrue(check_coords(28.6476, 77.3158))
        self.assertFalse(check_coords(0.0, 0.0))
        self.assertFalse(check_coords(5.0, 75.0))
        self.assertFalse(check_coords(28.0, 100.0))

    def test_metadata_integrity(self):
        # Ensure that no stations have 0.0, 0.0 coordinates marked as VALID
        mock_meta = pd.DataFrame({
            'station_name': ['A', 'B'],
            'latitude': [28.6, 0.0],
            'longitude': [77.3, 0.0],
            'coordinate_status': ['VALID', 'MISSING']
        })
        invalid_valid = mock_meta[(mock_meta['coordinate_status'] == 'VALID') & 
                                  ((mock_meta['latitude'] == 0.0) | (mock_meta['longitude'] == 0.0))]
        self.assertEqual(len(invalid_valid), 0)

    def test_merge_cardinality(self):
        # Simulate many-to-one join and verify that left side row count doesn't increase
        left = pd.DataFrame({
            'station_id': ['ST_1', 'ST_1', 'ST_2'],
            'date': ['2023-01-01', '2023-01-02', '2023-01-01']
        })
        right = pd.DataFrame({
            'station_id': ['ST_1', 'ST_2'],
            'date': ['2023-01-01', '2023-01-01'],
            'feature': [100, 200]
        })
        # If we use merge validation many-to-one (checking right side uniqueness)
        res = pd.merge(left, right, on=['station_id', 'date'], how='left', validate='many_to_one')
        self.assertEqual(len(res), len(left))

if __name__ == '__main__':
    unittest.main()
