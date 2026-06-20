import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

def generate_dashboard_html(df: pd.DataFrame, metrics: dict, output_path: str = "tmp/dashboard.html"):
    """
    Generates a dark-themed interactive HTML dashboard.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 1. Equity Curve (Plotly)
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(x=df.index, y=df['Cum_Market']*100, name='BTC Buy & Hold', line=dict(color='#64748b', width=1.5)))
    fig_eq.add_trace(go.Scatter(x=df.index, y=df['Cum_Strat']*100, name='Ichimoku Quant Strategy', line=dict(color='#818cf8', width=2.5)))
    fig_eq.update_layout(
        template='plotly_dark',
        title='Strategy Equity Growth vs Benchmark (%)',
        margin=dict(l=40, r=20, t=50, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        hovermode='x unified',
        font=dict(family='Inter, sans-serif')
    )
    eq_html = fig_eq.to_html(include_plotlyjs='cdn', full_html=False)
    
    # 2. IMO Oscillator Subplots (Plotly)
    fig_combo = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.1, 
                               row_heights=[0.5, 0.5])
                               
    # IMO Oscillator on top subplot
    fig_combo.add_trace(go.Scatter(x=df.index, y=df['IMO'], name='IMO (Smoothed)', line=dict(color='#38bdf8', width=2)), row=1, col=1)
    
    if 'IMO_Std' in df.columns:
        adaptive_upper = df['IMO_Std'] * 0.40
        fig_combo.add_trace(go.Scatter(x=df.index, y=adaptive_upper, name='Entry Threshold', line=dict(color='rgba(226, 232, 240, 0.4)', dash='dot')), row=1, col=1)
    
    fig_combo.add_hline(y=0.50, line_dash="dash", line_color="#22c55e", annotation_text="Immunity Threshold (0.50)", row=1, col=1)
    fig_combo.add_hline(y=-0.30, line_dash="dash", line_color="#ef4444", annotation_text="Exit Threshold (-0.30)", row=1, col=1)
    fig_combo.add_hline(y=0.0, line_color="rgba(148, 163, 184, 0.3)", row=1, col=1)

    # ER on bottom subplot
    if 'ER' in df.columns:
        fig_combo.add_trace(go.Scatter(x=df.index, y=df['ER'], name='Efficiency Ratio', line=dict(color='#f59e0b', width=1.5)), row=2, col=1)
        fig_combo.add_hline(y=0.25, line_dash="dash", line_color="#ef4444", annotation_text="ER Entry Threshold (0.25)", row=2, col=1)
        
    # Entropy overlay on bottom subplot
    if 'Entropy' in df.columns:
        fig_combo.add_trace(go.Scatter(x=df.index, y=df['Entropy']/df['Entropy'].max(), name='Shannon Entropy (Normalized)', line=dict(color='#c084fc', width=1.5)), row=2, col=1)
    
    fig_combo.update_layout(
        template='plotly_dark', 
        title='Oscillators and Denoising Filters',
        height=600,
        margin=dict(l=40, r=20, t=50, b=40),
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        hovermode='x unified',
        font=dict(family='Inter, sans-serif')
    )
    combo_html = fig_combo.to_html(include_plotlyjs=False, full_html=False)
    
    # 3. Extract Trades
    df_temp = df.copy()
    df_temp['trade_id'] = (df_temp['Active_Pos'].diff().abs() > 0).cumsum()
    in_trade = df_temp[df_temp['Active_Pos'] == 1.0]
    
    trades_list = []
    if len(in_trade) > 0:
        trade_num = 1
        for _, group in in_trade.groupby('trade_id'):
            entry_idx = group.index[0]
            exit_idx = group.index[-1]
            
            exit_loc = df.index.get_loc(exit_idx)
            actual_exit_idx = df.index[exit_loc + 1] if exit_loc + 1 < len(df) else exit_idx
            
            entry_price = df.loc[entry_idx, 'Close']
            exit_price = df.loc[actual_exit_idx, 'Close']
            
            trade_ret = (1.0 + group['Strat_Net_Ret']).prod() - 1.0
            max_price = group['Close'].max()
            run_up = (max_price - entry_price) / entry_price * 100
            
            sig_exit_row = df.loc[exit_idx]
            exit_reason = "Signal Exit"
            
            cloud_a = sig_exit_row['senkou_span_a']
            cloud_b = sig_exit_row['senkou_span_b']
            cloud_max = max(cloud_a, cloud_b) if not (pd.isna(cloud_a) or pd.isna(cloud_b)) else np.nan
            is_above_cloud = (not pd.isna(cloud_max) and sig_exit_row['Close'] >= cloud_max)
            is_not_crashing = (sig_exit_row.get('roc_gate', 0.0) >= -0.20)
            
            is_immune = (sig_exit_row['IMO'] >= 0.50)
            if is_above_cloud and is_not_crashing:
                is_immune = is_immune or (sig_exit_row['IMO'] >= -0.30)
                
            current_macro_exit_th = 0.0
            if is_above_cloud and is_not_crashing:
                current_macro_exit_th = -0.30
                
            if sig_exit_row['S_Chikou'] < -0.30 and not is_immune:
                exit_reason = "Chikou Exit"
            elif sig_exit_row['IMO'] < current_macro_exit_th:
                exit_reason = "Macro IMO Exit"
            
            trades_list.append({
                'num': trade_num,
                'entry_date': entry_idx.strftime('%Y-%m-%d'),
                'exit_date': actual_exit_idx.strftime('%Y-%m-%d'),
                'entry_price': entry_price,
                'exit_price': exit_price,
                'return': trade_ret * 100,
                'run_up': run_up,
                'reason': exit_reason
            })
            trade_num += 1

    trades_rows = ""
    for t in reversed(trades_list):
        ret_color = "#22c55e" if t['return'] >= 0 else "#ef4444"
        trades_rows += f"""
        <tr>
            <td>#{t['num']}</td>
            <td>{t['entry_date']}</td>
            <td>{t['exit_date']}</td>
            <td>${t['entry_price']:,.2f}</td>
            <td>${t['exit_price']:,.2f}</td>
            <td style="color: {ret_color}; font-weight: 600;">{t['return']:+.2f}%</td>
            <td style="color: #38bdf8;">{t['run_up']:+.2f}%</td>
            <td><span class="badge {t['reason'].lower().replace(' ', '-')}">{t['reason']}</span></td>
        </tr>
        """
        
    # Generate KPI card grids
    kpi_html = f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <span class="kpi-title">Total Return (Strategy)</span>
            <span class="kpi-value highlight-green">{metrics['Total Return (%)']:,.2f}%</span>
        </div>
        <div class="kpi-card">
            <span class="kpi-title">Total Return (Market)</span>
            <span class="kpi-value">{metrics['Market Total Return (%)']:,.2f}%</span>
        </div>
        <div class="kpi-card">
            <span class="kpi-title">Sharpe Ratio (Strategy)</span>
            <span class="kpi-value highlight-purple">{metrics['Sharpe Ratio']:,.2f}</span>
        </div>
        <div class="kpi-card">
            <span class="kpi-title">Max Drawdown (Strategy)</span>
            <span class="kpi-value highlight-red">{metrics['Max Drawdown (%)']:,.2f}%</span>
        </div>
        <div class="kpi-card">
            <span class="kpi-title">Win Rate</span>
            <span class="kpi-value">{metrics['Win Rate (%)']:,.1f}%</span>
        </div>
        <div class="kpi-card">
            <span class="kpi-title">Profit Factor</span>
            <span class="kpi-value">{metrics['Profit Factor']:,.2f}</span>
        </div>
        <div class="kpi-card">
            <span class="kpi-title">Number of Trades</span>
            <span class="kpi-value">{int(metrics['Number of Trades'])}</span>
        </div>
    </div>
    """
    
    # Core Dashboard HTML template
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Ichimoku Quant Terminal</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@600;700;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0b0f19;
            --card-bg: #161b30;
            --border-color: #272f4e;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-purple: #c084fc;
            --accent-green: #22c55e;
            --accent-red: #ef4444;
            --font-main: 'Inter', sans-serif;
            --font-header: 'Outfit', sans-serif;
        }}
        
        body {{
            background: var(--bg-color);
            color: var(--text-primary);
            font-family: var(--font-main);
            margin: 0;
            padding: 2rem;
        }}
        
        header {{
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 1rem;
        }}
        
        h1 {{
            font-family: var(--font-header);
            font-size: 2.5rem;
            font-weight: 800;
            margin: 0;
            background: linear-gradient(135deg, #c7d2fe 0%, #818cf8 50%, #38bdf8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        p.subtitle {{
            color: var(--text-secondary);
            font-size: 1rem;
            margin: 0.5rem 0 0 0;
        }}
        
        /* Layout Grid */
        .dashboard-container {{
            display: flex;
            flex-direction: column;
            gap: 2rem;
        }}
        
        .top-row {{
            display: grid;
            grid-template-columns: 3fr 2fr;
            gap: 2rem;
        }}
        
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            display: flex;
            flex-direction: column;
        }}
        
        .card-title {{
            font-family: var(--font-header);
            font-size: 1.25rem;
            font-weight: 700;
            margin-top: 0;
            margin-bottom: 1.5rem;
            color: #c7d2fe;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        /* KPI styling */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 1rem;
            margin-bottom: 1rem;
        }}
        
        .kpi-card {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }}
        
        .kpi-title {{
            color: var(--text-secondary);
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }}
        
        .kpi-value {{
            font-family: var(--font-header);
            font-size: 1.5rem;
            font-weight: 700;
        }}
        
        .highlight-green {{ color: var(--accent-green); text-shadow: 0 0 10px rgba(34, 197, 94, 0.2); }}
        .highlight-purple {{ color: var(--accent-purple); text-shadow: 0 0 10px rgba(192, 132, 252, 0.2); }}
        .highlight-red {{ color: var(--accent-red); text-shadow: 0 0 10px rgba(239, 68, 68, 0.2); }}
        
        /* TradingView Widget Container */
        .tradingview-container {{
            height: 480px;
            width: 100%;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid var(--border-color);
        }}
        
        /* Table Styling */
        .table-container {{
            overflow-x: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.9rem;
        }}
        
        th, td {{
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
        }}
        
        th {{
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
        }}
        
        tr:hover {{
            background: rgba(255, 255, 255, 0.01);
        }}
        
        .badge {{
            padding: 0.25rem 0.5rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .badge.chikou-exit {{ background: rgba(239, 68, 68, 0.15); color: var(--accent-red); }}
        .badge.macro-imo-exit {{ background: rgba(192, 132, 252, 0.15); color: var(--accent-purple); }}
        .badge.signal-exit {{ background: rgba(56, 189, 248, 0.15); color: var(--accent-blue); }}
        
        /* Tabs */
        .tabs-header {{
            display: flex;
            gap: 1rem;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 1.5rem;
        }}
        
        .tab-btn {{
            background: none;
            border: none;
            color: var(--text-secondary);
            font-family: var(--font-header);
            font-weight: 600;
            padding: 0.75rem 1rem;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }}
        
        .tab-btn.active {{
            color: var(--accent-blue);
            border-bottom: 2px solid var(--accent-blue);
        }}
        
        .tab-pane {{
            display: none;
        }}
        
        .tab-pane.active {{
            display: block;
        }}
    </style>
</head>
<body>
    <header>
        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
            <div>
                <h1>Ichimoku Quant Terminal</h1>
                <p class="subtitle">Denoised Multi-Gate Trend-Following Trading System (Ehler SuperSmoother + ER + Shannon Entropy)</p>
            </div>
            <div style="font-family: 'JetBrains Mono'; font-size: 0.85rem; color: var(--text-secondary);">
                System Status: <span style="color: var(--accent-green); font-weight: bold;">ONLINE</span> | Run Local Time: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>
    </header>
    
    <div class="dashboard-container">
        <!-- Top Row: Interactive TV Chart + KPI Grid & Summary -->
        <div class="top-row">
            <div class="card">
                <div class="card-title">
                    <span>Live TradingView Terminal</span>
                    <span style="font-size: 0.8rem; color: var(--text-secondary);">INDEX:BTCUSD (1D)</span>
                </div>
                <div class="tradingview-container">
                    <!-- TradingView Widget BEGIN -->
                    <div class="tradingview-widget-container" style="height:100%;width:100%">
                      <div id="tradingview_chart" style="height:100%;width:100%"></div>
                      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
                      <script type="text/javascript">
                      new TradingView.widget({{
                        "autosize": true,
                        "symbol": "INDEX:BTCUSD",
                        "interval": "D",
                        "timezone": "Etc/UTC",
                        "theme": "dark",
                        "style": "1",
                        "locale": "en",
                        "enable_publishing": false,
                        "hide_side_toolbar": false,
                        "allow_symbol_change": true,
                        "container_id": "tradingview_chart"
                      }});
                      </script>
                    </div>
                    <!-- TradingView Widget END -->
                </div>
            </div>
            
            <div class="card">
                <div class="card-title">Backtest Analytics & Summary</div>
                {kpi_html}
                
                <div style="margin-top: 1rem; flex-grow: 1; border-top: 1px solid var(--border-color); padding-top: 1rem;">
                    <h3 style="font-family: var(--font-header); font-size: 1rem; color: #c7d2fe; margin-top: 0;">Strategy Engine Core Specifications:</h3>
                    <ul style="font-size: 0.85rem; color: var(--text-secondary); padding-left: 1.25rem; line-height: 1.6;">
                        <li><strong>Spectral Denoising:</strong> Ehler's SuperSmoother removes high-frequency price fluctuations from the composite IMO oscillator.</li>
                        <li><strong>Fractal Efficiency Gate:</strong> Positions are only entered when the Efficiency Ratio (ER) exceeds 0.25, ensuring clear directional momentum.</li>
                        <li><strong>Entropy Chaos Filter:</strong> Sinyal masuk ditolak jika Shannon Entropy (keacakan harga) harian di atas 2.15 (TV) / 2.271 (Python) untuk menghindari whipsaw.</li>
                        <li><strong>Batas Stop/likuidasi:</strong> Proteksi spot dengan 100% margin (tanpa leverage) didukung buffer alokasi equity 99% agar bebas dari Margin Call.</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <!-- Bottom Row: Tabs for Charts & Trade Log -->
        <div class="card">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="switchTab('charts-tab')">Performance Charts</button>
                <button class="tab-btn" onclick="switchTab('trades-tab')">Strategy Trade Log</button>
            </div>
            
            <div id="charts-tab" class="tab-pane active">
                <div style="display: flex; flex-direction: column; gap: 2rem;">
                    <div>{eq_html}</div>
                    <div>{combo_html}</div>
                </div>
            </div>
            
            <div id="trades-tab" class="tab-pane">
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Trade</th>
                                <th>Entry Date</th>
                                <th>Exit Date</th>
                                <th>Entry Price</th>
                                <th>Exit Price</th>
                                <th>Return</th>
                                <th>Max Run-up</th>
                                <th>Exit Reason</th>
                            </tr>
                        </thead>
                        <tbody>
                            {trades_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function switchTab(tabId) {{
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
            
            // Set active button
            const activeBtn = Array.from(document.querySelectorAll('.tab-btn')).find(btn => btn.innerText.includes(tabId === 'charts-tab' ? 'Charts' : 'Trade'));
            if (activeBtn) activeBtn.classList.add('active');
            
            // Show active pane
            document.getElementById(tabId).classList.add('active');
        }}
    </script>
</body>
</html>
"""

    with open(output_path, "w") as f:
        f.write(html)
    print(f"Dashboard saved to {output_path}")
