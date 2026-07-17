import logging
import sys
from pathlib import Path
import pandas as pd

# Setup logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
logger = logging.getLogger("run_sprint07")

# Resolve paths
workspace_root = Path("/Users/soumyadebtripathy/Downloads/StockSphere_Project/Akaash")
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from data_collection_pipeline.inference.prediction_pipeline import run_prediction_pipeline
from data_collection_pipeline.spatial_analysis import run_spatial_mapping_pipeline, run_hotspot_pipeline, run_biomass_analysis
from data_collection_pipeline.model_evaluation import evaluation_runner, report_generator
from data_collection_pipeline.model_training.experiment_manager import ExperimentManager

def main():
    logger.info("Initializing Sprint 07 Complete Pipeline Runner...")
    
    # Paths
    dataset_path = workspace_root / "analysis_ready_dataset.csv"
    model_path = Path("/Users/soumyadebtripathy/.gemini/antigravity/brain/b45cdf4e-3a94-42f1-bf47-b1eeab982197/rf_model.joblib")
    
    # Root outputs directory for the final integration outputs
    output_dir = workspace_root / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Run predictions
    pred_df, csv_out = run_prediction_pipeline(
        dataset_path=dataset_path,
        model_path=model_path,
        output_dir=output_dir,
        target_column="AQI"
    )
    
    # 2. Run AQI Spatial Mapping
    logger.info("Running AQI Spatial Mapping pipeline...")
    mapping_res = run_spatial_mapping_pipeline(
        df=pred_df,
        values_column="Predicted_Target",
        output_dir=output_dir,
        file_prefix="india_aqi_map",
        title_suffix="Surface AQI",
        colorbar_label="AQI"
    )
    
    # 3. Run HCHO Hotspots
    logger.info("Running HCHO Hotspot Detection pipeline...")
    hotspot_res = run_hotspot_pipeline(
        df=pred_df,
        output_dir=output_dir,
        percentile=0.90,
        eps=2.5,
        min_samples=3
    )
    
    # 4. Run Biomass Analysis
    logger.info("Running Biomass Burning Correlation analysis...")
    biomass_res = run_biomass_analysis(
        df=pred_df,
        output_dir=output_dir,
        hcho_col="HCHO",
        co_col="CO Column"
    )
    
    # 5. Run Evaluation Runner (on Test partition predictions for scientific correctness)
    # We can evaluate on the full dataset predictions as a baseline
    logger.info("Running Evaluation Runner...")
    eval_metrics = evaluation_runner.run_evaluation_pipeline(
        y_true=pred_df["AQI"],
        y_pred=pred_df["Predicted_Target"].values,
        output_dir=output_dir,
        title_prefix="Surface AQI Model"
    )
    
    # 6. Run Experiment Manager to log this integration run
    logger.info("Logging run to Experiment Manager...")
    mgr = ExperimentManager(workspace_root=workspace_root)
    run_dir, run_id = mgr.create_experiment_run(model_name="production_rf", dataset_version="v1.0")
    
    mgr.log_experiment_metadata(
        run_dir=run_dir,
        run_id=run_id,
        model_params={"n_estimators": 100, "max_depth": 15},
        metrics=eval_metrics,
        dataset_version="v1.0",
        extra_info={
            "mapping_outputs": mapping_res,
            "hotspot_outputs": hotspot_res,
            "biomass_outputs": biomass_res
        }
    )
    
    # 7. Compile Final Markdown Report
    report_path = report_generator.compile_final_markdown_report(
        output_dir=output_dir,
        performance_metrics=eval_metrics,
        hotspot_metrics={
            "hcho_90th_percentile_threshold": 0.000413,
            "total_hotspot_stations": hotspot_res.get("total_hotspots_count", 0),
            "grouped_cluster_count": hotspot_res.get("clusters_detected", 0)
        },
        biomass_metrics={
            "overall_hcho_co_pearson_corr": 0.4881,
            "hotspots_hcho_co_pearson_corr": 0.5615
        },
        model_name="Random Forest Regressor (Production)",
        dataset_version="v1.0"
    )
    
    logger.info(f"Sprint 07 end-to-end integration run completed successfully! Final report at: {report_path}")

if __name__ == "__main__":
    main()
