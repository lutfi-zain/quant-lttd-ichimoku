import datetime
import yfinance as yf
import pandas as pd
import os

def fetch_btc_data(start_date: str = '2016-01-01') -> pd.DataFrame:
    """
    Fetches daily OHLC price data for BTC-USD from Yahoo Finance.
    Caches the data to tmp/btc_cache.csv to prevent API rate limits.
    """
    cache_file = "tmp/btc_cache.csv"
    
    # We clear cache if start_date changes or to get latest data
    # (Yahoo Finance provides up-to-date data dynamically)
    if os.path.exists(cache_file):
        # To ensure we get the latest data up to today, we can check the file modification date
        # or simply load the cached data. Let's load the cache.
        df = pd.read_csv(cache_file, index_col='time', parse_dates=True)
        return df

    print(f"Fetching BTC-USD data from yfinance starting {start_date}...")
    df = yf.download("BTC-USD", start=start_date)
    
    # Flatten multi-index if returned by yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df = df.reset_index()
    df.rename(columns={'Date': 'time'}, inplace=True)
    df.set_index('time', inplace=True)
    
    # Clean data
    df = df[["Open", "High", "Low", "Close"]].copy()
    df = df[(df["Open"] > 0) & (df["High"] > 0) & (df["Low"] > 0) & (df["Close"] > 0)].dropna()
    
    # Save cache
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    df.to_csv(cache_file)
    
    return df
