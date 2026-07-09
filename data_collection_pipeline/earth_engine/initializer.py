"""
Earth Engine Initialization Module.

Handles GEE authentication and initialization, supporting both interactive
user credentials and non-interactive service accounts.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global flag to track if Earth Engine was successfully initialized
_EE_INITIALIZED = False


def is_ee_initialized() -> bool:
    """Returns True if Earth Engine has been successfully initialized in this process."""
    return _EE_INITIALIZED


def initialize_ee(
    sa_key_path: Optional[str] = None,
    project: Optional[str] = None
) -> bool:
    """
    Initializes Google Earth Engine Python API.
    
    Tries to authenticate using the provided service account key or falls back
    to standard user credentials stored locally.
    
    Args:
        sa_key_path: Path to the service account private key JSON file (optional).
        project: Google Cloud Project ID to bill for Earth Engine requests (optional).
        
    Returns:
        True if initialization succeeded, False otherwise.
    """
    global _EE_INITIALIZED
    
    try:
        import ee
    except ImportError:
        logger.error(
            "Earth Engine Python API ('earthengine-api') is not installed. "
            "Please run 'pip install earthengine-api' to use this module."
        )
        return False
        
    if _EE_INITIALIZED:
        logger.debug("Earth Engine already initialized.")
        return True
        
    try:
        if sa_key_path:
            logger.info(f"Attempting GEE initialization via service account key: {sa_key_path}")
            # Try to initialize using service account credentials if supported by GEE version
            try:
                # Modern ee version service account auth
                ee.Initialize(
                    credentials=ee.ServiceAccountCredentials(None, sa_key_path),
                    project=project
                )
                logger.info("Earth Engine initialized successfully using Service Account.")
                _EE_INITIALIZED = True
                return True
            except Exception as e:
                logger.warning(f"Failed service account credentials setup: {e}. Falling back to default Initialize.")
                
        # Fallback/Default Initialize
        logger.info("Attempting standard GEE initialization using local user credentials...")
        if project:
            ee.Initialize(project=project)
        else:
            ee.Initialize()
            
        logger.info("Earth Engine initialized successfully.")
        _EE_INITIALIZED = True
        return True
        
    except Exception as e:
        logger.error(
            f"Failed to initialize Earth Engine: {e}. "
            "Ensure you have run 'earthengine authenticate' in your shell or "
            "configured the correct credentials / billing project ID."
        )
        _EE_INITIALIZED = False
        return False
