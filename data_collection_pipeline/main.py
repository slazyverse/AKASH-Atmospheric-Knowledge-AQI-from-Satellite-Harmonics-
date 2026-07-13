import logging
import pandas as pd
from pathlib import Path
import datetime
from data_collection_pipeline import config, utils, setup, cpcb_collector, openaq_collector, era5_downloader

logger = logging.getLogger("data_collection_pipeline.main")

def build_station_metadata(df_cpcb: pd.DataFrame, df_openaq: pd.DataFrame) -> pd.DataFrame:
    """
    Consolidates and enriches station metadata from both CPCB and OpenAQ.
    Resolves coordinates for CPCB stations using city lookups and matches them
    with OpenAQ coordinates where possible.
    Assigns sequential unique Station IDs.
    """
    logger.info("Building consolidated station metadata...")
    stations_dict = {}

    # Process CPCB stations
    if df_cpcb is not None and not df_cpcb.empty:
        for _, row in df_cpcb.iterrows():
            station_name = row["station"]
            city = row["city"]
            state = row["state"]
            country = row["country"]
            
            # Retrieve approximate coordinates from lookup table
            lat, lon = utils.get_coordinates_for_city(city)
            
            stations_dict[station_name] = {
                "Station Name": station_name,
                "City": city,
                "State": state,
                "Latitude": lat,
                "Longitude": lon,
                "Source": "CPCB",
                "Last Updated": row["last_update"]
            }

    # Process OpenAQ stations
    if df_openaq is not None and not df_openaq.empty:
        for _, row in df_openaq.iterrows():
            station_name = row["location"]
            city = row["city"]
            lat = row["latitude"]
            lon = row["longitude"]
            utc_time = row["utc_time"]
            
            # If the station is already in CPCB, merge the records
            if station_name in stations_dict:
                stations_dict[station_name]["Source"] = "CPCB, OpenAQ"
                # OpenAQ has native lat/lon, prefer them over city lookup
                if pd.notna(lat) and pd.notna(lon):
                    stations_dict[station_name]["Latitude"] = lat
                    stations_dict[station_name]["Longitude"] = lon
            else:
                stations_dict[station_name] = {
                    "Station Name": station_name,
                    "City": city,
                    "State": "",  # OpenAQ usually doesn't provide state information
                    "Latitude": lat,
                    "Longitude": lon,
                    "Source": "OpenAQ",
                    "Last Updated": utc_time
                }

    # Convert to DataFrame and assign unique IDs in a sorted, deterministic order
    if not stations_dict:
        logger.warning("No station metadata could be compiled.")
        return pd.DataFrame(columns=[
            "Station ID", "Station Name", "City", "State", "Latitude", "Longitude", "Source", "Last Updated"
        ])

    sorted_station_names = sorted(list(stations_dict.keys()))
    df_rows = []
    
    for index, name in enumerate(sorted_station_names):
        stn_id = f"STN_{index + 1:03d}"
        s_data = stations_dict[name]
        df_rows.append({
            "Station ID": stn_id,
            "Station Name": s_data["Station Name"],
            "City": s_data["City"],
            "State": s_data["State"],
            "Latitude": s_data["Latitude"],
            "Longitude": s_data["Longitude"],
            "Source": s_data["Source"],
            "Last Updated": s_data["Last Updated"]
        })

    return pd.DataFrame(df_rows)

def run_collection_pipeline(dry_run: bool = True) -> bool:
    """
    Orchestrates the data collection:
    1. Initialize the workspace folders (setup.py)
    2. Collect CPCB Air Quality data & update manifest
    3. Collect OpenAQ Air Quality data & update manifest
    4. Prepare ERA5 meteorological download specs & update manifest
    5. Compile and save station metadata
    """
    logger.info("=========================================")
    logger.info("Starting Data Collection Pipeline run")
    logger.info("=========================================")
    
    # 1. Ensure workspace directories are set up
    try:
        setup.init_workspace()
    except OSError as e:
        logger.error(f"Workspace directory setup failed: {e}")
        return False
        
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 2. CPCB Collection
    cpcb_status = "FAILED"
    cpcb_rows = 0
    try:
        cpcb_window = getattr(config, "CPCB_WINDOW_DAYS", 1)
        df_cpcb = cpcb_collector.collect_cpcb_data(window_days=cpcb_window)
        if df_cpcb is not None and not df_cpcb.empty:
            cpcb_rows = len(df_cpcb)
            cpcb_file = config.RAW_DATA_DIR / f"cpcb_raw_{timestamp}.csv"
            df_cpcb.to_csv(cpcb_file, index=False)
            logger.info(f"Saved raw CPCB data to {cpcb_file}")
            
            # Determine if we used live API or mock fallback
            if config.DATA_GOV_API_KEY:
                cpcb_status = "SUCCESS"
            else:
                cpcb_status = "FALLBACK_MOCK"
        else:
            logger.warning("Collected CPCB data was empty.")
            df_cpcb = pd.DataFrame()
    except (IOError, OSError) as e:
        logger.error(f"CPCB Ingest write error: {e}")
        df_cpcb = pd.DataFrame()
    except Exception as e:
        logger.error(f"Unexpected CPCB Ingest failure: {e}")
        df_cpcb = pd.DataFrame()

    utils.append_to_source_manifest(
        dataset="CPCB Real-time Air Quality",
        url=config.CPCB_BASE_URL,
        rows=cpcb_rows,
        status=cpcb_status
    )

    # 3. OpenAQ Collection
    openaq_status = "FAILED"
    openaq_rows = 0
    try:
        df_openaq = openaq_collector.collect_openaq_data()
        if df_openaq is not None and not df_openaq.empty:
            openaq_rows = len(df_openaq)
            openaq_file = config.RAW_DATA_DIR / f"openaq_raw_{timestamp}.csv"
            df_openaq.to_csv(openaq_file, index=False)
            logger.info(f"Saved raw OpenAQ data to {openaq_file}")
            
            if config.OPENAQ_API_KEY:
                openaq_status = "SUCCESS"
            else:
                openaq_status = "FALLBACK_MOCK"
        else:
            logger.warning("Collected OpenAQ data was empty.")
            df_openaq = pd.DataFrame()
    except (IOError, OSError) as e:
        logger.error(f"OpenAQ Ingest write error: {e}")
        df_openaq = pd.DataFrame()
    except Exception as e:
        logger.error(f"Unexpected OpenAQ Ingest failure: {e}")
        df_openaq = pd.DataFrame()

    utils.append_to_source_manifest(
        dataset="OpenAQ India Air Quality",
        url=config.OPENAQ_BASE_URL,
        rows=openaq_rows,
        status=openaq_status
    )

    # 4. ERA5 Preparation
    era5_status = "FAILED"
    try:
        era5_success = era5_downloader.prepare_era5_download(dry_run=dry_run)
        if era5_success:
            era5_status = "DRY_RUN" if dry_run else "SUCCESS"
            logger.info("ERA5 preparation completed successfully.")
        else:
            logger.warning("ERA5 preparation encountered warnings/errors.")
    except (IOError, OSError) as e:
        logger.error(f"ERA5 Ingest write error: {e}")
    except Exception as e:
        logger.error(f"Unexpected ERA5 Ingest failure: {e}")

    utils.append_to_source_manifest(
        dataset="ERA5 Meteorological Reanalysis",
        url="https://cds.climate.copernicus.eu/api/v2",
        rows=0 if dry_run or era5_status == "FAILED" else 1,
        status=era5_status
    )

    # 5. Compile Station Metadata
    try:
        df_metadata = build_station_metadata(df_cpcb, df_openaq)
        meta_file = config.METADATA_DIR / "station_metadata.csv"
        df_metadata.to_csv(meta_file, index=False)
        logger.info(f"Station metadata built and saved to {meta_file} ({len(df_metadata)} stations)")
    except (IOError, OSError) as e:
        logger.error(f"Error saving station metadata: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error building station metadata: {e}")
        return False

    logger.info("=========================================")
    logger.info("Data Collection Pipeline run completed!")
    logger.info("=========================================")
    return True

if __name__ == "__main__":
    utils.setup_logging()
    run_collection_pipeline(dry_run=True)
