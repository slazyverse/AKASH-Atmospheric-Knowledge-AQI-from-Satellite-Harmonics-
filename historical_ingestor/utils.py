import time
import requests
from typing import Dict, Any
from historical_ingestor.config import MAX_RETRIES, SLEEP_INTERVAL
from historical_ingestor.logger import logger

def make_request_with_retry(url: str, params: Dict[str, Any] = None, headers: Dict[str, str] = None, timeout: int = 30) -> requests.Response:
    """Make an HTTP GET request with exponential backoff on failures and 429 rate limits.
    
    Aborts immediately without retries for 401 and 403.
    """
    retries = 0
    backoff = SLEEP_INTERVAL
    
    while retries <= MAX_RETRIES:
        try:
            req = requests.Request('GET', url, params=params)
            prepared = req.prepare()
            logger.info(f"Fetching URL: {prepared.url}")
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            
            if response.status_code == 200:
                return response
            elif response.status_code in (401, 403):
                logger.error(f"Authentication failure ({response.status_code}) for {url}. Please check your OPENAQ_API_KEY. Aborting.")
                raise PermissionError(f"Authentication failure {response.status_code}: {response.text}")
            elif response.status_code in (429, 500, 502, 503, 504):
                if response.status_code == 429:
                    logger.warning(f"Rate limited (429) for {url}. Retrying in {backoff} seconds...")
                else:
                    logger.warning(f"Server error {response.status_code} for {url}. Retrying in {backoff} seconds...")
                raise requests.exceptions.HTTPError(f"Retryable status {response.status_code}", response=response)
            else:
                logger.error(f"Failed request to {url} with status {response.status_code}: {response.text}")
                raise RuntimeError(f"Unrecoverable HTTP status code {response.status_code}: {response.text}")
                
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            logger.warning(f"Retryable network/HTTP error: {e}. Retrying in {backoff} seconds...")
        except requests.exceptions.RequestException as e:
            logger.error(f"Unrecoverable network error: {e}")
            raise
            
        retries += 1
        if retries <= MAX_RETRIES:
            time.sleep(backoff)
            backoff *= 2  # Exponential backoff
        
    logger.error(f"Max retries reached for {url}.")
    raise Exception(f"Failed to fetch {url} after {MAX_RETRIES} retries.")
