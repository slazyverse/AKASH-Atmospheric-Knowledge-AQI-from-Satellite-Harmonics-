# Ground-Data Ingestion Validation & Audit Report

*Execution Completed at: 2026-07-17 15:23:32*

**Total Processing Time**: 3.57 seconds

## 1. Ground observations Volume Summary
| Data Source | Raw Rows Ingested | Standardized Measurements |
| :--- | :---: | :---: |
| CPCB Ingestion | 6650 | 6650 |
| OpenAQ Ingestion | 0 | 0 |
| **Merged Unified Warehouse** | - | **6650** |

## 2. Ingestion QA Flags Audit
| QA Flag Status | Total Measurements | Percentage | Action Description |
| :--- | :---: | :---: | :--- |
| `VALID` | 6628 | 99.67% | Kept as-is for training. |
| `SUSPECT_STUCK` | 0 | 0.00% | Retained but annotated for outlier audits. |
| `SUSPECT_SPIKE` | 22 | 0.33% | Retained but annotated for outlier audits. |
| `INVALID` | 0 | 0.00% | Value set to NaN (excluded from model). |

## 3. Station Metadata Mapping Registry
| Registry ID | Station Name | Network | Records Contributed | Source Ingested |
| :--- | :--- | :---: | :---: | :---: |
| `STN_065` | Arumbakkam, Chennai - TNPCB | CPCB | 1462 | CPCB |
| `STN_080` | Anand Vihar, Delhi - DPCC | CPCB | 1296 | CPCB |
| `STN_113` | Central University, Hyderabad - TSPCB | CPCB | 1114 | CPCB |
| `STN_152` | Ballygunge, Kolkata - WBPCB | CPCB | 1360 | CPCB |
| `STN_185` | Bandra Kurla Complex, Mumbai - MPCB | CPCB | 1416 | CPCB |
| `STN_283` | SPARTAN - IIT Kanpur | CPCB | 2 | CPCB |