import sys
import os
import subprocess

from src.ichimoku_quant.data import fetch_btc_data
from src.ichimoku_quant.features import generate_ichimoku_features
from src.ichimoku_quant.strategy import generate_signals
from src.ichimoku_quant.backtest import run_backtest, calculate_metrics
from src.ichimoku_quant.visuals import generate_dashboard_html

def main():
    print("=== STARTING ICHIMOKU QUANT PIPELINE ===")
    
    # 1. Fetch data
    print("1. Fetching historical BTC data from yfinance...")
    df = fetch_btc_data()
    
    # 2. Generate features
    print("2. Generating technical indicators & denoising features...")
    df = generate_ichimoku_features(df)
    
    # 3. Generate strategy signals
    print("3. Evaluating strategy rules & gates...")
    df = generate_signals(df)
    
    # 4. Run backtest
    print("4. Executing backtest simulation (with transaction costs)...")
    df = run_backtest(df, transaction_cost=0.001)
    
    # 5. Calculate metrics
    print("5. Calculating performance metrics...")
    metrics = calculate_metrics(df)
    
    # 6. Print console summary
    print("\n" + "="*50)
    print("      STRATEGY PERFORMANCE METRICS SUMMARY")
    print("="*50)
    for k, v in metrics.items():
        if "Return" in k or "Drawdown" in k or "Volatility" in k or "Win Rate" in k:
            print(f"{k:<30} : {v:>10.2f}%")
        elif "Sharpe" in k or "Factor" in k:
            print(f"{k:<30} : {v:>10.2f}")
        elif "Trades" in k:
            print(f"{k:<30} : {int(v):>10}")
    print("="*50 + "\n")
    
    # 7. Generate interactive bento dashboard
    dashboard_path = "tmp/dashboard.html"
    print(f"6. Compiling interactive bento dashboard to {dashboard_path}...")
    generate_dashboard_html(df, metrics, output_path=dashboard_path)
    
    # 8. Open in Google Chrome as per project rules
    print("7. Launching Google Chrome to display the interactive dashboard...")
    abs_path = os.path.abspath(dashboard_path)
    try:
        subprocess.Popen(["google-chrome", f"file://{abs_path}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Dashboard opened successfully in Google Chrome.")
    except Exception as e:
        print(f"Warning: Could not launch Google Chrome: {e}. Opening with system default...")
        try:
            if sys.platform == 'darwin':
                subprocess.Popen(['open', abs_path])
            elif sys.platform.startswith('linux'):
                subprocess.Popen(['xdg-open', abs_path])
        except Exception:
            pass

if __name__ == "__main__":
    main()
