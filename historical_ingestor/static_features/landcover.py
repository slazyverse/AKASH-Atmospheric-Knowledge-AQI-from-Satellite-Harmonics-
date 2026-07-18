import logging
try:
    import ee
except ImportError:
    pass

logger = logging.getLogger("LandCoverExtractor")

# ESA WorldCover 2021 v200 class values
LANDCOVER_CLASSES = {
    10: "Trees",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen"
}

def extract_landcover(lat: float, lon: float) -> dict:
    """Extract land cover for a given coordinate using ESA WorldCover."""
    try:
        point = ee.Geometry.Point(lon, lat)
        dataset = ee.ImageCollection("ESA/WorldCover/v200").first()
        value = dataset.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=point,
            scale=10,
            maxPixels=1e9
        ).getInfo()
        
        lc_code = value.get('Map', -1)
        if lc_code is None:
            lc_code = -1
        
        return {
            'land_cover_code': lc_code,
            'land_cover_name': LANDCOVER_CLASSES.get(lc_code, "Unknown")
        }
    except Exception as e:
        logger.error(f"Failed to extract landcover for {lat}, {lon}: {e}")
        return {
            'land_cover_code': -1,
            'land_cover_name': "Error"
        }
