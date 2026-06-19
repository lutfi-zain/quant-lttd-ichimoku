# AGENTS.md

## What is this

Ichimoku quantification project. Goal: measure Ichimoku indicator performance as a trend-following system for Bitcoin.

## Tech decisions (confirmed)

- **Language:** Python (primary)
- **Charts:** Python can do this — use `matplotlib`, `plotly`, or `mplfinance` for Ichimoku visualization. No separate frontend needed initially.
- **Future:** React frontend with charting may be added later, but not now.

## Project phase

Greenfield — no code yet. Setting up from scratch.

## Evolution

Evolve local / global AGENTS.md by spawning subagents periodically to learn from current session, then propose amandemet. The goal is to not repeating the same step every time new session spawns.


## Learnings

- **[2026-06-20]** Avoid Chikou exits on low-volatility consolidations by using a dynamic cloud immunity gate (`Close >= cloud_max` and `IMO >= -0.25`) paired with a crash gate (`30-day ROC >= -0.20` to prevent holding through bear markets). This resolves the 2020 whipsaw exits while increasing returns to 86,714.48% and reducing trades to 13. (Evidence: `strategy.py`, `features.py` changes)
- **[2026-06-20]** ATR normalization of indicators makes them hyper-sensitive to echo effects during low-volatility sideways ranges. Always pair ATR-normalized indicators with absolute price momentum (ROC) gates to filter low-volatility noise. (Evidence: Chikou echo analysis on July/September 2020)
- **[2026-06-20]** In backtest simulations with shifted/lagged indicators (like shifted Senkou Spans), do not skip NaN rows globally at the top of the loop as it delays history and distorts returns. Handle NaNs locally or dynamically per field. (Evidence: NaN-skipping mismatch in `tmp/test_er_exit_gate.py:36` vs production `strategy.py:57` fix)

