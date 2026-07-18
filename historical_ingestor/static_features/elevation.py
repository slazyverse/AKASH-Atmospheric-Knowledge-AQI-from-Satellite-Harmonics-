import logging
try:
    import ee
except ImportError:
    pass

logger = logging.getLogger("ElevationExtractor")

def extract_elevation(lat: float, lon: float) -> dict:
    """Extract elevation for a given coordinate using Copernicus DEM."""
    try:
        point = ee.Geometry.Point(lon, lat)
        # Using Copernicus DEM GLO-30
        dataset = ee.ImageCollection("COPERNICUS/DEM/GLO30").select('DEM')
        # We need a single image, so mosaic it
        mosaic = dataset.mosaic()
        
        value = mosaic.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=point,
            scale=30,
            maxPixels=1e9
        ).getInfo()
        
        elev = value.get('DEM', None)
        if elev is None:
            # Fallback to SRTM
            dataset_srtm = ee.Image("CGIAR/SRTM90_V4")
            value = dataset_srtm.reduceRegion(
                reducer=ee.Reducer.first(),
                geometry=point,
                scale=90,
                maxPixels=1e9
            ).getInfo()
            elev = value.get('elevation', None)
            
        return {
            'elevation_m': float(elev) if elev is not None else -999.0
        }
    except Exception as e:
        logger.error(f"Failed to extract elevation for {lat}, {lon}: {e}")
        return {
            'elevation_m': -999.0
        }
