import pandas as pd
from src.ichimoku_quant.data import fetch_btc_data
from src.ichimoku_quant.features import generate_ichimoku_features
from src.ichimoku_quant.strategy import generate_signals
from src.ichimoku_quant.backtest import run_backtest, calculate_metrics

df = fetch_btc_data()
df = generate_ichimoku_features(df)

df['IMO_Raw'] = (df['S_TK'] + df['S_Cloud'] + df['S_Future'] + df['S_Chikou']) / 4.0
df['IMO'] = df['IMO_Raw'] # Revert to raw
def binary_sig(data):
    pos = 0.0; sigs=[]
    for imo in data['IMO']:
        if pd.isna(imo): sigs.append(0.0); continue
        if pos == 0.0 and imo > 0.15: pos = 1.0
        elif pos == 1.0 and imo < -0.15: pos = 0.0
        sigs.append(pos)
    d = data.copy()
    d['Pos'] = sigs
    return d

df_orig = binary_sig(df)
met_orig = calculate_metrics(run_backtest(df_orig))
print(f"Original Binary Return: {met_orig.get('Total Return (%)', 0):,.2f}% | Sharpe: {met_orig.get('Sharpe Ratio', 0):.2f} | Trades: {met_orig.get('Number of Trades', 0)}")

# Test 2: Raw IMO + Scaling
df_scaled = generate_signals(df) # Uses strategy.py logic (0.15 / 0.60 / 0.20 / -0.15)
met_scaled = calculate_metrics(run_backtest(df_scaled))
print(f"Scaled Return: {met_scaled.get('Total Return (%)', 0):,.2f}% | Sharpe: {met_scaled.get('Sharpe Ratio', 0):.2f} | Trades: {met_scaled.get('Number of Trades', 0)}")

