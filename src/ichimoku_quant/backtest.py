import numpy as np
import pandas as pd
from typing import Dict, Any

def run_backtest(df: pd.DataFrame, transaction_cost: float = 0.001) -> pd.DataFrame:
    """
    Computes vectorised equity curves and trades based on 'Pos' column.
    """
    if 'Pos' not in df.columns:
        raise ValueError("Pos column not found. Run generate_signals first.")
        
    df = df.copy()
    
    # Position acts on the *next* day's return (signal at close -> return next close)
    df['Active_Pos'] = df['Pos'].shift(1).fillna(0)
    
    df['Market_Ret'] = df['Close'].pct_change()
    df['Strat_Raw_Ret'] = df['Active_Pos'] * df['Market_Ret']
    
    # Calculate transaction costs when position changes
    df['TC'] = df['Active_Pos'].diff().abs().fillna(0) * transaction_cost
    df['Strat_Net_Ret'] = df['Strat_Raw_Ret'] - df['TC']
    
    # Cumulative curves
    df['Cum_Market'] = (1 + df['Market_Ret'].fillna(0)).cumprod() - 1
    df['Cum_Strat'] = (1 + df['Strat_Net_Ret'].fillna(0)).cumprod() - 1
    
    return df

def calculate_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculates key trading metrics from a backtest dataframe.
    """
    if 'Strat_Net_Ret' not in df.columns:
        return {}
        
    ann_factor = 365.25
    ann_market = df['Market_Ret'].mean() * ann_factor
    ann_strat = df['Strat_Net_Ret'].mean() * ann_factor
    
    vol_market = df['Market_Ret'].std() * np.sqrt(ann_factor)
    vol_strat = df['Strat_Net_Ret'].std() * np.sqrt(ann_factor)
    
    sharpe_strat = ann_strat / vol_strat if vol_strat > 0 else 0.0
    sharpe_market = ann_market / vol_market if vol_market > 0 else 0.0
    
    equity = df['Cum_Strat'] + 1
    mdd_strat = ((equity - equity.cummax()) / equity.cummax()).min()
    
    market_eq = df['Cum_Market'] + 1
    mdd_market = ((market_eq - market_eq.cummax()) / market_eq.cummax()).min()
    
    trades = (df['Active_Pos'].diff().abs() > 0).sum() / 2.0
    
    return {
        'Total Return (%)': df['Cum_Strat'].iloc[-1] * 100,
        'Ann. Return (%)': ann_strat * 100,
        'Ann. Volatility (%)': vol_strat * 100,
        'Max Drawdown (%)': mdd_strat * 100,
        'Sharpe Ratio': sharpe_strat,
        'Number of Trades': trades,
        'Market Total Return (%)': df['Cum_Market'].iloc[-1] * 100,
        'Market Max Drawdown (%)': mdd_market * 100,
        'Market Sharpe Ratio': sharpe_market
    }
