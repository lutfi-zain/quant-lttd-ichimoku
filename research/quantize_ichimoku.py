import os
import sys
import datetime
import requests
import pandas as pd
import numpy as np
import scipy.stats as stats
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def fetch_btc_data():
    """Fetch BTC OHLC data from bitview.space from 2016-01-01 to now."""
    url = "https://bitview.space/api/series/price_ohlc/day?start=2016-01-01"
    print(f"Fetching BTC data from {url}...")
    r = requests.get(url)
    r.raise_for_status()
    resp = r.json()
    
    start_idx = resp["start"]
    data = resp["data"]
    
    base_date = datetime.date(2009, 1, 1)
    dates = [base_date + datetime.timedelta(days=start_idx + i) for i in range(len(data))]
    
    df = pd.DataFrame(data, columns=["Open", "High", "Low", "Close"], index=dates)
    df.index = pd.to_datetime(df.index)
    df = df[(df["Open"] > 0) & (df["High"] > 0) & (df["Low"] > 0) & (df["Close"] > 0)]
    return df

def calculate_indicators(df):
    """Calculate Ichimoku components, ATR, and the quantized oscillator (IMO)."""
    print("Calculating Ichimoku & ATR components...")
    
    # 1. ATR (Average True Range) for normalization
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift(1)).abs()
    tr3 = (df['Low'] - df['Close'].shift(1)).abs()
    df['TR'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = df['TR'].rolling(window=14).mean()
    
    # 2. Tenkan-sen & Kijun-sen
    df['tenkan_sen'] = (df['High'].rolling(9).max() + df['Low'].rolling(9).min()) / 2
    df['kijun_sen'] = (df['High'].rolling(26).max() + df['Low'].rolling(26).min()) / 2
    
    # 3. Senkou Spans
    df['senkou_span_a_raw'] = (df['tenkan_sen'] + df['kijun_sen']) / 2
    df['senkou_span_b_raw'] = (df['High'].rolling(52).max() + df['Low'].rolling(52).min()) / 2
    
    # Projections
    df['senkou_span_a'] = df['senkou_span_a_raw'].shift(26)
    df['senkou_span_b'] = df['senkou_span_b_raw'].shift(26)
    df['chikou_span'] = df['Close'].shift(-26)
    
    # 4. Quantized Sub-scores (Normalized using tanh to map to [-1, 1])
    # Sub-score 1: TK Distance
    df['dist_tk'] = (df['tenkan_sen'] - df['kijun_sen']) / df['ATR']
    df['score_tk'] = np.tanh(df['dist_tk'])
    
    # Sub-score 2: Cloud Distance
    # Determine distance to nearest cloud edge or set to 0 if inside
    cloud_max = np.maximum(df['senkou_span_a'], df['senkou_span_b'])
    cloud_min = np.minimum(df['senkou_span_a'], df['senkou_span_b'])
    
    dist_cloud = np.zeros(len(df))
    # Above cloud
    above_mask = df['Close'] > cloud_max
    dist_cloud[above_mask] = (df['Close'] - cloud_max)[above_mask] / df['ATR'][above_mask]
    # Below cloud
    below_mask = df['Close'] < cloud_min
    dist_cloud[below_mask] = (df['Close'] - cloud_min)[below_mask] / df['ATR'][below_mask]
    # Inside cloud stays 0
    df['dist_cloud'] = dist_cloud
    df['score_cloud'] = np.tanh(df['dist_cloud'])
    
    # Sub-score 3: Future Cloud Color/Thickness
    df['dist_future'] = (df['senkou_span_a_raw'] - df['senkou_span_b_raw']) / df['ATR']
    df['score_future'] = np.tanh(df['dist_future'])
    
    # Sub-score 4: Lagging Chikou Span vs Price (26 days ago)
    # Since Chikou is current Close vs Close from 26 days ago:
    df['dist_chikou'] = (df['Close'] - df['Close'].shift(26)) / df['ATR']
    df['score_chikou'] = np.tanh(df['dist_chikou'])
    
    # Composite Ichimoku Multi-Component Oscillator (IMO)
    df['IMO'] = (df['score_tk'] + df['score_cloud'] + df['score_future'] + df['score_chikou']) / 4.0
    
    # Forward Returns for Statistical Validation
    df['fwd_ret_5d'] = np.log(df['Close'].shift(-5) / df['Close'])
    df['fwd_ret_10d'] = np.log(df['Close'].shift(-10) / df['Close'])
    df['fwd_ret_20d'] = np.log(df['Close'].shift(-20) / df['Close'])
    
    return df

def analyze_statistical_edge(df):
    """Analyze the statistical edge of the oscillator using forward returns."""
    print("Performing statistical edge analysis...")
    
    # Drop rows without IMO or forward returns
    clean_df = df.dropna(subset=['IMO', 'fwd_ret_10d'])
    
    # Define IMO Bins
    bins = [-1.0, -0.5, -0.15, 0.15, 0.5, 1.0]
    labels = ['Strong Bearish (-1.0 to -0.5)', 
              'Weak Bearish (-0.5 to -0.15)', 
              'Neutral/Chop (-0.15 to 0.15)', 
              'Weak Bullish (0.15 to 0.5)', 
              'Strong Bullish (0.5 to 1.0)']
    
    clean_df['IMO_bin'] = pd.cut(clean_df['IMO'], bins=bins, labels=labels, include_lowest=True)
    
    edge_stats = []
    for label in labels:
        bin_data = clean_df[clean_df['IMO_bin'] == label]
        count = len(bin_data)
        if count > 5:
            mean_ret = bin_data['fwd_ret_10d'].mean() * 100 # percentage
            std_ret = bin_data['fwd_ret_10d'].std() * 100
            t_stat, p_val = stats.ttest_1samp(bin_data['fwd_ret_10d'], 0)
            
            # Win rate (percent of positive forward returns)
            win_rate = (bin_data['fwd_ret_10d'] > 0).sum() / count * 100
        else:
            mean_ret, std_ret, t_stat, p_val, win_rate = 0, 0, 0, 1.0, 0
            
        edge_stats.append({
            "Bin": label,
            "Count": count,
            "Mean 10D Return (%)": mean_ret,
            "Std 10D Return (%)": std_ret,
            "t-statistic": t_stat,
            "p-value": p_val,
            "Win Rate (%)": win_rate
        })
        
    edge_df = pd.DataFrame(edge_stats)
    
    # Information Coefficient (IC) Analysis
    # Rolling 120-day correlation between IMO and 10D forward returns
    rolling_ic = clean_df['IMO'].rolling(120).corr(clean_df['fwd_ret_10d'])
    mean_ic = rolling_ic.mean()
    t_ic, p_ic = stats.ttest_1samp(rolling_ic.dropna(), 0)
    
    ic_summary = {
        "Mean IC": mean_ic,
        "IC t-statistic": t_ic,
        "IC p-value": p_ic
    }
    
    return edge_df, ic_summary, rolling_ic

def run_backtest(df, entry_thresh=0.15, exit_thresh=-0.15, transaction_cost=0.001):
    """Run a long-only vectorized backtest (100% equity / cash) based on IMO thresholds."""
    print("Running strategy backtest...")
    
    # We active position on day t+1 based on IMO on day t
    df['Signal'] = 0
    
    position = 0
    signals = []
    
    # Loop to generate signals (long-only trend following)
    for idx, row in df.iterrows():
        imo = row['IMO']
        if pd.isna(imo):
            signals.append(0)
            continue
            
        if position == 0:
            if imo > entry_thresh:
                position = 1 # Enter long
        else:
            if imo < exit_thresh:
                position = 0 # Exit to cash
                
        signals.append(position)
        
    df['Position'] = signals
    # Shift position by 1 day to execute at next open/close (no lookahead bias)
    df['Active_Position'] = df['Position'].shift(1).fillna(0)
    
    # Calculate returns
    df['Market_Return'] = df['Close'].pct_change()
    df['Strategy_Raw_Return'] = df['Active_Position'] * df['Market_Return']
    
    # Transaction costs: fee paid on position change
    df['Position_Change'] = df['Active_Position'].diff().abs().fillna(0)
    df['Transaction_Costs'] = df['Position_Change'] * transaction_cost
    df['Strategy_Net_Return'] = df['Strategy_Raw_Return'] - df['Transaction_Costs']
    
    # Cumulative returns
    df['Cum_Market_Return'] = (1 + df['Market_Return'].fillna(0)).cumprod() - 1
    df['Cum_Strategy_Return'] = (1 + df['Strategy_Net_Return'].fillna(0)).cumprod() - 1
    
    # Performance Metrics
    hist_df = df.dropna(subset=['Market_Return', 'Strategy_Net_Return'])
    
    # Annualized Returns & Vol
    ann_factor = 365.25 # crypto trades 24/7/365
    
    ann_market_ret = hist_df['Market_Return'].mean() * ann_factor
    ann_market_vol = hist_df['Market_Return'].std() * np.sqrt(ann_factor)
    market_sharpe = ann_market_ret / ann_market_vol if ann_market_vol > 0 else 0
    
    ann_strat_ret = hist_df['Strategy_Net_Return'].mean() * ann_factor
    ann_strat_vol = hist_df['Strategy_Net_Return'].std() * np.sqrt(ann_factor)
    strat_sharpe = ann_strat_ret / ann_strat_vol if ann_strat_vol > 0 else 0
    
    # Max Drawdowns
    def get_max_drawdown(cum_returns):
        equity = cum_returns + 1
        running_max = equity.cummax()
        drawdown = (equity - running_max) / running_max
        return drawdown.min()
        
    market_mdd = get_max_drawdown(hist_df['Cum_Market_Return'])
    strat_mdd = get_max_drawdown(hist_df['Cum_Strategy_Return'])
    
    # Trade Count & Win Rate
    # A trade is defined by entering long (Position_Change == 1 and Position == 1)
    num_trades = int((df['Position_Change'] > 0).sum() / 2) # entry + exit
    
    # Win rate of active days
    active_days = hist_df[hist_df['Active_Position'] == 1]
    day_win_rate = (active_days['Market_Return'] > 0).sum() / len(active_days) * 100 if len(active_days) > 0 else 0
    
    metrics = {
        "Total Return (Market) (%)": hist_df['Cum_Market_Return'].iloc[-1] * 100,
        "Total Return (Strategy) (%)": hist_df['Cum_Strategy_Return'].iloc[-1] * 100,
        "Annualized Return (Market) (%)": ann_market_ret * 100,
        "Annualized Return (Strategy) (%)": ann_strat_ret * 100,
        "Annualized Volatility (Market) (%)": ann_market_vol * 100,
        "Annualized Volatility (Strategy) (%)": ann_strat_vol * 100,
        "Sharpe Ratio (Market)": market_sharpe,
        "Sharpe Ratio (Strategy)": strat_sharpe,
        "Max Drawdown (Market) (%)": market_mdd * 100,
        "Max Drawdown (Strategy) (%)": strat_mdd * 100,
        "Number of Trades": num_trades,
        "Daily Active Win Rate (%)": day_win_rate
    }
    
    return df, metrics

def generate_report_html(df, edge_df, ic_summary, rolling_ic, metrics, output_path):
    """Generate a highly detailed interactive HTML report with Plotly charts."""
    print("Generating comprehensive reports and visual assets...")
    
    # Filter historical data for visualization
    plot_df = df.dropna(subset=['Close'])
    
    # Create Subplots
    # Row 1: BTC Price & Ichimoku
    # Row 2: IMO Oscillator
    # Row 3: Cumulative Performance
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05,
                        row_heights=[0.45, 0.20, 0.35])
    
    # Trace 1: Price Candlestick (Row 1)
    fig.add_trace(
        go.Candlestick(
            x=plot_df.index, open=plot_df['Open'], high=plot_df['High'], low=plot_df['Low'], close=plot_df['Close'],
            name='BTC Price', showlegend=True,
            increasing_line_color='rgb(34, 197, 94)', decreasing_line_color='rgb(239, 68, 68)',
            increasing_fillcolor='rgba(34, 197, 94, 0.2)', decreasing_fillcolor='rgba(239, 68, 68, 0.2)'
        ),
        row=1, col=1
    )
    
    # Trace 2: Tenkan-sen (Row 1)
    fig.add_trace(
        go.Scatter(x=plot_df.index, y=plot_df['tenkan_sen'], name='Tenkan-sen', line=dict(color='rgb(56, 189, 248)', width=1.2)),
        row=1, col=1
    )
    
    # Trace 3: Kijun-sen (Row 1)
    fig.add_trace(
        go.Scatter(x=plot_df.index, y=plot_df['kijun_sen'], name='Kijun-sen', line=dict(color='rgb(244, 63, 94)', width=1.2)),
        row=1, col=1
    )
    
    # Trace 4: Kumo cloud boundaries for fill (Row 1)
    fig.add_trace(
        go.Scatter(x=plot_df.index, y=plot_df['senkou_span_a'], name='Span A', line=dict(color='rgba(34, 197, 94, 0.3)', width=1.0)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=plot_df.index, y=plot_df['senkou_span_b'], name='Span B', line=dict(color='rgba(239, 68, 68, 0.3)', width=1.0),
                   fill='tonexty', fillcolor='rgba(99, 102, 241, 0.05)'),
        row=1, col=1
    )
    
    # Trace 5: IMO Oscillator (Row 2)
    # Color bar chart or smooth line
    fig.add_trace(
        go.Scatter(
            x=plot_df.index, y=plot_df['IMO'], name='IMO Oscillator',
            line=dict(color='rgb(245, 158, 11)', width=1.5), # amber/gold
            fill='tozeroy', fillcolor='rgba(245, 158, 11, 0.05)'
        ),
        row=2, col=1
    )
    # Thresholds
    fig.add_hline(y=0.15, line_dash="dash", line_color="rgba(34, 197, 94, 0.6)", annotation_text="Buy Threshold (+0.15)", row=2, col=1)
    fig.add_hline(y=-0.15, line_dash="dash", line_color="rgba(239, 68, 68, 0.6)", annotation_text="Sell Threshold (-0.15)", row=2, col=1)
    
    # Trace 6: Cumulative returns (Row 3)
    fig.add_trace(
        go.Scatter(x=plot_df.index, y=plot_df['Cum_Market_Return'] * 100, name='BTC Buy-and-Hold', line=dict(color='rgb(148, 163, 184)', width=1.5)),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(x=plot_df.index, y=plot_df['Cum_Strategy_Return'] * 100, name='Ichimoku Quant Strategy', line=dict(color='rgb(99, 102, 241)', width=2.0)),
        row=3, col=1
    )
    
    # Update chart layouts
    fig.update_layout(
        template='plotly_dark',
        height=1000,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgb(10, 10, 12)',
        plot_bgcolor='rgb(10, 10, 12)',
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.01, xanchor='right', x=1)
    )
    
    fig.update_yaxes(title_text="Price (USD, Log)", type="log", row=1, col=1, side="right")
    fig.update_yaxes(title_text="IMO Score", range=[-1.1, 1.1], row=2, col=1, side="right")
    fig.update_yaxes(title_text="Cumulative Return (%)", row=3, col=1, side="right")
    
    main_chart_html = fig.to_html(include_plotlyjs='cdn', full_html=False)
    
    # Create statistical validation bar chart
    fig_edge = go.Figure()
    fig_edge.add_trace(
        go.Bar(
            x=edge_df['Bin'],
            y=edge_df['Mean 10D Return (%)'],
            text=edge_df.apply(lambda r: f"t={r['t-statistic']:.2f}<br>n={r['Count']}", axis=1),
            textposition='auto',
            marker_color=['rgba(239, 68, 68, 0.7)', 'rgba(239, 68, 68, 0.4)', 'rgba(148, 163, 184, 0.4)', 'rgba(34, 197, 94, 0.5)', 'rgba(34, 197, 94, 0.8)'],
            name='10D Mean Return (%)'
        )
    )
    fig_edge.update_layout(
        template='plotly_dark',
        height=400,
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor='rgb(15, 15, 20)',
        plot_bgcolor='rgb(15, 15, 20)',
        title=dict(text="Average 10-Day Forward BTC Return by IMO Oscillator Bin", font=dict(family='Outfit', size=16)),
        yaxis=dict(title='Mean Return (%)')
    )
    edge_chart_html = fig_edge.to_html(include_plotlyjs=False, full_html=False)
    
    # Format tables for HTML template
    metrics_rows = ""
    for k, v in metrics.items():
        val_str = f"{v:,.2f}" if "Sharpe" in k or "Number" in k else f"{v:+,.2f}%" if "%" in k else f"{v:,.2f}"
        if "Market" in k:
            row_style = "style='color: var(--text-secondary);'"
        elif "Strategy" in k:
            row_style = "style='font-weight: 600; color: #a5b4fc;'"
        else:
            row_style = ""
        metrics_rows += f"<tr {row_style}><td>{k}</td><td>{val_str}</td></tr>"
        
    stats_rows = ""
    for _, row in edge_df.iterrows():
        p_color = "var(--bullish-color)" if row['p-value'] < 0.05 and row['t-statistic'] > 0 else "var(--bearish-color)" if row['p-value'] < 0.05 else "var(--text-secondary)"
        stats_rows += f"""<tr>
            <td>{row['Bin']}</td>
            <td>{int(row['Count']):,}</td>
            <td>{row['Mean 10D Return (%)']:+,.3f}%</td>
            <td>{row['Win Rate (%)']:.1f}%</td>
            <td style="font-family: 'JetBrains Mono', monospace;">{row['t-statistic']:.3f}</td>
            <td style="font-family: 'JetBrains Mono', monospace; color: {p_color}">{row['p-value']:.4f}</td>
        </tr>"""

    # Final HTML template
    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ichimoku Cloud Statistical Quant & Oscillator Analysis</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #050508;
            --card-bg: #0b0b10;
            --card-inner: #12121a;
            --card-border: #1a1a26;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --bullish-color: #22c55e;
            --bullish-bg: rgba(34, 197, 94, 0.1);
            --bearish-color: #ef4444;
            --bearish-bg: rgba(239, 68, 68, 0.1);
            --accent-color: #6366f1;
            --font-mono: 'JetBrains Mono', monospace;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            background-color: var(--bg-color);
            color: var(--text-primary);
            font-family: 'Inter', sans-serif;
            padding: 2.5rem;
            min-height: 100vh;
        }}
        
        header {{
            margin-bottom: 2.5rem;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 1.5rem;
        }}
        
        h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #fff 0%, #818cf8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}
        
        .subtitle {{
            color: var(--text-secondary);
            font-size: 1.1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .grid-2 {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 2rem;
            margin-bottom: 2.5rem;
        }}
        
        .grid-1-2 {{
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 2rem;
            margin-bottom: 2.5rem;
        }}
        
        .section-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.5rem;
            font-weight: 700;
            color: #c7d2fe;
            margin-bottom: 1.25rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .section-title::before {{
            content: '';
            display: inline-block;
            width: 4px;
            height: 1.2rem;
            background-color: var(--accent-color);
            border-radius: 2px;
        }}
        
        .card {{
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.75rem;
            box-shadow: 0 10px 25px rgba(0,0,0,0.4);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 0.5rem;
            font-size: 0.95rem;
        }}
        
        th, td {{
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid var(--card-border);
        }}
        
        th {{
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.8rem;
            letter-spacing: 0.05em;
        }}
        
        td {{
            color: var(--text-primary);
        }}
        
        tr:hover td {{
            background-color: var(--card-inner);
        }}
        
        .badge {{
            font-family: var(--font-mono);
            font-size: 0.8rem;
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            font-weight: 500;
        }}
        
        .badge.success {{ background-color: var(--bullish-bg); color: var(--bullish-color); }}
        .badge.warning {{ background-color: rgba(245, 158, 11, 0.1); color: rgb(245, 158, 11); }}
        .badge.danger {{ background-color: var(--bearish-bg); color: var(--bearish-color); }}
        
        .chart-box {{
            background-color: rgba(10, 10, 15, 0.8);
            border-radius: 12px;
            border: 1px solid var(--card-border);
            overflow: hidden;
        }}
        
        .theory-block {{
            background-color: var(--card-inner);
            border-left: 4px solid var(--accent-color);
            border-radius: 4px;
            padding: 1.25rem;
            margin-bottom: 1.5rem;
            font-size: 0.95rem;
            line-height: 1.6;
        }}
        
        .theory-block p {{
            margin-bottom: 0.75rem;
        }}
        
        .theory-block ul {{
            list-style-type: none;
            padding-left: 0.5rem;
        }}
        
        .theory-block li {{
            margin-bottom: 0.4rem;
            display: flex;
            align-items: baseline;
            gap: 0.5rem;
        }}
        
        .theory-block li::before {{
            content: '▫';
            color: var(--accent-color);
        }}
        
        .text-highlight {{
            color: #a5b4fc;
            font-weight: 600;
        }}
        
        .footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-top: 3rem;
            padding-top: 1.5rem;
            border-top: 1px solid var(--card-border);
        }}
        
        .footer a {{
            color: var(--accent-color);
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <header>
        <h1>Bitcoin Ichimoku Quant Analysis</h1>
        <div class="subtitle">
            <span>Statistical Quantization, Oscillator Edge Validation, & Backtesting</span>
            <span class="timestamp">Period: 2016 – Present</span>
        </div>
    </header>
    
    <div class="grid-2">
        <!-- Left: Strategy Theory and Mathematical Framework -->
        <div class="card">
            <h2 class="section-title">Statistical Quantization Framework (IMO)</h2>
            <div class="theory-block">
                <p>To evaluate Ichimoku indicators rigorously, we map qualitative visual rules to a scale-invariant, continuous z-score equivalent: the <span class="text-highlight">Ichimoku Multi-Component Oscillator (IMO)</span>. By normalizing price distances with a rolling <span class="text-highlight">ATR (14)</span>, we remove price scaling drift. A hyperbolic tangent function <span class="text-highlight">tanh(x)</span> maps each metric into a bounded range of <span class="text-highlight">[-1.0, 1.0]</span>, representing bearish-to-bullish consensus strength.</p>
                <ul>
                    <li><strong>TK Score ($S_{{TK}}$)</strong>: $\\tanh(\\frac{{\\text{{Tenkan}} - \\text{{Kijun}}}}{{\\text{{ATR}}}})$. Measures crossover convergence.</li>
                    <li><strong>Cloud Score ($S_{{Cloud}}$)</strong>: $\\tanh(\\frac{{\\text{{Close}} - \\text{{Nearest Cloud Edge}}}}{{\\text{{ATR}}}})$ (or $0$ if inside). Measures trend location.</li>
                    <li><strong>Future Score ($S_{{Future}}$)</strong>: $\\tanh(\\frac{{\\text{{Span A}} - \\text{{Span B}}}}{{\\text{{ATR}}}})$. Quantifies projected momentum.</li>
                    <li><strong>Lagging Score ($S_{{Chikou}}$)</strong>: $\\tanh(\\frac{{\\text{{Close}} - \\text{{Close}}_{{t-26}}}}{{\\text{{ATR}}}})$. Quantifies historical momentum edge.</li>
                </ul>
                <p style="margin-top:0.75rem;">The composite oscillator is the equally-weighted average of the sub-scores: $IMO_t = \\frac{{S_{{TK}} + S_{{Cloud}} + S_{{Future}} + S_{{Chikou}}}}{{4}} \\in [-1.0, 1.0]$.</p>
            </div>
            
            <h2 class="section-title">Interactive Multi-Pane Strategy Chart</h2>
            <div class="chart-box">
                {main_chart_html}
            </div>
        </div>
        
        <!-- Right: Strategy Performance & Edge Metrics -->
        <div style="display: flex; flex-direction: column; gap: 2rem;">
            <div class="card">
                <h2 class="section-title">Performance Metrics</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        {metrics_rows}
                    </tbody>
                </table>
            </div>
            
            <div class="card">
                <h2 class="section-title">Backtest Parameters</h2>
                <div style="font-size: 0.9rem; line-height: 1.6; color: var(--text-secondary);">
                    <p>• <strong>Buy Threshold</strong>: <span class="text-highlight">&gt; +0.15</span> (Positive consensus)</p>
                    <p>• <strong>Sell/Exit Threshold</strong>: <span class="text-highlight">&lt; -0.15</span> (Negative consensus)</p>
                    <p>• <strong>Position Type</strong>: Long-Only / 100% Equity or Cash (USD)</p>
                    <p>• <strong>Transaction Cost</strong>: 10 bps (0.1%) per trade execution</p>
                    <p>• <strong>Execution Delay</strong>: Next-day active (T+1) to prevent look-ahead bias</p>
                </div>
            </div>
            
            <div class="card">
                <h2 class="section-title">Information Coefficient (IC)</h2>
                <div style="font-size: 0.9rem; line-height: 1.6; color: var(--text-secondary);">
                    <p>• <strong>Mean 10D IC</strong>: <span class="text-highlight">{ic_summary['Mean IC']:.4f}</span></p>
                    <p>• <strong>t-statistic</strong>: <span class="text-highlight">{ic_summary['IC t-statistic']:.3f}</span> (p-val: {ic_summary['IC p-value']:.4e})</p>
                    <p style="margin-top: 0.5rem; font-size: 0.85rem;">A positive t-stat &gt; 2.0 indicates the oscillator has a statistically significant predictive edge for forward BTC returns.</p>
                </div>
            </div>
        </div>
    </div>
    
    <div class="grid-1-2">
        <!-- Left: Bin Statistics -->
        <div class="card">
            <h2 class="section-title">Statistical Edge (10-Day Forward Returns)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Score Bin</th>
                        <th>Samples</th>
                        <th>Mean Ret</th>
                        <th>Win Rate</th>
                        <th>t-stat</th>
                        <th>p-value</th>
                    </tr>
                </thead>
                <tbody>
                    {stats_rows}
                </tbody>
            </table>
        </div>
        
        <!-- Right: Statistical Bar Chart -->
        <div class="card">
            <h2 class="section-title">Visualizing Edge</h2>
            <div class="chart-box">
                {edge_chart_html}
            </div>
        </div>
    </div>
    
    <div class="footer">
        <span>Powered by <a href="https://bitview.space" target="_blank">bitview.space (BRK API)</a></span>
        <span>Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
    </div>
    
    <!-- Include KaTeX for equations rendering -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js" onload="renderMathInElement(document.body);"></script>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_html)
    print(f"Report successfully saved to {output_path}")

def main():
    output_dir = "tmp"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "ichimoku_quant_analysis.html")
    
    try:
        df = fetch_btc_data()
        df = calculate_indicators(df)
        edge_df, ic_summary, rolling_ic = analyze_statistical_edge(df)
        df, metrics = run_backtest(df)
        generate_report_html(df, edge_df, ic_summary, rolling_ic, metrics, output_path)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
