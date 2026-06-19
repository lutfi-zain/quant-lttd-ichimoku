import datetime
import requests
import pandas as pd
import os

def fetch_btc_data(start_date: str = '2016-01-01') -> pd.DataFrame:
    """
    Fetches daily OHLC price data for BTC/USD from Bitview API.
    Caches the data to tmp/btc_cache.csv to prevent API rate limits or hangs.
    """
    cache_file = "tmp/btc_cache.csv"
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file, index_col='time', parse_dates=True)
        return df

    url = f"https://bitview.space/api/series/price_ohlc/day?start={start_date}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    resp = response.json()
    
    start_idx = resp["start"]
    data = resp["data"]
    
    base_date = datetime.date(2009, 1, 1)
    dates = [base_date + datetime.timedelta(days=start_idx + i) for i in range(len(data))]
    
    df = pd.DataFrame(data, columns=["Open", "High", "Low", "Close"], index=dates)
    df.index.name = 'time'
    df.index = pd.to_datetime(df.index)
    df = df[(df["Open"] > 0) & (df["High"] > 0) & (df["Low"] > 0) & (df["Close"] > 0)].copy()
    
    # Save cache
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    df.to_csv(cache_file)
    
    return df
