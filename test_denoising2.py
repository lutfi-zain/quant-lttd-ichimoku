import pandas as pd
import numpy as np
from src.ichimoku_quant.data import fetch_btc_data
from src.ichimoku_quant.features import generate_ichimoku_features
from src.ichimoku_quant.backtest import run_backtest, calculate_metrics

def ehler_supersmoother(series: pd.Series, length: int = 14) -> pd.Series:
    a1 = np.exp(-1.414 * np.pi / length)
    b1 = 2 * a1 * np.cos(np.radians(1.414 * 180.0 / length))
    c2 = b1; c3 = -a1 * a1; c1 = 1 - c2 - c3
    vals = series.ffill().fillna(0).values
    filt = np.zeros(len(vals))
    filt[0] = vals[0]
    if len(vals) > 1: filt[1] = vals[1]
    for i in range(2, len(vals)):
        filt[i] = c1*(vals[i]+vals[i-1])/2 + c2*filt[i-1] + c3*filt[i-2]
    return pd.Series(filt, index=series.index)

def signals_v2(df: pd.DataFrame, smooth_len=7, confirm_bars=3, min_hold=45,
               er_entry=0.20, er_exit=0.10, t_strong=0.50, t_weak=0.25) -> pd.DataFrame:
    df = df.copy()
    df['IMO_S'] = ehler_supersmoother(df['IMO'], length=smooth_len)
    df['IMO_Std_S'] = df['IMO_S'].rolling(30).std()
    
    pos = 0.0; signals = []; regimes = []
    confirm_count = 0; hold_days = 0; intent = None
    
    for _, row in df.iterrows():
        imo = row['IMO_S']; er = row['ER']; std = row['IMO_Std_S']
        
        if pd.isna(imo) or pd.isna(er) or pd.isna(std):
            signals.append(pos)
            regimes.append('Neutral' if pos==0 else ('Weak Bull' if pos==0.5 else 'Strong Bull'))
            continue
        
        t_s = std * t_strong; t_w = std * t_weak; t_x = 0.0
        
        if pos > 0: hold_days += 1
        else: hold_days = 0
        
        can_exit = hold_days >= min_hold
        
        if pos == 0.0:
            if imo > t_s and er > er_entry: raw = 1.0
            elif imo > t_w and er > er_entry * 0.7: raw = 0.5
            else: raw = 0.0
        elif pos == 0.5:
            if imo > t_s and er > er_entry: raw = 1.0
            elif imo < t_x and can_exit and er < er_exit: raw = 0.0  # Exit needs BOTH: imo negative AND low ER (sideways)
            else: raw = 0.5
        elif pos == 1.0:
            if imo < t_x and can_exit and er < er_exit: raw = 0.0
            elif imo < t_w and can_exit: raw = 0.5
            else: raw = 1.0
        
        # Confirm N bars before acting
        if raw != intent:
            intent = raw; confirm_count = 1
        else:
            confirm_count += 1
        
        if confirm_count >= confirm_bars and raw != pos:
            pos = raw; confirm_count = 0; hold_days = 0
        
        signals.append(pos)
        regimes.append('Neutral' if pos==0 else ('Weak Bull' if pos==0.5 else 'Strong Bull'))
    
    df['Pos'] = signals; df['Regime'] = regimes
    return df

print("Fetching + generating features...")
df_raw = fetch_btc_data()
df_feat = generate_ichimoku_features(df_raw)

results = []
for smooth in [5, 7, 10]:
    for confirm in [3, 4, 5]:
        for min_hold in [30, 45, 60]:
            for er_exit in [0.08, 0.12]:
                df_s = signals_v2(df_feat, smooth_len=smooth, confirm_bars=confirm, 
                                   min_hold=min_hold, er_exit=er_exit)
                met = calculate_metrics(run_backtest(df_s))
                trades = met.get('Number of Trades', 0)
                if trades == 0: continue
                changes = df_s['Pos'].diff().ne(0).sum()
                ret = met.get('Total Return (%)', 0)
                sharpe = met.get('Sharpe Ratio', 0)
                trade_pen = abs(trades - 28) / 28.0
                score = (ret/1000.0) * sharpe * np.exp(-trade_pen)
                results.append({'smooth': smooth, 'confirm': confirm, 'min_hold': min_hold,
                                 'er_exit': er_exit, 'trades': trades, 'changes': int(changes),
                                 'ret': round(ret, 1), 'sharpe': round(sharpe, 2), 
                                 'score': round(score, 2)})

df_res = pd.DataFrame(results).sort_values('score', ascending=False)
print("\n=== TOP 15 CONFIGS v2 ===")
print(df_res.head(15).to_string(index=False))
print(f"\nBest: {df_res.iloc[0].to_dict()}")
