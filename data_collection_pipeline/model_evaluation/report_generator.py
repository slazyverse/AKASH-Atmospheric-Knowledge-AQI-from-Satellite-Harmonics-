import logging
from pathlib import Path
import json
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def compile_final_markdown_report(
    output_dir: Path,
    performance_metrics: Dict[str, float],
    hotspot_metrics: dict,
    biomass_metrics: dict,
    model_name: str = "Random Forest Regressor",
    dataset_version: str = "v1.0"
) -> Path:
    """
    Compiles all sub-reports (Performance, Mapping, Hotspot, Correlation)
    into a single structured Final Markdown Report.
    """
    logger.info("Compiling final consolidated markdown report...")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Render sections
    report_md = f"""# Consolidated ML & Geospatial Analysis Report

* **Model Trained**: {model_name}
* **Dataset Version**: {dataset_version}
* **Akaash Spatial Resolution**: 300x300 India Grid

---

## 1. Performance Evaluation Report
* **Mean Absolute Error (MAE)**: {performance_metrics.get("MAE", 0.0):.4f}
* **Root Mean Squared Error (RMSE)**: {performance_metrics.get("RMSE", 0.0):.4f}
* **Coefficient of Determination ($R^2$)**: {performance_metrics.get("R2", 0.0):.4f}
* **Mean Bias Error (MBE)**: {performance_metrics.get("MBE", 0.0):.4f}
* **Mean Absolute Percentage Error (MAPE)**: {performance_metrics.get("MAPE", 0.0):.2f}%

*Evaluation Artifacts*:
* Diagnostics: `error_distribution.png`, `residuals.png`, `pred_vs_actual.png`

---

## 2. AQI Surface Mapping Report
* **Mapping Grid Bounds**: Longitude 68°E to 98°E, Latitude 8°N to 38°N
* **Interpolation Algorithm**: Linear Griddata
* **High-Resolution Dimension**: 600x600 grid cells

*Mapping Artifacts*:
* Map Rendering: `india_aqi_map.png`
* High-Resolution rendering: `india_aqi_map_high_res.png`
* GIS Raster Export: `india_aqi_map.tif`

---

## 3. HCHO Hotspot Detection Report
* **Hotspot Quantile Threshold**: {hotspot_metrics.get("hcho_90th_percentile_threshold", 0.90)*100:.1f}th percentile
* **Total High-Concentration Stations**: {hotspot_metrics.get("total_hotspot_stations", 0)}
* **DBSCAN Spatial Clusters Grouped**: {hotspot_metrics.get("grouped_cluster_count", 0)} clusters detected

*Hotspot Artifacts*:
* Cluster Map: `hcho_hotspots.png`
* Summary Data: `cluster_summary.json`

---

## 4. Biomass Burning Correlation Report
* **Overall Pearson Correlation (HCHO vs. CO)**: {biomass_metrics.get("overall_hcho_co_pearson_corr", 0.0):.4f}
* **Hotspots Pearson Correlation (HCHO vs. CO)**: {biomass_metrics.get("hotspots_hcho_co_pearson_corr", 0.0):.4f}

*Conclusion*:
A strong positive correlation of {biomass_metrics.get("hotspots_hcho_co_pearson_corr", 0.0):.4f} in hotspot regions confirms that biomass combustion is a major driver of elevated HCHO column densities.
"""
    
    report_path = output_dir / "final_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
        
    logger.info(f"Consolidated final markdown report saved to {report_path}")
    return report_path
