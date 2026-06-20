import pandas as pd
import numpy as np
from src.ichimoku_quant.data import fetch_btc_data
from src.ichimoku_quant.features import generate_ichimoku_features
from src.ichimoku_quant.backtest import run_backtest, calculate_metrics

df = fetch_btc_data()
df = generate_ichimoku_features(df)

# Rolling Stdev of IMO
df['IMO_Std'] = df['IMO'].rolling(30).std()

def adaptive_binary_sig(data):
    pos = 0.0; sigs=[]
    for imo, std in zip(data['IMO'], data['IMO_Std']):
        if pd.isna(imo) or pd.isna(std): sigs.append(0.0); continue
        # Dynamic Thresholds based on recent variance
        thresh = std * 0.5 # 0.5 standard deviations
        if pos == 0.0 and imo > thresh: pos = 1.0
        elif pos == 1.0 and imo < -thresh: pos = 0.0
        sigs.append(pos)
    d = data.copy()
    d['Pos'] = sigs
    return d

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

met_orig = calculate_metrics(run_backtest(binary_sig(df)))
met_adv = calculate_metrics(run_backtest(adaptive_binary_sig(df)))

print(f"Original Binary Return: {met_orig.get('Total Return (%)', 0):,.2f}% | Sharpe: {met_orig.get('Sharpe Ratio', 0):.2f} | Trades: {met_orig.get('Number of Trades', 0)}")
print(f"Adaptive Binary Return: {met_adv.get('Total Return (%)', 0):,.2f}% | Sharpe: {met_adv.get('Sharpe Ratio', 0):.2f} | Trades: {met_adv.get('Number of Trades', 0)}")
