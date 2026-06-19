# Ichimoku Quantitative Quantification & Strategy System

[![Performance](https://img.shields.io/badge/Total%20Return-79%2C426.78%25-brightgreen?style=for-the-badge)](https://github.com/lutfi-zain/ichimoku)
[![Sharpe Ratio](https://img.shields.io/badge/Sharpe%20Ratio-1.57-blue?style=for-the-badge)](https://github.com/lutfi-zain/ichimoku)
[![Drawdown](https://img.shields.io/badge/Max%20Drawdown--48.49%25-red?style=for-the-badge)](https://github.com/lutfi-zain/ichimoku)
[![Trades](https://img.shields.io/badge/Total%20Trades-18.0-orange?style=for-the-badge)](https://github.com/lutfi-zain/ichimoku)

A rigorous mathematical and algorithmic system designed to quantify and optimize the traditional Ichimoku Kinko Hyo trading system for Bitcoin trend-following. By translating subjective visual lines into normalized, stationary mathematical features, the strategy eliminates trading noise and lag.

> [!NOTE]
> This system is built using the **4-Layer Development Framework** from the `lz-technical-indicator-architect` methodology, stacking four distinct indicator families to filter market noise without adding execution lag.

---

## 🏗️ Multi-Principle Architecture

The strategy operates across four robust statistical layers:

```
                      ┌────────────────────────────────┐
                      │    Layer 1: INPUT PROCESSING   │
                      │ Ehlers SuperSmoother Filter    │
                      └───────────────┬────────────────┘
                                      ▼
                      ┌────────────────────────────────┐
                      │    Layer 2: FRACTAL GATING     │
                      │   Kaufman Efficiency Ratio     │
                      └───────────────┬────────────────┘
                                      ▼
                      ┌────────────────────────────────┐
                      │   Layer 3: INFORMATION THEORY  │
                      │   Shannon Entropy Noise Gate   │
                      └───────────────┬────────────────┘
                                      ▼
                      ┌────────────────────────────────┐
                      │    Layer 4: TREND BOUNDARY     │
                      │      Ichimoku Cloud Gate       │
                      └───────────────┬────────────────┘
                                      ▼
                      ┌────────────────────────────────┐
                      │    Layer 5: SIGNAL GENERATION  │
                      │    Confirmation & Exit Logic   │
                      └────────────────────────────────┘
```

1. **Layer 1: Spectral Filtering (Ehlers SuperSmoother)**
   * Removes high-frequency noise from raw price indicators using a 2-pole Infinite Impulse Response (IIR) filter without adding the lag associated with moving averages.
2. **Layer 2: Fractal Family (Kaufman Efficiency Ratio)**
   * Measures trend efficiency (Net Displacement / Sum of Absolute Daily Changes). Sinyal entry diblokir jika pasar berada dalam fase konsolidasi/mean-reverting ($ER < 0.25$).
3. **Layer 3: Entropy & Information Family (Shannon Entropy)**
   * Computes the rolling randomness of return distributions. If return sequences are highly chaotic and random ($Entropy > 2.271$), entry signals are blocked to prevent whipsaws.
4. **Layer 4: Smoothing & Regression (Ichimoku Cloud Gate)**
   * Price must trade above the bottom of the Ichimoku Cloud ($Close_t \ge \min(SpanA_t, SpanB_t)$). This prevents catching falling knives during bearish downtrends.

---

## 📈 Performance Summary (10-Year Backtest)

The backtest runs on Bitcoin daily OHLC data from 2016 to 2026 with a transaction cost constraint of **0.1% per trade** (10 bps slippage/commission).

| Metric | Buy & Hold BTC | Baseline Strategy | Fully Denoised (Entropy + Cloud Gate) |
| :--- | :--- | :--- | :--- |
| **Total Return (%)** | 14,446.87% | 71,696.20% | **79,426.78%** |
| **Annualized Return (%)** | - | 74.62% | **75.20%** |
| **Annualized Volatility (%)** | 70.12% | 48.66% | **47.84%** |
| **Max Drawdown (%)** | -83.40% | -48.49% | **-48.49%** |
| **Sharpe Ratio** | 1.05 | 1.53 | **1.57** |
| **Total Trades** | 1.0 | 24.0 | **18.0** *(25% lower fee friction)* |

---

## 📁 Repository Structure

```text
ichimoku/
├── pyproject.toml              # Poetry packaging & dependencies
├── src/
│   ├── cli.py                  # Command line interface
│   └── ichimoku_quant/         # Core package
│       ├── __init__.py
│       ├── data.py             # Caching data fetcher
│       ├── features.py         # Rolling formula math
│       ├── strategy.py         # Signal logic loops
│       ├── backtest.py         # Backtest runner & metrics
│       └── visuals.py          # Interactive Plotly engine
├── tests/                      # Pytest verification suites
└── research/                   # Exploratory scripts & statistical tests
```

---

## 🚀 Getting Started

### 1. Setup Environment
Ensure you have Python 3.10+ installed.

```bash
# Clone the repository
git clone https://github.com/lutfi-zain/ichimoku.git
cd ichimoku

# Install dependencies using Poetry
poetry install
# Or fallback to pip:
pip install pandas numpy scipy plotly requests
```

### 2. Command Line Usage

Set the `PYTHONPATH` variable pointing to `src/` when executing commands:

* **Run Backtest:** Runs vectorized backtest calculations and prints summary metrics.
  ```bash
  PYTHONPATH=src poetry run python src/cli.py backtest --start 2016-01-01 --tc 0.001
  ```

* **Generate Dashboard:** Generates an interactive dashboard containing cumulative curves, drawdowns, and indicators.
  ```bash
  PYTHONPATH=src poetry run python src/cli.py dashboard
  ```
  The dashboard will be saved at `tmp/dashboard.html`.

* **Serve Locally:** Run a local server to view the dashboard:
  ```bash
  python3 -m http.server 8080 --directory tmp
  ```
  Then open [http://localhost:8080/dashboard.html](http://localhost:8080/dashboard.html) in your browser.
