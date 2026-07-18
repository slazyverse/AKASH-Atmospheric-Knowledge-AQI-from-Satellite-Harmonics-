import pandas as pd
from typing import List, Optional
from historical_ingestor.cpcb.schema import CommonObservationSchema
import pyarrow as pa
import pyarrow.parquet as pq
import os

def merge_datasets(cpcb_obs: List[CommonObservationSchema], openaq_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Merges CPCB observations with OpenAQ observations applying Source Priority Policy (CPCB > OpenAQ).
    """
    # Convert CPCB observations to DataFrame
    cpcb_dicts = [vars(obs) for obs in cpcb_obs]
    cpcb_df = pd.DataFrame(cpcb_dicts)
    
    if openaq_df is None or openaq_df.empty:
        return cpcb_df
        
    # Ensure schemas align
    common_cols = ['location_id', 'timestamp_utc', 'pollutant']
    
    # Concatenate both, OpenAQ is lower priority so we put it first, CPCB second
    # Then drop duplicates keeping the 'last' which is CPCB.
    merged_df = pd.concat([openaq_df, cpcb_df], ignore_index=True)
    
    merged_df.drop_duplicates(subset=common_cols, keep='last', inplace=True)
    
    return merged_df

def export_to_parquet(df: pd.DataFrame, output_dir: str):
    """
    Exports the merged dataset to Parquet format, partitioned by year and month.
    """
    if df.empty:
        return
        
    os.makedirs(output_dir, exist_ok=True)
    
    # Ensure timestamp_utc is datetime
    df['timestamp_utc'] = pd.to_datetime(df['timestamp_utc'])
    
    # Create partition columns
    df['year'] = df['timestamp_utc'].dt.year
    df['month'] = df['timestamp_utc'].dt.month
    
    table = pa.Table.from_pandas(df)
    
    # Write partitioned dataset
    pq.write_to_dataset(
        table,
        root_path=output_dir,
        partition_cols=['year', 'month', 'location_id'],
        compression='snappy'
    )
