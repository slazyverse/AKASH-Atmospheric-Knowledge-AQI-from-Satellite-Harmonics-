# Historical Data Validation Report

## 1. Execution Summary
- **Total Rows Downloaded from API**: 1488
- **Total Rows Saved to CSV**: 1356
- **Total Rows Rejected**: 132

## 2. Rejection Audit
| Reason for Rejection | Count |
|---|---|
| missing measurement value | 132 |

## 3. Mock Data Audit
- **Mock Data Exists anywhere**: ✅ PASS (No mock data found)

## 4. Timestamps & Log Warnings Audit
- **Warnings for missing UTC/local timestamp in log**: 0 (Success criteria: 0) - ✅ PASS
- **Yearly date requests found in log**: 0 (Success criteria: 0) - ✅ PASS
- **At least one CSV has > 500 rows**: ✅ PASS

## 5. Live API Verification (Random 5 Rows)
| Station | CSV Timestamp | API Timestamp | CSV Value | API Value | Matches |
|---|---|---|---|---|---|
| Mumbai | 2025-01-22T23:30:00Z | 2025-01-22T23:30:00Z | 80.0 | 80.0 | ✅ YES |
| New Delhi | 2025-01-18T07:30:00Z | 2025-01-18T07:30:00Z | 147.0 | 147.0 | ✅ YES |
| New Delhi | 2025-01-08T23:30:00Z | 2025-01-08T23:30:00Z | 176.0 | 176.0 | ✅ YES |
| Mumbai | 2025-01-19T03:30:00Z | 2025-01-19T03:30:00Z | 151.0 | 151.0 | ✅ YES |
| New Delhi | 2025-01-28T16:30:00Z | 2025-01-28T16:30:00Z | 184.0 | 184.0 | ✅ YES |

## 6. Sample API Response
```json
{
  "value": 107.0,
  "flagInfo": {
    "hasFlags": false
  },
  "parameter": {
    "id": 2,
    "name": "pm25",
    "units": "\u00b5g/m\u00b3",
    "displayName": null
  },
  "period": {
    "label": "raw",
    "interval": "01:00:00",
    "datetimeFrom": {
      "utc": "2024-12-31T23:30:00Z",
      "local": "2025-01-01T05:00:00+05:30"
    },
    "datetimeTo": {
      "utc": "2025-01-01T00:30:00Z",
      "local": "2025-01-01T06:00:00+05:30"
    }
  },
  "coordinates": null,
  "summary": null,
  "coverage": {
    "expectedCount": 1,
    "expectedInterval": "01:00:00",
    "observedCount": 1,
    "observedInterval": "01:00:00",
    "percentComplete": 100.0,
    "percentCoverage": 100.0,
    "datetimeFrom": {
      "utc": "2024-12-31T23:30:00Z",
      "local": "2025-01-01T05:00:00+05:30"
    },
    "datetimeTo": {
      "utc": "2025-01-01T00:30:00Z",
      "local": "2025-01-01T06:00:00+05:30"
    }
  }
}
```

## 7. First 10 Saved Rows
| Location ID | Station Name | Latitude | Longitude | Parameter | Value | Unit | Date UTC | Date Local |
|---|---|---|---|---|---|---|---|---|
| 8039 | Mumbai | 19.07283 | 72.88261 | PM2.5 | 107.0 | µg/m³ | 2025-01-01T00:30:00Z | 2025-01-01T06:00:00+05:30 |
| 8039 | Mumbai | 19.07283 | 72.88261 | PM2.5 | 122.0 | µg/m³ | 2025-01-01T01:30:00Z | 2025-01-01T07:00:00+05:30 |
| 8039 | Mumbai | 19.07283 | 72.88261 | PM2.5 | 107.0 | µg/m³ | 2025-01-01T02:30:00Z | 2025-01-01T08:00:00+05:30 |
| 8039 | Mumbai | 19.07283 | 72.88261 | PM2.5 | 78.0 | µg/m³ | 2025-01-01T03:30:00Z | 2025-01-01T09:00:00+05:30 |
| 8039 | Mumbai | 19.07283 | 72.88261 | PM2.5 | 113.0 | µg/m³ | 2025-01-01T04:30:00Z | 2025-01-01T10:00:00+05:30 |
| 8039 | Mumbai | 19.07283 | 72.88261 | PM2.5 | 75.0 | µg/m³ | 2025-01-01T05:30:00Z | 2025-01-01T11:00:00+05:30 |
| 8039 | Mumbai | 19.07283 | 72.88261 | PM2.5 | 77.0 | µg/m³ | 2025-01-01T06:30:00Z | 2025-01-01T12:00:00+05:30 |
| 8039 | Mumbai | 19.07283 | 72.88261 | PM2.5 | 38.0 | µg/m³ | 2025-01-01T07:30:00Z | 2025-01-01T13:00:00+05:30 |
| 8039 | Mumbai | 19.07283 | 72.88261 | PM2.5 | 58.0 | µg/m³ | 2025-01-01T08:30:00Z | 2025-01-01T14:00:00+05:30 |
| 8039 | Mumbai | 19.07283 | 72.88261 | PM2.5 | 69.0 | µg/m³ | 2025-01-01T09:30:00Z | 2025-01-01T15:00:00+05:30 |