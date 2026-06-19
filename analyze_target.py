import pandas as pd
import numpy as np

# Analyze target signal characteristics
df = pd.read_csv('isps/isp-signals-btcusd-2026-06-13.csv', parse_dates=['Date'])
df = df.sort_values('Date')

print("=== TARGET CSV ANALYSIS ===")
print(f"Total trades: {len(df)}")
print()

# Inter-signal gaps
df['Days_Since_Last'] = df['Date'].diff().dt.days
print("Days between consecutive signals:")
print(df['Days_Since_Last'].describe())
print()

# Min gap
print(f"Min gap: {df['Days_Since_Last'].min()} days")
print(f"Max gap: {df['Days_Since_Last'].max()} days")
print(f"Median gap: {df['Days_Since_Last'].median():.0f} days")
print()

# Regime counts
print("Regime distribution:")
print(df['Regime'].value_counts())
print()

# Identify rapid transitions (< 30 days)
rapid = df[df['Days_Since_Last'] < 30]
print(f"\nRapid transitions (<30 days): {len(rapid)}")
print(rapid[['Date', 'Action', 'Regime', 'Days_Since_Last']])
