"""
Base API class with common functionality for government data sources
"""
import requests
import json
import time
import pandas as pd
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

try:
    from ..config.settings import get_api_key, REQUEST_SETTINGS
except ImportError:
    # For direct execution, use absolute imports
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.settings import get_api_key, REQUEST_SETTINGS


class BaseGovernmentAPI(ABC):
    """Base class for government API wrappers"""
    
    def __init__(self, service_name: str, base_url: str):
        self.service_name = service_name
        self.base_url = base_url
        self.api_key = get_api_key(service_name)
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
    def _make_request(self, url: str, data: Optional[Dict] = None, 
                     method: str = 'GET', **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic and rate limiting"""
        
        for attempt in range(REQUEST_SETTINGS['retry_attempts']):
            try:
                if method.upper() == 'POST':
                    response = self.session.post(
                        url, 
                        data=json.dumps(data) if data else None,
                        timeout=REQUEST_SETTINGS['timeout'],
                        **kwargs
                    )
                else:
                    response = self.session.get(
                        url, 
                        params=data,
                        timeout=REQUEST_SETTINGS['timeout'],
                        **kwargs
                    )
                
                response.raise_for_status()
                
                # Rate limiting
                time.sleep(REQUEST_SETTINGS['rate_limit_delay'])
                
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt == REQUEST_SETTINGS['retry_attempts'] - 1:
                    raise Exception(f"API request failed after {REQUEST_SETTINGS['retry_attempts']} attempts: {e}")
                time.sleep(REQUEST_SETTINGS['retry_delay'] * (attempt + 1))
    
    @abstractmethod
    def get_data(self, **kwargs) -> pd.DataFrame:
        """Abstract method to be implemented by each API wrapper"""
        pass
