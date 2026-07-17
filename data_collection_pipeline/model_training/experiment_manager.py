import logging
import json
import datetime
from pathlib import Path
from typing import Dict, Any, Union
from data_collection_pipeline.config_loader import config_instance

logger = logging.getLogger(__name__)

class ExperimentManager:
    """Manages ML experiments, tracking versions, hyperparameters, metrics, and output paths."""
    
    def __init__(self, workspace_root: Union[str, Path]):
        self.workspace_root = Path(workspace_root)
        exp_dir_name = config_instance.get("paths", "experiments_dir")
        self.experiments_base = self.workspace_root / exp_dir_name
        self.experiments_base.mkdir(parents=True, exist_ok=True)
        
    def create_experiment_run(
        self,
        model_name: str,
        dataset_version: str = "v1.0"
    ) -> Tuple[Path, str]:
        """
        Creates a new timestamped directory for an experiment run.
        Returns the output directory Path and the run ID.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"run_{model_name.replace(' ', '_').lower()}_{timestamp}"
        run_dir = self.experiments_base / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized experiment run folder at {run_dir}")
        return run_dir, run_id

    def log_experiment_metadata(
        self,
        run_dir: Path,
        run_id: str,
        model_params: Dict[str, Any],
        metrics: Dict[str, Any],
        dataset_version: str = "v1.0",
        extra_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """Saves a JSON log compiling the metadata of the experiment run."""
        metadata = {
            "run_id": run_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "dataset_version": dataset_version,
            "model_hyperparameters": model_params,
            "evaluation_metrics": metrics,
            "environment_info": {
                "os": os.name,
                "cwd": os.getcwd()
            }
        }
        
        if extra_info:
            metadata.update(extra_info)
            
        meta_path = run_dir / "experiment_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)
            
        logger.info(f"Saved experiment metadata JSON to {meta_path}")

import os
from typing import Tuple, Optional
