import pandas as pd
import numpy as np
from src.ichimoku_quant.data import fetch_btc_data
from src.ichimoku_quant.backtest import run_backtest, calculate_metrics

def generate_ichimoku_features(df: pd.DataFrame, p1=20, p2=60, p3=120) -> pd.DataFrame:
    df = df.copy()
    
    # Tenkan-sen (Conversion Line)
    high_p1 = df['High'].rolling(window=p1).max()
    low_p1 = df['Low'].rolling(window=p1).min()
    df['tenkan_sen'] = (high_p1 + low_p1) / 2
    
    # Kijun-sen (Base Line)
    high_p2 = df['High'].rolling(window=p2).max()
    low_p2 = df['Low'].rolling(window=p2).min()
    df['kijun_sen'] = (high_p2 + low_p2) / 2
    
    # Senkou Span A (Leading Span A)
    df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(p2)
    
    # Senkou Span B (Leading Span B)
    high_p3 = df['High'].rolling(window=p3).max()
    low_p3 = df['Low'].rolling(window=p3).min()
    df['senkou_span_b'] = ((high_p3 + low_p3) / 2).shift(p2)
    
    # Chikou Span (Lagging Span)
    df['chikou_span'] = df['Close'].shift(-p2)
    
    # ATR for normalization
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift(1)).abs()
    tr3 = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=p2).mean()
    
    # Features
    df['S_TK'] = np.tanh((df['tenkan_sen'] - df['kijun_sen']) / df['ATR'])
    df['S_Cloud'] = np.tanh((df['senkou_span_a'] - df['senkou_span_b']) / df['ATR'])
    df['S_Future'] = np.tanh((df['Close'] - df['senkou_span_a']) / df['ATR'])
    df['S_Chikou'] = np.tanh((df['Close'] - df['Close'].shift(p2)) / df['ATR'])
    
    # Composite IMO
    df['IMO'] = (df['S_TK'] + df['S_Cloud'] + df['S_Future'] + df['S_Chikou']) / 4.0
    return df

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    pos = 0.0; signals = []
    
    # Thresholds
    t_strong_bull_enter = 0.60
    t_weak_bull_enter = 0.15
    t_strong_bull_exit = 0.20
    t_weak_bull_exit = -0.15
    
    for _, row in df.iterrows():
        imo_val = row['IMO']
        if pd.isna(imo_val):
            signals.append(0.0)
            continue
            
        if pos == 0.0:
            if imo_val > t_strong_bull_enter: pos = 1.0
            elif imo_val > t_weak_bull_enter: pos = 0.5
        elif pos == 0.5:
            if imo_val > t_strong_bull_enter: pos = 1.0
            elif imo_val < t_weak_bull_exit: pos = 0.0
        elif pos == 1.0:
            if imo_val < t_weak_bull_exit: pos = 0.0
            elif imo_val < t_strong_bull_exit: pos = 0.5
        signals.append(pos)
    df['Pos'] = signals
    return df

df = fetch_btc_data()

params = [(9, 26, 52), (10, 30, 60), (20, 60, 120), (30, 90, 180)]

for p1, p2, p3 in params:
    df_feat = generate_ichimoku_features(df, p1, p2, p3)
    df_sig = generate_signals(df_feat)
    met = calculate_metrics(run_backtest(df_sig))
    print(f"Params ({p1},{p2},{p3}): Return {met.get('Total Return (%)', 0):,.2f}%, Trades {met.get('Number of Trades', 0)}")
