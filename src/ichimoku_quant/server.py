from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np
import os
import uvicorn
from typing import Dict, Any, List

from ichimoku_quant.data import fetch_btc_data
from ichimoku_quant.features import generate_ichimoku_features
from ichimoku_quant.strategy import generate_signals
from ichimoku_quant.backtest import run_backtest, calculate_metrics

app = FastAPI(title="Ichimoku Quant Backtest API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BacktestRequest(BaseModel):
    # Ichimoku Periods
    p1: int = 20
    p2: int = 60
    p3: int = 120
    
    # Feature engineering lengths
    er_len: int = 14
    std_len: int = 30
    entropy_window: int = 15
    entropy_bins: int = 6
    
    # Strategy thresholds
    confirm_entry: int = 2
    confirm_exit: int = 1
    min_hold_days: int = 10
    er_entry: float = 0.25
    t_entry: float = 0.40
    chikou_thresh: float = -0.30
    immunity_thresh: float = 0.50
    entropy_thresh: float = 2.271
    imo_min_limit: float = -0.30
    imo_exit_bull: float = -0.30
    roc_gate_limit: float = -0.20
    transaction_cost: float = 0.001
    start_date: str = ""
    end_date: str = ""

def extract_trades(df: pd.DataFrame, chikou_thresh: float, imo_exit_bull: float) -> List[Dict[str, Any]]:
    trades = []
    in_position = False
    entry_idx = None
    trade_id = 1
    
    for i in range(1, len(df)):
        prev_pos = df['Active_Pos'].iloc[i-1]
        curr_pos = df['Active_Pos'].iloc[i]
        
        # Entry signal (Active_Pos goes from 0 to 1)
        if prev_pos == 0.0 and curr_pos == 1.0:
            in_position = True
            entry_idx = i
        
        # Exit signal (Active_Pos goes from 1 to 0) or end of dataset
        elif (prev_pos == 1.0 and curr_pos == 0.0) or (in_position and i == len(df) - 1):
            if in_position:
                exit_idx = i
                entry_row = df.iloc[entry_idx]
                exit_row = df.iloc[exit_idx]
                
                ret = (exit_row['Close'] - entry_row['Close']) / entry_row['Close'] * 100
                
                # Determine exit reason at trigger index (exit_idx - 1)
                last_pos_idx = exit_idx - 1
                row_last_pos = df.iloc[last_pos_idx]
                
                exit_reason = "Macro Exit"
                chikou_val = row_last_pos.get('S_Chikou', 0.0)
                imo_val = row_last_pos.get('IMO', 0.0)
                
                # If chikou was below threshold and not immune, it's a Chikou Exit
                if not pd.isna(chikou_val) and chikou_val < chikou_thresh:
                    exit_reason = "Chikou Exit"
                elif not pd.isna(imo_val) and imo_val < imo_exit_bull:
                    exit_reason = "Macro Exit (IMO)"
                
                trades.append({
                    "id": trade_id,
                    "entry_date": str(entry_row.name.date()) if isinstance(entry_row.name, pd.Timestamp) else str(entry_row.name),
                    "entry_price": float(entry_row['Close']),
                    "exit_date": str(exit_row.name.date()) if isinstance(exit_row.name, pd.Timestamp) else str(exit_row.name),
                    "exit_price": float(exit_row['Close']),
                    "return": float(ret),
                    "holding_days": int(exit_idx - entry_idx),
                    "exit_reason": exit_reason
                })
                trade_id += 1
                in_position = False
                
    return trades

@app.get("/api/status")
def get_status():
    cache_file = "tmp/btc_cache.csv"
    cached = os.path.exists(cache_file)
    date_range = {}
    if cached:
        try:
            df = pd.read_csv(cache_file, index_col='time', parse_dates=True)
            date_range = {
                "start": str(df.index[0].date()),
                "end": str(df.index[-1].date()),
                "bars": len(df)
            }
        except Exception:
            pass
    return {
        "status": "ready",
        "cached": cached,
        "date_range": date_range
    }

@app.post("/api/backtest")
def api_backtest(req: BacktestRequest):
    try:
        # 1. Fetch data
        df = fetch_btc_data()
        
        # 2. Generate features (recomputed if lengths differ)
        df_feat = generate_ichimoku_features(
            df,
            p1=req.p1,
            p2=req.p2,
            p3=req.p3,
            er_len=req.er_len,
            std_len=req.std_len,
            entropy_window=req.entropy_window,
            entropy_bins=req.entropy_bins
        )
        
        # 3. Generate Signals
        df_sig = generate_signals(
            df_feat,
            confirm_entry=req.confirm_entry,
            confirm_exit=req.confirm_exit,
            min_hold_days=req.min_hold_days,
            er_entry=req.er_entry,
            t_entry=req.t_entry,
            chikou_thresh=req.chikou_thresh,
            immunity_thresh=req.immunity_thresh,
            entropy_thresh=req.entropy_thresh,
            imo_min_limit=req.imo_min_limit,
            imo_exit_bull=req.imo_exit_bull,
            roc_gate_limit=req.roc_gate_limit
        )
        
        # 4. Run Backtest
        df_back_full = run_backtest(df_sig, transaction_cost=req.transaction_cost)
        
        # Extract trades on full series to keep complete trade detail
        all_trades = extract_trades(df_back_full, req.chikou_thresh, req.imo_exit_bull)
        
        # Slice the backtest range if parameters are provided
        df_back = df_back_full.copy()
        if req.start_date:
            df_back = df_back[df_back.index >= pd.to_datetime(req.start_date)]
        if req.end_date:
            df_back = df_back[df_back.index <= pd.to_datetime(req.end_date)]
            
        # Recalculate cumulative returns from the start of the sliced dataset
        df_back['Cum_Market'] = (1 + df_back['Market_Ret'].fillna(0)).cumprod() - 1
        df_back['Cum_Strat'] = (1 + df_back['Strat_Net_Ret'].fillna(0)).cumprod() - 1
        
        # 5. Calculate Metrics on the sliced series
        metrics = calculate_metrics(df_back)
        
        # Filter trades list to match the date range
        trades = []
        trade_id = 1
        for t in all_trades:
            entry_dt = pd.to_datetime(t['entry_date'])
            if req.start_date and entry_dt < pd.to_datetime(req.start_date):
                continue
            if req.end_date and entry_dt > pd.to_datetime(req.end_date):
                continue
            t['id'] = trade_id
            trades.append(t)
            trade_id += 1
            
        # Override trade metrics to reflect the filtered trades list
        if len(trades) > 0:
            trade_returns = np.array([t['return'] / 100.0 for t in trades])
            wins = trade_returns[trade_returns > 0]
            losses = trade_returns[trade_returns <= 0]
            metrics['Number of Trades'] = len(trades)
            metrics['Win Rate (%)'] = (len(wins) / len(trades) * 100.0)
            if len(losses) > 0 and abs(losses.sum()) > 0:
                metrics['Profit Factor'] = float(wins.sum() / abs(losses.sum()))
            else:
                metrics['Profit Factor'] = float(wins.sum()) if len(wins) > 0 else 1.0
        else:
            metrics['Number of Trades'] = 0
            metrics['Win Rate (%)'] = 0.0
            metrics['Profit Factor'] = 1.0
        
        # 7. Build timeseries response (for interactive charts)
        # Select key columns and replace NaNs with None/null for JSON compatibility
        timeseries_df = df_back[[
            'Open', 'High', 'Low', 'Close', 'Cum_Market', 'Cum_Strat', 'IMO', 'IMO_Std', 'ER', 'Entropy', 'Pos', 'Active_Pos',
            'S_Chikou', 'S_TK', 'S_Cloud', 'S_Future', 'tenkan_sen', 'kijun_sen', 'senkou_span_a', 'senkou_span_b'
        ]].copy()
        
        # Add index Date as string
        timeseries_df['Date'] = [str(d.date()) for d in timeseries_df.index]
        # Replace NaNs with None for JSON serialisation
        timeseries_data = timeseries_df.replace({np.nan: None}).to_dict(orient='records')
        
        return {
            "metrics": metrics,
            "trades": trades,
            "timeseries": timeseries_data
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("ichimoku_quant.server:app", host="127.0.0.1", port=8000, reload=True)
