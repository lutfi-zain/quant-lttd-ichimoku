import React, { useState, useEffect, useRef } from 'react';
import Chart from 'react-apexcharts';
import { createChart, LineStyle, CandlestickSeries, LineSeries, createSeriesMarkers } from 'lightweight-charts';
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

  // TradingView Lightweight Charts DOM refs
  const priceChartRef = useRef(null);
  const oscChartRef = useRef(null);
  
  // Chart instances references
  const chartsRef = useRef({ priceChart: null, oscChart: null });

  // Load status and run initial backtest
  useEffect(() => {
    fetchStatus();
    runBacktest();
  }, []);

  // Build TradingView Lightweight Charts
  useEffect(() => {
    if (timeseries.length === 0 || !priceChartRef.current || !oscChartRef.current) return;

    // 1. Clean containers
    priceChartRef.current.innerHTML = '';
    oscChartRef.current.innerHTML = '';

    const width = priceChartRef.current.clientWidth;

    // Common chart options
    const chartOptions = {
      width: width,
      layout: {
        background: { type: 'solid', color: '#11131a' },
        textColor: '#94a1b2',
        fontSize: 12,
        fontFamily: 'Outfit, sans-serif'
      },
      grid: {
        vertLines: { color: '#1e2230', style: 2 },
        horzLines: { color: '#1e2230', style: 2 }
      },
      rightPriceScale: {
        borderColor: '#1e2230',
        textColor: '#94a1b2'
      },
      timeScale: {
        borderColor: '#1e2230',
        textColor: '#94a1b2'
      },
      crosshair: {
        vertLine: { color: '#3f4765', width: 1, style: 1 },
        horzLine: { color: '#3f4765', width: 1, style: 1 }
      }
    };

    // 2. Create Price Chart (Upper Pane)
    const priceChart = createChart(priceChartRef.current, {
      ...chartOptions,
      height: 380,
      timeScale: {
        ...chartOptions.timeScale,
        visible: false // Hide time axis on price chart to save vertical space
      }
    });

    // 3. Create Oscillator Chart (Lower Pane)
    const oscChart = createChart(oscChartRef.current, {
      ...chartOptions,
      height: 220
    });

    chartsRef.current = { priceChart, oscChart };

    // --- POPULATE PRICE CHART ---
    // Candlestick Series in v5
    const candleSeries = priceChart.addSeries(CandlestickSeries, {
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444'
    });

    const candleData = timeseries.map(d => ({
      time: d.Date,
      open: d.Open !== null ? d.Open : d.Close,
      high: d.High !== null ? d.High : d.Close,
      low: d.Low !== null ? d.Low : d.Close,
      close: d.Close
    })).filter(d => d.open !== null);

    candleSeries.setData(candleData);

    // Ichimoku Lines in v5
    const tenkanSeries = priceChart.addSeries(LineSeries, { color: '#ef4444', lineWidth: 1.5, title: 'Tenkan-sen' });
    const kijunSeries = priceChart.addSeries(LineSeries, { color: '#2563eb', lineWidth: 2, title: 'Kijun-sen' });
    const spanASeries = priceChart.addSeries(LineSeries, { color: 'rgba(16, 185, 129, 0.4)', lineWidth: 1, title: 'Span A' });
    const spanBSeries = priceChart.addSeries(LineSeries, { color: 'rgba(239, 68, 68, 0.4)', lineWidth: 1, title: 'Span B' });

    tenkanSeries.setData(timeseries.map(d => ({ time: d.Date, value: d.tenkan_sen })).filter(d => d.value !== null));
    kijunSeries.setData(timeseries.map(d => ({ time: d.Date, value: d.kijun_sen })).filter(d => d.value !== null));
    spanASeries.setData(timeseries.map(d => ({ time: d.Date, value: d.senkou_span_a })).filter(d => d.value !== null));
    spanBSeries.setData(timeseries.map(d => ({ time: d.Date, value: d.senkou_span_b })).filter(d => d.value !== null));

    // Buy/Sell Markers on Candlestick
    const markers = [];
    for (let i = 1; i < timeseries.length; i++) {
      const prev = timeseries[i - 1].Active_Pos;
      const curr = timeseries[i].Active_Pos;
      if (prev === 0 && curr === 1) {
        markers.push({
          time: timeseries[i].Date,
          position: 'belowBar',
          color: '#10b981',
          shape: 'arrowUp',
          text: 'BUY'
        });
      } else if (prev === 1 && curr === 0) {
        markers.push({
          time: timeseries[i].Date,
          position: 'aboveBar',
          color: '#ef4444',
          shape: 'arrowDown',
          text: 'SELL'
        });
      }
    }
    createSeriesMarkers(candleSeries, markers);

    // --- POPULATE OSCILLATOR CHART ---
    // Composite IMO Series in v5
    const imoSeries = oscChart.addSeries(LineSeries, {
      color: '#ff8800',
      lineWidth: 2,
      title: 'IMO'
    });
    imoSeries.setData(timeseries.map(d => ({ time: d.Date, value: d.IMO })).filter(d => d.value !== null));

    // Entry Threshold Series in v5
    const threshSeries = oscChart.addSeries(LineSeries, {
      color: '#626f84',
      lineWidth: 1.2,
      lineStyle: LineStyle.Dashed,
      title: 'Entry Threshold'
    });
    threshSeries.setData(timeseries.map(d => ({ time: d.Date, value: d.IMO_Std !== null ? d.IMO_Std * params.t_entry : null })).filter(d => d.value !== null));

    // Shannon Entropy Series in v5
    const entropySeries = oscChart.addSeries(LineSeries, {
      color: '#c084fc',
      lineWidth: 1.5,
      title: 'Entropy'
    });
    entropySeries.setData(timeseries.map(d => ({ time: d.Date, value: d.Entropy })).filter(d => d.value !== null));

    // S_Chikou Momentum Series in v5
    const chikouSeries = oscChart.addSeries(LineSeries, {
      color: '#00e5ff',
      lineWidth: 1.2,
      title: 'S_Chikou'
    });
    chikouSeries.setData(timeseries.map(d => ({ time: d.Date, value: d.S_Chikou })).filter(d => d.value !== null));

    // Add Horizontal Price Lines for thresholds (baseline limits)
    entropySeries.createPriceLine({
      price: params.entropy_thresh,
      color: 'rgba(239, 68, 68, 0.6)',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      axisLabelVisible: true,
      title: 'Entropy Limit'
    });

    chikouSeries.createPriceLine({
      price: params.chikou_thresh,
      color: 'rgba(255, 51, 102, 0.6)',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      axisLabelVisible: true,
      title: 'Chikou Exit'
    });

    // --- SINKRONISASI VISIBLE LOGICAL RANGE (ZOOM / SCROLL) ---
    let isSyncing = false;
    
    priceChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      if (isSyncing) return;
      isSyncing = true;
      oscChart.timeScale().setVisibleLogicalRange(range);
      isSyncing = false;
    });

    oscChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      if (isSyncing) return;
      isSyncing = true;
      priceChart.timeScale().setVisibleLogicalRange(range);
      isSyncing = false;
    });

    // --- SINKRONISASI CROSSHAIR MOVE ---
    priceChart.subscribeCrosshairMove(param => {
      if (isSyncing) return;
      isSyncing = true;
      if (param.time) {
        oscChart.setCrosshairPosition(param.time);
      }
      isSyncing = false;
    });

    oscChart.subscribeCrosshairMove(param => {
      if (isSyncing) return;
      isSyncing = true;
      if (param.time) {
        priceChart.setCrosshairPosition(param.time);
      }
      isSyncing = false;
    });

    // Fit content initially
    priceChart.timeScale().fitContent();

    // Resize observer to make charts fully responsive
    const resizeObserver = new ResizeObserver(entries => {
      if (entries.length === 0) return;
      const { width: newWidth } = entries[0].contentRect;
      priceChart.resize(newWidth, 380);
      oscChart.resize(newWidth, 220);
    });

    resizeObserver.observe(priceChartRef.current);

    return () => {
      resizeObserver.disconnect();
      priceChart.remove();
      oscChart.remove();
    };
  }, [timeseries, params.entropy_thresh, params.chikou_thresh, params.t_entry]);

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

  // Prepare ApexCharts Equity data
  const categories = timeseries.map(d => d.Date);
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

          {/* Synchronized TradingView Lightweight Charts (The main request visual!) */}
          <div className="chart-container" style={{ padding: '20px' }}>
            <h3 className="section-title">
              <Eye size={20} />
              <span>TradingView Chart Lite (Synchronized Candlesticks & Indicators)</span>
            </h3>
            
            {/* Price Chart Pane */}
            <div style={{ position: 'relative' }}>
              <div 
                ref={priceChartRef} 
                style={{ width: '100%', height: '380px' }}
              />
              <div style={{ position: 'absolute', top: '10px', left: '10px', background: 'rgba(17, 19, 26, 0.85)', padding: '6px 12px', borderRadius: '6px', border: '1px solid var(--border-muted)', fontSize: '11px', color: 'var(--color-text-secondary)', display: 'flex', gap: '12px', pointerEvents: 'none', zIndex: 10 }}>
                <span><strong style={{ color: '#fff' }}>BTCUSD Daily</strong></span>
                <span><strong style={{ color: '#ef4444' }}>■</strong> Tenkan-sen</span>
                <span><strong style={{ color: '#2563eb' }}>■</strong> Kijun-sen</span>
                <span><strong style={{ color: '#10b981' }}>■</strong> Span A</span>
                <span><strong style={{ color: '#ef4444' }}>■</strong> Span B</span>
              </div>
            </div>

            {/* Gap/Border separator */}
            <div style={{ height: '1px', background: 'var(--border-muted)', margin: '4px 0' }} />

            {/* Oscillator Chart Pane */}
            <div style={{ position: 'relative' }}>
              <div 
                ref={oscChartRef} 
                style={{ width: '100%', height: '220px' }}
              />
              <div style={{ position: 'absolute', top: '10px', left: '10px', background: 'rgba(17, 19, 26, 0.85)', padding: '6px 12px', borderRadius: '6px', border: '1px solid var(--border-muted)', fontSize: '11px', color: 'var(--color-text-secondary)', display: 'flex', gap: '12px', pointerEvents: 'none', zIndex: 10 }}>
                <span><strong style={{ color: '#ff8800' }}>■</strong> IMO</span>
                <span><strong style={{ color: '#626f84' }}>■</strong> Threshold</span>
                <span><strong style={{ color: '#c084fc' }}>■</strong> Shannon Entropy</span>
                <span><strong style={{ color: '#00e5ff' }}>■</strong> S_Chikou</span>
              </div>
            </div>
          </div>

          {/* Interactive ApexCharts for Equity comparison */}
          {timeseries.length > 0 && (
            <div className="chart-container">
              <div>
                <h3 className="section-title">
                  <TrendingUp size={20} />
                  <span>Cumulative Equity Curves</span>
                </h3>
                <Chart 
                  options={equityChartOptions} 
                  series={equitySeries} 
                  type="line" 
                  height={320} 
                />
              </div>
            </div>
          )}

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
        </main>
      </div>
    </div>
  );
}

export default App;
