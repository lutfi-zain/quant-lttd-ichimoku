"""
CLEANEST APPROACH:
Binary state (0=flat, 1=positioned).
Position SIZE is determined by regime at entry:
- If IMO strong (>1.0*std) at entry → size=1.0 (full)
- If IMO weak (>0.5*std) at entry → size=0.5 (half)
- Size CAN upgrade during position (once, after holding N bars, if signal strengthens)
- BUT: Pos column only changes on: entry, exit (2 events per trade)
- No intra-trade state machine flipping = maximum noise reduction
- Regime stored separately for display
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

def cleanest_signals(df, smooth_len=5, confirm_entry=3, min_hold=30, er_entry=0.18, t_entry=0.50):
    """
    Binary Pos (0/1). 
    Regime column captures Weak Bull / Strong Bull at the time of the signal.
    """
    df = df.copy()
    df['IMO_S'] = ehler_supersmoother(df['IMO'], length=smooth_len)
    df['IMO_Std_S'] = df['IMO_S'].rolling(30).std()
    
    pos = 0.0; signals = []; regimes = []
    confirm_count = 0; hold_days = 0; intent = None
    
    for _, row in df.iterrows():
        imo = row['IMO_S']; er = row['ER']; std = row['IMO_Std_S']
        
        if pd.isna(imo) or pd.isna(er) or pd.isna(std):
            signals.append(pos)
            regimes.append('Neutral' if pos==0 else 'Positioned')
            continue
        
        t_s = std * t_entry
        
        if pos > 0: hold_days += 1
        else: hold_days = 0
        
        if pos == 0.0:
            # Look for entry
            if imo > t_s and er > er_entry:
                if intent != 1.0: intent = 1.0; confirm_count = 1
                else: confirm_count += 1
                if confirm_count >= confirm_entry:
                    pos = 1.0; confirm_count = 0; hold_days = 0; intent = None
            else:
                intent = None; confirm_count = 0
        else:  # pos == 1.0
            # Look for exit
            if hold_days >= min_hold and imo < 0:
                if intent != 0.0: intent = 0.0; confirm_count = 1
                else: confirm_count += 1
                if confirm_count >= 2:  # exit needs 2 bars confirmation
                    pos = 0.0; confirm_count = 0; hold_days = 0; intent = None
            else:
                if not (hold_days >= min_hold and imo < 0):
                    intent = None; confirm_count = 0
        
        signals.append(pos)
        # Regime: at time of being positioned, is signal strong or weak?
        if pos == 1.0:
            regime = 'Strong Bull' if imo > std * 0.5 else 'Weak Bull'
        else:
            regime = 'Neutral'
        regimes.append(regime)
    
    df['Pos'] = signals; df['Regime'] = regimes
    return df

print("Loading data...")
df_raw = fetch_btc_data()
df_feat = generate_ichimoku_features(df_raw)

results = []
for smooth in [3, 5, 7, 10]:
    for confirm in [2, 3, 4]:
        for min_hold in [21, 30, 45, 60]:
            for er_entry in [0.15, 0.18, 0.22]:
                for t in [0.40, 0.50, 0.60]:
                    df_s = cleanest_signals(df_feat, smooth_len=smooth, confirm_entry=confirm,
                                             min_hold=min_hold, er_entry=er_entry, t_entry=t)
                    met = calculate_metrics(run_backtest(df_s))
                    trades = met.get('Number of Trades', 0)
                    if trades == 0: continue
                    changes = int(df_s['Pos'].diff().ne(0).sum())
                    ret = met.get('Total Return (%)', 0)
                    sharpe = met.get('Sharpe Ratio', 0)
                    max_dd = met.get('Max Drawdown (%)', 0)
                    # Target ~14 trades (14 entries = 28 state changes)
                    trade_pen = abs(trades - 14) / 14.0
                    score = (ret/1000.0) * sharpe * np.exp(-trade_pen)
                    results.append({'smooth': smooth, 'confirm': confirm, 'min_hold': min_hold,
                                     'er': er_entry, 't': t, 
                                     'trades': trades, 'changes': changes,
                                     'ret': round(ret, 0), 'sharpe': round(sharpe, 2),
                                     'dd': round(max_dd, 1), 'score': round(score, 2)})

df_res = pd.DataFrame(results).sort_values('score', ascending=False)
print("\n=== TOP 15 CLEANEST CONFIGS ===")
print(df_res.head(15).to_string(index=False))
best = df_res.iloc[0]
print(f"\nBest: {best.to_dict()}")

df_best = cleanest_signals(df_feat, smooth_len=int(best['smooth']), confirm_entry=int(best['confirm']),
                             min_hold=int(best['min_hold']), er_entry=best['er'], t_entry=best['t'])
state_changes = df_best['Pos'].diff().ne(0).sum()
changes_df = df_best[df_best['Pos'].diff().ne(0)].dropna()
rapid = (changes_df.index.to_series().diff().dt.days < 14).sum()
met = calculate_metrics(run_backtest(df_best))

print(f"\nTotal state changes: {state_changes}")
print(f"Rapid changes (<14 days): {rapid}")
print(f"Return: {met.get('Total Return (%)', 0):,.0f}% | Sharpe: {met.get('Sharpe Ratio', 0):.2f} | DD: {met.get('Max Drawdown (%)', 0):.1f}%")
print(f"\nAll signal events:")
print(changes_df[['Pos', 'Regime']].to_string())
