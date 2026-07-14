# Auto-generated script to download ERA5 data for India.
# Requirements: pip install cdsapi
# Configure credentials: ~/.cdsapirc or CDSAPI_KEY env var.

import cdsapi

client = cdsapi.Client()

dataset = 'reanalysis-era5-single-levels'
request = {
    "product_type": "reanalysis",
    "format": "netcdf",
    "variable": [
        "2m_temperature",
        "10m_u_component_of_wind",
        "10m_v_component_of_wind",
        "total_precipitation",
        "boundary_layer_height",
        "relative_humidity",
        "surface_pressure",
        "2m_dewpoint_temperature"
    ],
    "year": "2026",
    "month": "07",
    "day": "01",
    "time": [
        "00:00",
        "01:00",
        "02:00",
        "03:00",
        "04:00",
        "05:00",
        "06:00",
        "07:00",
        "08:00",
        "09:00",
        "10:00",
        "11:00",
        "12:00",
        "13:00",
        "14:00",
        "15:00",
        "16:00",
        "17:00",
        "18:00",
        "19:00",
        "20:00",
        "21:00",
        "22:00",
        "23:00"
    ],
    "area": [
        38.0,
        68.0,
        6.0,
        98.0
    ]
}
target = 'era5_meteorological_india.nc'

print(f"Downloading ERA5 data to {target} ...")
client.retrieve(dataset, request, target)
print("Download complete!")
