"""
Understand WHY exits are 40 days late.
Look at what IMO looks like around target exit dates.
"""
import pandas as pd
import numpy as np
from src.ichimoku_quant.data import fetch_btc_data
from src.ichimoku_quant.features import generate_ichimoku_features

target = pd.read_csv('isps/isp-signals-btcusd-2026-06-13.csv', parse_dates=['Date'])
tgt_exits = target[target['Action'] == 'SELL'].sort_values('Date')

df = fetch_btc_data()
df = generate_ichimoku_features(df)

print("=== IMO DYNAMICS AROUND TARGET EXIT DATES ===\n")
for _, row in tgt_exits.iterrows():
    tgt_date = row['Date']
    if tgt_date not in df.index:
        continue
    
    # Look at 20 days before and after the target exit
    start = tgt_date - pd.Timedelta(days=20)
    end = tgt_date + pd.Timedelta(days=20)
    window = df.loc[start:end]
    
    tgt_row = df.loc[tgt_date]
    imo_val = tgt_row['IMO']
    er_val = tgt_row['ER']
    std_val = tgt_row['IMO_Std']
    
    # When does IMO cross zero after the target date?
    after_target = df.loc[tgt_date:]
    zero_cross = after_target[after_target['IMO'] < 0]
    if len(zero_cross) > 0:
        zero_date = zero_cross.index[0]
        zero_lag = (zero_date - tgt_date).days
    else:
        zero_date = 'never'
        zero_lag = 'N/A'
    
    # S_Chikou at target date (momentum indicator)
    chikou = tgt_row['S_Chikou'] if 'S_Chikou' in df.columns else 'N/A'
    
    # Peak IMO before the target exit
    before_target = df.loc[:tgt_date].tail(60)
    peak_imo = before_target['IMO'].max()
    peak_date = before_target['IMO'].idxmax()
    days_since_peak = (tgt_date - peak_date).days
    
    print(f"Target exit: {tgt_date.strftime('%Y-%m-%d')} (Price: {row['Price']:.2f})")
    print(f"  IMO at target: {imo_val:.4f} (still positive = our system hasn't triggered exit)")
    print(f"  ER at target: {er_val:.4f}")
    print(f"  S_Chikou at target: {chikou:.4f}" if isinstance(chikou, float) else f"  S_Chikou: {chikou}")
    print(f"  IMO peaks at {peak_imo:.4f} on {peak_date.strftime('%Y-%m-%d')} ({days_since_peak}d before exit)")
    print(f"  IMO crosses zero: {zero_date.strftime('%Y-%m-%d') if isinstance(zero_date, pd.Timestamp) else zero_date} (lag: {zero_lag}d)")
    
    # What's IMO_derivative at target?
    imo_deriv = df['IMO'].diff().loc[tgt_date]
    imo_deriv5 = (df['IMO'].loc[tgt_date] - df['IMO'].shift(5).loc[tgt_date]) if tgt_date in df.index else 'N/A'
    print(f"  IMO change (1d): {imo_deriv:.6f}, IMO change (5d): {imo_deriv5:.4f}")
    print()

print("\n=== KEY INSIGHT ===")
print("Exit lag sources:")
print("1. IMO uses Ichimoku lines with p2=60, p3=120 → inherently lagging")
print("2. Exit requires IMO < 0 → waits for full zero-cross which takes ~30-60 days")
print("3. min_hold=30 days adds more delay on top")
print("\nSolution directions:")
print("A. Use IMO DERIVATIVE (rate of change) for earlier exit detection")
print("B. Use S_Chikou turning negative as an early exit warning")
print("C. Reduce Ichimoku periods to less lagging values")
print("D. Use price-based exit (% drawdown from peak) instead of pure IMO")
print("E. Use 'IMO falling below recent high' instead of 'IMO < 0'")
