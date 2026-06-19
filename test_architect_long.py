import pandas as pd
import numpy as np
from src.ichimoku_quant.data import fetch_btc_data
from src.ichimoku_quant.backtest import run_backtest, calculate_metrics

def generate_features_advanced(df: pd.DataFrame, p1=20, p2=60, p3=120) -> pd.DataFrame:
    df = df.copy()
    high_p1 = df['High'].rolling(window=p1).max()
    low_p1 = df['Low'].rolling(window=p1).min()
    df['tenkan_sen'] = (high_p1 + low_p1) / 2
    
    high_p2 = df['High'].rolling(window=p2).max()
    low_p2 = df['Low'].rolling(window=p2).min()
    df['kijun_sen'] = (high_p2 + low_p2) / 2
    
    df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(p2)
    
    high_p3 = df['High'].rolling(window=p3).max()
    low_p3 = df['Low'].rolling(window=p3).min()
    df['senkou_span_b'] = ((high_p3 + low_p3) / 2).shift(p2)
    df['chikou_span'] = df['Close'].shift(-p2)
    
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift(1)).abs()
    tr3 = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=p2).mean()
    
    df['S_TK'] = np.tanh((df['tenkan_sen'] - df['kijun_sen']) / df['ATR'])
    df['S_Cloud'] = np.tanh((df['senkou_span_a'] - df['senkou_span_b']) / df['ATR'])
    df['S_Future'] = np.tanh((df['Close'] - df['senkou_span_a']) / df['ATR'])
    df['S_Chikou'] = np.tanh((df['Close'] - df['Close'].shift(p2)) / df['ATR'])
    
    df['IMO'] = (df['S_TK'] + df['S_Cloud'] + df['S_Future'] + df['S_Chikou']) / 4.0
    
    # ER (Longer lookback for macro scale)
    n_er = 30
    change = df['Close'].diff().abs()
    volatility = change.rolling(n_er).sum()
    direction = df['Close'].diff(n_er).abs()
    df['ER'] = direction / volatility
    
    df['IMO_Std'] = df['IMO'].rolling(60).std()
    return df

def generate_signals_advanced(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    pos = 0.0; signals = []
    
    for _, row in df.iterrows():
        imo_val = row['IMO']
        er_val = row['ER']
        std_val = row['IMO_Std']
        
        if pd.isna(imo_val) or pd.isna(er_val) or pd.isna(std_val):
            signals.append(0.0)
            continue
            
        adaptive_thresh_enter = std_val * 0.5
        adaptive_thresh_exit = -std_val * 0.5
        
        if pos == 0.0:
            if imo_val > adaptive_thresh_enter and er_val > 0.15: pos = 1.0
        elif pos == 1.0:
            if imo_val < adaptive_thresh_exit: pos = 0.0
        signals.append(pos)
    df['Pos'] = signals
    return df

df = fetch_btc_data()
df_feat = generate_features_advanced(df, 20, 60, 120)
df_sig = generate_signals_advanced(df_feat)
met = calculate_metrics(run_backtest(df_sig))
print(f"Macro-Scale Advanced (20,60,120) -> Return {met.get('Total Return (%)', 0):,.2f}%, Trades {met.get('Number of Trades', 0)}")
