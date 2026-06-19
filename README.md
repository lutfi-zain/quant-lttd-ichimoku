# Ichimoku Quantification System

A rigorous data-science approach to quantifying the Ichimoku Kinko Hyo indicator for Bitcoin trend-following.

## Project Structure
This project has been rebuilt into a modular, production-ready Python package:
```text
ichimoku/
├── pyproject.toml              # Project dependencies
├── src/
│   ├── cli.py                  # Main entrypoint for CLI operations
│   └── ichimoku_quant/         # Core trading & research modules
│       ├── data.py             # Fetch OHLC data (Bitview API)
│       ├── features.py         # Compute Ichimoku & IMO oscillators
│       ├── strategy.py         # Signal generation (Long/Flat)
│       ├── backtest.py         # Vectorized backtester & metrics
│       └── visuals.py          # Dashboard generation (Plotly HTML)
├── tests/                      # Unit testing suite (pytest)
└── research/                   # Exploratory scripts and statistical tests
```

## Setup
It is recommended to use the standard `.venv` virtual environment for isolation. 

```bash
# Ensure you are using Python 3.10+
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # OR pip install pandas numpy scipy plotly requests
```

## Usage
The core library operates through the CLI. Ensure your `PYTHONPATH` points to `src/` when running.

### 1. Run a Quick Backtest
Prints out all critical strategy metrics without generating files:
```bash
PYTHONPATH=src .venv/bin/python src/cli.py backtest --start 2016-01-01 --tc 0.001
```

### 2. Generate the Visual Dashboard
Generates an interactive HTML dashboard containing the Equity Curve, Drawdowns, and the IMO Oscillator:
```bash
PYTHONPATH=src .venv/bin/python src/cli.py dashboard
```
The output will be saved to `tmp/dashboard.html`.

You can view it locally via the built-in HTTP server:
```bash
python3 -m http.server 8080 --directory tmp
```
Then open `http://localhost:8080/dashboard.html` in your browser.

## The IMO Strategy (Ichimoku Multi-Component Oscillator)
Traditional Ichimoku analysis is visual and subjective. The **IMO** strategy translates it into a stationary, mean-reverting numerical oscillator bounds to `[-1.0, 1.0]`.

1. **S_TK:** Tenkan-sen vs Kijun-sen distance.
2. **S_Cloud:** Price vs Kumo (Cloud) resistance/support distance.
3. **S_Future:** Future Senkou Span A vs B thickness/twist.
4. **S_Chikou:** Current Price vs Price 26 periods ago.

By normalizing these distances with the **14-day Average True Range (ATR)** and bounding them via a `tanh` function, we obtain a robust quant signal.
* **Bullish Regime:** `IMO > 0.15`
* **Bearish Regime:** `IMO < -0.15`

*See `research/statistical_tests.py` or the `statistical_tests.md` artifact for a detailed CRISP-DM statistical breakdown.*
