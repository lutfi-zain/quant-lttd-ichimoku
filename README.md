# Ichimoku Quantitative Optimization & Systematic Trend-Following System

[![Performance](https://img.shields.io/badge/Total%20Return-109%2C368.07%25-brightgreen?style=for-the-badge)](https://github.com/lutfi-zain/ichimoku)
[![Sharpe Ratio](https://img.shields.io/badge/Sharpe%20Ratio-1.47-blue?style=for-the-badge)](https://github.com/lutfi-zain/ichimoku)
[![Drawdown](https://img.shields.io/badge/Max%20Drawdown--48.17%25-red?style=for-the-badge)](https://github.com/lutfi-zain/ichimoku)
[![Trades](https://img.shields.io/badge/Total%20Trades-14-orange?style=for-the-badge)](https://github.com/lutfi-zain/ichimoku)

This repository implements a production-grade, mathematically rigorous optimization of the traditional Ichimoku Kinko Hyo trading system, tailored specifically for Bitcoin (BTC-USD) trend-following. By translating subjective visual lines into stationary, normalized mathematical features and applying a multi-layered statistical gating architecture, the strategy isolates true market momentum while filtering out whipsaw-inducing noise.

---

## 📸 Dashboard Preview

### Sleek, Data-Dense Obsidian Ledger Theme
![Dashboard Main View](docs/dashboard_preview.png)

### Synchronized Multi-Pane Analytics (Maximized View)
![Maximized Chart Panels](docs/dashboard_maximized_charts.png)

### Price Chart & Execution Signal Focus (Maximized View)
![Maximized Price Focus](docs/dashboard_maximized_price.png)

---

## 🔬 Economic Hypothesis & Research Motivation

The traditional Ichimoku Kinko Hyo system relies on midpoint-of-range calculations:
$$\text{Midpoint} = \frac{\max(\text{High}, N) + \min(\text{Low}, N)}{2}$$
While midpoint-of-range estimators are robust, non-linear smoothers (conceptually similar to rank-order filters), they suffer from two critical flaws when applied to 24/7 crypto markets:
1. **Parameter Mismatch**: The default settings $(9, 26, 52)$ were calibrated for a 6-day Japanese stock week of the 1930s. They under-sample the 24/7 continuous cryptocurrency market.
2. **Midpoint Step-Function Lag**: Midpoint adjustments occur in discrete steps when new extreme highs or lows are reached. This creates a step-function that induces execution lag in fast directional breakouts, and triggers rapid whipsaws during consolidation.

Our system solves these flaws by **normalizing** all Ichimoku components using Average True Range (ATR) to enforce stationarity, and passing the signals through **five sequential mathematical gates** to block false entries without increasing execution lag.

---

## 🏗️ Multi-Principle Denoising Gating System

Signals are filtered through a multi-layered gating architecture designed to prevent over-trading and whipsaw execution:

```
                      ┌────────────────────────────────┐
                      │    Layer 1: SPECTRAL FILTER    │
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

### Layer 1: Spectral Filtering (Ehlers SuperSmoother)
To eliminate high-frequency noise from raw price indicators without the lag penalty of moving averages, we apply a 2-pole Infinite Impulse Response (IIR) filter. The difference equation is:
$$y_t = c_1 \cdot \frac{x_t + x_{t-1}}{2} + c_2 \cdot y_{t-1} + c_3 \cdot y_{t-2}$$
where the constants are derived from the cutoff period $P = 7$ and damping factor:
$$a = \exp\left(-\frac{\sqrt{2}\pi}{P}\right), \quad b = 2a\cos\left(\frac{\sqrt{2}\pi}{P}\right)$$
$$c_2 = b, \quad c_3 = -a^2, \quad c_1 = 1 - c_2 - c_3$$

### Layer 2: Fractal Family (Kaufman Efficiency Ratio)
Measures trend efficiency (Net Displacement / Sum of Absolute Daily Changes) over a 14-day rolling window:
$$ER_t = \frac{|P_t - P_{t-14}|}{\sum_{i=0}^{13} |P_{t-i} - P_{t-i-1}|}$$
Entry signals are blocked if the market is consolidating or mean-reverting ($ER_t < 0.25$).

### Layer 3: Information Theory (Shannon Entropy Noise Gate)
Measures rolling randomness of the return distribution over a 15-day window using 6 empirical bins:
$$H(X) = -\sum_{i=1}^{6} p(x_i) \log_2 p(x_i)$$
Where $p(x_i)$ is the probability of returns falling into bin $i$. Entries are blocked if the return series is highly chaotic ($H(X) > 2.271$), indicating a lack of structured trend direction.

### Layer 4: Trend Boundary (Ichimoku Cloud Gate)
Price must trade above the bottom of the Ichimoku Cloud ($Close_t \ge \min(SpanA_t, SpanB_t)$). This blocks trend-following long attempts during systemic bear markets.

### Layer 5: Signal Confirmation & Persistence
Requires entry signals to persist for $N = 2$ consecutive days to filter out short-term spike noise, while exits trigger instantly ($N = 1$) to minimize exit lag once a trend breaks down.

---

## 📈 Performance Summary (10-Year Backtest)

The backtest simulations run on daily Bitcoin OHLC data from **2016 to 2026** (using 2015 for rolling indicator warm-up). All trades are constrained by a **0.10% transaction cost** (10 bps slippage/commission per side) on full capital.

| Metric | Buy & Hold BTC | Baseline Strategy (No Entropy Gate) | Fully Denoised (Entropy + Cloud Gate) |
| :--- | :--- | :--- | :--- |
| **Total Return (%)** | 20,009.78% | 76,052.90% | **109,368.07%** |
| **Annualized Return (%)** | - | 70.38% | **73.37%** |
| **Annualized Volatility (%)** | - | 50.10% | **49.75%** |
| **Max Drawdown (%)** | -83.40% | -48.54% | **-48.17%** |
| **Sharpe Ratio** | 1.03 | 1.40 | **1.47** |
| **Total Trades** | 1.0 | 18.0 | **14.0** *(22% lower fee friction)* |

---

## 📊 Statistical Validation & Rigor

To verify that the strategy's historical performance represents a genuine structural edge rather than a statistical artifact of data mining, we subjected the Ichimoku Momentum Oscillator (IMO) and strategy returns to a suite of statistical tests:

### 1. Signal Stationarity (ADF Test)
A stationary signal is necessary for fixed thresholds to remain valid.
* **Null Hypothesis ($H_0$):** The IMO series is non-stationary (contains a unit root).
* **Test Statistic:** `-7.1735`
* **p-value:** `2.7655e-10`
* **Result:** **Reject $H_0$**. Bounding the signal using the hyperbolic tangent ($\tanh$) successfully forces stationarity, ensuring long-term parameter validity.

### 2. Regime Divergence (Kolmogorov-Smirnov Test)
Verifies if the strategy successfully segments the market into distinct return regimes.
* **Null Hypothesis ($H_0$):** 10-day forward returns for bullish and bearish signal states come from the same distribution.
* **KS Statistic:** `0.0626`
* **p-value:** `2.3039e-03`
* **Result:** **Reject $H_0$**. The return distributions under bullish and bearish signals are statistically distinct.

### 3. Mean Return Significance (Welch's t-test)
Confirms positive expectancy during active trade regimes.
* **Null Hypothesis ($H_0$):** The mean 10-day forward return of bullish signals is $\le 0$.
* **Mean Return:** `+2.51%` per 10-day window
* **t-statistic:** `9.9006`
* **p-value:** `6.9220e-23`
* **Result:** **Reject $H_0$**. Positive expected return during bullish regimes is highly significant.

### 4. Bootstrap Confidence Intervals (FAT-Tail Check)
Since crypto returns exhibit fat tails, we bootstrapped 10-day forward returns ($B = 10,000$ resamples) without assuming normality:
* **95% Confidence Interval:** `[+2.01%, +3.01%]`
* **Result:** The entire interval is strictly positive, verifying resilience against outlier-driven performance skew.

### 5. Bonferroni Multiple Testing Correction
Because we engineered multiple sub-components ($S_{TK}$, $S_{Cloud}$, $S_{Future}$, $S_{Chikou}$), we adjusted the significance threshold ($\alpha_{adj} = 0.05 / 4 = 0.0125$) to prevent p-hacking:
* All 4 component signals achieved individual p-values $\le 10^{-8}$, surviving the Bonferroni penalty.

---

## 🛡️ Dynamic Exit Mechanics & Regime Adaptation

The core engine implements a two-stage adaptive exit model to balance return preservation and draw-down defense:
1. **S_Chikou Momentum Gate**: Exits are triggered if the 60-day momentum representation ($S_{Chikou}$) drops below `-0.30`.
2. **Dynamic Cloud Immunity**: Under extreme bull markets, momentum dips are often noise. If the close price sits above the maximum cloud boundary ($P_t \ge \max(SpanA, SpanB)$) and volatility is stable, the Chikou exit is temporarily bypassed.
3. **Macro Crash Gate**: If the 30-day Rate of Change (ROC) drops below `-20%` ($ROC_{30} < -0.20$), cloud immunity is instantly revoked, forcing immediate exit to shield capital. This dynamic successfully cut the maximum drawdown from the market's **-83.40%** to **-48.17%**.

---

## 📁 Repository Structure

```text
ichimoku/
├── pyproject.toml              # Dependency requirements
├── main.py                     # CLI pipeline wrapper
├── src/
│   ├── cli.py                  # CLI parsing and backtesting endpoints
│   └── ichimoku_quant/         # Core quantitative modules
│       ├── __init__.py
│       ├── data.py             # Caching data downloader
│       ├── features.py         # Rolling formula math & Ehlers/Entropy calculations
│       ├── strategy.py         # Signal logic loop & gating rules
│       ├── backtest.py         # Vectorized backtest simulator
│       ├── server.py           # FastAPI backend server
│       └── visuals.py          # Plotly dashboard renderer
├── web/                        # React / Vite frontend UI
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx             # React dashboard charts & state
│   │   ├── index.css           # Obsidian dark mode theme
│   │   └── main.jsx
│   └── index.html
├── docs/                       # Visual assets & screenshots
└── research/                   # Exploratory notebooks, parameter sweeps & statistical scripts
```

---

## 🚀 Getting Started

### 1. Setup Backend Environment
Ensure you have Python 3.10+ installed.

```bash
# Clone the repository
git clone https://github.com/lutfi-zain/ichimoku.git
cd ichimoku

# Install backend dependencies using Poetry
poetry install
```

### 2. Setup Frontend Environment
Ensure you have Bun installed.

```bash
cd web
bun install
```

### 3. Running System Locally

* **Start Backend API Server:**
  ```bash
  poetry run python src/ichimoku_quant/server.py
  ```

* **Start Frontend Dev Server:**
  ```bash
  cd web
  bun run dev
  ```
  Open [http://localhost:5173](http://localhost:5173) in your browser.

* **Run Command-Line Backtest CLI:**
  ```bash
  poetry run python src/cli.py backtest --start 2015-01-01
  ```

---

## ⚠️ Quant Caveats & The Haircut Rule

Before deploying capital to this strategy, consider these systemic risks:
* **The Haircut Rule**: Backtests are optimized representations of history. In production, we expect a **30% to 50% haircut** on the Sharpe ratio (translating to a live target Sharpe of **0.75 - 1.00**).
* **Execution & Timing Risk**: The backtest assumes execution at the UTC daily close. Intraday execution delay or executing during low-liquidity hours will alter returns.
* **Non-Stationarity**: While the IMO signal is stationary, the underlying market regime distributions drift. There is no guarantee that future consolidation periods will match the entropy profile of 2018 or 2022.
