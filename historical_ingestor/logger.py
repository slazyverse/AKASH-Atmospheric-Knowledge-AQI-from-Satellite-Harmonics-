import logging
import os
from historical_ingestor.config import LOG_DIRECTORY

def get_logger(name="openaq_downloader"):
    """Set up and return a logger that writes to a file and console."""
    os.makedirs(LOG_DIRECTORY, exist_ok=True)
    
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # File handler
        log_file = os.path.join(LOG_DIRECTORY, "download.log")
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
    return logger

logger = get_logger()
