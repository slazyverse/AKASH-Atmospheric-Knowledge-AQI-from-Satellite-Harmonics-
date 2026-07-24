# ARD V2 Data-Driven Validation Report
## Section 1 — Dataset Overview
- **Total rows**: 3333- **Total columns**: 55- **Dataset size (MB)**: 0.23- **Number of stations**: 12- **Earliest timestamp**: 2020-01-01 00:00:00+00:00- **Latest timestamp**: 2026-07-13 19:00:00+00:00- **Total study duration (days)**: 2385- **Number of unique days**: 33- **Number of unique months**: 3- **Number of unique years**: 3
## Section 2 — Station Summary
Top 5 and Bottom 5 Stations by Completeness:
| station_id   | station_name                   | city      | state         |   observations | first_observation         | last_observation          |   expected_observations |   completeness_percentage |   duplicate_timestamps |   missing_timestamps |
|:-------------|:-------------------------------|:----------|:--------------|---------------:|:--------------------------|:--------------------------|------------------------:|--------------------------:|-----------------------:|---------------------:|
| ST_0073c676  | Victoria, Kolkata - WBPCB      | Kolkata   | West Bengal   |              1 | 2026-07-13 19:00:00+00:00 | 2026-07-13 19:00:00+00:00 |                       1 |                       100 |                      0 |                    0 |
| ST_3c956e87  | Lalbagh, Lucknow - UPPCB       | Lucknow   | Uttar Pradesh |              1 | 2026-07-13 19:00:00+00:00 | 2026-07-13 19:00:00+00:00 |                       1 |                       100 |                      0 |                    0 |
| ST_44c28da7  | Sanathnagar, Hyderabad - TSPCB | Hyderabad | Telangana     |              1 | 2026-07-13 19:00:00+00:00 | 2026-07-13 19:00:00+00:00 |                       1 |                       100 |                      0 |                    0 |
| ST_6738592a  | Velachery, Chennai - TNPCB     | Chennai   | Tamil Nadu    |              1 | 2026-07-13 19:00:00+00:00 | 2026-07-13 19:00:00+00:00 |                       1 |                       100 |                      0 |                    0 |
| ST_d202e018  | Rajbansi Nagar, Patna - BSPCB  | Patna     | Bihar         |              1 | 2026-07-13 19:00:00+00:00 | 2026-07-13 19:00:00+00:00 |                       1 |                       100 |                      0 |                    0 |

| station_id   | station_name                          | city      | state       |   observations | first_observation         | last_observation          |   expected_observations |   completeness_percentage |   duplicate_timestamps |   missing_timestamps |
|:-------------|:--------------------------------------|:----------|:------------|---------------:|:--------------------------|:--------------------------|------------------------:|--------------------------:|-----------------------:|---------------------:|
| ST_86a1774d  | Anand Vihar, Delhi - DPCC             | Delhi     | Delhi       |            649 | 2025-01-01 00:30:00+00:00 | 2026-07-13 19:00:00+00:00 |                   13411 |                      4.84 |                      0 |                12762 |
| ST_c4e4d1a0  | Bandra Kurla Complex, Mumbai - MPCB   | Mumbai    | Maharashtra |            709 | 2025-01-01 00:30:00+00:00 | 2026-07-13 19:00:00+00:00 |                   13411 |                      5.29 |                      0 |                12702 |
| ST_e954f86b  | Central University, Hyderabad - TSPCB | Hyderabad | Telangana   |            557 | 2025-01-01 00:30:00+00:00 | 2025-01-31 23:30:00+00:00 |                     744 |                     74.87 |                      0 |                  187 |
| ST_db6bb351  | Ballygunge, Kolkata - WBPCB           | Kolkata   | West Bengal |            680 | 2025-01-01 00:30:00+00:00 | 2025-01-31 23:30:00+00:00 |                     744 |                     91.4  |                      0 |                   64 |
| ST_986f38db  | Arumbakkam, Chennai - TNPCB           | Chennai   | Tamil Nadu  |            731 | 2025-01-01 00:30:00+00:00 | 2025-01-31 23:30:00+00:00 |                     744 |                     98.25 |                      0 |                   13 |

## Section 3 — Missing Value Analysis
- **Features >5% missing**: None
- **Features >20% missing**: utc_time, PM10, NO2, SO2, CO, O3, location, AOD, AOD_055, AOD_047
- **Completely missing features**: None

| feature               |   total_missing_values |   missing_percentage |   available_percentage |
|:----------------------|-----------------------:|---------------------:|-----------------------:|
| utc_time              |                   3325 |                99.76 |                   0.24 |
| PM10                  |                   3325 |                99.76 |                   0.24 |
| NO2                   |                   3325 |                99.76 |                   0.24 |
| SO2                   |                   3325 |                99.76 |                   0.24 |
| CO                    |                   3325 |                99.76 |                   0.24 |
| O3                    |                   3325 |                99.76 |                   0.24 |
| location              |                   3325 |                99.76 |                   0.24 |
| AOD                   |                   1257 |                37.71 |                  62.29 |
| AOD_055               |                   1257 |                37.71 |                  62.29 |
| AOD_047               |                   1257 |                37.71 |                  62.29 |
| v_wind_component      |                      9 |                 0.27 |                  99.73 |
| Relative Humidity     |                      9 |                 0.27 |                  99.73 |
| Boundary Layer Height |                      9 |                 0.27 |                  99.73 |
| Surface Pressure      |                      9 |                 0.27 |                  99.73 |
| u_wind_component      |                      9 |                 0.27 |                  99.73 |

## Section 4 — Feature Availability
### Ground Features
- Feature count: 7
- Average completeness: 28.71%
- Minimum completeness: 0.24%
- Maximum completeness: 100.0%

### Meteorological Features
- Feature count: 6
- Average completeness: 99.73%
- Minimum completeness: 99.73%
- Maximum completeness: 99.73%

### Satellite Features
- Feature count: 6
- Average completeness: 81.01%
- Minimum completeness: 62.29%
- Maximum completeness: 99.73%

### Static Features
- Feature count: 3
- Average completeness: 100.0%
- Minimum completeness: 100.0%
- Maximum completeness: 100.0%

## Section 5 — Ground Data QA
- **VALID**: 3333 (100.0%)
- **SUSPECT_STUCK**: 0 (0.0%)
- **SUSPECT_SPIKE**: 0 (0.0%)
- **INVALID**: 0 (0.0%)

## Section 6 — Temporal Validation
- Expected hourly timestamps: 29061
- Observed timestamps: 3333
- Missing timestamps: 25728 (88.53%)
- Duplicate timestamps: 0
- Largest temporal gap: 527 days 19:30:00
- Median sampling interval: 0 days 01:00:00
- Mean sampling interval: 0 days 08:44:50.514905

**Hourly Continuity**: PASS
**Monotonic Timestamps**: FAIL

## Section 7 — Spatial Validation
- Duplicate coordinates: 12
- Missing coordinates: 0
- Stations outside India bounds: 0
- Latitude range: 8.5149093 to 34.066206
- Longitude range: 70.776774 to 94.636574

- All ARD stations in metadata: False
- All ARD stations in static features: True

## Section 8 — Static Feature Validation
### Elevation Validation
- Minimum: 8.00 m
- Maximum: 885.00 m
- Mean: 146.83 m
- Median: 9.00 m
- Standard Deviation: 217.50 m
- Missing Percentage: 0.00%
- Range Validation (-100m to 9000m): PASS
- Completeness Validation: PASS

### Land Cover Code Validation
- Minimum Code: 10.0
- Maximum Code: 50.0
- Mean Code: 35.52
- Median Code: 50.0
- Standard Deviation: 19.22
- Missing Percentage: 0.00%
- Class Code Validity Check: PASS
- Completeness Validation: PASS

### Land Cover Frequencies
- Built-up (Urban): 2126
- Trees: 1206
- Cropland: 1

### Distance to Coast Validation (km)
- Minimum: 10.53 km
- Maximum: 932.25 km
- Mean: 251.74 km
- Median: 87.10 km
- Standard Deviation: 347.33 km
- Missing Percentage: 0.00%
- Range Validation (0 to 5000km): PASS
- Completeness Validation: PASS

## Section 9 — ERA5 Validation
- Coverage percentage: 99.73%
- Missing values: 54
- Variables available: Temperature, Relative Humidity, Boundary Layer Height, Surface Pressure, Wind Speed, Wind Direction
- Temperature outside physical limits (-50 to 60C): 3324

## Section 10 — Sentinel Validation
- Coverage: 99.73%
- **HCHO**: Min=7.004705031473888e-05, Max=0.00044142130624046517, Mean=0.0003, Median=0.0002479317143486015
- **NO2 Column**: Min=7.838746085754742e-05, Max=0.0003376602490122128, Mean=0.0002, Median=0.0002115846929564032
- **CO Column**: Min=0.006697373081805311, Max=0.04485778915903632, Mean=0.0257, Median=0.02588078835889689

## Section 11 — MODIS Validation
- Coverage: 62.29%
- **AOD**: Min=0.152, Max=2.164, Mean=0.6546, Median=0.596
- **AOD_047**: Min=0.202, Max=2.666, Mean=0.8319, Median=0.7665000000000001
- **AOD_055**: Min=0.152, Max=2.164, Mean=0.6546, Median=0.596

## Section 12 — Merge Validation
- Ground Data Available: 28.71%
- ERA5 Merged: 99.73%
- Satellite Merged: 81.01%
- Static Features Merged: 100.0%

## Section 13 — Correlation Overview
**Highest Positive Correlations:**
- PM2.5 & Relative Humidity: 0.154
- PM2.5 & AOD: 0.342
- AOD & PM2.5: 0.342
- PM10 & PM2.5: 0.98
- PM2.5 & PM10: 0.98

**Highest Negative Correlations:**
- PM2.5 & NO2: -0.163
- NO2 & PM2.5: -0.163
- Temperature & PM2.5: -0.106
- PM2.5 & Temperature: -0.106
- NO2 & PM10: -0.097

## Section 14 — Outlier Detection
Top features with highest outlier percentages:
| feature           |            Q1 |           Q3 |        IQR |   Lower_Bound |   Upper_Bound |   Outlier_Count |   Outlier_Percentage |
|:------------------|--------------:|-------------:|-----------:|--------------:|--------------:|----------------:|---------------------:|
| longitude         |     77.2245   |     80.2112  |   2.98675  |     72.7443   |      84.6913  |             681 |                20.43 |
| distance_to_coast |     16.39     |    274       | 257.61     |   -370.025    |     660.415   |             651 |                19.53 |
| elevation         |      9        |    209       | 200        |   -291        |     509       |             559 |                16.77 |
| Wind Direction    |    277.24     |    312.361   |  35.1209   |    224.559    |     365.043   |             145 |                 4.35 |
| PM2.5             |     66        |    150       |  84        |    -60        |     276       |             122 |                 3.66 |
| AOD               |      0.4135   |      0.832   |   0.4185   |     -0.21425  |       1.45975 |              46 |                 1.38 |
| AOD_055           |      0.4135   |      0.832   |   0.4185   |     -0.21425  |       1.45975 |              46 |                 1.38 |
| AOD_047           |      0.539    |      1.0505  |   0.5115   |     -0.22825  |       1.81775 |              46 |                 1.38 |
| u_wind_component  |      0.656075 |      1.33912 |   0.683045 |     -0.368492 |       2.36369 |              32 |                 0.96 |
| Surface Pressure  | 101184        | 101446       | 261.904    | 100791        |  101839       |              30 |                 0.9  |

## Section 15 — Data Integrity
- Duplicated Primary Keys (station_id + timestamp): 0
- Future timestamps: 0
- Empty station IDs: 0
- Invalid coordinate ranges: 0

## Section 16 — Pipeline Summary
- **Dataset Completeness**: PASS
- **Ground Coverage**: WARNING
- **Satellite Coverage**: PASS
- **Temporal Consistency**: WARNING
- **Duplicate Detection**: PASS
- **Coordinate Validation**: PASS
