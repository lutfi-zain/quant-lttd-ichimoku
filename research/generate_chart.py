import os
import sys
import datetime
import requests
import pandas as pd
import numpy as np
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
    data = resp["data"] # [[open, high, low, close], ...]
    
    # Base date of the BRK index is January 1, 2009
    base_date = datetime.date(2009, 1, 1)
    dates = [base_date + datetime.timedelta(days=start_idx + i) for i in range(len(data))]
    
    df = pd.DataFrame(data, columns=["Open", "High", "Low", "Close"], index=dates)
    df.index = pd.to_datetime(df.index)
    
    # Clean any zeros or NaNs in data
    df = df[(df["Open"] > 0) & (df["High"] > 0) & (df["Low"] > 0) & (df["Close"] > 0)]
    return df

def calculate_ichimoku(df):
    """
    Calculate Ichimoku Kinko Hyo elements:
    - Tenkan-sen (9-Period Conversion Line)
    - Kijun-sen (26-Period Base Line)
    - Senkou Span A (Leading Span A) - projected 26 periods ahead
    - Senkou Span B (Leading Span B) - projected 26 periods ahead
    - Chikou Span (Lagging Span) - projected 26 periods behind
    """
    print("Calculating Ichimoku indicators...")
    
    # Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
    nine_high = df['High'].rolling(window=9).max()
    nine_low = df['Low'].rolling(window=9).min()
    df['tenkan_sen'] = (nine_high + nine_low) / 2
    
    # Kijun-sen (Base Line): (26-period high + 26-period low) / 2
    twentysix_high = df['High'].rolling(window=26).max()
    twentysix_low = df['Low'].rolling(window=26).min()
    df['kijun_sen'] = (twentysix_high + twentysix_low) / 2
    
    # Senkou Span A (Leading Span A): (Tenkan-sen + Kijun-sen) / 2
    df['senkou_span_a_raw'] = (df['tenkan_sen'] + df['kijun_sen']) / 2
    
    # Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2
    fiftytwo_high = df['High'].rolling(window=52).max()
    fiftytwo_low = df['Low'].rolling(window=52).min()
    df['senkou_span_b_raw'] = (fiftytwo_high + fiftytwo_low) / 2
    
    # Create extended index to host future projections (26 days ahead)
    last_date = df.index[-1]
    future_dates = [last_date + datetime.timedelta(days=i) for i in range(1, 27)]
    extended_index = df.index.append(pd.DatetimeIndex(future_dates))
    
    # Build extended DataFrame
    ext_df = pd.DataFrame(index=extended_index)
    ext_df = ext_df.join(df)
    
    # Shift Leading Spans 26 periods forward (to project into the future)
    ext_df['senkou_span_a'] = ext_df['senkou_span_a_raw'].shift(26)
    ext_df['senkou_span_b'] = ext_df['senkou_span_b_raw'].shift(26)
    
    # Chikou Span (Lagging Line): Close price shifted 26 periods backward
    ext_df['chikou_span'] = ext_df['Close'].shift(-26)
    
    return ext_df

def generate_dashboard_html(df, output_path):
    """Generate a premium dark-mode HTML dashboard containing the interactive Plotly chart."""
    print("Generating interactive dashboard HTML...")
    
    # Get latest data points for metrics
    # We look for the last row in df that has actual Close data (which is the last day of historical data, before future projection)
    hist_df = df.dropna(subset=["Close"])
    latest_row = hist_df.iloc[-1]
    prev_row = hist_df.iloc[-2]
    
    latest_price = latest_row["Close"]
    prev_price = prev_row["Close"]
    price_change = latest_price - prev_price
    price_change_pct = (price_change / prev_price) * 100
    
    latest_date_str = hist_df.index[-1].strftime('%B %d, %Y')
    
    # Determine Ichimoku status signals
    tenkan = latest_row["tenkan_sen"]
    kijun = latest_row["kijun_sen"]
    span_a = latest_row["senkou_span_a"] # this is projected from 26 days ago
    span_b = latest_row["senkou_span_b"] # this is projected from 26 days ago
    
    # 1. Tenkan / Kijun Crossover
    tk_signal = "Bullish Crossover" if tenkan > kijun else "Bearish Cross"
    tk_class = "bullish" if tenkan > kijun else "bearish"
    tk_desc = f"Tenkan-sen (${tenkan:,.2f}) is above Kijun-sen (${kijun:,.2f})." if tenkan > kijun else f"Tenkan-sen (${tenkan:,.2f}) is below Kijun-sen (${kijun:,.2f})."
    
    # 2. Price vs Cloud (Kumo)
    # The current cloud is plotted from calculations 26 days ago. So we look at senkou_span_a and senkou_span_b at the current date.
    cloud_top = max(span_a, span_b) if not (pd.isna(span_a) or pd.isna(span_b)) else latest_price
    cloud_bottom = min(span_a, span_b) if not (pd.isna(span_a) or pd.isna(span_b)) else latest_price
    
    if latest_price > cloud_top:
        cloud_signal = "Bullish (Above Cloud)"
        cloud_class = "bullish"
        cloud_desc = "Price is trading above the Kumo Cloud, indicating a strong upward trend."
    elif latest_price < cloud_bottom:
        cloud_signal = "Bearish (Below Cloud)"
        cloud_class = "bearish"
        cloud_desc = "Price is trading below the Kumo Cloud, indicating a strong downward trend."
    else:
        cloud_signal = "Neutral (Inside Cloud)"
        cloud_class = "neutral"
        cloud_desc = "Price is trading inside the Kumo Cloud, indicating market consolidation/chop."
        
    # 3. Kumo Future Cloud State (at the end of the extended index, 26 days in the future)
    future_row = df.iloc[-1]
    fut_span_a = future_row["senkou_span_a"]
    fut_span_b = future_row["senkou_span_b"]
    future_cloud_color = "Green (Bullish)" if fut_span_a > fut_span_b else "Red (Bearish)"
    future_cloud_class = "bullish" if fut_span_a > fut_span_b else "bearish"
    future_cloud_desc = f"Future cloud is Span A (${fut_span_a:,.2f}) > Span B (${fut_span_b:,.2f}), suggesting continued bullish momentum." if fut_span_a > fut_span_b else f"Future cloud is Span A (${fut_span_a:,.2f}) < Span B (${fut_span_b:,.2f}), suggesting potential bearish pressure."

    # Create Plotly Chart
    fig = make_subplots(rows=1, cols=1)
    
    # 1. Candlestick Chart for Price
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='BTC/USD',
            increasing_line_color='rgb(34, 197, 94)', # Green
            decreasing_line_color='rgb(239, 68, 68)', # Red
            increasing_fillcolor='rgba(34, 197, 94, 0.3)',
            decreasing_fillcolor='rgba(239, 68, 68, 0.3)',
            showlegend=True
        )
    )
    
    # 2. Tenkan-sen (sky blue)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['tenkan_sen'],
            name='Tenkan-sen (Conversion Line)',
            line=dict(color='rgb(56, 189, 248)', width=1.5),
            hoverinfo='y'
        )
    )
    
    # 3. Kijun-sen (rose/red)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['kijun_sen'],
            name='Kijun-sen (Base Line)',
            line=dict(color='rgb(244, 63, 94)', width=1.5),
            hoverinfo='y'
        )
    )
    
    # 4. Chikou Span (purple/lagging) - plotted 26 days in past
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['chikou_span'],
            name='Chikou Span (Lagging Line)',
            line=dict(color='rgb(168, 85, 247)', width=1.0, dash='dash'),
            hoverinfo='y'
        )
    )
    
    # 5. Senkou Span A (green/light)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['senkou_span_a'],
            name='Senkou Span A',
            line=dict(color='rgba(34, 197, 94, 0.4)', width=1.2),
            hoverinfo='y',
            showlegend=True
        )
    )
    
    # 6. Senkou Span B (red/light) with fill to Senkou Span A
    # To show the Kumo cloud, we can shade between Span A and Span B.
    # Plotly fills to the next trace, so drawing B immediately after A with fill='tonexty' works perfectly!
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['senkou_span_b'],
            name='Senkou Span B',
            line=dict(color='rgba(239, 68, 68, 0.4)', width=1.2),
            fill='tonexty',
            fillcolor='rgba(99, 102, 241, 0.08)', # Soft indigo/neutral cloud fill
            hoverinfo='y',
            showlegend=True
        )
    )
    
    # Update chart layout for a sleek, premium dark-tech terminal aesthetic
    fig.update_layout(
        template='plotly_dark',
        height=700,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(
            rangeslider=dict(visible=False),
            gridcolor='rgb(30, 30, 35)',
            linecolor='rgb(50, 50, 55)',
            type='date'
        ),
        yaxis=dict(
            gridcolor='rgb(30, 30, 35)',
            linecolor='rgb(50, 50, 55)',
            side='right',
            title='Price (USD)',
            type='log' # Log scale is vital for BTC since 2016
        ),
        paper_bgcolor='rgb(10, 10, 12)',
        plot_bgcolor='rgb(10, 10, 12)',
        hovermode='x unified',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            bgcolor='rgba(10, 10, 12, 0.8)',
            bordercolor='rgba(50, 50, 55, 0.5)',
            borderwidth=1
        )
    )
    
    # Export chart to HTML snippet
    plotly_html = fig.to_html(include_plotlyjs='cdn', full_html=False)
    
    # Build complete dashboard page
    dashboard_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bitcoin Ichimoku Cloud Quantification Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #050507;
            --card-bg: #0d0d12;
            --card-border: #1f1f2e;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --bullish-color: #22c55e;
            --bullish-bg: rgba(34, 197, 94, 0.1);
            --bearish-color: #ef4444;
            --bearish-bg: rgba(239, 68, 68, 0.1);
            --neutral-color: #e2e8f0;
            --neutral-bg: rgba(226, 232, 240, 0.08);
            --accent-color: #6366f1;
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
            padding: 2rem;
            min-height: 100vh;
        }}
        
        header {{
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 1.5rem;
        }}
        
        h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #fff 0%, #a5b4fc 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}
        
        .subtitle {{
            color: var(--text-secondary);
            font-size: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .timestamp {{
            font-family: 'JetBrains Mono', monospace;
            background: var(--neutral-bg);
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.85rem;
            border: 1px solid var(--card-border);
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .card {{
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 1.5rem;
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
        }}
        
        .card:hover {{
            transform: translateY(-2px);
            border-color: rgba(99, 102, 241, 0.4);
        }}
        
        .card-label {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.75rem;
        }}
        
        .card-value {{
            font-size: 1.8rem;
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: baseline;
            gap: 0.5rem;
        }}
        
        .card-change {{
            font-size: 0.9rem;
            font-family: 'Inter', sans-serif;
            font-weight: 500;
        }}
        
        .card-change.up {{ color: var(--bullish-color); }}
        .card-change.down {{ color: var(--bearish-color); }}
        
        .card-status {{
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }}
        
        .card-status.bullish {{
            background-color: var(--bullish-bg);
            color: var(--bullish-color);
        }}
        
        .card-status.bearish {{
            background-color: var(--bearish-bg);
            color: var(--bearish-color);
        }}
        
        .card-status.neutral {{
            background-color: var(--neutral-bg);
            color: var(--neutral-color);
        }}
        
        .card-desc {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            line-height: 1.4;
        }}
        
        .chart-container {{
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        
        .footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-top: 2rem;
            padding-top: 1.5rem;
            border-top: 1px solid var(--card-border);
        }}
        
        .footer a {{
            color: var(--accent-color);
            text-decoration: none;
        }}
        
        .footer a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <header>
        <h1>Bitcoin Ichimoku Kinko Hyo</h1>
        <div class="subtitle">
            <span>Daily Trend Analysis & Cloud Quantification (2016 – Present)</span>
            <span class="timestamp">Data Date: {latest_date_str}</span>
        </div>
    </header>
    
    <div class="metrics-grid">
        <!-- Card 1: Price -->
        <div class="card">
            <div class="card-label">BTC/USD Latest Price</div>
            <div class="card-value">
                ${latest_price:,.2f}
                <span class="card-change {'up' if price_change >= 0 else 'down'}">
                    {'▲' if price_change >= 0 else '▼'} {price_change_pct:+.2f}%
                </span>
            </div>
            <div class="card-desc">Latest daily closing price retrieved directly from bitview.space API.</div>
        </div>
        
        <!-- Card 2: Price vs Cloud -->
        <div class="card">
            <div class="card-label">Trend State (Price vs Cloud)</div>
            <div class="card-status {cloud_class}">{cloud_signal}</div>
            <div class="card-desc">{cloud_desc}</div>
        </div>
        
        <!-- Card 3: TK Crossover -->
        <div class="card">
            <div class="card-label">TK Cross (Conversion vs Base)</div>
            <div class="card-status {tk_class}">{tk_signal}</div>
            <div class="card-desc">{tk_desc}</div>
        </div>
        
        <!-- Card 4: Future Cloud Projection -->
        <div class="card">
            <div class="card-label">Future Cloud (T+26 Projection)</div>
            <div class="card-status {future_cloud_class}">{future_cloud_color}</div>
            <div class="card-desc">{future_cloud_desc}</div>
        </div>
    </div>
    
    <div class="chart-container">
        {plotly_html}
    </div>
    
    <div class="footer">
        <span>Powered by <a href="https://bitview.space" target="_blank">bitview.space (BRK API)</a></span>
        <span>Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
    </div>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(dashboard_html)
    print(f"Dashboard successfully saved to {output_path}")

def main():
    output_dir = "tmp"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "btc_ichimoku.html")
    
    try:
        df = fetch_btc_data()
        ext_df = calculate_ichimoku(df)
        generate_dashboard_html(ext_df, output_path)
    except Exception as e:
        print(f"Error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
