import logging
import json
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
from sklearn.cluster import DBSCAN
from typing import Dict, List, Tuple, Any, Optional
from data_collection_pipeline.config_loader import config_instance
from data_collection_pipeline.spatial_analysis import color_scheme, india_grid_generator

logger = logging.getLogger(__name__)

def run_hotspot_pipeline(
    df: pd.DataFrame,
    output_dir: Path,
    percentile: Optional[float] = None,
    eps: Optional[float] = None,
    min_samples: Optional[int] = None
) -> dict:
    """
    Runs the complete HCHO Hotspot Detection and Clustering Pipeline.
    Saves the cluster details JSON and renders a hotspot visualization map.
    """
    logger.info("Initializing HCHO Hotspot Detection Pipeline...")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Load config parameters
    db_cfg = config_instance.get("dbscan")
    if percentile is None:
        percentile = db_cfg.get("percentile", 0.90)
    if eps is None:
        eps = db_cfg.get("eps", 2.5)
    if min_samples is None:
        min_samples = db_cfg.get("min_samples", 3)
        
    # 2. Filter hotspot stations
    hcho_thresh = df["HCHO"].quantile(percentile)
    hotspots_df = df[df["HCHO"] >= hcho_thresh].copy()
    logger.info(f"Hotspot threshold ({percentile*100}th pct): {hcho_thresh:.6f}. Selected {len(hotspots_df)} stations.")
    
    if len(hotspots_df) == 0:
        logger.warning("No hotspot stations detected. Exiting hotspot pipeline.")
        return {}
        
    # 3. DBSCAN spatial clustering on station coordinates
    db = DBSCAN(eps=eps, min_samples=min_samples)
    clusters = db.fit_predict(hotspots_df[["Longitude", "Latitude"]])
    hotspots_df["Cluster_ID"] = clusters
    
    # 4. Generate statistics for each cluster
    unique_clusters = set(clusters)
    cluster_details = []
    
    for cid in unique_clusters:
        if cid == -1:
            # Noise points
            continue
        cluster_points = hotspots_df[hotspots_df["Cluster_ID"] == cid]
        detail = {
            "cluster_id": int(cid),
            "station_count": int(len(cluster_points)),
            "mean_latitude": float(cluster_points["Latitude"].mean()),
            "mean_longitude": float(cluster_points["Longitude"].mean()),
            "mean_hcho": float(cluster_points["HCHO"].mean()),
            "mean_co_column": float(cluster_points["CO Column"].mean()) if "CO Column" in cluster_points.columns else 0.0,
            "stations": list(cluster_points["Station Name"].values)
        }
        cluster_details.append(detail)
        
    # Save hotspot summary JSON
    summary_path = output_dir / "cluster_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(cluster_details, f, indent=4)
    logger.info(f"Saved cluster summary JSON to {summary_path}")
    
    # 5. Render Hotspot Map Visualization
    logger.info("Rendering HCHO hotspot visualization map...")
    grid_x, grid_y = india_grid_generator.generate_grid(resolution=300)
    grid_z_hcho = griddata(
        (df["Longitude"].values, df["Latitude"].values),
        df["HCHO"].values,
        (grid_x, grid_y),
        method="linear"
    )
    
    plt.figure(figsize=(10, 8))
    
    # Draw background HCHO density
    hcho_cmap = color_scheme.get_hcho_colormap()
    im_hcho = plt.imshow(
        grid_z_hcho.T,
        extent=(68, 98, 8, 38),
        origin="lower",
        cmap=hcho_cmap,
        alpha=0.7
    )
    plt.colorbar(im_hcho, label="HCHO Column Density (mol/m²)")
    
    # Draw cluster overlay
    colors = plt.cm.rainbow(np.linspace(0, 1, len(unique_clusters)))
    for i, cid in enumerate(unique_clusters):
        if cid == -1:
            # Noise points as small black crosses
            c_points = hotspots_df[hotspots_df["Cluster_ID"] == cid]
            plt.scatter(
                c_points["Longitude"], 
                c_points["Latitude"], 
                c="black", 
                marker="x", 
                s=25, 
                label="Isolated / Noise Hotspots"
            )
            continue
        c_points = hotspots_df[hotspots_df["Cluster_ID"] == cid]
        plt.scatter(
            c_points["Longitude"],
            c_points["Latitude"],
            color=colors[i],
            edgecolors="k",
            s=80,
            label=f"Cluster {cid} (N={len(c_points)})"
        )
        
    plt.xlabel("Longitude (°E)")
    plt.ylabel("Latitude (°N)")
    plt.title(f"HCHO Hotspot Spatial Clusters over India (DBSCAN Clustering, eps={eps})")
    plt.legend(loc="upper right")
    plt.tight_layout()
    
    map_path = output_dir / "hcho_hotspots.png"
    plt.savefig(map_path, dpi=150)
    plt.close()
    logger.info(f"Saved hotspot map image to {map_path}")
    
    return {
        "cluster_summary_json": str(summary_path),
        "hcho_hotspots_png": str(map_path),
        "total_hotspots_count": len(hotspots_df),
        "clusters_detected": len([c for c in unique_clusters if c != -1])
    }
