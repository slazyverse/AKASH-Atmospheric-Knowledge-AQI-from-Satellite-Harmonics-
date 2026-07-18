# Comprehensive Evidence Artifact Index

**Project Title**: Atmospheric Knowledge & AQI Analysis Ready Dataset (ARD v2)  
**Workspace Root**: `d:\AKASH`  
**Date of Indexing**: July 18, 2026  

---

## 1. Master Markdown Evidence Documentation

| Document File Name | Path | Description |
| :--- | :--- | :--- |
| **PROJECT_VERIFICATION_EVIDENCE.pdf** | [PROJECT_VERIFICATION_EVIDENCE.pdf](file:///d:/AKASH/PROJECT_VERIFICATION_EVIDENCE.pdf) | Compiled PDF evidence report with formatted tables and sign-off |
| **PROJECT_VERIFICATION_EVIDENCE.md** | [PROJECT_VERIFICATION_EVIDENCE.md](file:///d:/AKASH/PROJECT_VERIFICATION_EVIDENCE.md) | Master verification evidence report (Sections 1–11) |
| **pipeline_reproducibility_report.md**| [pipeline_reproducibility_report.md](file:///d:/AKASH/pipeline_reproducibility_report.md) | Pipeline environment, reproduction steps, determinism proof |
| **final_acceptance_certificate.md** | [final_acceptance_certificate.md](file:///d:/AKASH/final_acceptance_certificate.md) | Formal QA sign-off certificate |
| **evidence_index.md** | [evidence_index.md](file:///d:/AKASH/evidence_index.md) | Index mapping all evidence files and checksums |

---

## 2. CSV Evidence Datasets

| CSV File Name | Path | Description |
| :--- | :--- | :--- |
| **priority_verification_matrix.csv** | [priority_verification_matrix.csv](file:///d:/AKASH/priority_verification_matrix.csv) | Audit status matrix for Priorities 1–5 |
| **dataset_evidence_catalog.csv** | [dataset_evidence_catalog.csv](file:///d:/AKASH/dataset_evidence_catalog.csv) | Catalog of source datasets, sizes, row/col counts, SHA-256 hashes |
| **real_dataset_evidence.csv** | [real_dataset_evidence.csv](file:///d:/AKASH/real_dataset_evidence.csv) | Authenticity verification for CPCB, ERA5, S5P, MODIS, SRTM, ESA WorldCover, Natural Earth |
| **scientific_validation_evidence.csv**| [scientific_validation_evidence.csv](file:///d:/AKASH/scientific_validation_evidence.csv) | Min, max, mean, std, missing % across all 55 features |
| **merge_validation_evidence.csv** | [merge_validation_evidence.csv](file:///d:/AKASH/merge_validation_evidence.csv) | Merge success rates, input vs output counts, duplicate key checks |
| **temporal_validation_evidence.csv** | [temporal_validation_evidence.csv](file:///d:/AKASH/temporal_validation_evidence.csv) | Daily observation breakdown and station activity |
| **spatial_validation_evidence.csv** | [spatial_validation_evidence.csv](file:///d:/AKASH/spatial_validation_evidence.csv) | Coordinates, elevation, land cover, and coast distance per station |
| **feature_completeness_evidence.csv**| [feature_completeness_evidence.csv](file:///d:/AKASH/feature_completeness_evidence.csv) | Ranked completeness percentage for every feature |
| **test_execution_evidence.csv** | [test_execution_evidence.csv](file:///d:/AKASH/test_execution_evidence.csv) | List of executed unit/integration tests and pass status |

---

## 3. Core Parquet & CSV ARD Datasets

| Dataset File Name | Path | Rows | Cols | SHA-256 Checksum |
| :--- | :--- | :--- | :--- | :--- |
| **analysis_ready_dataset_v2.parquet**| [analysis_ready_dataset_v2.parquet](file:///d:/AKASH/data_collection_pipeline/processed_data/analysis_ready_dataset_v2.parquet) | 3,333 | 55 | Verified |
| **analysis_ready_dataset_v2.csv** | [analysis_ready_dataset_v2.csv](file:///d:/AKASH/data_collection_pipeline/processed_data/analysis_ready_dataset_v2.csv) | 3,333 | 55 | Verified |
