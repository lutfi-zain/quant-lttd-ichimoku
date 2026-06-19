"""
FINAL DENOISING APPROACH:
Problem: with ER exit gate, we lose too much return (dropping from 70K% to 20K%)
Root cause: ER gate on exit is overly restrictive; it prevents exits during volatile downtrends
             when ER is actually HIGH (volatility is directional - but bearish).

New approach from lz-technical-indicator-architect:
- Smoothing family: Use Ehler SuperSmoother (good)  
- Signal Persistence: Require 2-3 bars consistent (good)
- Min Holding Period: 30-45 days (good)
- REMOVE ER exit gate -- ER should only gate ENTRIES not exits
- Use IMO threshold crossing for exit as the primary signal
- Add a secondary CHIKOU confirmation for exit: chikou must also confirm bearish
"""
import pandas as pd
import numpy as np
from src.ichimoku_quant.data import fetch_btc_data
from src.ichimoku_quant.features import generate_ichimoku_features
from src.ichimoku_quant.backtest import run_backtest, calculate_metrics

def ehler_supersmoother(series: pd.Series, length: int = 7) -> pd.Series:
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

def signals_v3(df: pd.DataFrame, smooth_len=7, confirm_bars=2, min_hold=30,
               er_entry=0.18, t_strong=0.50, t_weak=0.25, 
               exit_confirm=2, chikou_gate=True) -> pd.DataFrame:
    """
    Clean denoised signal logic:
    ENTRY: ER gate + IMO threshold + confirm bars
    EXIT: IMO threshold + confirm bars + min hold (NO ER gate on exit)
    OPTION: Chikou (S_Chikou) must confirm bearish before exit
    """
    df = df.copy()
    df['IMO_S'] = ehler_supersmoother(df['IMO'], length=smooth_len)
    df['IMO_Std_S'] = df['IMO_S'].rolling(30).std()
    
    pos = 0.0; signals = []; regimes = []
    entry_confirm = 0; ex_confirm = 0; hold_days = 0
    bull_intent = None; exit_intent = None
    
    imo_vals = df['IMO_S'].values
    er_vals = df['ER'].values
    std_vals = df['IMO_Std_S'].values
    chikou_vals = df['S_Chikou'].values if 'S_Chikou' in df.columns else np.zeros(len(df))
    
    for i in range(len(df)):
        imo = imo_vals[i]; er = er_vals[i]; std = std_vals[i]; chikou = chikou_vals[i]
        
        if np.isnan(imo) or np.isnan(er) or np.isnan(std):
            signals.append(pos)
            regimes.append('Neutral' if pos==0 else ('Weak Bull' if pos==0.5 else 'Strong Bull'))
            continue
        
        t_s = std * t_strong; t_w = std * t_weak
        
        if pos > 0: hold_days += 1
        else: hold_days = 0
        
        can_exit = hold_days >= min_hold
        
        # --- ENTRY LOGIC (ER-gated) ---
        if pos < 1.0:
            strong_signal = imo > t_s and er > er_entry
            weak_signal = imo > t_w and er > er_entry * 0.65
            
            target = 1.0 if strong_signal else (0.5 if weak_signal else None)
            
            if target and target > pos:
                if target != bull_intent:
                    bull_intent = target; entry_confirm = 1
                else:
                    entry_confirm += 1
                if entry_confirm >= confirm_bars:
                    pos = target; entry_confirm = 0; hold_days = 0; exit_intent = None; ex_confirm = 0
            else:
                bull_intent = None; entry_confirm = 0
        
        # --- EXIT LOGIC (min_hold gated, NO ER gate) ---
        if can_exit and pos > 0:
            chikou_bearish = chikou < 0 if chikou_gate else True
            
            if pos == 1.0:
                if imo < t_w:  # Strong → Weak
                    target_exit = 0.5
                    if target_exit != exit_intent:
                        exit_intent = target_exit; ex_confirm = 1
                    else:
                        ex_confirm += 1
                    if ex_confirm >= exit_confirm:
                        pos = 0.5; ex_confirm = 0; hold_days = 0; bull_intent = None; entry_confirm = 0
                else:
                    exit_intent = None; ex_confirm = 0
                    
            if pos in (0.5, 1.0):
                if imo < 0 and chikou_bearish:  # Full exit: IMO negative + chikou bearish
                    if 0.0 != exit_intent:
                        exit_intent = 0.0; ex_confirm = 1
                    else:
                        ex_confirm += 1
                    if ex_confirm >= exit_confirm:
                        pos = 0.0; ex_confirm = 0; hold_days = 0; bull_intent = None; entry_confirm = 0
                        
        signals.append(pos)
        regimes.append('Neutral' if pos==0 else ('Weak Bull' if pos==0.5 else 'Strong Bull'))
    
    df['Pos'] = signals; df['Regime'] = regimes
    return df

print("Loading data...")
df_raw = fetch_btc_data()
df_feat = generate_ichimoku_features(df_raw)

results = []
for smooth in [5, 7, 10]:
    for confirm in [2, 3]:
        for min_hold in [21, 30, 45]:
            for ex_confirm in [1, 2, 3]:
                for chikou_gate in [True, False]:
                    df_s = signals_v3(df_feat, smooth_len=smooth, confirm_bars=confirm,
                                       min_hold=min_hold, exit_confirm=ex_confirm,
                                       chikou_gate=chikou_gate)
                    met = calculate_metrics(run_backtest(df_s))
                    trades = met.get('Number of Trades', 0)
                    if trades == 0: continue
                    changes = int(df_s['Pos'].diff().ne(0).sum())
                    ret = met.get('Total Return (%)', 0)
                    sharpe = met.get('Sharpe Ratio', 0)
                    trade_pen = abs(trades - 28) / 28.0
                    score = (ret/1000.0) * sharpe * np.exp(-trade_pen)
                    results.append({'smooth': smooth, 'confirm': confirm, 'min_hold': min_hold,
                                     'ex_confirm': ex_confirm, 'chikou': chikou_gate,
                                     'trades': trades, 'changes': changes,
                                     'ret': round(ret, 0), 'sharpe': round(sharpe, 2), 
                                     'score': round(score, 2)})

df_res = pd.DataFrame(results).sort_values('score', ascending=False)
print("\n=== TOP 15 CONFIGS v3 ===")
print(df_res.head(15).to_string(index=False))
print(f"\nBest: {df_res.iloc[0].to_dict()}")
