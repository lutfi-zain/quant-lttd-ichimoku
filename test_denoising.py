import pandas as pd
import numpy as np
from src.ichimoku_quant.data import fetch_btc_data
from src.ichimoku_quant.features import generate_ichimoku_features
from src.ichimoku_quant.backtest import run_backtest, calculate_metrics

# ============================================================
# NOISE REDUCTION EXPERIMENT
# Testing multiple denoising layers from lz-technical-indicator-architect:
# 1. Ehler's SuperSmoother (Spectral / Filtering family)
# 2. Confirmation Bars (Signal Persistence)
# 3. Minimum Hold Period (Trade Throttling)
# 4. Adaptive ER Gate (Fractal family - stricter re-entry)
# ============================================================

def ehler_supersmoother(series: pd.Series, length: int = 14) -> pd.Series:
    """Spectral principle: removes high-frequency noise below 'length' period cycle."""
    a1 = np.exp(-1.414 * np.pi / length)
    b1 = 2 * a1 * np.cos(np.radians(1.414 * 180.0 / length))
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3
    
    vals = series.fillna(method='ffill').fillna(0).values
    filt = np.zeros(len(vals))
    filt[0] = vals[0]
    if len(vals) > 1:
        filt[1] = vals[1]
    for i in range(2, len(vals)):
        filt[i] = c1 * (vals[i] + vals[i-1]) / 2 + c2 * filt[i-1] + c3 * filt[i-2]
    return pd.Series(filt, index=series.index)

def signals_with_denoising(df: pd.DataFrame, 
                            smooth_len: int = 10,
                            confirm_bars: int = 3,
                            min_hold: int = 21,
                            er_entry: float = 0.20,
                            er_weak: float = 0.12,
                            t_strong: float = 0.50,
                            t_weak: float = 0.25,
                            t_exit: float = 0.0) -> pd.DataFrame:
    df = df.copy()
    
    # Layer 1: Ehler SuperSmoother on IMO (Spectral / Filtering)
    df['IMO_Smooth'] = ehler_supersmoother(df['IMO'], length=smooth_len)
    df['IMO_Std_Smooth'] = df['IMO_Smooth'].rolling(30).std()
    
    pos = 0.0
    signals = []
    regimes = []
    confirm_count = 0       # bars confirming current intent
    hold_days = 0           # days held in current position
    intent = None           # pending direction before confirmation
    
    for _, row in df.iterrows():
        imo = row['IMO_Smooth']
        er = row['ER']
        std = row['IMO_Std_Smooth']
        
        if pd.isna(imo) or pd.isna(er) or pd.isna(std):
            signals.append(pos)
            regimes.append('Neutral' if pos == 0 else ('Weak Bull' if pos == 0.5 else 'Strong Bull'))
            continue
        
        t_s = std * t_strong
        t_w = std * t_weak
        t_x = std * t_exit
        
        # Track holding time
        if pos > 0:
            hold_days += 1
        else:
            hold_days = 0
        
        # Determine raw intent
        if pos == 0.0:
            if imo > t_s and er > er_entry:
                raw_intent = 1.0
            elif imo > t_w and er > er_weak:
                raw_intent = 0.5
            else:
                raw_intent = 0.0
        elif pos == 0.5:
            if imo > t_s and er > er_entry:
                raw_intent = 1.0
            elif imo < t_x and hold_days >= min_hold:
                raw_intent = 0.0
            else:
                raw_intent = 0.5
        elif pos == 1.0:
            if imo < t_x and hold_days >= min_hold:
                raw_intent = 0.0
            elif imo < t_w and hold_days >= min_hold:
                raw_intent = 0.5
            else:
                raw_intent = 1.0
        
        # Confirmation Bar Filter
        if raw_intent != intent:
            intent = raw_intent
            confirm_count = 1
        else:
            confirm_count += 1
        
        # Only act after N consecutive confirming bars
        if confirm_count >= confirm_bars and raw_intent != pos:
            pos = raw_intent
            confirm_count = 0
            hold_days = 0
        
        signals.append(pos)
        if pos == 1.0:
            regimes.append('Strong Bull')
        elif pos == 0.5:
            regimes.append('Weak Bull')
        else:
            regimes.append('Neutral')
    
    df['Pos'] = signals
    df['Regime'] = regimes
    return df

print("Fetching data...")
df_raw = fetch_btc_data()
df_feat = generate_ichimoku_features(df_raw)

# === Grid search over denoising parameters ===
results = []

for smooth in [7, 10, 14]:
    for confirm in [2, 3, 5]:
        for min_hold in [14, 21, 30]:
            for er_entry in [0.18, 0.22]:
                df_s = signals_with_denoising(df_feat, 
                                               smooth_len=smooth,
                                               confirm_bars=confirm,
                                               min_hold=min_hold,
                                               er_entry=er_entry)
                met = calculate_metrics(run_backtest(df_s))
                
                trades = met.get('Number of Trades', 0)
                if trades == 0:
                    continue
                
                # Count state changes
                changes = df_s['Pos'].diff().ne(0).sum()
                ret = met.get('Total Return (%)', 0)
                sharpe = met.get('Sharpe Ratio', 0)
                
                # Fitness: maximize return * sharpe, minimize deviation from 28 trades
                trade_pen = abs(trades - 28) / 28.0
                score = (ret / 1000.0) * sharpe * np.exp(-trade_pen)
                
                results.append({
                    'smooth': smooth, 'confirm': confirm, 'min_hold': min_hold, 
                    'er_entry': er_entry, 'trades': trades, 'changes': changes,
                    'ret': ret, 'sharpe': sharpe, 'score': score
                })

df_res = pd.DataFrame(results).sort_values('score', ascending=False)
print("\n=== TOP 10 DENOISING CONFIGS ===")
print(df_res.head(10).to_string(index=False))
print(f"\nBest: {df_res.iloc[0].to_dict()}")
