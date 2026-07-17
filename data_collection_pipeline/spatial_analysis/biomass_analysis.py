import logging
import json
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import pearsonr, spearmanr
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

def run_biomass_analysis(
    df: pd.DataFrame,
    output_dir: Path,
    hcho_col: str = "HCHO",
    co_col: str = "CO Column"
) -> dict:
    """
    Performs biomass burning correlation and regression analysis between HCHO and CO.
    Generates scatter/regression plots and exports a summary report JSON.
    """
    logger.info("Initializing Biomass Burning Correlation Analysis...")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if hcho_col not in df.columns or co_col not in df.columns:
        raise ValueError(f"Required columns {hcho_col} or {co_col} not found in input DataFrame.")
        
    # Drop rows with NaNs in either variable
    clean_df = df[[hcho_col, co_col]].dropna().copy()
    x = clean_df[co_col].values
    y = clean_df[hcho_col].values
    
    if len(x) < 2:
        raise ValueError("Insufficient data points (less than 2) for correlation analysis.")
        
    # 1. Compute correlation coefficients
    p_corr, p_val = pearsonr(x, y)
    s_corr, s_val = spearmanr(x, y)
    logger.info(f"Pearson Correlation: {p_corr:.4f} (p={p_val:.2e})")
    logger.info(f"Spearman Correlation: {s_corr:.4f} (p={s_val:.2e})")
    
    # 2. Fit a linear regression trendline
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    
    # R2 of linear fit
    y_mean = np.mean(y)
    ss_tot = np.sum((y - y_mean) ** 2)
    ss_res = np.sum((y - y_pred) ** 2)
    r2_fit = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    
    # 3. Save correlation plot
    plt.figure(figsize=(8, 6))
    plt.scatter(x, y, alpha=0.6, color="purple", edgecolors="k", label="Station Observations")
    # Draw trendline
    plt.plot(x, y_pred, color="red", lw=2, linestyle="--", label=f"Fit (R²={r2_fit:.3f})")
    
    plt.xlabel("CO Column Density (mol/m²)")
    plt.ylabel("HCHO Column Density (mol/m²)")
    plt.title("Correlation Analysis: HCHO vs. CO Column (Biomass Burning Tracer)")
    plt.legend()
    plt.tight_layout()
    
    plot_path = output_dir / "correlation_plot.png"
    plt.savefig(plot_path, dpi=150)
    plt.close()
    logger.info(f"Saved biomass burning correlation plot to {plot_path}")
    
    # 4. Generate JSON report
    report = {
        "pearson_correlation": float(p_corr),
        "pearson_p_value": float(p_val),
        "spearman_correlation": float(s_corr),
        "spearman_p_value": float(s_val),
        "regression_fit": {
            "slope": float(slope),
            "intercept": float(intercept),
            "r2": float(r2_fit)
        },
        "statistics": {
            "samples_count": len(clean_df),
            "hcho_mean": float(np.mean(y)),
            "hcho_std": float(np.std(y)),
            "co_mean": float(np.mean(x)),
            "co_std": float(np.std(x))
        }
    }
    
    report_path = output_dir / "correlation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
    logger.info(f"Saved biomass burning correlation report JSON to {report_path}")
    
    return {
        "correlation_report_json": str(report_path),
        "correlation_plot_png": str(plot_path),
        "pearson_r": p_corr,
        "regression_r2": r2_fit
    }
