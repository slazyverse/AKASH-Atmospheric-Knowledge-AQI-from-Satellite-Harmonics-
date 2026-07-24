"""Historical CPCB and OpenAQ ground observation loader.

Implements raw CPCB parsing, metadata extraction, timestamp normalization,
pollutant standardization, unit normalization, missing-value handling,
duplicate removal, validation QA checks, unified schema conversion,
OpenAQ + CPCB merging, Parquet export, and validation report generation.
"""

from __future__ import annotations

import json
import logging
import re
import time
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import pandas as pd

from data_collection_pipeline import config, openaq_collector
from data_collection_pipeline.dlq import handle_ingestion_failure
from data_collection_pipeline.historical_ingestor import config as hist_config

logger = logging.getLogger("data_collection_pipeline.historical_ingestor.cpcb_loader")

# Pollutant rename mappings
POLLUTANT_MAP = {
    "pm25": "PM2.5",
    "pm2_5": "PM2.5",
    "pm2.5": "PM2.5",
    "pm 2.5": "PM2.5",
    "PM25": "PM2.5",
    "PM2_5": "PM2.5",
    "PM2.5": "PM2.5",
    "pm10": "PM10",
    "PM10": "PM10",
    "no2": "NO2",
    "NO2": "NO2",
    "so2": "SO2",
    "SO2": "SO2",
    "co": "CO",
    "CO": "CO",
    "o3": "O3",
    "O3": "O3",
    "ozone": "O3",
    "OZONE": "O3",
    "aqi": "AQI",
    "AQI": "AQI"
}

# Standard physical bounds
POLLUTANT_BOUNDS = {
    "PM2.5": (0.0, 1000.0),
    "PM10": (0.0, 1500.0),
    "NO2": (0.0, 500.0),
    "SO2": (0.0, 500.0),
    "CO": (0.0, 50.0),
    "O3": (0.0, 500.0),
    "AQI": (0.0, 1000.0)
}

# Standard units
POLLUTANT_UNITS = {
    "PM2.5": "ug/m3",
    "PM10": "ug/m3",
    "NO2": "ug/m3",
    "SO2": "ug/m3",
    "CO": "mg/m3",
    "O3": "ug/m3",
    "AQI": "index"
}


def standardize_station_name(name: str) -> str:
    """Standardizes station name for matching against registry.
    
    Removes suffix monitoring agencies (e.g. - DPCC) and special characters.
    """
    if not isinstance(name, str):
        return ""
    # Strip suffix agencies
    cleaned = re.sub(
        r'\s*-\s*(DPCC|MPCB|CPCB|TSPCB|WBPCB|GPCB|IITM|SAFAR|TNPCB|KSPCB|SPCB|UPPCB|BSPCB|CECB|IMC)\b',
        '',
        name,
        flags=re.IGNORECASE
    )
    # Remove all non-alphanumeric chars and lowercase
    return re.sub(r'[^a-zA-Z0-9]', '', cleaned).lower()


class HistoricalCPCBLoader:
    """Ingests and standardizes historical ground station observations."""

    def __init__(
        self,
        csv_folder: Optional[Path] = None,
        use_openaq: bool = True,
    ) -> None:
        self.csv_folder = (
            Path(csv_folder) if csv_folder is not None
            else config.RAW_DATA_DIR / "historical" / "cpcb"
        )
        self.use_openaq = use_openaq
        self.station_registry = self._load_station_registry()

    def _load_station_registry(self) -> Dict[str, Dict[str, Any]]:
        """Load station registry metadata and build standardized lookup mapping."""
        meta_path = config.METADATA_DIR / "station_metadata.csv"
        registry = {}
        if not meta_path.exists():
            logger.warning(f"Station metadata file not found at {meta_path}. Dynamic matching fallback will be used.")
            return registry
            
        try:
            df = pd.read_csv(meta_path)
            for _, row in df.iterrows():
                stn_id = row.get("Station ID")
                stn_name = row.get("Station Name")
                if pd.notna(stn_id) and pd.notna(stn_name):
                    clean_key = standardize_station_name(str(stn_name))
                    registry[clean_key] = row.to_dict()
            logger.info(f"Loaded {len(registry)} station mappings from registry.")
        except Exception as e:
            logger.error(f"Error loading station metadata registry: {e}")
        return registry

    def _find_station_id(self, raw_name: str) -> Tuple[str, Dict[str, Any]]:
        """Match raw station name to registry Station ID and metadata."""
        clean_raw = standardize_station_name(raw_name)
        if clean_raw in self.station_registry:
            meta = self.station_registry[clean_raw]
            return str(meta["Station ID"]), meta
            
        # Try substring matching
        for key, meta in self.station_registry.items():
            if clean_raw in key or key in clean_raw:
                return str(meta["Station ID"]), meta
                
        # Fallback mapping for the 10 core stations if metadata lacks exact string
        core_fallbacks = {
            "anandvihar": ("STN_012", "Delhi"),
            "rkpuram": ("STN_342", "Delhi"),
            "worli": ("STN_504", "Mumbai"),
            "btmlayout": ("STN_024", "Bengaluru"),
            "manali": ("STN_249", "Chennai"),
            "zoopark": ("STN_508", "Hyderabad"),
            "rabindrabharati": ("STN_346", "Kolkata"),
            "maninagar": ("STN_253", "Ahmedabad"),
            "shivajinagar": ("STN_372", "Pune"),
            "lalbagh": ("STN_222", "Lucknow")
        }
        
        for fallback_key, (stn_id, city) in core_fallbacks.items():
            if fallback_key in clean_raw:
                # Retrieve from registry by ID directly if possible
                for meta in self.station_registry.values():
                    if meta.get("Station ID") == stn_id:
                        return stn_id, meta
                # Default meta details if ID not in registry yet
                return stn_id, {
                    "Station ID": stn_id,
                    "Station Name": raw_name,
                    "City": city,
                    "State": "",
                    "Country": "IN",
                    "Latitude": 20.5937,
                    "Longitude": 78.9629
                }
                
        # Final fallback - assign dynamic ID
        h = hash(clean_raw) % 1000
        fallback_id = f"STN_FLB{h:03d}"
        return fallback_id, {
            "Station ID": fallback_id,
            "Station Name": raw_name,
            "City": "Unknown",
            "State": "",
            "Country": "IN",
            "Latitude": 20.5937,
            "Longitude": 78.9629
        }

    def load(
        self,
        start_date: str,
        end_date: str,
        output_path: Optional[Path] = None,
    ) -> pd.DataFrame:
        """Runs the Ground data ingestion, standardizing CPCB + OpenAQ observations.
        
        Validates observations, exports to Parquet, writes wide-format compatibility file,
        and generates a data validation report.
        """
        output_path = output_path or hist_config.HIST_CPCB_RAW
        start_time = time.perf_counter()
        
        logger.info(f"Ingesting Ground historical observations for period: {start_date} -> {end_date}")
        
        # 1. Parse and Standardize CPCB CSV Files
        cpcb_raw_df = self.load_from_csv_folder(self.csv_folder, start_date, end_date)
        
        cpcb_obs = pd.DataFrame()
        if cpcb_raw_df is not None and not cpcb_raw_df.empty:
            logger.info(f"CPCB raw CSV files loaded: {len(cpcb_raw_df)} rows. Processing...")
            cpcb_obs = self._process_and_standardize(cpcb_raw_df, source_name="CPCB")
            logger.info(f"CPCB standardized observations count: {len(cpcb_obs)}")
        else:
            logger.warning("No CPCB raw data found in drop-folder.")

        # 2. Ingest and Standardize OpenAQ Historical Data
        openaq_obs = pd.DataFrame()
        if self.use_openaq:
            openaq_raw_df = self.load_from_openaq(start_date, end_date)
            if openaq_raw_df is not None and not openaq_raw_df.empty:
                # OpenAQ API data is returned standardized by the collector, but in wide-format or melted.
                # Standardize it to the long observation schema.
                openaq_obs = self._process_and_standardize(openaq_raw_df, source_name="OpenAQ")
                logger.info(f"OpenAQ standardized observations count: {len(openaq_obs)}")
            else:
                # Try reading local OpenAQ historical station files (if downloaded)
                openaq_local_df = self._load_local_openaq_files(start_date, end_date)
                if openaq_local_df is not None and not openaq_local_df.empty:
                    openaq_obs = self._process_and_standardize(openaq_local_df, source_name="OpenAQ")
                    logger.info(f"OpenAQ local files standardized observations count: {len(openaq_obs)}")
                else:
                    logger.warning("No OpenAQ data fetched or cached locally.")

        # 3. Merger: Combine OpenAQ and CPCB observations
        if cpcb_obs.empty and openaq_obs.empty:
            handle_ingestion_failure(
                source="CPCB",
                operation="load",
                message=f"No ground observations could be loaded or parsed from CPCB or OpenAQ for range {start_date} -> {end_date}.",
                payload={"start_date": start_date, "end_date": end_date},
                logger_instance=logger,
            )
            
        merged_obs = self._merge_and_deduplicate(cpcb_obs, openaq_obs)
        logger.info(f"Merged ground observations: {len(merged_obs)} rows.")

        # 4. Parquet Export (Partitioned by Year, Month, Station ID)
        parquet_dir = config.PROCESSED_DATA_DIR / "historical" / "ground"
        self._export_to_parquet(merged_obs, parquet_dir)
        logger.info(f"Unified ground observations written to Parquet warehouse at {parquet_dir}")

        # 5. Backward Compatibility Wide-Format Export
        wide_df = self._convert_to_wide_format(merged_obs)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        wide_df.to_csv(output_path, index=False)
        logger.info(f"Wide compatibility CPCB raw dataset written to {output_path} ({len(wide_df)} rows).")

        # 6. Generate Validation Report
        elapsed_time = time.perf_counter() - start_time
        self._generate_validation_report(merged_obs, cpcb_obs, openaq_obs, elapsed_time)

        return wide_df

    def load_from_csv_folder(
        self,
        folder: Path,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """Loads all CPCB CSV files from the folder."""
        if not folder.exists():
            logger.warning(f"CPCB historical folder {folder} does not exist.")
            return None
            
        csv_files = sorted(folder.glob("*.csv"))
        if not csv_files:
            logger.warning(f"No CPCB CSV files found in {folder}.")
            return None
            
        logger.info(f"Loading {len(csv_files)} CSV files from CPCB drop-folder...")
        dfs = []
        for path in csv_files:
            try:
                df = pd.read_csv(path, low_memory=False)
                dfs.append(df)
                logger.info(f"  Successfully loaded {path.name} ({len(df)} rows)")
            except Exception as e:
                logger.error(f"  Failed to load {path.name}: {e}")
                
        if not dfs:
            return None
            
        combined = pd.concat(dfs, ignore_index=True)
        return combined

    def load_from_openaq(self, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Fetches OpenAQ observations from the API client."""
        logger.info(f"Requesting OpenAQ observations from API: {start_date} to {end_date}")
        try:
            df = openaq_collector.collect_openaq_data(date_from=start_date, date_to=end_date)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            logger.error(f"OpenAQ API collection failed: {e}")
        return None

    def _load_local_openaq_files(self, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Loads locally cached OpenAQ historical station files."""
        openaq_dir = Path("historical_data/openaq")
        if not openaq_dir.exists():
            return None
            
        # Parse years in date range
        start_year = pd.to_datetime(start_date).year
        end_year = pd.to_datetime(end_date).year
        years = list(range(start_year, end_year + 1))
        
        dfs = []
        for y in years:
            y_dir = openaq_dir / str(y)
            if y_dir.exists():
                for path in y_dir.glob("station_*.csv"):
                    try:
                        df = pd.read_csv(path)
                        # The OpenAQ historical files are long-format:
                        # location_id, station_name, latitude, longitude, city, state, country, parameter, value, unit, date_utc, date_local
                        # Map columns to match what _process_and_standardize expects:
                        df = df.rename(columns={
                            "location_id": "station_id_raw",
                            "station_name": "station",
                            "date_utc": "last_update",
                            "parameter": "pollutant_id_raw"
                        })
                        dfs.append(df)
                    except Exception as e:
                        logger.debug(f"Failed to read local OpenAQ station file {path.name}: {e}")
                        
        if not dfs:
            return None
            
        return pd.concat(dfs, ignore_index=True)

    def _process_and_standardize(self, df: pd.DataFrame, source_name: str) -> pd.DataFrame:
        """Processes, validates, cleans, and standardizes wide or long format ground observations."""
        df_clean = df.copy()
        
        # Standardize columns to lower for flexible mapping
        col_mapping = {str(c).strip().lower(): c for c in df_clean.columns}
        
        # Resolve datetime column
        time_col = None
        for tc in ["last_update", "lastupdate", "timestamp", "date_utc", "utc_time", "datetime", "date"]:
            if tc in col_mapping:
                time_col = col_mapping[tc]
                break
        if not time_col:
            logger.error("No timestamp column could be identified in input dataset.")
            return pd.DataFrame()
            
        # Resolve station column
        stn_col = None
        for sc in ["station", "location", "station_name", "location_id", "station_id_raw"]:
            if sc in col_mapping:
                stn_col = col_mapping[sc]
                break
        if not stn_col:
            logger.error("No station column identified in input dataset.")
            return pd.DataFrame()

        # Rename pollutant columns using standardized naming map
        rename_dict = {}
        for col in df_clean.columns:
            cleaned_col = str(col).strip()
            if cleaned_col in POLLUTANT_MAP:
                rename_dict[col] = POLLUTANT_MAP[cleaned_col]
            elif cleaned_col.lower() in POLLUTANT_MAP:
                rename_dict[col] = POLLUTANT_MAP[cleaned_col.lower()]
                
        df_clean = df_clean.rename(columns=rename_dict)

        # Standardize Datetimes (Timezone Normalization)
        # Parse timestamp strings into local (IST, UTC+5:30) and UTC.
        # In CPCB exports, times are local IST (UTC+5:30). In OpenAQ, they are UTC.
        local_times = []
        utc_times = []
        
        for val in df_clean[time_col]:
            if pd.isna(val) or str(val).strip() == "":
                local_times.append(pd.NaT)
                utc_times.append(pd.NaT)
                continue
                
            try:
                # parse mixed strings
                dt = pd.to_datetime(val, errors="coerce", format="mixed")
                if pd.isna(dt):
                    local_times.append(pd.NaT)
                    utc_times.append(pd.NaT)
                    continue
                    
                # Timezone localization
                if dt.tzinfo is not None:
                    # Timezone aware
                    dt_utc = dt.tz_convert("UTC")
                    dt_local = dt.tz_convert("Asia/Kolkata")
                else:
                    # Timezone naive
                    if source_name == "OpenAQ" or "T" in str(val) or "Z" in str(val):
                        # Assume UTC
                        dt_utc = dt.tz_localize("UTC")
                        dt_local = dt_utc.tz_convert("Asia/Kolkata")
                    else:
                        # Assume IST for CPCB local
                        dt_local = dt.tz_localize("Asia/Kolkata", ambiguous="NaT", nonexistent="NaT")
                        dt_utc = dt_local.tz_convert("UTC")
                        
                local_times.append(dt_local)
                utc_times.append(dt_utc)
            except Exception:
                local_times.append(pd.NaT)
                utc_times.append(pd.NaT)

        df_clean["timestamp_local"] = local_times
        df_clean["timestamp_utc"] = utc_times
        
        # Filter rows with invalid timestamps
        invalid_ts_count = df_clean["timestamp_utc"].isna().sum()
        if invalid_ts_count > 0:
            logger.warning(f"Filtered out {invalid_ts_count} rows with invalid/null timestamps.")
            df_clean = df_clean.dropna(subset=["timestamp_utc"])

        # Determine Format: Wide vs Long
        # Wide format has pollutants as columns (e.g. CPCB raw). Long format has parameter + value columns.
        observations = []
        
        # Standard pollutant list
        pollutants = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "AQI"]
        
        is_long = "pollutant_id_raw" in df_clean.columns or "parameter" in df_clean.columns or "value" in df_clean.columns
        
        if is_long:
            # Melted long format structure (like OpenAQ)
            val_col = "value" if "value" in df_clean.columns else col_mapping.get("value")
            param_col = "parameter" if "parameter" in df_clean.columns else ("pollutant_id_raw" if "pollutant_id_raw" in df_clean.columns else None)
            
            for _, row in df_clean.iterrows():
                raw_stn = row[stn_col]
                stn_id, meta = self._find_station_id(str(raw_stn))
                
                raw_pol = row[param_col]
                pol = POLLUTANT_MAP.get(str(raw_pol).strip(), None)
                if not pol or pol not in pollutants:
                    continue
                    
                val = row[val_col]
                
                # GPS coordinates checks & fallbacks
                lat = row.get("latitude") if pd.notna(row.get("latitude")) else meta.get("Latitude")
                lon = row.get("longitude") if pd.notna(row.get("longitude")) else meta.get("Longitude")
                
                if pd.isna(lat) or pd.isna(lon) or not (8.0 <= lat <= 38.0) or not (68.0 <= lon <= 98.0):
                    # Reject null or out of bounds coordinates
                    continue
                    
                observations.append({
                    "station_id": stn_id,
                    "station_name": meta.get("Station Name"),
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "city": meta.get("City"),
                    "state": meta.get("State"),
                    "country": meta.get("Country", "IN"),
                    "timestamp_utc": row["timestamp_utc"],
                    "timestamp_local": row["timestamp_local"],
                    "pollutant": pol,
                    "value": float(val) if pd.notna(val) else np.nan,
                    "unit": POLLUTANT_UNITS[pol],
                    "source": source_name
                })
        else:
            # Wide format structure (like CPCB)
            for _, row in df_clean.iterrows():
                raw_stn = row[stn_col]
                stn_id, meta = self._find_station_id(str(raw_stn))
                
                lat = row.get("latitude") if pd.notna(row.get("latitude")) else meta.get("Latitude")
                lon = row.get("longitude") if pd.notna(row.get("longitude")) else meta.get("Longitude")
                
                if pd.isna(lat) or pd.isna(lon) or not (8.0 <= lat <= 38.0) or not (68.0 <= lon <= 98.0):
                    continue
                    
                for pol in pollutants:
                    if pol in df_clean.columns:
                        val = row[pol]
                        observations.append({
                            "station_id": stn_id,
                            "station_name": meta.get("Station Name"),
                            "latitude": float(lat),
                            "longitude": float(lon),
                            "city": meta.get("City"),
                            "state": meta.get("State"),
                            "country": meta.get("Country", "IN"),
                            "timestamp_utc": row["timestamp_utc"],
                            "timestamp_local": row["timestamp_local"],
                            "pollutant": pol,
                            "value": float(val) if pd.notna(val) else np.nan,
                            "unit": POLLUTANT_UNITS[pol],
                            "source": source_name
                        })
                        
        if not observations:
            return pd.DataFrame()
            
        obs_df = pd.DataFrame(observations)
        
        # Deduplicate on key variables before running QA checks
        obs_df = obs_df.drop_duplicates(subset=["station_id", "timestamp_utc", "pollutant"], keep="first")
        
        # Run Data Quality and Validation framework checks
        obs_df = self._validate_and_flag_observations(obs_df)
        
        return obs_df

    def _validate_and_flag_observations(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applies physical range checks, stuck value detection, and spike checks."""
        validated = df.copy()
        validated["qa_flag"] = "VALID"
        
        # 1. Range Validation Bounds Check
        for pol, (low, high) in POLLUTANT_BOUNDS.items():
            mask = (validated["pollutant"] == pol) & (
                (validated["value"] < low) | 
                (validated["value"] > high) | 
                validated["value"].isna()
            )
            validated.loc[mask, "value"] = np.nan
            validated.loc[mask, "qa_flag"] = "INVALID"
            
        # 2. Sort by Station, Pollutant, and UTC time to perform sequential QA checks
        validated = validated.sort_values(by=["station_id", "pollutant", "timestamp_utc"])
        
        # 3. Stuck Value Detection (float repeating for > 12 hours)
        # Use pandas grouping and shift checks
        stuck_mask = None
        for shift_idx in range(1, 12):
            val_shift = validated.groupby(["station_id", "pollutant"])["value"].shift(shift_idx)
            if shift_idx == 1:
                stuck_mask = (validated["value"] == val_shift)
            else:
                stuck_mask = stuck_mask & (validated["value"] == val_shift)
                
        # Fill NA from shifts to False
        if stuck_mask is not None:
            stuck_mask = stuck_mask.fillna(False)
            # Mark stuck observations
            validated.loc[stuck_mask & (validated["qa_flag"] == "VALID"), "qa_flag"] = "SUSPECT_STUCK"
        
        # 4. Spike Detection Check (> 500% change in 1 hr where base > 10)
        prev_val = validated.groupby(["station_id", "pollutant"])["value"].shift(1)
        spike_mask = (validated["value"] > 5.0 * prev_val) & (prev_val > 10.0)
        spike_mask = spike_mask.fillna(False)
        validated.loc[spike_mask & (validated["qa_flag"] == "VALID"), "qa_flag"] = "SUSPECT_SPIKE"
        
        return validated

    def _merge_and_deduplicate(self, cpcb: pd.DataFrame, openaq: pd.DataFrame) -> pd.DataFrame:
        """Merges CPCB and OpenAQ observations, prioritizing CPCB on conflicts."""
        if cpcb.empty:
            return openaq
        if openaq.empty:
            return cpcb
            
        # Concatenate both sources
        combined = pd.concat([cpcb, openaq], ignore_index=True)
        
        # Prioritize CPCB: sort such that CPCB comes before OpenAQ
        combined["source_priority"] = combined["source"].map({"CPCB": 0, "OpenAQ": 1}).fillna(2)
        combined = combined.sort_values(by=["station_id", "timestamp_utc", "pollutant", "source_priority"])
        
        # Deduplicate on station_id, timestamp_utc, pollutant and keep first (CPCB)
        before = len(combined)
        combined = combined.drop_duplicates(subset=["station_id", "timestamp_utc", "pollutant"], keep="first")
        combined = combined.drop(columns=["source_priority"])
        
        logger.info(f"Deduplicated combined CPCB + OpenAQ dataset: {before} -> {len(combined)} rows.")
        return combined

    def _export_to_parquet(self, df: pd.DataFrame, output_dir: Path) -> None:
        """Writes the standardized ground-truth observations to partitioned Parquet warehouse."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        df_parquet = df.copy()
        
        # Convert timestamp objects to naive datetime objects for Parquet compatibility
        df_parquet["timestamp_utc"] = pd.to_datetime(df_parquet["timestamp_utc"]).dt.tz_localize(None)
        df_parquet["timestamp_local"] = pd.to_datetime(df_parquet["timestamp_local"]).dt.tz_localize(None)
        
        # Extract year and month partition variables
        df_parquet["year"] = df_parquet["timestamp_utc"].dt.year
        df_parquet["month"] = df_parquet["timestamp_utc"].dt.month
        
        # Write to partitioned directory structure
        df_parquet.to_parquet(
            output_dir,
            partition_cols=["year", "month", "station_id"],
            compression="snappy",
            index=False
        )

    def _convert_to_wide_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """Pivots unified long-format ground observations back to wide format for pipeline compatibility."""
        # We need columns: station, city, country, latitude, longitude, last_update, PM2.5, PM10, NO2, SO2, CO, O3, AQI
        
        # First format timestamps
        df_wide = df.copy()
        # Convert UTC timestamp to naive string or standard format
        df_wide["last_update"] = pd.to_datetime(df_wide["timestamp_local"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # Pivot table
        pivoted = df_wide.pivot_table(
            index=["station_name", "city", "country", "latitude", "longitude", "last_update"],
            columns="pollutant",
            values="value",
            aggfunc="first"
        ).reset_index()
        
        # Rename station column back to 'station'
        pivoted = pivoted.rename(columns={"station_name": "station"})
        
        # Ensure all standard pollutant columns exist
        for pol in ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "AQI"]:
            if pol not in pivoted.columns:
                pivoted[pol] = np.nan
                
        # Re-order columns
        cols = ["station", "city", "country", "latitude", "longitude", "last_update", "PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "AQI"]
        return pivoted[cols]

    def _generate_validation_report(
        self,
        merged: pd.DataFrame,
        cpcb: pd.DataFrame,
        openaq: pd.DataFrame,
        elapsed_seconds: float,
    ) -> None:
        """Generates a comprehensive markdown data validation report."""
        report = []
        report.append("# Ground-Data Ingestion Validation & Audit Report")
        report.append(f"\n*Execution Completed at: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        report.append(f"\n**Total Processing Time**: {elapsed_seconds:.2f} seconds")
        
        report.append("\n## 1. Ground observations Volume Summary")
        report.append("| Data Source | Raw Rows Ingested | Standardized Measurements |")
        report.append("| :--- | :---: | :---: |")
        report.append(f"| CPCB Ingestion | {len(cpcb) if not cpcb.empty else 0} | {len(cpcb[cpcb['source'] == 'CPCB']) if not cpcb.empty else 0} |")
        report.append(f"| OpenAQ Ingestion | {len(openaq) if not openaq.empty else 0} | {len(openaq[openaq['source'] == 'OpenAQ']) if not openaq.empty else 0} |")
        report.append(f"| **Merged Unified Warehouse** | - | **{len(merged)}** |")

        report.append("\n## 2. Ingestion QA Flags Audit")
        report.append("| QA Flag Status | Total Measurements | Percentage | Action Description |")
        report.append("| :--- | :---: | :---: | :--- |")
        
        total_meas = len(merged)
        for flag in ["VALID", "SUSPECT_STUCK", "SUSPECT_SPIKE", "INVALID"]:
            count = len(merged[merged["qa_flag"] == flag])
            pct = (count / total_meas * 100) if total_meas > 0 else 0
            desc = "Kept as-is for training."
            if flag == "INVALID":
                desc = "Value set to NaN (excluded from model)."
            elif "SUSPECT" in flag:
                desc = "Retained but annotated for outlier audits."
            report.append(f"| `{flag}` | {count} | {pct:.2f}% | {desc} |")
            
        report.append("\n## 3. Station Metadata Mapping Registry")
        report.append("| Registry ID | Station Name | Network | Records Contributed | Source Ingested |")
        report.append("| :--- | :--- | :---: | :---: | :---: |")
        
        stn_counts = merged.groupby(["station_id", "station_name", "source"]).size().reset_index(name="count")
        for _, row in stn_counts.iterrows():
            report.append(f"| `{row['station_id']}` | {row['station_name']} | CPCB | {row['count']} | {row['source']} |")

        report_content = "\n".join(report)
        
        # Save to artifacts directory
        art_dir = Path("historical_data")
        art_dir.mkdir(parents=True, exist_ok=True)
        report_path = art_dir / "historical_data_verification_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        logger.info(f"Validation report saved to: {report_path}")
        
        # Save to workspace root
        workspace_report_path = Path("historical_data_verification_report.md")
        with open(workspace_report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        logger.info(f"Validation report saved to workspace root: {workspace_report_path}")
