# AGENTS.md

## What is this

Ichimoku quantification project. Goal: measure Ichimoku indicator performance as a trend-following system for Bitcoin.

## Tech decisions (confirmed)

- **Language:** Python (primary codebase)
- **Dependencies:** `pandas`, `numpy`, `yfinance`, `plotly`, `matplotlib`
- **TradingView Integration:** Pine Script v6 strategy compiled on TradingView browser interface.
- **Pasting Automation:** Custom helper script `tmp/sync_pinescript_to_tv.py` uses simulated `ClipboardEvent('paste')` with temporary window buffer (`window.__temp_pine_code`) to bypass Monaco Editor's auto-indentation formatting bugs.
- **Verification/Tests:** Fast validation using `python -m pytest` or `PYTHONPATH=. pytest`.

## Project phase

**Production & Optimization Phase**
The core backtesting engine, feature generators, strategy parameters, HTML visualizer, and Pine Script v6 TradingView script are fully implemented, verified, and synchronized.

## Codebase Architecture

The project follows a modular structure under `src/ichimoku_quant/`:
- [data.py](./src/ichimoku_quant/data.py): Handles historical daily Bitcoin data fetching via yfinance.
- [features.py](./features.py): Generates technical indicators (Ichimoku Spans, Ehler's SuperSmoother, normalized TK Cross, normalized S_Cloud, normalized S_Future, smoothed S_Chikou, stdev IMO, Efficiency Ratio, Shannon Entropy, and price ROC).
- [strategy.py](./strategy.py): Implements entry/exit gates (low entropy, high efficiency, cloud confirmation, minimum holding period of 10 days, price ROC crash gate, and dynamic cloud immunity).
- [backtest.py](./backtest.py): Simulates daily equity growth, returns, drawdowns, and Sharpe ratios.
- [visuals.py](./visuals.py): Generates rich interactive HTML charts and dashboard files stored in `tmp/`.
- [ichimoku_quant_v6.pinescript](./ichimoku/ichimoku_quant_v6.pinescript): The TradingView-compatible Pine Script v6 strategy utilizing robust state representations.

## Evolution

Evolve local / global AGENTS.md by spawning subagents periodically to learn from current session, then propose amandemet. The goal is to not repeating the same step every time new session spawns.

## Learnings

- **[2026-06-20]** Avoid Chikou exits on low-volatility consolidations by using a dynamic cloud immunity gate (`Close >= cloud_max` and `IMO >= -0.30`) paired with a crash gate (`30-day ROC >= -0.20` to prevent holding through bear markets). This resolves the 2020 whipsaw exits while increasing returns to 86,714.48% and reducing trades to 13. (Evidence: `strategy.py`, `features.py` changes)
- **[2026-06-20]** ATR normalization of indicators makes them hyper-sensitive to echo effects during low-volatility sideways ranges. Always pair ATR-normalized indicators with absolute price momentum (ROC) gates to filter low-volatility noise. (Evidence: Chikou echo analysis on July/September 2020)
- **[2026-06-20]** In backtest simulations with shifted/lagged indicators (like shifted Senkou Spans), do not skip NaN rows globally at the top of the loop as it delays history and distorts returns. Handle NaNs locally or dynamically per field. (Evidence: NaN-skipping mismatch in `tmp/test_er_exit_gate.py:36` vs production `strategy.py:57` fix)
- **[2026-06-20]** Monaco Editor Auto-Indent Mangle dapat dihindari dengan mem-paste kode secara utuh menggunakan event `paste` native (`ClipboardEvent` + `DataTransfer`) setelah menumpuk potongan kode di variabel `window`, serta merestrukturisasi fungsi bersarang multi-baris menjadi inline ternary expression. (Evidence: `tmp/sync_pinescript_to_tv.py`, `ichimoku_quant_v6.pinescript` compiler error fix)
- **[2026-06-20]** Deviasi minor eksekusi transaksi antara Python (yfinance) dan TradingView wajar terjadi karena perbedaan pencatatan harga close harian (timezone UTC bursa vs Yahoo Finance). Hal ini memengaruhi filter sensitif (seperti Shannon Entropy dan Cloud Gate) pada batas borderline, yang pada kasus April 2022 justru menguntungkan karena memblokir trade rugi.
- **[2026-06-20]** Monaco Editor di TradingView mengabaikan event pembersihan keystroke (`Ctrl+A` + `Backspace`) yang dikirim melalui `dispatchEvent` JS biasa. Solusi andal 100% adalah menggunakan native CLI keyboard commands dari `agent-browser` (yaitu `agent-browser click ".monaco-editor" && agent-browser press Control+a && agent-browser press Backspace`).
- **[2026-06-20]** Di TradingView, parameter `linewidth` pada fungsi `plot` harus berupa integer (`literal int` atau `input int`), bukan float. Memberikan nilai float seperti `1.5` akan memicu compiler error `CE10123`.
- **[2026-06-20]** Untuk membuat visualisasi terpadu backend Python dan frontend React, gunakan FastAPI dengan CORS middleware aktif, simulasikan data timeseries ApexCharts dengan penonaktifan animasi agar INP responsif, serta sematkan TradingView iframe widget menggunakan element DOM dinamis.

## Design Context (from PRODUCT.md)

- **Register**: `product` (Interactive parameter optimization & backtest dashboard)
- **Brand Personality**: High-End Corporate Dark Mode (Charcoal background, neon cyan/teal accents, bold Switzer & Geist Mono typography)
- **Key Principles**: Utilitarian density & stacked charts, monospace numeric alignment, flat & layered (no drop shadows/glassmorphism), restrained accent color usage (≤ 10%).
- **Anti-references**: Cyberpunk glow excess, warm "SaaS-cream" palettes, nested card grids, all-caps eyebrows on every section.

