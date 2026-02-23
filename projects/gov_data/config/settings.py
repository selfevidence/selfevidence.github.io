"""
Configuration settings for government API access
"""
import os
from typing import Dict, Any

# API Base URLs
API_URLS = {
    'bls': 'https://api.bls.gov/publicAPI/v2/timeseries/data/',
    'bea': 'https://apps.bea.gov/api/data',
    'census': 'https://api.census.gov/data',
    'fred': 'https://api.stlouisfed.org/fred',
    'treasury': 'https://api.fiscaldata.treasury.gov/services/api/v1'
}

# Request settings
REQUEST_SETTINGS = {
    'timeout': 30,
    'retry_attempts': 3,
    'retry_delay': 1,  # seconds
    'rate_limit_delay': 1  # seconds between requests
}

# Data processing settings
DATA_SETTINGS = {
    'output_format': 'csv',  # csv, parquet, json
    'date_format': '%Y-%m-%d',
    'float_precision': 2
}

# File paths
PATHS = {
    'raw_data': 'output/raw_data',
    'processed_data': 'output/processed_data',
    'figures': 'output/figures'
}

def get_api_key(service: str) -> str:
    """Get API key for specified service"""
    try:
        from .api_keys import API_KEYS
        return API_KEYS.get(service.lower(), '')
    except ImportError:
        # Fallback to environment variables
        key_mapping = {
            'bls': 'BLS_API_KEY',
            'bea': 'BEA_API_KEY', 
            'census': 'CENSUS_API_KEY',
            'fred': 'FRED_API_KEY'
        }
        return os.getenv(key_mapping.get(service.lower(), ''), '')

def get_config() -> Dict[str, Any]:
    """Get complete configuration"""
    return {
        'api_urls': API_URLS,
        'request_settings': REQUEST_SETTINGS,
        'data_settings': DATA_SETTINGS,
        'paths': PATHS
    }
