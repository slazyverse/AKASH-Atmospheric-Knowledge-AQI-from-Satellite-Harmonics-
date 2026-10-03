"""
Analysis Grid Module.

Implements the common 5 km spatial analysis grid over India (or target bounding boxes)
for grid centroid generation, cell geometry generation, and Earth Engine coordinate
alignment.
"""

import math
from typing import List, Tuple, Union


class AnalysisGrid:
    """
    Utility class to construct and manage the common 5 km analysis grid
    over a specified bounding box.
    """

    def __init__(
        self,
        bbox: List[float],  # [West, South, East, North]
        resolution_km: float = 5.0
    ):
        self.bbox = bbox
        self.resolution_km = resolution_km
        
        # Approximate degree conversion: 1 degree latitude ~ 111.12 km
        # 5 km ~ 5.0 / 111.12 ~ 0.045 degrees.
        # Longitude spacing varies by latitude, but we use the mean latitude of the bbox for uniform grid cells.
        self.lat_step = resolution_km / 111.12
        
        mean_lat = (bbox[1] + bbox[3]) / 2.0
        self.lon_step = resolution_km / (111.12 * math.cos(math.radians(mean_lat)))

    def generate_python_grid_coords(self) -> List[Tuple[float, float]]:
        """
        Generates a list of (longitude, latitude) grid point centroids
        within the bounding box using pure Python (offline execution).
        
        Returns:
            List of (lon, lat) tuples representing grid centroids.
        """
        w, s, e, n = self.bbox
        centroids = []
        
        # Use simple coordinate generation
        curr_lat = s + (self.lat_step / 2.0)
        while curr_lat <= n:
            curr_lon = w + (self.lon_step / 2.0)
            while curr_lon <= e:
                centroids.append((round(curr_lon, 5), round(curr_lat, 5)))
                curr_lon += self.lon_step
            curr_lat += self.lat_step
            
        return centroids

    def to_gee_feature_collection(self) -> Union["ee.FeatureCollection", None]:
        """
        Converts the generated grid coordinates to a GEE ee.FeatureCollection
        of point centroids.
        
        Returns:
            ee.FeatureCollection containing the grid centroids, or None if ee is not initialized.
        """
        try:
            import ee
            from data_collection_pipeline.earth_engine.initializer import is_ee_initialized
        except ImportError:
            return None
            
        if not is_ee_initialized():
            return None
            
        coords = self.generate_python_grid_coords()
        features = []
        
        for idx, (lon, lat) in enumerate(coords):
            geom = ee.Geometry.Point([lon, lat])
            feature = ee.Feature(geom, {"grid_id": f"GRID_{idx:06d}", "longitude": lon, "latitude": lat})
            features.append(feature)
            
        return ee.FeatureCollection(features)

    def generate_gee_grid_cells(self) -> Union["ee.FeatureCollection", None]:
        """
        Generates a cell-based grid of bounding polygons instead of points in GEE.
        
        Returns:
            ee.FeatureCollection containing grid square cells, or None if ee is not initialized.
        """
        try:
            import ee
            from data_collection_pipeline.earth_engine.initializer import is_ee_initialized
        except ImportError:
            return None
            
        if not is_ee_initialized():
            return None
            
        coords = self.generate_python_grid_coords()
        features = []
        
        half_lat = self.lat_step / 2.0
        half_lon = self.lon_step / 2.0
        
        for idx, (lon, lat) in enumerate(coords):
            # Compute corners of the 5km bounding cell
            cell_coords = [
                [lon - half_lon, lat - half_lat],
                [lon + half_lon, lat - half_lat],
                [lon + half_lon, lat + half_lat],
                [lon - half_lon, lat + half_lat],
                [lon - half_lon, lat - half_lat]
            ]
            geom = ee.Geometry.Polygon([cell_coords])
            feature = ee.Feature(geom, {"grid_id": f"CELL_{idx:06d}", "centroid_lon": lon, "centroid_lat": lat})
            features.append(feature)
            
        return ee.FeatureCollection(features)
