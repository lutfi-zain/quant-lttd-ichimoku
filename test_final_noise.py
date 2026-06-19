"""
Fine-tune around the best discovered config:
smooth=5, confirm=2, min_hold=30, ex_confirm=1, chikou=False
Let's try expanding the search space slightly with finer granularity.
Also try: stronger ER entry filter, different t_strong/t_weak ratios.
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

def signals_final(df, smooth_len=5, confirm_bars=2, min_hold=30, ex_confirm=1,
                  er_entry=0.18, t_strong=0.50, t_weak=0.25):
    df = df.copy()
    df['IMO_S'] = ehler_supersmoother(df['IMO'], length=smooth_len)
    df['IMO_Std_S'] = df['IMO_S'].rolling(30).std()
    
    pos = 0.0; signals = []; regimes = []
    entry_confirm = 0; ex_confirm_cnt = 0; hold_days = 0
    bull_intent = None; exit_intent = None
    
    for _, row in df.iterrows():
        imo = row['IMO_S']; er = row['ER']; std = row['IMO_Std_S']
        
        if pd.isna(imo) or pd.isna(er) or pd.isna(std):
            signals.append(pos)
            regimes.append('Neutral' if pos==0 else ('Weak Bull' if pos==0.5 else 'Strong Bull'))
            continue
        
        t_s = std * t_strong; t_w = std * t_weak
        
        if pos > 0: hold_days += 1
        else: hold_days = 0
        
        can_exit = hold_days >= min_hold
        
        # ENTRY (ER-gated)
        if pos < 1.0:
            strong_sig = imo > t_s and er > er_entry
            weak_sig = imo > t_w and er > er_entry * 0.65
            
            target = 1.0 if strong_sig else (0.5 if weak_sig else None)
            if target and target > pos:
                if target != bull_intent: bull_intent = target; entry_confirm = 1
                else: entry_confirm += 1
                if entry_confirm >= confirm_bars:
                    pos = target; entry_confirm = 0; hold_days = 0; exit_intent = None; ex_confirm_cnt = 0
            else:
                bull_intent = None; entry_confirm = 0
        
        # EXIT (min-hold gated, no ER gate)
        if can_exit and pos > 0:
            if pos == 1.0 and imo < t_w:
                if 0.5 != exit_intent: exit_intent = 0.5; ex_confirm_cnt = 1
                else: ex_confirm_cnt += 1
                if ex_confirm_cnt >= ex_confirm:
                    pos = 0.5; ex_confirm_cnt = 0; hold_days = 0; bull_intent = None; entry_confirm = 0
            elif imo < 0:
                if 0.0 != exit_intent: exit_intent = 0.0; ex_confirm_cnt = 1
                else: ex_confirm_cnt += 1
                if ex_confirm_cnt >= ex_confirm:
                    pos = 0.0; ex_confirm_cnt = 0; hold_days = 0; bull_intent = None; entry_confirm = 0
                    exit_intent = None
            else:
                exit_intent = None; ex_confirm_cnt = 0
        
        signals.append(pos)
        regimes.append('Neutral' if pos==0 else ('Weak Bull' if pos==0.5 else 'Strong Bull'))
    
    df['Pos'] = signals; df['Regime'] = regimes
    return df

print("Loading data...")
df_raw = fetch_btc_data()
df_feat = generate_ichimoku_features(df_raw)

results = []
for smooth in [3, 4, 5]:
    for confirm in [2, 3]:
        for min_hold in [25, 30, 35, 40]:
            for er_entry in [0.15, 0.18, 0.20, 0.22]:
                for t_weak in [0.20, 0.25, 0.30]:
                    df_s = signals_final(df_feat, smooth_len=smooth, confirm_bars=confirm,
                                          min_hold=min_hold, er_entry=er_entry, t_weak=t_weak)
                    met = calculate_metrics(run_backtest(df_s))
                    trades = met.get('Number of Trades', 0)
                    if trades == 0: continue
                    changes = int(df_s['Pos'].diff().ne(0).sum())
                    ret = met.get('Total Return (%)', 0)
                    sharpe = met.get('Sharpe Ratio', 0)
                    max_dd = met.get('Max Drawdown (%)', 0)
                    trade_pen = abs(trades - 28) / 28.0
                    score = (ret/1000.0) * sharpe * np.exp(-trade_pen)
                    results.append({'smooth': smooth, 'confirm': confirm, 'min_hold': min_hold,
                                     'er': er_entry, 't_weak': t_weak,
                                     'trades': trades, 'changes': changes,
                                     'ret': round(ret, 0), 'sharpe': round(sharpe, 2),
                                     'dd': round(max_dd, 1),
                                     'score': round(score, 2)})

df_res = pd.DataFrame(results).sort_values('score', ascending=False)
print("\n=== TOP 15 FINE-TUNED CONFIGS ===")
print(df_res.head(15).to_string(index=False))
best = df_res.iloc[0].to_dict()
print(f"\nBest config: {best}")
