import pandas as pd
from src.ichimoku_quant.data import fetch_btc_data
from src.ichimoku_quant.features import generate_ichimoku_features
from src.ichimoku_quant.strategy import generate_signals

df = fetch_btc_data()
df = generate_ichimoku_features(df)
df = generate_signals(df)

# State changes analysis
changes = df[df['Pos'].diff().ne(0)].dropna()
rapid = (changes.index.to_series().diff().dt.days < 14).sum()

print(f"=== NOISE METRICS ===")
print(f"Total state changes: {len(changes)}")
print(f"Rapid flips (<14 days): {rapid}")
print(f"Rapid flips (<7 days): {(changes.index.to_series().diff().dt.days < 7).sum()}")

inter_signal_gaps = changes.index.to_series().diff().dt.days.dropna()
print(f"\nGaps between signals:")
print(f"  Min: {inter_signal_gaps.min():.0f} days")
print(f"  Median: {inter_signal_gaps.median():.0f} days")
print(f"  Max: {inter_signal_gaps.max():.0f} days")

print(f"\nAll signal events:")
print(changes[['Pos', 'Regime']].to_string())
