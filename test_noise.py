import pandas as pd
from src.ichimoku_quant.data import fetch_btc_data
from src.ichimoku_quant.features import generate_ichimoku_features
from src.ichimoku_quant.strategy import generate_signals

df = fetch_btc_data()
df = generate_ichimoku_features(df)
df = generate_signals(df)

df['Signal_Change'] = df['Pos'].diff()
changes = df[df['Signal_Change'] != 0].dropna()

# Count consecutive changes within N days
for days in [3, 7, 14]:
    rapid = (changes.index.to_series().diff().dt.days < days).sum()
    print(f"Signal flips within {days} days: {rapid} times")

print(f"\nTotal state changes: {len(changes)}")
