import argparse
import sys
from ichimoku_quant import fetch_btc_data, generate_ichimoku_features, generate_signals, run_backtest, calculate_metrics
from ichimoku_quant.visuals import generate_dashboard_html

def main():
    parser = argparse.ArgumentParser(description="Ichimoku Quant Trading System")
    parser.add_argument("action", choices=["backtest", "dashboard"], help="Action to perform")
    parser.add_argument("--start", default="2018-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--tc", type=float, default=0.001, help="Transaction cost per trade")
    
    args = parser.parse_args()
    
    print("Fetching data...")
    df = fetch_btc_data(start_date=args.start)
    
    print("Generating features...")
    df = generate_ichimoku_features(df)
    
    print("Generating signals...")
    df = generate_signals(df)
    
    print("Running backtest...")
    df = run_backtest(df, transaction_cost=args.tc)
    
    metrics = calculate_metrics(df)
    
    if args.action == "backtest":
        print("\n--- BACKTEST METRICS ---")
        for k, v in metrics.items():
            print(f"{k}: {v:,.2f}")
            
    elif args.action == "dashboard":
        output_file = "tmp/dashboard.html"
        generate_dashboard_html(df, metrics, output_path=output_file)
        print(f"\nDashboard generated at {output_file}")
        print("To view, run: python -m http.server 8080 --directory tmp")

if __name__ == "__main__":
    main()
