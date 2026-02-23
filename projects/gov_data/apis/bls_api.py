"""
Bureau of Labor Statistics API wrapper
Access BLS data for employment, wages, inflation, and other economic indicators
"""
import json
import pandas as pd
from typing import List, Optional, Dict, Any

# Handle imports for both direct execution and module import
try:
    from .base_api import BaseGovernmentAPI
    from ..config.settings import API_URLS
except ImportError:
    # For direct execution, use absolute imports
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from apis.base_api import BaseGovernmentAPI
    from config.settings import API_URLS


class BLSAPI(BaseGovernmentAPI):
    """Bureau of Labor Statistics API wrapper"""
    
    def __init__(self):
        super().__init__('bls', API_URLS['bls'])
    
    def get_data(self, series_ids: List[str], years: List[int], 
                 print_output: bool = False) -> pd.DataFrame:
        """
        Get BLS time series data
        
        Args:
            series_ids: List of BLS series IDs (max 50 per request)
            years: List of years to retrieve (max 20 years per request)
            print_output: Whether to print API responses
            
        Returns:
            DataFrame with columns: series_id, year, period, value
        """
        df = pd.DataFrame(columns=["series_id", "year", "period", "value"])
        
        # Process data in chunks due to API limits
        for y in range(0, len(years), 20):  # Max 20 years per request
            year_chunk = years[y:min(y+20, len(years))]
            start_year = min(year_chunk)
            end_year = max(year_chunk)
            
            for s in range(0, len(series_ids), 50):  # Max 50 series per request
                series_chunk = series_ids[s:min(s+50, len(series_ids))]
                
                request_data = {
                    "seriesid": series_chunk,
                    "startyear": str(start_year),
                    "endyear": str(end_year),
                }
                
                # Add API key if available
                if self.api_key:
                    request_data["registrationkey"] = self.api_key
                
                try:
                    response = self._make_request(self.base_url, request_data, method='POST')
                    
                    if print_output:
                        print(json.dumps(response, indent=2))
                    
                    # Parse response
                    if response.get('status') == 'REQUEST_SUCCEEDED':
                        for series in response['Results']['series']:
                            series_id = series['seriesID']
                            for item in series['data']:
                                if item.get('value') and item['value'] != '.':
                                    new_row = {
                                        'series_id': series_id,
                                        'year': int(item['year']),
                                        'period': item['period'],
                                        'value': float(item['value'])
                                    }
                                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    else:
                        print(f"API Error: {response.get('message', 'Unknown error')}")
                        
                except Exception as e:
                    print(f"Error fetching data for years {start_year}-{end_year}, series {s}-{min(s+49, len(series_ids))}: {e}")
        
        return df
    
    def clean_data_cpi_unadjusted(self, df: pd.DataFrame, base_series_ids: Dict[str, str], regions: Dict[str, str], items: Dict[str, str]) -> pd.DataFrame:
        """Clean inflation data"""
        df['data_type'] = df['series_id'].str[0:4].apply(lambda x: base_series_ids[x])
        df['region'] = df['series_id'].str[4:8].apply(lambda x: regions[x])
        df['item'] = df['series_id'].str[8:].apply(lambda x: items[x])
        df['date'] = df['year'].astype(str) + '-' + df['period'].str[1:]
        df['date'] = pd.to_datetime(df['date'])
        return df
    
    def clean_data_weekly_nominal_earnings(self, df: pd.DataFrame, series_id_dict: Dict[str, str]) -> pd.DataFrame:
        """Clean wages data"""
        df['data_type'] = 'CPS Weekly Nominal Earnings'
        df['description'] = df['series_id'].apply(lambda x: series_id_dict[x]['description'])
        df['percentile'] = df['series_id'].apply(lambda x: series_id_dict[x]['percentile'])
        df['race'] = df['series_id'].apply(lambda x: series_id_dict[x]['race'])
        df['year'] = df['year'].astype(int)
        df['value'] = df['value'].astype(float)
        
        quarter_mapping = {
            'Q01': '01-01',
            'Q02': '04-01',
            'Q03': '07-01',
            'Q04': '10-01',
        }
        df['date'] = df['year'].astype(str) + '-' + df['period'].map(quarter_mapping)
        df['date'] = pd.to_datetime(df['date'])

        return df

# Test the function
if __name__ == "__main__":
    print("🚀 BLS API Module Loaded Successfully!")
    print("=" * 50)
    
    # Test the new class
    print("✅ Class 'BLSAPI' is ready to use.")
    
    # Quick API test (uncomment to run actual test)
    print("\n🔄 Running quick API test...")
    try:
        bls = BLSAPI()
        test_series = ['LNS14000000']  # Unemployment rate
        test_years = [2023]
        
        df = bls.get_data(test_series, test_years)
        print(f"✅ API test successful! Retrieved {len(df)} data points.")
        print(df.head())
    except Exception as e:
        print(f"❌ API test failed: {e}")
