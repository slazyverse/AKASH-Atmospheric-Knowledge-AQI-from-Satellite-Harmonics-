import pandas as pd
from typing import List, Dict, Any, Tuple
from historical_ingestor.cpcb.schema import CommonObservationSchema, StationMetadataSchema
from historical_ingestor.cpcb.cleaner import clean_dataframe, standardize_pollutant_name, standardize_units
from historical_ingestor.cpcb.metadata import extract_metadata, generate_location_id
from historical_ingestor.cpcb.validator import apply_qa_flags

def parse_cpcb_file(filepath: str) -> Tuple[List[CommonObservationSchema], List[StationMetadataSchema]]:
    """
    Parses a single CPCB CSV file, extracts metadata, and melts wide data to the unified observation schema.
    """
    df = pd.read_csv(filepath)
    if df.empty:
        return [], []
        
    df_cleaned = clean_dataframe(df)
    
    # Extract metadata
    metadata_list = extract_metadata(df_cleaned)
    meta_dict = {m.station_name: m.location_id for m in metadata_list}
    
    # Identify value columns (pollutants/met)
    meta_cols = ['station', 'city', 'state', 'country', 'latitude', 'longitude', 'timestamp_local', 'timestamp_utc', 'AQI']
    value_cols = [col for col in df_cleaned.columns if col not in meta_cols]
    
    # Melt the dataframe
    if 'timestamp_utc' not in df_cleaned.columns:
        return [], metadata_list
        
    id_vars = ['station', 'timestamp_local', 'timestamp_utc']
    available_id_vars = [col for col in id_vars if col in df_cleaned.columns]
    
    df_melted = df_cleaned.melt(
        id_vars=available_id_vars,
        value_vars=value_cols,
        var_name='pollutant_raw',
        value_name='value'
    )
    
    # Drop rows where value is NaN to save memory
    df_melted.dropna(subset=['value'], inplace=True)
    
    observations = []
    for _, row in df_melted.iterrows():
        station_name = str(row['station']) if 'station' in row else 'Unknown'
        location_id = meta_dict.get(station_name, "UNKNOWN")
        
        raw_pollutant = row['pollutant_raw']
        std_pollutant = standardize_pollutant_name(raw_pollutant)
        unit = standardize_units(std_pollutant)
        
        obs = CommonObservationSchema(
            location_id=location_id,
            timestamp_utc=row['timestamp_utc'],
            timestamp_local=row.get('timestamp_local', row['timestamp_utc']),
            pollutant=std_pollutant,
            value=float(row['value']),
            unit=unit,
            source_name="CPCB",
            qa_flag="UNKNOWN"
        )
        observations.append(obs)
        
    # Apply QA flags
    observations = apply_qa_flags(observations)
    
    return observations, metadata_list
