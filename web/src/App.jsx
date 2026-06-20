import React, { useState, useEffect, useRef } from 'react';
import Chart from 'react-apexcharts';
import { createChart, LineStyle, CandlestickSeries, LineSeries, createSeriesMarkers, PriceScaleMode } from 'lightweight-charts';

// --- CUSTOM BESPOKE INLINE SVG PRIMITIVES ---
const IconSettings = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="4" y1="21" x2="4" y2="14" />
    <line x1="4" y1="10" x2="4" y2="3" />
    <line x1="12" y1="21" x2="12" y2="12" />
    <line x1="12" y1="8" x2="12" y2="3" />
    <line x1="20" y1="21" x2="20" y2="16" />
    <line x1="20" y1="12" x2="20" y2="3" />
    <line x1="1" y1="14" x2="7" y2="14" />
    <line x1="9" y1="8" x2="15" y2="8" />
    <line x1="17" y1="16" x2="23" y2="16" />
  </svg>
);

const IconTrending = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
    <polyline points="17 6 23 6 23 12" />
  </svg>
);

const IconAlert = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);

const IconDatabase = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <ellipse cx="12" cy="5" rx="9" ry="3" />
    <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
    <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3" />
  </svg>
);

const IconRefresh = ({ className }) => (
  <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
  </svg>
);

function App() {
  const [loading, setLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState({ status: 'offline', date_range: {} });
  const [errorMsg, setErrorMsg] = useState('');
  
  // UI Expand States
  const [paramsExpanded, setParamsExpanded] = useState(false); // Collapsible parameter tuning sidebar (default hide)
  const [isLogScale, setIsLogScale] = useState(false); // Log/Lin toggle for BTC Chart

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

    // Common chart options matching Off-White Minimalist UI
    const chartOptions = {
      width: width,
      layout: {
        background: { type: 'solid', color: '#ffffff' },
        textColor: '#2f3437',
        fontSize: 11,
        fontFamily: 'Geist Mono, SF Mono, monospace'
      },
      grid: {
        vertLines: { color: '#eaeaea', style: 2 },
        horzLines: { color: '#eaeaea', style: 2 }
      },
      rightPriceScale: {
        borderColor: '#eaeaea',
        textColor: '#2f3437',
        minimumWidth: 80 // Aligned Y-axis widths
      },
      timeScale: {
        borderColor: '#eaeaea',
        textColor: '#2f3437'
      },
      crosshair: {
        vertLine: { color: '#888888', width: 1, style: 1 },
        horzLine: { color: '#888888', width: 1, style: 1 }
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

    // Apply Logarithmic / Linear mode dynamically
    priceChart.priceScale('right').applyOptions({
      mode: isLogScale ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal,
      minimumWidth: 80
    });

    // 3. Create Oscillator Chart (Lower Pane)
    const oscChart = createChart(oscChartRef.current, {
      ...chartOptions,
      height: 220
    });

    chartsRef.current = { priceChart, oscChart };

    // --- POPULATE PRICE CHART ---
    // Candlestick Series using desaturated pastels
    const candleSeries = priceChart.addSeries(CandlestickSeries, {
      upColor: '#346538',
      downColor: '#9f2f2d',
      borderVisible: false,
      wickUpColor: '#346538',
      wickDownColor: '#9f2f2d'
    });

    const candleData = timeseries.map(d => ({
      time: d.Date,
      open: d.Open !== null ? d.Open : d.Close,
      high: d.High !== null ? d.High : d.Close,
      low: d.Low !== null ? d.Low : d.Close,
      close: d.Close
    })).filter(d => d.open !== null);

    candleSeries.setData(candleData);

    // Ichimoku Lines
    const tenkanSeries = priceChart.addSeries(LineSeries, { color: '#9f2f2d', lineWidth: 1.5, title: 'Tenkan-sen' });
    const kijunSeries = priceChart.addSeries(LineSeries, { color: '#1f6c9f', lineWidth: 1.8, title: 'Kijun-sen' });
    const spanASeries = priceChart.addSeries(LineSeries, { color: 'rgba(52, 101, 56, 0.25)', lineWidth: 1.2, title: 'Span A' });
    const spanBSeries = priceChart.addSeries(LineSeries, { color: 'rgba(159, 47, 45, 0.25)', lineWidth: 1.2, title: 'Span B' });

    tenkanSeries.setData(timeseries.map(d => ({ time: d.Date, value: d.tenkan_sen })).filter(d => d.value !== null));
    kijunSeries.setData(timeseries.map(d => ({ time: d.Date, value: d.kijun_sen })).filter(d => d.value !== null));
    spanASeries.setData(timeseries.map(d => ({ time: d.Date, value: d.senkou_span_a })).filter(d => d.value !== null));
    spanBSeries.setData(timeseries.map(d => ({ time: d.Date, value: d.senkou_span_b })).filter(d => d.value !== null));

    // Traditional Chikou Span (shifted backward by p2 periods)
    const traditionalChikouSeries = priceChart.addSeries(LineSeries, {
      color: 'rgba(107, 33, 168, 0.45)', // Sleek purple pastel
      lineWidth: 1.5,
      title: 'Chikou Span (Lagged)'
    });

    const chikouData = [];
    for (let i = 0; i < timeseries.length; i++) {
      if (i + params.p2 < timeseries.length) {
        chikouData.push({
          time: timeseries[i].Date,
          value: timeseries[i + params.p2].Close
        });
      }
    }
    traditionalChikouSeries.setData(chikouData);

    // Buy/Sell Markers on Candlestick
    const markers = [];
    for (let i = 1; i < timeseries.length; i++) {
      const prev = timeseries[i - 1].Active_Pos;
      const curr = timeseries[i].Active_Pos;
      if (prev === 0 && curr === 1) {
        markers.push({
          time: timeseries[i].Date,
          position: 'belowBar',
          color: '#346538',
          shape: 'arrowUp',
          text: 'BUY'
        });
      } else if (prev === 1 && curr === 0) {
        markers.push({
          time: timeseries[i].Date,
          position: 'aboveBar',
          color: '#9f2f2d',
          shape: 'arrowDown',
          text: 'SELL'
        });
      }
    }
    createSeriesMarkers(candleSeries, markers);

    // --- POPULATE OSCILLATOR CHART ---
    // Composite IMO Series
    const imoSeries = oscChart.addSeries(LineSeries, {
      color: '#d97706',
      lineWidth: 1.8,
      title: 'IMO'
    });
    imoSeries.setData(timeseries.map(d => ({ time: d.Date, value: d.IMO })).filter(d => d.value !== null));

    // Entry Threshold Series (Dashed)
    const threshSeries = oscChart.addSeries(LineSeries, {
      color: '#787774',
      lineWidth: 1.2,
      lineStyle: LineStyle.Dashed,
      title: 'Entry Threshold'
    });
    threshSeries.setData(timeseries.map(d => ({ time: d.Date, value: d.IMO_Std !== null ? d.IMO_Std * params.t_entry : null })).filter(d => d.value !== null));

    // Shannon Entropy Series
    const entropySeries = oscChart.addSeries(LineSeries, {
      color: '#7c3aed',
      lineWidth: 1.5,
      title: 'Entropy'
    });
    entropySeries.setData(timeseries.map(d => ({ time: d.Date, value: d.Entropy })).filter(d => d.value !== null));

    // S_Chikou Momentum Series
    const chikouSeries = oscChart.addSeries(LineSeries, {
      color: '#0891b2',
      lineWidth: 1.2,
      title: 'S_Chikou'
    });
    chikouSeries.setData(timeseries.map(d => ({ time: d.Date, value: d.S_Chikou })).filter(d => d.value !== null));

    // Add Horizontal Price Lines for thresholds (baseline limits)
    entropySeries.createPriceLine({
      price: params.entropy_thresh,
      color: 'rgba(159, 47, 45, 0.4)',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      axisLabelVisible: true,
      title: 'Entropy Limit'
    });

    chikouSeries.createPriceLine({
      price: params.chikou_thresh,
      color: 'rgba(159, 47, 45, 0.4)',
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

    // --- SINKRONISASI CROSSHAIR MOVE (WITH RESET ON MOUSE OUT) ---
    priceChart.subscribeCrosshairMove(param => {
      if (isSyncing) return;
      isSyncing = true;
      if (param && param.time) {
        oscChart.setCrosshairPosition(param.time);
      } else {
        oscChart.clearCrosshairPosition();
      }
      isSyncing = false;
    });

    oscChart.subscribeCrosshairMove(param => {
      if (isSyncing) return;
      isSyncing = true;
      if (param && param.time) {
        priceChart.setCrosshairPosition(param.time);
      } else {
        priceChart.clearCrosshairPosition();
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
  }, [timeseries, params.entropy_thresh, params.chikou_thresh, params.t_entry, isLogScale]);

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

  // Extract latest state from timeseries data
  const latestData = timeseries.length > 0 ? timeseries[timeseries.length - 1] : null;
  
  // Calculate position details
  let entryDate = '';
  let entryPrice = null;
  let holdingDays = 0;
  let unrealizedReturn = 0;
  if (latestData && latestData.Active_Pos === 1) {
    for (let i = timeseries.length - 1; i >= 0; i--) {
      if (timeseries[i].Active_Pos === 0) {
        if (i + 1 < timeseries.length) {
          entryDate = timeseries[i + 1].Date;
          entryPrice = timeseries[i + 1].Close;
          holdingDays = timeseries.length - 1 - i;
          unrealizedReturn = ((latestData.Close - entryPrice) / entryPrice) * 100;
        }
        break;
      }
    }
  }

  // Prepare ApexCharts Equity data (Light Theme)
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
      toolbar: { show: false }
    },
    theme: { mode: 'light' },
    colors: ['#111111', '#888888'],
    stroke: { curve: 'straight', width: 2 },
    xaxis: {
      type: 'datetime',
      categories: categories,
      labels: { style: { colors: '#2f3437', fontFamily: 'Geist Mono, monospace' } },
      axisBorder: { show: false },
      axisTicks: { show: false }
    },
    yaxis: {
      title: { text: 'Cumulative Return (%)', style: { color: '#2f3437', fontFamily: 'Switzer, sans-serif' } },
      labels: { 
        style: { colors: '#2f3437', fontFamily: 'Geist Mono, monospace' },
        formatter: (val) => `${val.toLocaleString()}%`
      }
    },
    grid: { borderColor: '#eaeaea', strokeDashArray: 4 },
    tooltip: { x: { format: 'dd MMM yyyy' } },
    legend: { labels: { colors: '#111111' } }
  };

  return (
    <div className="app-container">
      {/* Header section */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo">一</div>
          <div className="brand-title">
            <h1>Ichimoku Quant</h1>
            <p>Bitcoin Trend-Following Denoising Backtesting Engine</p>
          </div>
        </div>
        
        <div className="status-badge" onClick={fetchStatus} style={{ cursor: 'pointer' }}>
          <div className="status-dot"></div>
          <span>API Backend: {backendStatus.status === 'ready' ? 'ONLINE' : 'OFFLINE'}</span>
          {backendStatus.date_range?.bars && (
            <span style={{ color: 'var(--color-text-muted)', marginLeft: '8px' }}>
              ({backendStatus.date_range.bars} bars)
            </span>
          )}
        </div>
      </header>

      {errorMsg && (
        <div style={{ background: 'var(--badge-danger-bg)', border: '1px solid rgba(159, 47, 45, 0.2)', padding: '16px', borderRadius: '6px', color: 'var(--badge-danger-text)', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <IconAlert />
          <span style={{ fontSize: '14px', fontWeight: '500' }}>{errorMsg}</span>
        </div>
      )}

      {/* Bento Card: Summary Current State (Top Card) */}
      {latestData && (
        <section className="summary-card-top">
          <div className="summary-item">
            <span className="summary-label">BTC Price</span>
            <span className="summary-value">
              ${latestData.Close.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </span>
            <span className="summary-subtext">As of latest historical bar</span>
          </div>

          <div className="summary-item">
            <span className="summary-label">System Position Status</span>
            <span className="summary-value">
              {latestData.Active_Pos === 1 ? (
                <>
                  <span className="m-badge success">Long Position</span>
                </>
              ) : (
                <>
                  <span className="m-badge danger">Flat</span>
                </>
              )}
            </span>
            <span className="summary-subtext">
              {latestData.Active_Pos === 1 
                ? `Entered on ${entryDate} at $${entryPrice?.toLocaleString()} (${holdingDays}d hold, unrealized: +${unrealizedReturn.toFixed(2)}%)`
                : 'Waiting for trend signals'}
            </span>
          </div>

          <div className="summary-item">
            <span className="summary-label">Market Complexity (Entropy)</span>
            <span className="summary-value">
              {latestData.Entropy !== null ? latestData.Entropy.toFixed(3) : 'N/A'}
              {latestData.Entropy !== null && (
                latestData.Entropy < params.entropy_thresh ? (
                  <span className="m-badge success">Stable</span>
                ) : (
                  <span className="m-badge danger">Noisy</span>
                )
              )}
            </span>
            <span className="summary-subtext">
              Entropy limit set at {params.entropy_thresh}
            </span>
          </div>

          <div className="summary-item">
            <span className="summary-label">Denoised Momentum (IMO)</span>
            <span className="summary-value">
              {latestData.IMO !== null ? latestData.IMO.toFixed(3) : 'N/A'}
              {latestData.IMO !== null && (
                latestData.IMO > (latestData.IMO_Std * params.t_entry) ? (
                  <span className="m-badge success">Bullish</span>
                ) : (
                  <span className="m-badge warning">Neutral</span>
                )
              )}
            </span>
            <span className="summary-subtext">
              Signal threshold level at {(latestData.IMO_Std * params.t_entry).toFixed(3)}
            </span>
          </div>
        </section>
      )}

      {/* Main Grid Layout */}
      <div className="dashboard-grid">
        {/* Collapsible Parameter Tuning Sidebar */}
        {!paramsExpanded ? (
          <aside className="sidebar-collapsed">
            <button onClick={() => setParamsExpanded(true)} className="icon-btn-toggle" title="Show parameters">
              <span style={{ fontSize: '16px', fontWeight: 'bold' }}>+</span>
            </button>
            <div className="vertical-text">PARAMETERS</div>
          </aside>
        ) : (
          <aside className="sidebar-expanded">
            <div className="sidebar-header">
              <span className="sidebar-title">Tuning Panel</span>
              <button onClick={() => setParamsExpanded(false)} className="icon-btn-toggle" title="Hide parameters">
                <span style={{ fontSize: '16px', fontWeight: 'bold' }}>-</span>
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {/* Ichimoku periods */}
              <div>
                <span className="param-section-title">
                  <IconSettings /> Ichimoku Periods
                </span>
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
                <span className="param-section-title">
                  <IconSettings /> Noise Filters
                </span>
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
                <span className="param-section-title">
                  <IconSettings /> Denoising Gates
                </span>
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
              >
                {loading ? (
                  <>
                    <IconRefresh className="animate-spin" />
                    <span>Computing...</span>
                  </>
                ) : (
                  <>
                    <span>RUN BACKTEST</span>
                  </>
                )}
              </button>
            </div>
          </aside>
        )}

        {/* Dashboard Content Column */}
        <main className="dashboard-main">
          {/* Bento Metrik */}
          {metrics && (
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-label">Strategy Return</div>
                <div className="metric-value text-success">
                  {metrics['Total Return (%)'].toLocaleString(undefined, { maximumFractionDigits: 2 })}%
                </div>
                <div className="metric-sub">Net after fees</div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Win Rate</div>
                <div className="metric-value text-success">
                  {metrics['Win Rate (%)'].toFixed(1)}%
                </div>
                <div className="metric-sub">{metrics['Number of Trades']} completed trades</div>
              </div>

              <div className="metric-card">
                <div className="metric-label">Profit Factor</div>
                <div className="metric-value text-success">
                  {metrics['Profit Factor'].toFixed(2)}
                </div>
                <div className="metric-sub">Gross win / loss</div>
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
                <div className="metric-sub">Market: {metrics['Market Sharpe Ratio'].toFixed(2)}</div>
              </div>
            </div>
          )}

          {/* Synchronized TradingView Lightweight Charts (Log/Lin Scale Toggle + Aligned Y Axis) */}
          <div className="chart-container">
            <h3 className="section-title">
              <div className="section-title-left">
                <span>TradingView Chart Lite (BTC Daily & Denoising Indicators)</span>
              </div>
              
              {/* Log/Lin Toggle Button */}
              <div className="toggle-btn-group">
                <button 
                  onClick={() => setIsLogScale(false)} 
                  className={`toggle-option-btn ${!isLogScale ? 'active' : ''}`}
                >
                  LIN
                </button>
                <button 
                  onClick={() => setIsLogScale(true)} 
                  className={`toggle-option-btn ${isLogScale ? 'active' : ''}`}
                >
                  LOG
                </button>
              </div>
            </h3>

            {/* Legend indicators overlay */}
            <div className="chart-legend-box">
              <div className="chart-legend-item">
                <span className="legend-color-dot" style={{ backgroundColor: '#9f2f2d' }}></span>
                <span>Tenkan-sen</span>
              </div>
              <div className="chart-legend-item">
                <span className="legend-color-dot" style={{ backgroundColor: '#1f6c9f' }}></span>
                <span>Kijun-sen</span>
              </div>
              <div className="chart-legend-item">
                <span className="legend-color-dot" style={{ backgroundColor: 'rgba(52, 101, 56, 0.45)' }}></span>
                <span>Span A</span>
              </div>
              <div className="chart-legend-item">
                <span className="legend-color-dot" style={{ backgroundColor: 'rgba(159, 47, 45, 0.45)' }}></span>
                <span>Span B</span>
              </div>
              <div className="chart-legend-item">
                <span className="legend-color-dot" style={{ backgroundColor: 'rgba(107, 33, 168, 0.7)' }}></span>
                <span>Chikou Span (Lagged)</span>
              </div>
            </div>
            
            {/* Price Chart Pane */}
            <div style={{ position: 'relative' }}>
              <div 
                ref={priceChartRef} 
                style={{ width: '100%', height: '380px' }}
              />
            </div>

            {/* Gap separator line */}
            <div style={{ height: '1px', background: 'var(--border-muted)' }} />

            {/* Legend for Oscillators */}
            <div className="chart-legend-box">
              <div className="chart-legend-item">
                <span className="legend-color-dot" style={{ backgroundColor: '#d97706' }}></span>
                <span>IMO</span>
              </div>
              <div className="chart-legend-item">
                <span className="legend-color-dot" style={{ backgroundColor: '#787774' }}></span>
                <span>Threshold</span>
              </div>
              <div className="chart-legend-item">
                <span className="legend-color-dot" style={{ backgroundColor: '#7c3aed' }}></span>
                <span>Shannon Entropy</span>
              </div>
              <div className="chart-legend-item">
                <span className="legend-color-dot" style={{ backgroundColor: '#0891b2' }}></span>
                <span>S_Chikou</span>
              </div>
            </div>

            {/* Oscillator Chart Pane */}
            <div style={{ position: 'relative' }}>
              <div 
                ref={oscChartRef} 
                style={{ width: '100%', height: '220px' }}
              />
            </div>
          </div>

          {/* Interactive ApexCharts for Equity comparison */}
          {timeseries.length > 0 && (
            <div className="chart-container">
              <div>
                <h3 className="section-title" style={{ marginBottom: '16px' }}>
                  <div className="section-title-left">
                    <IconTrending />
                    <span>Cumulative Equity Growth</span>
                  </div>
                </h3>
                <Chart 
                  options={equityChartOptions} 
                  series={equitySeries} 
                  type="line" 
                  height={300} 
                />
              </div>
            </div>
          )}

          {/* Historical Trades Log Table */}
          <div className="table-card">
            <h3 className="section-title" style={{ marginBottom: '20px' }}>
              <div className="section-title-left">
                <IconDatabase />
                <span>Completed Trades Log</span>
              </div>
              {trades.length > 0 && (
                <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)' }}>
                  {trades.length} trades total
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
                          <span className={`m-badge ${trade.exit_reason.toLowerCase().includes('chikou') ? 'info' : 'warning'}`}>
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
