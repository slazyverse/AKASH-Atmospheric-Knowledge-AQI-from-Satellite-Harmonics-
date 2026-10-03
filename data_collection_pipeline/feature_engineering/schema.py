"""
Feature Schema Definitions.

Defines the structure, data types, units, and validation ranges for
satellite, meteorological, geographic, temporal, and metadata features.
"""

from typing import Any, Dict, List, Optional, Tuple


class FeatureMetadata:
    """Represents the definition and validation constraints of a single feature."""

    def __init__(
        self,
        name: str,
        group: str,
        data_type: str,  # 'numeric', 'categorical', 'boolean', 'datetime', 'string'
        units: str,
        source: str,
        valid_range: Optional[Tuple[float, float]] = None,
        description: str = ""
    ):
        self.name = name
        self.group = group.upper()
        self.data_type = data_type
        self.units = units
        self.source = source
        self.valid_range = valid_range
        self.description = description

    def validate_value(self, val: Any) -> bool:
        """
        Validates if a single raw value matches datatype and range constraints.
        Null values (None, NaN) are considered valid at schema level (checked via validator).
        """
        if val is None or val != val:  # check None or NaN
            return True
            
        if self.data_type == 'numeric':
            try:
                num = float(val)
                if self.valid_range:
                    return self.valid_range[0] <= num <= self.valid_range[1]
                return True
            except (ValueError, TypeError):
                return False
                
        elif self.data_type == 'boolean':
            return isinstance(val, bool) or str(val).lower() in {'true', 'false', '0', '1'}
            
        elif self.data_type == 'categorical':
            return True  # Categorical types are structurally checked at group level
            
        return True


# Global central feature specifications map
FEATURE_SCHEMA: Dict[str, FeatureMetadata] = {
    # 1. Pollutants / Ground Targets
    "PM2.5": FeatureMetadata("PM2.5", "target", "numeric", "ug/m3", "CPCB", (0.0, 1000.0), "Fine particulate matter"),
    "PM10": FeatureMetadata("PM10", "target", "numeric", "ug/m3", "CPCB", (0.0, 1500.0), "Coarse particulate matter"),
    "NO2": FeatureMetadata("NO2", "target", "numeric", "ug/m3", "CPCB", (0.0, 1000.0), "Nitrogen Dioxide ground concentration"),
    "SO2": FeatureMetadata("SO2", "target", "numeric", "ug/m3", "CPCB", (0.0, 2000.0), "Sulfur Dioxide ground concentration"),
    "CO": FeatureMetadata("CO", "target", "numeric", "mg/m3", "CPCB", (0.0, 100.0), "Carbon Monoxide ground concentration"),
    "O3": FeatureMetadata("O3", "target", "numeric", "ug/m3", "CPCB", (0.0, 1000.0), "Ozone ground concentration"),
    "AQI": FeatureMetadata("AQI", "target", "numeric", "index", "CPCB", (0.0, 500.0), "Air Quality Index value"),

    # 2. Satellite Features
    "AOD": FeatureMetadata("AOD", "satellite", "numeric", "unitless", "MODIS", (0.0, 5.0), "Aerosol Optical Depth at 550nm"),
    "HCHO": FeatureMetadata("HCHO", "satellite", "numeric", "mol/m2", "TROPOMI", (0.0, 0.01), "Formaldehyde vertical column density"),
    "NO2 Column": FeatureMetadata("NO2 Column", "satellite", "numeric", "mol/m2", "TROPOMI", (0.0, 0.01), "NO2 vertical column density"),
    "SO2 Column": FeatureMetadata("SO2 Column", "satellite", "numeric", "mol/m2", "TROPOMI", (0.0, 0.05), "SO2 vertical column density"),
    "CO Column": FeatureMetadata("CO Column", "satellite", "numeric", "mol/m2", "TROPOMI", (0.0, 0.5), "CO column number density"),
    "O3 Column": FeatureMetadata("O3 Column", "satellite", "numeric", "mol/m2", "TROPOMI", (0.0, 0.5), "O3 column density"),

    # 3. Meteorological Features
    "Temperature": FeatureMetadata("Temperature", "meteorology", "numeric", "K", "ERA5", (200.0, 330.0), "2m air temperature"),
    "Relative Humidity": FeatureMetadata("Relative Humidity", "meteorology", "numeric", "%", "ERA5", (0.0, 100.0), "Relative humidity"),
    "Boundary Layer Height": FeatureMetadata("Boundary Layer Height", "meteorology", "numeric", "m", "ERA5", (0.0, 6000.0), "Planetary boundary layer height"),
    "Wind Speed": FeatureMetadata("Wind Speed", "meteorology", "numeric", "m/s", "ERA5", (0.0, 100.0), "Wind speed derived from U/V components"),
    "Wind Direction": FeatureMetadata("Wind Direction", "meteorology", "numeric", "degrees", "ERA5", (0.0, 360.0), "Wind direction derived from U/V components"),
    "Surface Pressure": FeatureMetadata("Surface Pressure", "meteorology", "numeric", "Pa", "ERA5", (50000.0, 110000.0), "Surface atmospheric pressure"),

    # 4. Geographic Features
    "Elevation": FeatureMetadata("Elevation", "geography", "numeric", "m", "DEM", (-100.0, 9000.0), "Altitude above sea level"),
    "Distance to Coast": FeatureMetadata("Distance to Coast", "geography", "numeric", "km", "GIS", (0.0, 2000.0), "Distance to the nearest shoreline"),
    "Land Cover Class": FeatureMetadata("Land Cover Class", "geography", "categorical", "class", "MODIS", None, "Dominant land cover type index"),
    "Latitude": FeatureMetadata("Latitude", "geography", "numeric", "degrees", "Station", (5.0, 40.0), "Latitude coordinate"),
    "Longitude": FeatureMetadata("Longitude", "geography", "numeric", "degrees", "Station", (65.0, 100.0), "Longitude coordinate"),

    # 5. Temporal Features
    "Day of Week": FeatureMetadata("Day of Week", "temporal", "numeric", "index", "Derived", (0.0, 6.0), "Day index where Mon=0"),
    "Month": FeatureMetadata("Month", "temporal", "numeric", "index", "Derived", (1.0, 12.0), "Calendar month number"),
    "Season": FeatureMetadata("Season", "temporal", "categorical", "category", "Derived", None, "India meteorological season classification"),
    "Weekend Flag": FeatureMetadata("Weekend Flag", "temporal", "boolean", "bool", "Derived", None, "True if Saturday or Sunday"),

    # 6. Metadata Features
    "Station ID": FeatureMetadata("Station ID", "metadata", "string", "id", "Station", None, "Unique ground monitoring station code"),
    "Station Name": FeatureMetadata("Station Name", "metadata", "string", "name", "Station", None, "Name of monitoring station"),
    "Date": FeatureMetadata("Date", "metadata", "string", "date", "Pipeline", None, "Formatted string date yyyy-MM-dd"),
    "Time": FeatureMetadata("Time", "metadata", "string", "time", "Pipeline", None, "Observation time hh:mm:ss"),
    "Source": FeatureMetadata("Source", "metadata", "string", "source", "Pipeline", None, "Primary database source"),
}
