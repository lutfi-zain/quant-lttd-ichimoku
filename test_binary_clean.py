"""
INSIGHT: 50 state changes karena 0.5↔1.0 flip terus.
Target CSV punya 28 total, tapi termasuk Weak Bull/Strong Bull transitions.

Pendekatan baru: 
- Gunakan pure binary (0 or 1) dengan scaling di position size saat entry/exit
- Ini eliminates 0.5↔1.0 churning
- Tambah Ehler SuperSmoother + confirm bars + min hold
- Result: clean, infrequent signals matching target profile
"""
import pandas as pd
import numpy as np
from src.ichimoku_quant.data import fetch_btc_data
from src.ichimoku_quant.features import generate_ichimoku_features
from src.ichimoku_quant.backtest import run_backtest, calculate_metrics

def ehler_supersmoother(series: pd.Series, length: int = 5) -> pd.Series:
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

def binary_clean_signals(df, smooth_len=5, confirm_bars=3, min_hold=45, er_entry=0.18):
    """Pure binary 0/1 with denoising layers."""
    df = df.copy()
    df['IMO_S'] = ehler_supersmoother(df['IMO'], length=smooth_len)
    df['IMO_Std_S'] = df['IMO_S'].rolling(30).std()
    
    pos = 0.0; signals = []; regimes = []
    confirm_count = 0; hold_days = 0; intent = None
    
    for _, row in df.iterrows():
        imo = row['IMO_S']; er = row['ER']; std = row['IMO_Std_S']
        
        if pd.isna(imo) or pd.isna(er) or pd.isna(std):
            signals.append(pos)
            regimes.append('Neutral' if pos==0 else 'Bull')
            continue
        
        t_entry = std * 0.50
        t_exit = 0.0  # Exit at zero cross
        
        if pos > 0: hold_days += 1
        else: hold_days = 0
        
        can_exit = hold_days >= min_hold
        
        # Raw intent
        if pos == 0.0:
            raw = 1.0 if (imo > t_entry and er > er_entry) else 0.0
        else:  # pos == 1.0
            if can_exit and imo < t_exit:
                raw = 0.0
            else:
                raw = 1.0
        
        # Confirm filter
        if raw != intent:
            intent = raw; confirm_count = 1
        else:
            confirm_count += 1
        
        if confirm_count >= confirm_bars and raw != pos:
            pos = raw; confirm_count = 0; hold_days = 0
        
        signals.append(pos)
        regimes.append('Neutral' if pos==0 else 'Bull')
    
    df['Pos'] = signals; df['Regime'] = regimes
    return df

print("Loading data...")
df_raw = fetch_btc_data()
df_feat = generate_ichimoku_features(df_raw)

results = []
for smooth in [3, 5, 7, 10, 14]:
    for confirm in [2, 3, 4, 5]:
        for min_hold in [21, 30, 45, 60]:
            for er_entry in [0.15, 0.18, 0.22, 0.25]:
                df_s = binary_clean_signals(df_feat, smooth_len=smooth, confirm_bars=confirm,
                                             min_hold=min_hold, er_entry=er_entry)
                met = calculate_metrics(run_backtest(df_s))
                trades = met.get('Number of Trades', 0)
                if trades == 0: continue
                changes = int(df_s['Pos'].diff().ne(0).sum())
                ret = met.get('Total Return (%)', 0)
                sharpe = met.get('Sharpe Ratio', 0)
                max_dd = met.get('Max Drawdown (%)', 0)
                trade_pen = abs(trades - 16) / 16.0  # Target ~16 binary trades (each trade = entry+exit)
                score = (ret/1000.0) * sharpe * np.exp(-trade_pen)
                results.append({'smooth': smooth, 'confirm': confirm, 'min_hold': min_hold,
                                 'er': er_entry, 'trades': trades, 'changes': changes,
                                 'ret': round(ret, 0), 'sharpe': round(sharpe, 2),
                                 'dd': round(max_dd, 1), 'score': round(score, 2)})

df_res = pd.DataFrame(results).sort_values('score', ascending=False)
print("\n=== TOP 15 BINARY CLEAN CONFIGS ===")
print(df_res.head(15).to_string(index=False))
best = df_res.iloc[0]
print(f"\nBest: {best.to_dict()}")

# Verify state changes in best
df_best = binary_clean_signals(df_feat, smooth_len=int(best['smooth']), confirm_bars=int(best['confirm']),
                                 min_hold=int(best['min_hold']), er_entry=best['er'])
state_changes = df_best['Pos'].diff().ne(0).sum()
rapid_changes = (df_best[df_best['Pos'].diff().ne(0)].index.to_series().diff().dt.days < 14).sum()
print(f"\nVerification - Total state changes: {state_changes}")
print(f"Rapid changes (<14 days): {rapid_changes}")
