import logging

from dotenv import load_dotenv

from data_collection_pipeline import config

# Configure a basic logger for setup purposes
logger = logging.getLogger("data_collection_pipeline.setup")

def init_workspace() -> None:
    """
    Initializes the workspace directory structure required by the pipeline.
    Ensures all folders exist without side effects on module load.
    """
    # Keep this call for direct setup.py use; config.py also loads dotenv before os.getenv.
    load_dotenv()
    
    directories = [
        config.RAW_DATA_DIR,
        config.PROCESSED_DATA_DIR,
        config.METADATA_DIR,
        config.LOG_DIR,
        config.DOCUMENTATION_DIR
    ]
    
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            # Use print if logging has not yet been fully configured
            logger.info(f"Initialized directory: {directory}")
        except OSError as e:
            print(f"Error creating directory {directory}: {e}")
            raise

if __name__ == "__main__":
    # If run directly, configure simple logging and initialize workspace
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    init_workspace()
    print("Workspace setup completed successfully.")
