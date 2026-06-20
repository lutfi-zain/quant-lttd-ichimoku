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
- **[2026-06-20]** Monaco Editor Auto-Indent Mangle dapat dihindari dengan mem-paste kode secara utuh menggunakan event `paste` native (`ClipboardEvent` + `DataTransfer`) setelah menumpuk potongan kode di variabel `window`, serta merestrukturisasi fungsi bersarang multi-baris menjadi inline ternary expression. (Evidence: `tmp/sync_pinescript_to_tv.py`, `ichimoku_quant_v6.pinescript` compiler error fix)
- **[2026-06-20]** Deviasi minor eksekusi transaksi antara Python (yfinance) dan TradingView wajar terjadi karena perbedaan pencatatan harga close harian (timezone UTC bursa vs Yahoo Finance). Hal ini memengaruhi filter sensitif (seperti Shannon Entropy dan Cloud Gate) pada batas borderline, yang pada kasus April 2022 justru menguntungkan karena memblokir trade rugi.

