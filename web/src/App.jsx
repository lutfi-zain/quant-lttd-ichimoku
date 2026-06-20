import React, { useState, useEffect, useRef } from 'react';
import Chart from 'react-apexcharts';
import { 
  TrendingUp, 
  Settings, 
  Activity, 
  RefreshCw, 
  CheckCircle, 
  Database,
  Calendar,
  AlertTriangle,
  Percent,
  Layers,
  Shield,
  Eye,
  Sliders,
  DollarSign
} from 'lucide-react';

function App() {
  const [loading, setLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState({ status: 'offline', date_range: {} });
  const [errorMsg, setErrorMsg] = useState('');
  
  // Backtest Parameters State
  const [params, setParams] = useState({
    p1: 20,
    p2: 60,
    p3: 120,
    er_len: 14,
    std_len: 30,
    entropy_window: 15,
    entropy_bins: 6,
    confirm_entry: 2,
    confirm_exit: 1,
    min_hold_days: 10,
    er_entry: 0.25,
    t_entry: 0.40,
    chikou_thresh: -0.30,
    immunity_thresh: 0.50,
    entropy_thresh: 2.271,
    imo_min_limit: -0.30,
    imo_exit_bull: -0.30,
    roc_gate_limit: -0.20,
    transaction_cost: 0.001
  });

  const [metrics, setMetrics] = useState(null);
  const [trades, setTrades] = useState([]);
  const [timeseries, setTimeseries] = useState([]);

  // TradingView Iframe Widget ref
  const tvContainerRef = useRef(null);

  // Load status and run initial backtest
  useEffect(() => {
    fetchStatus();
    runBacktest();
  }, []);

  // Build TradingView Embed Widget
  useEffect(() => {
    if (tvContainerRef.current) {
      tvContainerRef.current.innerHTML = '';
      const script = document.createElement('script');
      script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
      script.type = 'text/javascript';
      script.async = true;
      script.innerHTML = JSON.stringify({
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
        "calendar": false,
        "support_host": "https://www.tradingview.com"
      });
      tvContainerRef.current.appendChild(script);
    }
  }, [backendStatus]);

  const fetchStatus = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/status');
      if (res.ok) {
        const data = await res.json();
        setBackendStatus(data);
      }
    } catch (e) {
      console.warn("Backend offline", e);
      setBackendStatus({ status: 'offline', date_range: {} });
    }
  };

  const runBacktest = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await fetch('http://127.0.0.1:8000/api/backtest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      });
      if (res.ok) {
        const data = await res.json();
        setMetrics(data.metrics);
        setTrades(data.trades);
        setTimeseries(data.timeseries);
      } else {
        const err = await res.json();
        setErrorMsg(err.detail || "Failed to execute backtest");
      }
    } catch (e) {
      setErrorMsg("Connection to Python API refused. Ensure uvicorn server is running on http://127.0.0.1:8000");
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (name, val) => {
    setParams(prev => ({
      ...prev,
      [name]: val
    }));
  };

  // Prepare Chart Data
  const categories = timeseries.map(d => d.Date);

  // Chart 1: Equity Curve Options
  const equitySeries = [
    {
      name: 'Strategy (Net)',
      data: timeseries.map(d => d.Cum_Strat !== null ? parseFloat((d.Cum_Strat * 100).toFixed(2)) : null)
    },
    {
      name: 'BTC Buy & Hold',
      data: timeseries.map(d => d.Cum_Market !== null ? parseFloat((d.Cum_Market * 100).toFixed(2)) : null)
    }
  ];

  const equityChartOptions = {
    chart: {
      id: 'equity-curve',
      animations: { enabled: false },
      background: 'transparent',
      toolbar: { show: true, tools: { selection: false } }
    },
    theme: { mode: 'dark' },
    colors: ['#00f0ff', '#626f84'],
    stroke: { curve: 'straight', width: 2 },
    xaxis: {
      type: 'datetime',
      categories: categories,
      labels: { style: { colors: '#94a1b2' } },
      axisBorder: { show: false },
      axisTicks: { show: false }
    },
    yaxis: {
      title: { text: 'Cumulative Return (%)', style: { color: '#94a1b2' } },
      labels: { 
        style: { colors: '#94a1b2' },
        formatter: (val) => `${val.toLocaleString()}%`
      }
    },
    grid: { borderColor: '#1e2230', strokeDashArray: 4 },
    tooltip: { x: { format: 'dd MMM yyyy' } },
    legend: { labels: { colors: '#f1f2f6' } }
  };

  // Chart 2: Shannon Entropy & Indicators Options (The main request visual!)
  const indicatorSeries = [
    {
      name: 'IMO (Oscillator)',
      data: timeseries.map(d => d.IMO !== null ? parseFloat(d.IMO.toFixed(4)) : null)
    },
    {
      name: 'Entry Threshold',
      data: timeseries.map(d => d.IMO_Std !== null ? parseFloat((d.IMO_Std * params.t_entry).toFixed(4)) : null)
    },
    {
      name: 'Shannon Entropy',
      data: timeseries.map(d => d.Entropy !== null ? parseFloat(d.Entropy.toFixed(4)) : null)
    },
    {
      name: 'S_Chikou Momentum',
      data: timeseries.map(d => d.S_Chikou !== null ? parseFloat(d.S_Chikou.toFixed(4)) : null)
    }
  ];

  const indicatorChartOptions = {
    chart: {
      id: 'indicators',
      animations: { enabled: false },
      background: 'transparent'
    },
    theme: { mode: 'dark' },
    colors: ['#ff8800', '#626f84', '#c084fc', '#00e5ff'],
    stroke: { curve: 'straight', width: 1.5 },
    xaxis: {
      type: 'datetime',
      categories: categories,
      labels: { style: { colors: '#94a1b2' } }
    },
    yaxis: {
      title: { text: 'Indicator Value', style: { color: '#94a1b2' } },
      labels: { style: { colors: '#94a1b2' } }
    },
    grid: { borderColor: '#1e2230', strokeDashArray: 4 },
    annotations: {
      yaxis: [
        {
          y: params.entropy_thresh,
          borderColor: '#ef4444',
          strokeDashArray: 3,
          label: {
            text: `Entropy Limit (${params.entropy_thresh})`,
            style: { color: '#fff', background: '#ef4444' }
          }
        },
        {
          y: params.chikou_thresh,
          borderColor: '#ff3366',
          strokeDashArray: 3,
          label: {
            text: `Chikou Exit (${params.chikou_thresh})`,
            style: { color: '#fff', background: '#ff3366' }
          }
        }
      ]
    },
    legend: { labels: { colors: '#f1f2f6' } }
  };

  return (
    <div className="app-container">
      {/* Header section */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo">一</div>
          <div className="brand-title">
            <h1>ICHIMOKU QUANT SYSTEM</h1>
            <p>Bitcoin Trend-Following Denoised Quant Backtesting Dashboard</p>
          </div>
        </div>
        
        <div className="status-badge" onClick={fetchStatus} style={{ cursor: 'pointer' }}>
          <div className={`status-dot`} style={{ backgroundColor: backendStatus.status === 'ready' ? '#10b981' : '#ef4444', boxShadow: backendStatus.status === 'ready' ? '0 0 8px #10b981' : '0 0 8px #ef4444' }}></div>
          <span>API Backend: {backendStatus.status === 'ready' ? 'ONLINE' : 'OFFLINE'}</span>
          {backendStatus.date_range?.bars && (
            <span style={{ color: 'var(--color-text-muted)', marginLeft: '8px' }}>
              ({backendStatus.date_range.bars} bars loaded)
            </span>
          )}
        </div>
      </header>

      {errorMsg && (
        <div style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)', padding: '16px', borderRadius: '12px', color: 'var(--accent-danger)', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <AlertTriangle size={20} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Main Grid Layout */}
      <div className="dashboard-grid">
        {/* Param Left Column */}
        <aside className="bento-card">
          <div className="form-title">
            <Sliders size={18} />
            <span>Parameters tuning</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Ichimoku periods */}
            <div>
              <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: 'var(--color-text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Layers size={14} /> Ichimoku Periods
              </h4>
              <div className="param-group">
                <label>Tenkan (p1) <span>{params.p1}</span></label>
                <input type="number" value={params.p1} onChange={e => handleInputChange('p1', parseInt(e.target.value))} />
              </div>
              <div className="param-group">
                <label>Kijun (p2) <span>{params.p2}</span></label>
                <input type="number" value={params.p2} onChange={e => handleInputChange('p2', parseInt(e.target.value))} />
              </div>
              <div className="param-group">
                <label>Senkou B (p3) <span>{params.p3}</span></label>
                <input type="number" value={params.p3} onChange={e => handleInputChange('p3', parseInt(e.target.value))} />
              </div>
            </div>

            {/* Denoising Windows */}
            <div>
              <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: 'var(--color-text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Activity size={14} /> Noise Filters
              </h4>
              <div className="param-group">
                <label>ER Window <span>{params.er_len}</span></label>
                <input type="number" value={params.er_len} onChange={e => handleInputChange('er_len', parseInt(e.target.value))} />
              </div>
              <div className="param-group">
                <label>IMO StdDev Window <span>{params.std_len}</span></label>
                <input type="number" value={params.std_len} onChange={e => handleInputChange('std_len', parseInt(e.target.value))} />
              </div>
              <div className="param-group">
                <label>Entropy Window <span>{params.entropy_window}</span></label>
                <input type="number" value={params.entropy_window} onChange={e => handleInputChange('entropy_window', parseInt(e.target.value))} />
              </div>
              <div className="param-group">
                <label>Entropy Bins <span>{params.entropy_bins}</span></label>
                <input type="number" value={params.entropy_bins} onChange={e => handleInputChange('entropy_bins', parseInt(e.target.value))} />
              </div>
            </div>

            {/* Strategy Gates */}
            <div>
              <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: 'var(--color-text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Shield size={14} /> Denoising Gates
              </h4>
              <div className="param-group">
                <label>Entropy Limit <span>{params.entropy_thresh}</span></label>
                <input type="number" step="0.001" value={params.entropy_thresh} onChange={e => handleInputChange('entropy_thresh', parseFloat(e.target.value))} />
              </div>
              <div className="param-group">
                <label>Chikou Exit Limit <span>{params.chikou_thresh}</span></label>
                <input type="number" step="0.05" value={params.chikou_thresh} onChange={e => handleInputChange('chikou_thresh', parseFloat(e.target.value))} />
              </div>
              <div className="param-group">
                <label>Immunity Threshold <span>{params.immunity_thresh}</span></label>
                <input type="number" step="0.05" value={params.immunity_thresh} onChange={e => handleInputChange('immunity_thresh', parseFloat(e.target.value))} />
              </div>
              <div className="param-group">
                <label>IMO Exit (Bull) <span>{params.imo_exit_bull}</span></label>
                <input type="number" step="0.05" value={params.imo_exit_bull} onChange={e => handleInputChange('imo_exit_bull', parseFloat(e.target.value))} />
              </div>
              <div className="param-group">
                <label>Crash Gate (30d ROC) <span>{params.roc_gate_limit}</span></label>
                <input type="number" step="0.05" value={params.roc_gate_limit} onChange={e => handleInputChange('roc_gate_limit', parseFloat(e.target.value))} />
              </div>
              <div className="param-group">
                <label>TC (Cost %) <span>{(params.transaction_cost * 100).toFixed(2)}%</span></label>
                <input type="number" step="0.0001" value={params.transaction_cost} onChange={e => handleInputChange('transaction_cost', parseFloat(e.target.value))} />
              </div>
            </div>

            <button 
              className="btn-primary" 
              onClick={runBacktest} 
              disabled={loading}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
            >
              {loading ? (
                <>
                  <RefreshCw className="animate-spin" size={16} />
                  <span>Computing...</span>
                </>
              ) : (
                <>
                  <Activity size={16} />
                  <span>RUN BACKTEST</span>
                </>
              )}
            </button>
          </div>
        </aside>

        {/* Dashboard Content Right Column */}
        <main className="dashboard-main">
          {/* Bento Metrik */}
          {metrics && (
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-label">Strategy Total Return</div>
                <div className="metric-value text-success">
                  {metrics['Total Return (%)'].toLocaleString(undefined, { maximumFractionDigits: 2 })}%
                </div>
                <div className="metric-sub">Net after transaction costs</div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Win Rate (%)</div>
                <div className="metric-value text-success">
                  {metrics['Win Rate (%)'].toFixed(1)}%
                </div>
                <div className="metric-sub">{metrics['Number of Trades']} total trades completed</div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Profit Factor</div>
                <div className="metric-value text-success">
                  {metrics['Profit Factor'].toFixed(2)}
                </div>
                <div className="metric-sub">Gross Wins / Gross Losses</div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Max Drawdown</div>
                <div className="metric-value text-danger">
                  {metrics['Max Drawdown (%)'].toFixed(2)}%
                </div>
                <div className="metric-sub">Market: {metrics['Market Max Drawdown (%)'].toFixed(2)}%</div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Sharpe Ratio</div>
                <div className="metric-value text-success">
                  {metrics['Sharpe Ratio'].toFixed(2)}
                </div>
                <div className="metric-sub">Market Sharpe: {metrics['Market Sharpe Ratio'].toFixed(2)}</div>
              </div>

              <div className="metric-card market">
                <div className="metric-label">Buy & Hold Return</div>
                <div className="metric-value">
                  {metrics['Market Total Return (%)'].toLocaleString(undefined, { maximumFractionDigits: 2 })}%
                </div>
                <div className="metric-sub">Benchmark buy & hold return</div>
              </div>
            </div>
          )}

          {/* Interactive ApexCharts */}
          {timeseries.length > 0 && (
            <div className="chart-container">
              <div>
                <h3 className="section-title">
                  <TrendingUp size={20} />
                  <span>Interactive Equity Curves</span>
                </h3>
                <Chart 
                  options={equityChartOptions} 
                  series={equitySeries} 
                  type="line" 
                  height={320} 
                />
              </div>

              <div>
                <h3 className="section-title">
                  <Activity size={20} />
                  <span>Denoised Oscillator Subplots (with Shannon Entropy & S_Chikou)</span>
                </h3>
                <Chart 
                  options={indicatorChartOptions} 
                  series={indicatorSeries} 
                  type="line" 
                  height={320} 
                />
              </div>
            </div>
          )}

          {/* Interactive Widget Row */}
          <div className="widgets-section">
            {/* Historical Trades Log Table */}
            <div className="bento-card table-card">
              <h3 className="section-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Database size={18} />
                  <span>Completed Trades Log</span>
                </div>
                {trades.length > 0 && (
                  <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                    {trades.length} trades recorded
                  </span>
                )}
              </h3>

              <div className="table-wrapper">
                <table className="trades-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Entry Date</th>
                      <th>Entry Price</th>
                      <th>Exit Date</th>
                      <th>Exit Price</th>
                      <th>Return (%)</th>
                      <th>Hold Days</th>
                      <th>Exit Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.length > 0 ? (
                      trades.map(trade => (
                        <tr key={trade.id}>
                          <td>#{trade.id}</td>
                          <td>{trade.entry_date}</td>
                          <td>${trade.entry_price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                          <td>{trade.exit_date}</td>
                          <td>${trade.exit_price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                          <td className={trade.return >= 0 ? "profit" : "loss"}>
                            {trade.return >= 0 ? '+' : ''}{trade.return.toFixed(2)}%
                          </td>
                          <td>{trade.holding_days}d</td>
                          <td>
                            <span className={`badge-reason ${trade.exit_reason.toLowerCase().includes('chikou') ? 'chikou' : 'macro'}`}>
                              {trade.exit_reason}
                            </span>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={8} style={{ textAlign: 'center', padding: '24px', color: 'var(--color-text-muted)' }}>
                          No trades completed within the backtest range.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Live TradingView Widget */}
            <div className="tv-widget-card">
              <h3 className="section-title" style={{ marginBottom: '12px' }}>
                <Eye size={18} />
                <span>Live Reference (BTCUSD)</span>
              </h3>
              <div 
                ref={tvContainerRef} 
                style={{ height: 'calc(100% - 40px)', width: '100%', borderRadius: '12px', overflow: 'hidden' }}
              >
                {/* Embed Loading */}
                <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-muted)' }}>
                  <span>Loading TradingView chart...</span>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
