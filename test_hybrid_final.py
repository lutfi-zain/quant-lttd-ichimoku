"""
FINAL HYBRID APPROACH:
- Binary state machine (0 or 1) eliminates the 0.5↔1.0 churn
- BUT: position sizing is scaled via entry logic:
    * Entry: always start at 50% (Weak Bull mode)
    * Upgrade: 50% → 100% when IMO stays above threshold for N bars
    * Expressed in Pos column as float (0.0, 0.5, 1.0) for backtest compatibility
    * The KEY difference: upgrade is one-directional only during holding
    * Exit: from any state → 0.0 (no intermediate step)
    
This avoids the churn because:
- 0→0.5 is entry (one event)
- 0.5→1.0 is upgrade (happens max once per position)
- 1.0→0.0 or 0.5→0.0 is exit (one event)
Target: ~28 total events = 7 entries × 2 (half + full) + 14 exits = 28
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

def hybrid_signals(df, smooth_len=5, confirm_entry=3, confirm_upgrade=5, 
                   min_hold_exit=30, er_entry=0.18):
    """
    Entry at 50%, upgrade to 100% after sustained strength.
    Exit cleans at once (no step-down).
    One-directional within position = eliminates churn.
    """
    df = df.copy()
    df['IMO_S'] = ehler_supersmoother(df['IMO'], length=smooth_len)
    df['IMO_Std_S'] = df['IMO_S'].rolling(30).std()
    
    pos = 0.0; signals = []; regimes = []
    confirm_count = 0; hold_days = 0; upgraded = False
    phase = 'flat'  # 'flat', 'weak', 'strong'
    
    for _, row in df.iterrows():
        imo = row['IMO_S']; er = row['ER']; std = row['IMO_Std_S']
        
        if pd.isna(imo) or pd.isna(er) or pd.isna(std):
            signals.append(pos)
            regimes.append('Neutral' if pos==0 else ('Strong Bull' if pos==1.0 else 'Weak Bull'))
            continue
        
        t_entry = std * 0.50
        
        if pos > 0: hold_days += 1
        else: hold_days = 0
        
        can_exit = hold_days >= min_hold_exit
        
        if phase == 'flat':
            # Look for entry signal
            if imo > t_entry and er > er_entry:
                confirm_count += 1
                if confirm_count >= confirm_entry:
                    pos = 0.5; phase = 'weak'; confirm_count = 0; upgraded = False; hold_days = 0
            else:
                confirm_count = 0
                
        elif phase == 'weak':
            # Look for upgrade OR exit
            if can_exit and imo < 0:
                # Exit: back to flat
                pos = 0.0; phase = 'flat'; confirm_count = 0; hold_days = 0; upgraded = False
            elif not upgraded and imo > t_entry and er > er_entry:
                confirm_count += 1
                if confirm_count >= confirm_upgrade:
                    pos = 1.0; phase = 'strong'; confirm_count = 0; upgraded = True
            else:
                if not (imo > t_entry and er > er_entry):
                    confirm_count = 0  # Reset upgrade counter if signal falters
                    
        elif phase == 'strong':
            # Look for exit only
            if can_exit and imo < 0:
                pos = 0.0; phase = 'flat'; confirm_count = 0; hold_days = 0; upgraded = False
        
        signals.append(pos)
        regimes.append('Neutral' if pos==0 else ('Strong Bull' if pos==1.0 else 'Weak Bull'))
    
    df['Pos'] = signals; df['Regime'] = regimes
    return df

print("Loading data...")
df_raw = fetch_btc_data()
df_feat = generate_ichimoku_features(df_raw)

results = []
for smooth in [3, 5, 7]:
    for c_entry in [2, 3]:
        for c_upgrade in [3, 5, 7]:
            for min_hold in [21, 30, 45]:
                for er in [0.15, 0.18, 0.22]:
                    df_s = hybrid_signals(df_feat, smooth_len=smooth, confirm_entry=c_entry, 
                                           confirm_upgrade=c_upgrade, min_hold_exit=min_hold, er_entry=er)
                    met = calculate_metrics(run_backtest(df_s))
                    trades = met.get('Number of Trades', 0)
                    if trades == 0: continue
                    changes = int(df_s['Pos'].diff().ne(0).sum())
                    ret = met.get('Total Return (%)', 0)
                    sharpe = met.get('Sharpe Ratio', 0)
                    max_dd = met.get('Max Drawdown (%)', 0)
                    trade_pen = abs(trades - 28) / 28.0
                    score = (ret/1000.0) * sharpe * np.exp(-trade_pen)
                    results.append({'smooth': smooth, 'c_entry': c_entry, 'c_upg': c_upgrade, 
                                     'min_hold': min_hold, 'er': er, 
                                     'trades': trades, 'changes': changes,
                                     'ret': round(ret, 0), 'sharpe': round(sharpe, 2),
                                     'dd': round(max_dd, 1), 'score': round(score, 2)})

df_res = pd.DataFrame(results).sort_values('score', ascending=False)
print("\n=== TOP 15 HYBRID CONFIGS ===")
print(df_res.head(15).to_string(index=False))
best = df_res.iloc[0]
print(f"\nBest: {best.to_dict()}")

# Verify
df_best = hybrid_signals(df_feat, smooth_len=int(best['smooth']), confirm_entry=int(best['c_entry']),
                           confirm_upgrade=int(best['c_upg']), min_hold_exit=int(best['min_hold']),
                           er_entry=best['er'])
state_changes = df_best['Pos'].diff().ne(0).sum()
changes_df = df_best[df_best['Pos'].diff().ne(0)].dropna()
rapid = (changes_df.index.to_series().diff().dt.days < 14).sum()
print(f"\nTotal state changes: {state_changes}")
print(f"Rapid changes (<14 days): {rapid}")
print(f"\nSignal events:")
print(changes_df[['Pos', 'Regime']].to_string())
