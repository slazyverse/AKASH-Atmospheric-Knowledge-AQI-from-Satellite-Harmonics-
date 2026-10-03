"""
Process-wide holder for the loaded data sources.

Populated once at startup by load_configured_sources() (see app.main lifespan).
Services read `sources.<name>`; None means "not configured → demo data".
Tests set the attributes directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.data.dataset import StationDataset, load_dataset
from app.data.hotspots import HotspotRecord, load_hotspots
from app.data.model_artifact import ModelArtifact, load_model_artifact

if TYPE_CHECKING:
    from app.core.config import Settings


@dataclass
class DataSources:
    dataset: StationDataset | None = None
    hotspots: list[HotspotRecord] | None = None
    model: ModelArtifact | None = None

    def describe(self) -> dict[str, str]:
        """Which source backs each domain — reported by GET /version for the dashboard."""
        return {
            "stations": f"dataset:{self.dataset.source_name}" if self.dataset else "demo",
            "aqi": f"dataset:{self.dataset.source_name}" if self.dataset else "demo",
            "hcho": "hotspot_file" if self.hotspots is not None else "demo",
            "fire": "demo",
            "forecast": "simulated",
            "model": f"artifact:{self.model.directory_name}" if self.model else "none",
        }

    def reset(self) -> None:
        self.dataset = None
        self.hotspots = None
        self.model = None


sources = DataSources()


def load_configured_sources(settings: Settings) -> None:
    """
    Load every configured source. A configured-but-invalid source raises
    (DatasetError / HotspotFileError / ModelArtifactError) so the API fails at
    startup instead of silently serving demo data.
    """
    sources.reset()
    if settings.DATASET_PATH:
        sources.dataset = load_dataset(settings.DATASET_PATH)
    if settings.HCHO_HOTSPOTS_PATH:
        sources.hotspots = load_hotspots(settings.HCHO_HOTSPOTS_PATH)
    if settings.ENABLE_ML_ENDPOINTS and settings.ML_MODEL_PATH:
        sources.model = load_model_artifact(settings.ML_MODEL_PATH)
