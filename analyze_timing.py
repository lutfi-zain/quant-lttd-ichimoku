"""
Deep timing analysis: compare our system signals vs target CSV signals.
Goal: quantify exactly how late our entries and exits are.
"""
import pandas as pd
import numpy as np
from src.ichimoku_quant.data import fetch_btc_data
from src.ichimoku_quant.features import generate_ichimoku_features
from src.ichimoku_quant.strategy import generate_signals

# Load target
target = pd.read_csv('isps/isp-signals-btcusd-2026-06-13.csv', parse_dates=['Date'])
target = target.sort_values('Date')

# Generate our signals
df = fetch_btc_data()
df = generate_ichimoku_features(df)
df = generate_signals(df)

# Extract our entry/exit events
our_entries = df[(df['Pos'] == 1.0) & (df['Pos'].shift(1) == 0.0)].copy()
our_exits = df[(df['Pos'] == 0.0) & (df['Pos'].shift(1) == 1.0)].copy()

# Target entries (BUY) and exits (SELL)
tgt_entries = target[target['Action'] == 'BUY'].copy()
tgt_exits = target[target['Action'] == 'SELL'].copy()

print("=== ENTRY TIMING COMPARISON ===")
print(f"Target entries: {len(tgt_entries)}, Our entries: {len(our_entries)}")
print(f"\n{'Target Date':<14} {'Our Nearest':<14} {'Lag (days)':<12} {'Target Price':<14} {'Our Price':<14}")
print("-" * 70)

entry_lags = []
for _, tgt_row in tgt_entries.iterrows():
    tgt_date = tgt_row['Date']
    # Find nearest our entry within +/- 180 days
    diffs = (our_entries.index - tgt_date).days
    mask = np.abs(diffs) < 180
    if mask.any():
        nearest_idx = np.abs(diffs[mask]).argmin()
        our_date = our_entries.index[mask][nearest_idx]
        lag = (our_date - tgt_date).days
        our_price = our_entries.loc[our_date, 'Close']
        entry_lags.append(lag)
        print(f"{tgt_date.strftime('%Y-%m-%d'):<14} {our_date.strftime('%Y-%m-%d'):<14} {lag:>+5d}       {tgt_row['Price']:<14.2f} {our_price:<14.2f}")
    else:
        entry_lags.append(None)
        print(f"{tgt_date.strftime('%Y-%m-%d'):<14} {'NO MATCH':<14} {'N/A':<12} {tgt_row['Price']:<14.2f} {'N/A':<14}")

valid_lags = [l for l in entry_lags if l is not None]
print(f"\nEntry lag: Mean={np.mean(valid_lags):+.1f}d, Median={np.median(valid_lags):+.1f}d")

print("\n=== EXIT TIMING COMPARISON ===")
print(f"Target exits: {len(tgt_exits)}, Our exits: {len(our_exits)}")
print(f"\n{'Target Date':<14} {'Our Nearest':<14} {'Lag (days)':<12} {'Target Price':<14} {'Our Price':<14}")
print("-" * 70)

exit_lags = []
for _, tgt_row in tgt_exits.iterrows():
    tgt_date = tgt_row['Date']
    diffs = (our_exits.index - tgt_date).days
    mask = np.abs(diffs) < 180
    if mask.any():
        nearest_idx = np.abs(diffs[mask]).argmin()
        our_date = our_exits.index[mask][nearest_idx]
        lag = (our_date - tgt_date).days
        our_price = our_exits.loc[our_date, 'Close']
        exit_lags.append(lag)
        print(f"{tgt_date.strftime('%Y-%m-%d'):<14} {our_date.strftime('%Y-%m-%d'):<14} {lag:>+5d}       {tgt_row['Price']:<14.2f} {our_price:<14.2f}")
    else:
        exit_lags.append(None)
        print(f"{tgt_date.strftime('%Y-%m-%d'):<14} {'NO MATCH':<14} {'N/A':<12} {tgt_row['Price']:<14.2f} {'N/A':<14}")

valid_exit_lags = [l for l in exit_lags if l is not None]
print(f"\nExit lag: Mean={np.mean(valid_exit_lags):+.1f}d, Median={np.median(valid_exit_lags):+.1f}d")

# Identify the source of lag per component
print("\n\n=== LAG SOURCE ANALYSIS ===")
print("Our system has these lag sources:")
print("1. Ichimoku periods: p1=20, p2=60, p3=120 (rolling lookback windows)")
print("2. SuperSmoother length=7 (introduces ~3-4 bars delay)")
print("3. Confirmation bars=2 (2 days minimum)")
print("4. Min hold=30 days (prevents early exit)")
print("5. ER lookback=14 days")
print("6. IMO_Std rolling=30 days")

# Show what IMO/ER looked like at each target entry date
print("\n=== IMO/ER VALUES AT TARGET ENTRY DATES ===")
for _, tgt_row in tgt_entries.iterrows():
    tgt_date = tgt_row['Date']
    if tgt_date in df.index:
        row = df.loc[tgt_date]
        std = row['IMO_Std']
        thresh = std * 0.40 if not pd.isna(std) else 'N/A'
        print(f"  {tgt_date.strftime('%Y-%m-%d')}: IMO={row['IMO']:.4f}, ER={row['ER']:.4f}, Std={std:.4f}, Threshold={thresh:.4f if isinstance(thresh, float) else thresh}")
    else:
        print(f"  {tgt_date.strftime('%Y-%m-%d')}: Date not in data")

print("\n=== IMO/ER VALUES AT TARGET EXIT DATES ===")
for _, tgt_row in tgt_exits.iterrows():
    tgt_date = tgt_row['Date']
    if tgt_date in df.index:
        row = df.loc[tgt_date]
        print(f"  {tgt_date.strftime('%Y-%m-%d')}: IMO={row['IMO']:.4f}, ER={row['ER']:.4f}, Pos={row['Pos']}")
    else:
        print(f"  {tgt_date.strftime('%Y-%m-%d')}: Date not in data")
