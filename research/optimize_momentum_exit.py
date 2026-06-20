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

def signals_hybrid_exit(df, confirm_entry=2, min_hold=21, er_entry=0.22, t_entry=0.40,
                        roc_len=14, roc_thresh=-0.10, use_imo_exit=True):
    df = df.copy()
    df['ROC'] = df['Close'].pct_change(roc_len)
    
    pos = 0.0; signals = []; regimes = []
    confirm_count = 0; hold_days = 0; intent = None
    
    for _, row in df.iterrows():
        imo = row['IMO']; er = row['ER']; std = row['IMO_Std']
        roc = row['ROC']
        
        if pd.isna(imo) or pd.isna(er) or pd.isna(std):
            signals.append(pos)
            regimes.append('Neutral' if pos==0 else 'Bull')
            continue
        
        threshold = std * t_entry
        
        if pos > 0: hold_days += 1
        else: hold_days = 0
        
        can_exit = hold_days >= min_hold
        
        if pos == 0.0:
            if imo > threshold and er > er_entry:
                if intent != 1.0: intent = 1.0; confirm_count = 1
                else: confirm_count += 1
                if confirm_count >= confirm_entry:
                    pos = 1.0; confirm_count = 0; hold_days = 0; intent = None
            else:
                intent = None; confirm_count = 0
        
        else:  # pos == 1.0
            exit_signal = False
            if can_exit:
                # Primary exit: Momentum breaks down
                if (not pd.isna(roc)) and roc < roc_thresh:
                    exit_signal = True
                # Secondary exit: IMO naturally crosses 0 (for slow grinds)
                elif use_imo_exit and imo < 0:
                    exit_signal = True
            
            if exit_signal:
                if intent != 0.0: intent = 0.0; confirm_count = 1
                else: confirm_count += 1
                if confirm_count >= 1: # fast exit
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
target = pd.read_csv('isps/isp-signals-btcusd-2026-06-13.csv', parse_dates=['Date'])
tgt_exits = target[target['Action'] == 'SELL'].sort_values('Date')
tgt_entries = target[target['Action'] == 'BUY'].sort_values('Date')

def measure_lag(df_signals, target_dates, event_type):
    events = df_signals[(df_signals['Pos'] == (1.0 if event_type=='entry' else 0.0)) & 
                        (df_signals['Pos'].shift(1) == (0.0 if event_type=='entry' else 1.0))]
    lags = []
    for _, tgt_row in target_dates.iterrows():
        tgt_date = tgt_row['Date']
        diffs = (events.index - tgt_date).days
        mask = np.abs(diffs) < 180
        if mask.any():
            nearest_idx = np.abs(diffs[mask]).argmin()
            lags.append(diffs[mask][nearest_idx])
    return np.mean(lags) if lags else 999, np.median(lags) if lags else 999

results = []

# Tweak entry t_entry and er_entry to reduce trades down to ~14 (28 changes)
for er_entry in [0.22, 0.25]:
    for t_entry in [0.40, 0.50, 0.60]:
        for min_hold in [21, 30]:
            for roc_len in [10, 14, 21]:
                for roc_thresh in [-0.05, -0.10, -0.15]:
                    df_s = signals_hybrid_exit(df_feat, confirm_entry=2, min_hold=min_hold,
                                               er_entry=er_entry, t_entry=t_entry,
                                               roc_len=roc_len, roc_thresh=roc_thresh)
                    met = calculate_metrics(run_backtest(df_s))
                    trades = met.get('Number of Trades', 0)
                    if trades == 0: continue
                    
                    changes = int(df_s['Pos'].diff().ne(0).sum())
                    ret = met.get('Total Return (%)', 0)
                    sharpe = met.get('Sharpe Ratio', 0)
                    
                    mean_exit_lag, med_exit_lag = measure_lag(df_s, tgt_exits, 'exit')
                    mean_entry_lag, med_entry_lag = measure_lag(df_s, tgt_entries, 'entry')
                    
                    # We want exactly 14 trades (28 changes) and near 0 lag
                    trade_pen = abs(trades - 14) / 14.0
                    lag_pen = abs(med_exit_lag) / 30.0 + abs(med_entry_lag) / 30.0
                    
                    score = (ret/1000.0) * sharpe * np.exp(-trade_pen * 2) * np.exp(-lag_pen)
                    
                    results.append({
                        'er': er_entry, 't': t_entry, 'min_hold': min_hold,
                        'roc_len': roc_len, 'roc_thresh': roc_thresh,
                        'trades': trades, 'changes': changes,
                        'ret': round(ret, 0), 'sharpe': round(sharpe, 2),
                        'en_lag': round(med_entry_lag, 1), 'ex_lag': round(med_exit_lag, 1),
                        'score': round(score, 2)
                    })

df_res = pd.DataFrame(results).sort_values('score', ascending=False)
print("\n=== TOP 20 CONFIGS ===")
print(df_res.head(20).to_string(index=False))
