"""Unit tests for Hard Error Handling & Dead Letter Queue (ISSUE-#03)."""

import datetime
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import pandas as pd
import numpy as np

from data_collection_pipeline.exceptions import IngestionError
from data_collection_pipeline.dlq import DLQ_DIR, write_dlq, handle_ingestion_failure
from data_collection_pipeline import cpcb_collector, era5_historical, sentinel5p_historical
from data_collection_pipeline.historical_ingestor.era5_collector import HistoricalERA5Collector
from data_collection_pipeline.historical_ingestor.satellite_collector import HistoricalSatelliteCollector
from data_collection_pipeline.historical_ingestor.cpcb_loader import HistoricalCPCBLoader


@pytest.fixture
def tmp_dlq_dir(tmp_path):
    """Fixture providing a clean temporary DLQ directory."""
    dlq_dir = tmp_path / "logs" / "dlq"
    dlq_dir.mkdir(parents=True, exist_ok=True)
    with patch("data_collection_pipeline.dlq.DLQ_DIR", dlq_dir):
        yield dlq_dir


def _validate_dlq_record_schema(data: dict, expected_source: str, expected_op: str):
    """Helper to validate DLQ JSON schema completeness."""
    required_keys = {"timestamp", "source", "operation", "error_type", "message", "exception", "payload"}
    assert required_keys.issubset(data.keys()), f"Missing keys in DLQ JSON: {required_keys - set(data.keys())}"
    assert data["source"] == expected_source
    assert data["operation"] == expected_op
    assert isinstance(data["timestamp"], str)
    assert isinstance(data["message"], str) and len(data["message"]) > 0
    assert isinstance(data["exception"], str)
    assert isinstance(data["payload"], dict)


# ============================================================================
# CPCB Collector Tests
# ============================================================================

def test_cpcb_missing_api_key(tmp_dlq_dir):
    """Missing CPCB API key raises IngestionError and creates DLQ entry with full schema validation."""
    with patch("data_collection_pipeline.config.DATA_GOV_API_KEY", None):
        with pytest.raises(IngestionError) as exc_info:
            cpcb_collector.collect_cpcb_data()

        assert exc_info.value.source == "CPCB"
        assert exc_info.value.operation == "fetch_cpcb_raw"
        assert "DATA_GOV_API_KEY" in exc_info.value.message

        dlq_files = list(tmp_dlq_dir.glob("*.json"))
        assert len(dlq_files) == 1
        data = json.loads(dlq_files[0].read_text())
        _validate_dlq_record_schema(data, expected_source="CPCB", expected_op="fetch_cpcb_raw")
        assert data["error_type"] == "IngestionError"


def test_cpcb_network_failure(tmp_dlq_dir):
    """Network failure during CPCB fetch raises IngestionError with DLQ record validation."""
    with patch("data_collection_pipeline.config.DATA_GOV_API_KEY", "test_key"), \
         patch("data_collection_pipeline.utils.safe_request", side_effect=RuntimeError("Connection refused")):
        with pytest.raises(IngestionError) as exc_info:
            cpcb_collector.collect_cpcb_data()

        assert exc_info.value.source == "CPCB"
        dlq_files = list(tmp_dlq_dir.glob("*.json"))
        assert len(dlq_files) == 1
        data = json.loads(dlq_files[0].read_text())
        _validate_dlq_record_schema(data, expected_source="CPCB", expected_op="fetch_cpcb_raw")
        assert "Connection refused" in data["exception"] or "Network error" in data["message"]


def test_cpcb_malformed_response(tmp_dlq_dir):
    """Malformed API JSON response raises IngestionError and validates DLQ payload."""
    mock_resp = MagicMock()
    mock_resp.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)

    with patch("data_collection_pipeline.config.DATA_GOV_API_KEY", "test_key"), \
         patch("data_collection_pipeline.utils.safe_request", return_value=mock_resp):
        with pytest.raises(IngestionError) as exc_info:
            cpcb_collector.collect_cpcb_data()

        assert exc_info.value.source == "CPCB"
        dlq_files = list(tmp_dlq_dir.glob("*.json"))
        assert len(dlq_files) == 1
        data = json.loads(dlq_files[0].read_text())
        _validate_dlq_record_schema(data, expected_source="CPCB", expected_op="fetch_cpcb_raw")
        assert "JSON" in data["message"]


def test_cpcb_successful_ingestion(tmp_dlq_dir):
    """Successful CPCB ingestion produces valid DataFrame and no DLQ file."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "total": 1,
        "records": [
            {
                "country": "India",
                "state": "Delhi",
                "city": "Delhi",
                "station": "Anand Vihar",
                "last_update": "2026-07-24 12:00:00",
                "pollutant_id": "PM2.5",
                "avg_value": "120"
            }
        ]
    }

    with patch("data_collection_pipeline.config.DATA_GOV_API_KEY", "test_key"), \
         patch("data_collection_pipeline.utils.safe_request", return_value=mock_resp):
        df = cpcb_collector.collect_cpcb_data()

        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        dlq_files = list(tmp_dlq_dir.glob("*.json"))
        assert len(dlq_files) == 0


# ============================================================================
# ERA5 Historical Collector Tests
# ============================================================================

def test_era5_missing_credentials(tmp_dlq_dir, tmp_path):
    """Missing CDS API credentials raises IngestionError and validates DLQ fields."""
    with patch("pathlib.Path.home", return_value=tmp_path), \
         patch.dict("os.environ", {}, clear=True):
        output_nc = tmp_path / "era5_test.nc"
        with pytest.raises(IngestionError) as exc_info:
            era5_historical.download_historical_era5_month(
                year=2024, month=1, output_path=output_nc, variables=["temperature"]
            )

        assert exc_info.value.source == "ERA5"
        assert exc_info.value.operation == "download_historical_month"
        dlq_files = list(tmp_dlq_dir.glob("*.json"))
        assert len(dlq_files) == 1
        data = json.loads(dlq_files[0].read_text())
        _validate_dlq_record_schema(data, expected_source="ERA5", expected_op="download_historical_month")
        assert data["payload"]["year"] == 2024
        assert data["payload"]["month"] == 1


def test_era5_network_failure(tmp_dlq_dir, tmp_path):
    """Failed live download retries and raises IngestionError with DLQ validation."""
    mock_cdsapirc = tmp_path / ".cdsapirc"
    mock_cdsapirc.write_text("url: https://cds.climate.copernicus.eu/api/v2\nkey: 1234:5678\n")

    with patch("pathlib.Path.home", return_value=tmp_path), \
         patch.dict("sys.modules", {"cdsapi": MagicMock()}):
        import cdsapi
        mock_client = MagicMock()
        mock_client.retrieve.side_effect = RuntimeError("CDS API Timeout")
        cdsapi.Client.return_value = mock_client

        output_nc = tmp_path / "era5_test.nc"
        with pytest.raises(IngestionError) as exc_info:
            era5_historical.download_historical_era5_month(
                year=2024, month=1, output_path=output_nc, variables=["temperature"], max_retries=2, backoff_factor=0.01
            )

        assert exc_info.value.source == "ERA5"
        dlq_files = list(tmp_dlq_dir.glob("*.json"))
        assert len(dlq_files) == 1
        data = json.loads(dlq_files[0].read_text())
        _validate_dlq_record_schema(data, expected_source="ERA5", expected_op="download_historical_month")
        assert "CDS API Timeout" in data["exception"] or "failed" in data["message"]


def test_era5_partial_failure_multi_step(tmp_dlq_dir, tmp_path):
    """Multi-step ERA5 collection that fails on month 2 raises IngestionError and creates exactly 1 DLQ entry."""
    collector = HistoricalERA5Collector(
        output_path=tmp_path / "era5_out.csv",
        nc_output_dir=tmp_path / "cache"
    )

    def mock_prepare_download(start_date, end_date, output_filename, dry_run=False):
        if "2024-02" in start_date:
            return False  # Month 2 fails
        # Month 1 succeeds - create dummy NC file
        nc_path = collector.nc_output_dir / output_filename
        nc_path.parent.mkdir(parents=True, exist_ok=True)
        nc_path.write_bytes(b"dummy_nc_content")
        return True

    def mock_process(input_path, output_path):
        Path(output_path).write_text("timestamp,t2m\n2024-01-01 00:00:00,290.0\n")
        return True

    def mock_read_csv(filepath, **kwargs):
        return pd.DataFrame({"timestamp": ["2024-01-01 00:00:00"], "t2m": [290.0]})

    with patch("data_collection_pipeline.era5_downloader.prepare_era5_download", side_effect=mock_prepare_download), \
         patch("data_collection_pipeline.era5_processor.process_era5_netcdf", side_effect=mock_process), \
         patch("pandas.read_csv", side_effect=mock_read_csv):

        with pytest.raises(IngestionError) as exc_info:
            collector.collect(start_date="2024-01-01", end_date="2024-02-28")

        assert exc_info.value.source == "ERA5"
        dlq_files = list(tmp_dlq_dir.glob("*.json"))
        assert len(dlq_files) == 1
        data = json.loads(dlq_files[0].read_text())
        _validate_dlq_record_schema(data, expected_source="ERA5", expected_op="download_historical_month")
        assert data["payload"]["year"] == 2024
        assert data["payload"]["month"] == 2


# ============================================================================
# Sentinel-5P Historical Collector Tests
# ============================================================================

def test_sentinel5p_gee_init_failure(tmp_dlq_dir, tmp_path):
    """GEE init failure raises IngestionError and validates DLQ fields."""
    stations = pd.DataFrame([{"Station ID": "STN_1", "Latitude": 28.6, "Longitude": 77.2}])
    output_path = tmp_path / "sentinel_test.parquet"

    with patch("data_collection_pipeline.sentinel5p_historical.initialize_ee", side_effect=RuntimeError("GEE auth failed")):
        with pytest.raises(IngestionError) as exc_info:
            sentinel5p_historical.fetch_sentinel_month_gee(stations, 2024, 1, output_path)

        assert exc_info.value.source == "Sentinel-5P"
        dlq_files = list(tmp_dlq_dir.glob("*.json"))
        assert len(dlq_files) == 1
        data = json.loads(dlq_files[0].read_text())
        _validate_dlq_record_schema(data, expected_source="Sentinel-5P", expected_op="fetch_sentinel_month_gee")
        assert "GEE auth failed" in data["exception"] or "GEE initialization failed" in data["message"]


def test_sentinel5p_empty_results(tmp_dlq_dir, tmp_path):
    """Empty GEE query result raises IngestionError and validates DLQ content."""
    stations = pd.DataFrame([{"Station ID": "STN_1", "Latitude": 28.6, "Longitude": 77.2}])
    output_path = tmp_path / "sentinel_test.parquet"

    with patch("data_collection_pipeline.sentinel5p_historical.initialize_ee", return_value=True), \
         patch("data_collection_pipeline.sentinel5p_historical.is_ee_initialized", return_value=True), \
         patch.dict("sys.modules", {"ee": MagicMock()}):
        import ee
        mock_col = MagicMock()
        mock_col.flatten.return_value.getInfo.return_value = {"features": []}
        ee.ImageCollection.fromImages.return_value = mock_col

        with pytest.raises(IngestionError) as exc_info:
            sentinel5p_historical.fetch_sentinel_month_gee(stations, 2024, 1, output_path)

        assert exc_info.value.source == "Sentinel-5P"
        dlq_files = list(tmp_dlq_dir.glob("*.json"))
        assert len(dlq_files) == 1
        data = json.loads(dlq_files[0].read_text())
        _validate_dlq_record_schema(data, expected_source="Sentinel-5P", expected_op="fetch_sentinel_month_gee")
        assert "empty results" in data["message"]


# ============================================================================
# Concurrency & DLQ Resilience Tests (Fix 3, Fix 4, Fix 2)
# ============================================================================

def test_concurrent_dlq_writing(tmp_dlq_dir):
    """Multiple collectors writing DLQ at the same millisecond don't collide or overwrite."""
    p1 = write_dlq(
        source="ERA5",
        operation="download",
        error_type="NetworkError",
        message="Simultaneous failure 1",
        exception="ConnTimeout",
        dlq_dir=tmp_dlq_dir,
    )

    p2 = write_dlq(
        source="CPCB",
        operation="fetch",
        error_type="APIKeyMissing",
        message="Simultaneous failure 2",
        exception="KeyError",
        dlq_dir=tmp_dlq_dir,
    )

    assert p1.exists()
    assert p2.exists()
    assert p1 != p2
    dlq_files = list(tmp_dlq_dir.glob("*.json"))
    assert len(dlq_files) == 2


def test_dlq_write_failure_resilience(tmp_dlq_dir):
    """Fix 3: A filesystem error during DLQ write does NOT swallow the original IngestionError."""
    with patch("data_collection_pipeline.dlq.write_dlq", side_effect=PermissionError("Disk write denied")):
        with pytest.raises(IngestionError) as exc_info:
            handle_ingestion_failure(
                source="CPCB",
                operation="fetch_cpcb_raw",
                message="Original network timeout error",
                original_exception=RuntimeError("Original Cause"),
                dlq_dir=tmp_dlq_dir,
            )

        assert exc_info.value.source == "CPCB"
        assert exc_info.value.message == "Original network timeout error"
        assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_dlq_safe_payload_serialization(tmp_dlq_dir):
    """Fix 4: Complex payload with Path, Timestamp, numpy scalars, pd.NA, bytes, set serializes cleanly."""
    payload = {
        "path": Path("/var/data/nc.file"),
        "timestamp": pd.Timestamp("2026-07-24 12:00:00"),
        "datetime": datetime.datetime(2026, 7, 24, 12, 0, 0),
        "np_int": np.int64(42),
        "np_float": np.float64(3.14159),
        "np_array": np.array([1.0, 2.0, 3.0]),
        "bytes_val": b"raw_data_bytes",
        "set_val": {"a", "b"},
        "pd_na": pd.NA,
    }

    dlq_path = write_dlq(
        source="ERA5",
        operation="download_historical_month",
        error_type="TypeError",
        message="Complex payload test",
        exception="TypeError: un-serializable",
        payload=payload,
        dlq_dir=tmp_dlq_dir,
    )

    assert dlq_path.exists()
    data = json.loads(dlq_path.read_text(encoding="utf-8"))
    assert data["payload"]["path"] == "/var/data/nc.file" or data["payload"]["path"] == "\\var\\data\\nc.file"
    assert data["payload"]["np_int"] == 42
    assert data["payload"]["np_array"] == [1.0, 2.0, 3.0]
    assert data["payload"]["bytes_val"] == "raw_data_bytes"
    assert sorted(data["payload"]["set_val"]) == ["a", "b"]
    assert data["payload"]["pd_na"] is None


def test_ingestion_error_exception_chaining():
    """Fix 2: IngestionError raised via handle_ingestion_failure preserves __cause__ chaining."""
    orig_exc = ValueError("Underlying API format error")
    with pytest.raises(IngestionError) as exc_info:
        handle_ingestion_failure(
            source="Sentinel-5P",
            operation="fetch_sentinel_month_gee",
            message="Format parsing failed",
            original_exception=orig_exc,
        )

    assert exc_info.value.__cause__ is orig_exc
    assert exc_info.value.original_exception is orig_exc
