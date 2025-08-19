import sys
import requests
import json
import pandas as pd
import time
from secret_keys import bls_api_key

headers = {'Content-type': 'application/json'}

def get_bls_data(series_ids: list[str], years: list[int], print_output: bool = False):
    df = pd.DataFrame(columns=["series id", "year", "period", "value"])
    
    for y in range(0, len(years), 20):
        for s in range(0, len(series_ids), 50):
            data = json.dumps(
                {
                    "seriesid": series_ids[s:min(s+49, len(series_ids))],
                    "startyear": years[y],
                    "endyear": years[min(y+19, len(years)-1)],
                    "registrationkey": bls_api_key,
                }
            )
            p = requests.post('https://api.bls.gov/publicAPI/v2/timeseries/data/', data=data, headers=headers)
            json_data = json.loads(p.text)
            if print_output:
                print(json_data)
            for series in json_data['Results']['series']:
                seriesId = series['seriesID']
                for item in series['data']:
                    year = item['year']
                    period = item['period']
                    value = item['value']
                    if value:
                        df.loc[len(df)] = [seriesId, year, period, value]
            
            time.sleep(1)

    return df

# Test the function
if __name__ == "__main__":
    print("Script loaded successfully!")
    print("Function 'get_bls_data' is ready to use.")