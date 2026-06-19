import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

def generate_dashboard_html(df: pd.DataFrame, metrics: dict, output_path: str = "tmp/dashboard.html"):
    """
    Generates a dark-themed HTML dashboard for the multi-principle backtest.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 1. Equity Curve
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(x=df.index, y=df['Cum_Market']*100, name='BTC Buy & Hold', line=dict(color='#94a3b8')))
    fig_eq.add_trace(go.Scatter(x=df.index, y=df['Cum_Strat']*100, name='Multi-Principle Strategy', line=dict(color='#818cf8', width=2)))
    fig_eq.update_layout(template='plotly_dark', title='Cumulative Return (%)', margin=dict(l=20,r=20,t=40,b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    eq_html = fig_eq.to_html(include_plotlyjs='cdn', full_html=False)
    
    # 2. OHLC + IMO Oscillator Subplots
    fig_combo = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                              vertical_spacing=0.05, 
                              row_heights=[0.6, 0.2, 0.2])
                              
    # Candlestick
    fig_combo.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='BTC/USD', increasing_line_color='#22c55e', decreasing_line_color='#ef4444'
    ), row=1, col=1)
    
    # Overlay Ichimoku Cloud on top subplot
    if 'senkou_span_a' in df.columns and 'senkou_span_b' in df.columns:
        fig_combo.add_trace(go.Scatter(x=df.index, y=df['senkou_span_a'], line=dict(color='rgba(34, 197, 94, 0.5)', width=1), name='Span A'), row=1, col=1)
        fig_combo.add_trace(go.Scatter(x=df.index, y=df['senkou_span_b'], line=dict(color='rgba(239, 68, 68, 0.5)', width=1), fill='tonexty', fillcolor='rgba(148, 163, 184, 0.1)', name='Span B'), row=1, col=1)

    # IMO Oscillator on middle subplot
    fig_combo.add_trace(go.Scatter(x=df.index, y=df['IMO'], name='IMO', line=dict(color='#38bdf8')), row=2, col=1)
    
    # Adaptive Thresholds
    if 'IMO_Std' in df.columns:
        adaptive_upper = df['IMO_Std'] * 0.5
        adaptive_lower = -df['IMO_Std'] * 0.5
        fig_combo.add_trace(go.Scatter(x=df.index, y=adaptive_upper, name='+0.5 StdDev', line=dict(color='rgba(255, 255, 255, 0.3)', dash='dot')), row=2, col=1)
        fig_combo.add_trace(go.Scatter(x=df.index, y=adaptive_lower, name='-0.5 StdDev', line=dict(color='rgba(255, 255, 255, 0.3)', dash='dot')), row=2, col=1)

    # ER on bottom subplot
    if 'ER' in df.columns:
        fig_combo.add_trace(go.Scatter(x=df.index, y=df['ER'], name='Efficiency Ratio', line=dict(color='#f59e0b')), row=3, col=1)
        fig_combo.add_hline(y=0.15, line_dash="dash", line_color="#ef4444", annotation_text="Trend Threshold (0.15)", row=3, col=1)
    
    # Clean binary buy/sell markers (entry: 0→1, exit: 1→0)
    buy_signals = df[(df['Pos'] == 1.0) & (df['Pos'].shift(1) == 0.0)]
    sell_signals = df[(df['Pos'] == 0.0) & (df['Pos'].shift(1) == 1.0)]
    
    fig_combo.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Close'],
                             mode='markers', marker=dict(symbol='triangle-up', size=14, color='lime',
                                                          line=dict(color='white', width=1)),
                             name='ENTRY (Long)'), row=1, col=1)
                             
    fig_combo.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['Close'],
                             mode='markers', marker=dict(symbol='triangle-down', size=14, color='#ef4444',
                                                          line=dict(color='white', width=1)),
                             name='EXIT (Flat)'), row=1, col=1)
    
    # Shade holding periods
    holding = df[df['Pos'] == 1.0]
    if len(holding) > 0:
        fig_combo.add_trace(go.Scatter(
            x=list(holding.index) + list(holding.index[::-1]),
            y=list(holding['High'] * 1.02) + list(holding['Low'] * 0.98),
            fill='toself', fillcolor='rgba(129, 140, 248, 0.05)',
            line=dict(color='rgba(0,0,0,0)'), showlegend=False, name='Holding Period'
        ), row=1, col=1)
    
    # Layout adjustments
    fig_combo.update_layout(
        template='plotly_dark', 
        title='BTC/USD OHLC, IMO Oscillator, and Efficiency Ratio',
        height=900,
        margin=dict(l=20,r=20,t=40,b=20),
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis_rangeslider_visible=False
    )
    combo_html = fig_combo.to_html(include_plotlyjs=False, full_html=False)
    
    # Format metrics
    metrics_rows = "".join([f"<tr><td>{k}</td><td>{v:,.2f}</td></tr>" for k, v in metrics.items()])
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Ichimoku Quant Dashboard (Multi-Principle)</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Outfit:wght@700&display=swap" rel="stylesheet">
    <style>
        body {{ background: #0f111a; color: #f8fafc; font-family: 'Inter', sans-serif; margin: 0; padding: 2rem; }}
        h1 {{ font-family: 'Outfit'; font-size: 2.5rem; color: #818cf8; margin-bottom: 0.5rem; }}
        .card {{ background: #1a1b26; padding: 1.5rem; border-radius: 12px; border: 1px solid #2a2a35; margin-bottom: 2rem; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid #2a2a35; }}
        th {{ color: #94a3b8; font-size: 0.85rem; text-transform: uppercase; }}
    </style>
</head>
<body>
    <h1>Ichimoku Quant Trading System</h1>
    <p>Multi-Principle Denoised Framework: Ehler SuperSmoother + ER Gate + Adaptive Threshold + Confirmation Bars + Min Hold Period.</p>
    
    <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 2rem;">
        <div class="card">
            <h2 style="font-family: 'Outfit'; color: #c7d2fe;">Backtest Metrics</h2>
            <table>
                {metrics_rows}
            </table>
        </div>
        <div class="card">
            {eq_html}
        </div>
    </div>
    
    <div class="card">
        {combo_html}
    </div>
</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html)
    print(f"Dashboard saved to {output_path}")
