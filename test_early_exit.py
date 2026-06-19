"""
SOLVING EXIT LAG:

Root cause: tanh saturates IMO at ~0.99 for months.
Exit trigger 'IMO < 0' waits for full reversal = 40+ days late.

Solutions to test:
A. Peak Drawdown Exit: exit when IMO drops X% from its rolling peak
B. Momentum Exit: exit when price rate-of-change turns negative for N bars
C. Chikou Reversal: S_Chikou < threshold as early warning
D. Combined: any 2 of A/B/C triggers exit after min_hold
"""
import pandas as pd
import numpy as np
from src.ichimoku_quant.data import fetch_btc_data
from src.ichimoku_quant.features import generate_ichimoku_features
from src.ichimoku_quant.backtest import run_backtest, calculate_metrics

def ehler_supersmoother(series, length=7):
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

def signals_early_exit(df, confirm_entry=2, min_hold=14, er_entry=0.22, t_entry=0.40,
                        exit_mode='peak_dd', peak_dd_thresh=0.15, 
                        roc_len=14, roc_thresh=-0.05,
                        chikou_thresh=-0.3):
    df = df.copy()
    
    # Price ROC (momentum family)
    df['ROC'] = df['Close'].pct_change(roc_len)
    
    pos = 0.0; signals = []; regimes = []
    confirm_count = 0; hold_days = 0; intent = None
    imo_peak = -np.inf  # Track peak IMO during position
    
    for _, row in df.iterrows():
        imo = row['IMO']; er = row['ER']; std = row['IMO_Std']
        roc = row['ROC']
        chikou = row.get('S_Chikou', 0.0)
        
        if pd.isna(imo) or pd.isna(er) or pd.isna(std):
            signals.append(pos)
            regimes.append('Neutral' if pos==0 else 'Bull')
            continue
        
        threshold = std * t_entry
        
        if pos > 0:
            hold_days += 1
            imo_peak = max(imo_peak, imo)
        else:
            hold_days = 0
            imo_peak = -np.inf
        
        can_exit = hold_days >= min_hold
        
        if pos == 0.0:
            # ENTRY
            if imo > threshold and er > er_entry:
                if intent != 1.0: intent = 1.0; confirm_count = 1
                else: confirm_count += 1
                if confirm_count >= confirm_entry:
                    pos = 1.0; confirm_count = 0; hold_days = 0; intent = None
                    imo_peak = imo
            else:
                intent = None; confirm_count = 0
        
        else:  # pos == 1.0
            exit_signal = False
            
            if can_exit:
                if exit_mode == 'peak_dd':
                    # Exit when IMO drops peak_dd_thresh from peak
                    imo_dd = imo_peak - imo
                    exit_signal = imo_dd > peak_dd_thresh
                    
                elif exit_mode == 'roc':
                    # Exit when price momentum turns sufficiently negative
                    exit_signal = (not pd.isna(roc)) and roc < roc_thresh
                    
                elif exit_mode == 'chikou':
                    # Exit when chikou span turns bearish
                    exit_signal = chikou < chikou_thresh
                    
                elif exit_mode == 'combo_peak_roc':
                    # Exit when EITHER peak drawdown OR negative ROC
                    imo_dd = imo_peak - imo
                    exit_signal = (imo_dd > peak_dd_thresh) or ((not pd.isna(roc)) and roc < roc_thresh)
                    
                elif exit_mode == 'combo_peak_chikou':
                    # Exit when peak drawdown AND chikou confirms
                    imo_dd = imo_peak - imo
                    exit_signal = (imo_dd > peak_dd_thresh) and (chikou < chikou_thresh)
                    
                elif exit_mode == 'adaptive_peak':
                    # Adaptive: use std-scaled peak drawdown
                    imo_dd = imo_peak - imo
                    exit_signal = imo_dd > (std * peak_dd_thresh)
            
            if exit_signal:
                if intent != 0.0: intent = 0.0; confirm_count = 1
                else: confirm_count += 1
                if confirm_count >= 1:  # Fast exit (1 bar confirm)
                    pos = 0.0; confirm_count = 0; hold_days = 0; intent = None
            else:
                intent = None; confirm_count = 0
        
        signals.append(pos)
        regimes.append('Neutral' if pos==0 else ('Strong Bull' if imo > threshold else 'Weak Bull'))
    
    df['Pos'] = signals; df['Regime'] = regimes
    return df

print("Loading data...")
df_raw = fetch_btc_data()
df_feat = generate_ichimoku_features(df_raw)

# Load target for lag measurement
target = pd.read_csv('isps/isp-signals-btcusd-2026-06-13.csv', parse_dates=['Date'])
tgt_exits = target[target['Action'] == 'SELL'].sort_values('Date')

def measure_exit_lag(df_signals):
    """Average exit lag vs target CSV."""
    our_exits = df_signals[(df_signals['Pos'] == 0.0) & (df_signals['Pos'].shift(1) == 1.0)]
    lags = []
    for _, tgt_row in tgt_exits.iterrows():
        tgt_date = tgt_row['Date']
        diffs = (our_exits.index - tgt_date).days
        mask = np.abs(diffs) < 180
        if mask.any():
            nearest_idx = np.abs(diffs[mask]).argmin()
            lag = diffs[mask][nearest_idx]
            lags.append(lag)
    return np.mean(lags) if lags else 999, np.median(lags) if lags else 999

results = []

# Test different exit modes
for exit_mode in ['peak_dd', 'roc', 'chikou', 'combo_peak_roc', 'adaptive_peak']:
    if exit_mode in ('peak_dd', 'combo_peak_roc', 'adaptive_peak'):
        dd_range = [0.05, 0.10, 0.15, 0.20, 0.30]
    else:
        dd_range = [0.15]  # dummy
    
    for dd in dd_range:
        for min_hold in [7, 14, 21]:
            for roc_len in [10, 14]:
                for roc_thresh in [-0.05, -0.10]:
                    try:
                        df_s = signals_early_exit(df_feat, min_hold=min_hold,
                                                   exit_mode=exit_mode, peak_dd_thresh=dd,
                                                   roc_len=roc_len, roc_thresh=roc_thresh)
                        met = calculate_metrics(run_backtest(df_s))
                        trades = met.get('Number of Trades', 0)
                        if trades == 0: continue
                        
                        changes = int(df_s['Pos'].diff().ne(0).sum())
                        ret = met.get('Total Return (%)', 0)
                        sharpe = met.get('Sharpe Ratio', 0)
                        
                        mean_lag, med_lag = measure_exit_lag(df_s)
                        
                        # Fitness: minimize exit lag while keeping good returns
                        lag_score = max(0, 40 - abs(med_lag)) / 40.0  # Reward being close to 0
                        trade_score = np.exp(-abs(trades - 14) / 14.0)
                        perf_score = (ret/1000.0) * sharpe
                        score = perf_score * (1 + lag_score) * trade_score
                        
                        results.append({
                            'mode': exit_mode, 'dd': dd, 'min_hold': min_hold,
                            'roc_len': roc_len, 'roc_thresh': roc_thresh,
                            'trades': trades, 'changes': changes,
                            'ret': round(ret, 0), 'sharpe': round(sharpe, 2),
                            'exit_lag_mean': round(mean_lag, 1), 'exit_lag_med': round(med_lag, 1),
                            'score': round(score, 2)
                        })
                    except:
                        continue

df_res = pd.DataFrame(results).sort_values('score', ascending=False)
print("\n=== TOP 20 EARLY EXIT CONFIGS ===")
print(df_res.head(20).to_string(index=False))
print(f"\nBest: {df_res.iloc[0].to_dict()}")
