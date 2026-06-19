import pandas as pd
import numpy as np
import pytest
from src.ichimoku_quant.features import generate_ichimoku_features

def test_generate_ichimoku_features():
    # Create dummy OHLC data
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    df = pd.DataFrame({
        "Open": np.random.uniform(100, 200, 100),
        "High": np.random.uniform(150, 250, 100),
        "Low": np.random.uniform(50, 150, 100),
        "Close": np.random.uniform(100, 200, 100)
    }, index=dates)
    
    # Ensure High is highest and Low is lowest
    df['High'] = df[['Open', 'High', 'Close']].max(axis=1)
    df['Low'] = df[['Open', 'Low', 'Close']].min(axis=1)
    
    res = generate_ichimoku_features(df)
    
    # Check if necessary columns were created
    assert 'IMO' in res.columns
    assert 'ATR' in res.columns
    assert 'S_TK' in res.columns
    assert 'S_Cloud' in res.columns
    
    # Values should be tanh-normalized
    assert res['S_TK'].dropna().between(-1.0, 1.0).all()
    assert res['S_Cloud'].dropna().between(-1.0, 1.0).all()
    assert res['IMO'].dropna().between(-1.0, 1.0).all()
