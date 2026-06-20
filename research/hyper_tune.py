import pandas as pd
import numpy as np
from itertools import product
from src.ichimoku_quant.data import fetch_btc_data
from src.ichimoku_quant.backtest import run_backtest, calculate_metrics

def ehler_supersmoother(series, length=10):
    a1 = np.exp(-1.414 * np.pi / length)
    b1 = 2 * a1 * np.cos(1.414 * np.pi / length)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3
    
    filt = np.zeros(len(series))
    vals = series.fillna(0).values
    filt[0] = vals[0]
    filt[1] = vals[1]
    for i in range(2, len(series)):
        filt[i] = c1 * (vals[i] + vals[i-1])/2 + c2 * filt[i-1] + c3 * filt[i-2]
    return pd.Series(filt, index=series.index)

def generate_features(df: pd.DataFrame, p1, p2, p3, smooth_len, er_len, std_len) -> pd.DataFrame:
    df = df.copy()
    high_p1 = df['High'].rolling(window=p1).max()
    low_p1 = df['Low'].rolling(window=p1).min()
    df['tenkan_sen'] = (high_p1 + low_p1) / 2
    
    high_p2 = df['High'].rolling(window=p2).max()
    low_p2 = df['Low'].rolling(window=p2).min()
    df['kijun_sen'] = (high_p2 + low_p2) / 2
    
    df['senkou_span_a_raw'] = (df['tenkan_sen'] + df['kijun_sen']) / 2
    
    high_p3 = df['High'].rolling(window=p3).max()
    low_p3 = df['Low'].rolling(window=p3).min()
    df['senkou_span_b_raw'] = (high_p3 + low_p3) / 2
    
    df['senkou_span_a'] = df['senkou_span_a_raw'].shift(p2)
    df['senkou_span_b'] = df['senkou_span_b_raw'].shift(p2)
    
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift(1)).abs()
    tr3 = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=p2).mean()
    
    df['S_TK'] = np.tanh((df['tenkan_sen'] - df['kijun_sen']) / df['ATR'])
    
    cloud_max = np.maximum(df['senkou_span_a'], df['senkou_span_b'])
    cloud_min = np.minimum(df['senkou_span_a'], df['senkou_span_b'])
    dist_cloud = np.zeros(len(df))
    above = df['Close'] > cloud_max
    below = df['Close'] < cloud_min
    dist_cloud[above] = (df['Close'] - cloud_max)[above] / df['ATR'][above]
    dist_cloud[below] = (df['Close'] - cloud_min)[below] / df['ATR'][below]
    df['S_Cloud'] = np.tanh(dist_cloud)
    
    df['S_Future'] = np.tanh((df['senkou_span_a_raw'] - df['senkou_span_b_raw']) / df['ATR'])
    df['S_Chikou'] = np.tanh((df['Close'] - df['Close'].shift(p2)) / df['ATR'])
    
    imo_raw = (df['S_TK'] + df['S_Cloud'] + df['S_Future'] + df['S_Chikou']) / 4.0
    
    if smooth_len is not None:
        df['IMO'] = ehler_supersmoother(imo_raw, length=smooth_len)
    else:
        df['IMO'] = imo_raw
        
    change = df['Close'].diff().abs()
    volatility = change.rolling(er_len).sum()
    direction = df['Close'].diff(er_len).abs()
    df['ER'] = direction / volatility
    
    df['IMO_Std'] = df['IMO'].rolling(std_len).std()
    
    return df

def generate_signals(df: pd.DataFrame, t_strong, t_weak, t_exit) -> pd.DataFrame:
    df = df.copy()
    pos = 0.0; signals = []
    
    for _, row in df.iterrows():
        imo = row['IMO']
        er = row['ER']
        std = row['IMO_Std']
        
        if pd.isna(imo) or pd.isna(er) or pd.isna(std):
            signals.append(0.0)
            continue
            
        thresh_strong = std * t_strong
        thresh_weak = std * t_weak
        thresh_exit = std * t_exit
        
        if pos == 0.0:
            if imo > thresh_strong and er > 0.15: pos = 1.0
            elif imo > thresh_weak and er > 0.10: pos = 0.5
        elif pos == 0.5:
            if imo > thresh_strong and er > 0.15: pos = 1.0
            elif imo < thresh_exit: pos = 0.0
        elif pos == 1.0:
            if imo < thresh_exit: pos = 0.0
            elif imo < thresh_weak: pos = 0.5
            
        signals.append(pos)
    df['Pos'] = signals
    return df

print("Fetching data...")
df_raw = fetch_btc_data()

param_grid = {
    'p': [(10,30,60), (20,60,120)],
    'smooth': [None, 7, 14],
    'er': [14, 30],
    'std': [30, 60],
    't_strong': [0.5, 0.75, 1.0],
    't_weak': [0.0, 0.25],
    't_exit': [-0.5, -0.25, 0.0]
}

keys, values = zip(*param_grid.items())
combinations = [dict(zip(keys, v)) for v in product(*values)]
print(f"Total combinations to test: {len(combinations)}")

best_score = -np.inf
best_params = None
best_metrics = None

for i, params in enumerate(combinations):
    p1, p2, p3 = params['p']
    try:
        df_f = generate_features(df_raw, p1, p2, p3, params['smooth'], params['er'], params['std'])
        df_s = generate_signals(df_f, params['t_strong'], params['t_weak'], params['t_exit'])
        met = calculate_metrics(run_backtest(df_s))
        
        ret = met.get('Total Return (%)', 0)
        sharpe = met.get('Sharpe Ratio', 0)
        trades = met.get('Number of Trades', 0)
        
        if trades == 0: continue
        
        # We want to penalize extreme deviations from 28 trades
        trade_penalty = abs(trades - 28) / 28.0 
        
        # Fitness formula: High Return, High Sharpe, close to 28 trades
        # (ret / 1000) avoids large number dominance
        score = (ret / 1000.0) * sharpe * np.exp(-trade_penalty)
        
        if score > best_score:
            best_score = score
            best_params = params
            best_metrics = met
            print(f"[{i}/{len(combinations)}] New Best: Score={score:.2f} | Ret={ret:,.2f}% | Sharpe={sharpe:.2f} | Trades={trades} | {params}")
    except Exception as e:
        continue

print("\n--- FINAL BEST ---")
print(best_params)
print(f"Return: {best_metrics.get('Total Return (%)', 0):,.2f}%")
print(f"Sharpe: {best_metrics.get('Sharpe Ratio', 0):.2f}")
print(f"Trades: {best_metrics.get('Number of Trades', 0)}")

