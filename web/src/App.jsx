import React, { useState, useEffect, useRef } from 'react';
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
  const [isLogScale, setIsLogScale] = useState(true); // Log/Lin toggle for BTC Chart (default logarithmic)
  const [isMaximized, setIsMaximized] = useState(false); // Fullscreen maximize chart mode

  // Responsive helper for chart heights
  const getChartHeights = (maximized) => {
    const isMobile = window.innerWidth <= 600;
    if (maximized) {
      const pHeight = Math.floor((window.innerHeight - 56) * 0.65);
      const oHeight = window.innerHeight - 56 - pHeight;
      return { priceHeight: pHeight, oscHeight: oHeight, equityHeight: 0 };
    } else {
      return {
        priceHeight: isMobile ? 250 : 350,
        oscHeight: isMobile ? 150 : 200,
        equityHeight: isMobile ? 160 : 220
      };
    }
  };

  // Theme State (default: system)
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('ichimoku-theme') || 'system';
  });
  const [activeTheme, setActiveTheme] = useState('light');

  useEffect(() => {
    localStorage.setItem('ichimoku-theme', theme);
    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = (e) => {
        setActiveTheme(e.matches ? 'dark' : 'light');
      };
      setActiveTheme(mediaQuery.matches ? 'dark' : 'light');
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    } else {
      setActiveTheme(theme);
    }
  }, [theme]);

  useEffect(() => {
    document.documentElement.classList.remove('theme-light', 'theme-dark');
    document.documentElement.classList.add(`theme-${activeTheme}`);
  }, [activeTheme]);

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
    transaction_cost: 0.001,
    start_date: '2018-01-01',
    end_date: ''
  });

  const [metrics, setMetrics] = useState(null);
  const [trades, setTrades] = useState([]);
  const [timeseries, setTimeseries] = useState([]);

  // TradingView Lightweight Charts DOM refs
  const priceChartRef = useRef(null);
  const oscChartRef = useRef(null);
  const equityChartRef = useRef(null);
  const chartContainerRef = useRef(null);
  const chartsRef = useRef({ priceChart: null, oscChart: null, equityChart: null });
  const seriesRef = useRef(null);
  const priceLinesRef = useRef({ entropyLimit: null, chikouExit: null });
  const isMaximizedRef = useRef(isMaximized);
  useEffect(() => {
    isMaximizedRef.current = isMaximized;
  }, [isMaximized]);

  // Load status and run initial backtest
  useEffect(() => {
    fetchStatus();
    runBacktest();
  }, []);

  // Build TradingView Lightweight Charts
  // 1. Chart initialization effect (runs ONCE on mount)
  useEffect(() => {
    if (!priceChartRef.current || !oscChartRef.current || !equityChartRef.current) return;

    const width = chartContainerRef.current?.clientWidth || 800;
    const isDark = activeTheme === 'dark';

    // Common chart options matching Off-White / Dark Minimalist UI
    const chartOptions = {
      width: width,
      layout: {
        background: { type: 'solid', color: isDark ? '#151617' : '#ffffff' },
        textColor: isDark ? '#c7c9d3' : '#2f3437',
        fontSize: 11,
        fontFamily: 'Geist Mono, SF Mono, monospace'
      },
      grid: {
        vertLines: { color: isDark ? '#242528' : '#eaeaea', style: 2 },
        horzLines: { color: isDark ? '#242528' : '#eaeaea', style: 2 }
      },
      rightPriceScale: {
        borderColor: isDark ? '#242528' : '#eaeaea',
        textColor: isDark ? '#c7c9d3' : '#2f3437',
        minimumWidth: 80 // Aligned Y-axis widths
      },
      timeScale: {
        borderColor: isDark ? '#242528' : '#eaeaea',
        textColor: isDark ? '#c7c9d3' : '#2f3437'
      },
      crosshair: {
        vertLine: { color: isDark ? '#6b7280' : '#888888', width: 1, style: 1 },
        horzLine: { color: isDark ? '#6b7280' : '#888888', width: 1, style: 1 }
      }
    };

    const heights = getChartHeights(isMaximizedRef.current);

    // 2. Create Price Chart (Upper Pane)
    const priceChart = createChart(priceChartRef.current, {
      ...chartOptions,
      height: heights.priceHeight,
      timeScale: {
        ...chartOptions.timeScale,
        visible: false // Hide time axis on price chart to save vertical space
      }
    });

    // 3. Create Oscillator Chart (Middle Pane)
    const oscChart = createChart(oscChartRef.current, {
      ...chartOptions,
      height: heights.oscHeight,
      timeScale: {
        ...chartOptions.timeScale,
        visible: false // Hide time axis on oscillator chart to save vertical space
      }
    });

    // 4. Create Cumulative Equity Growth Chart (Lower Pane)
    const equityChart = createChart(equityChartRef.current, {
      ...chartOptions,
      height: heights.equityHeight,
      localization: {
        priceFormatter: price => `${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`
      }
    });

    chartsRef.current = { priceChart, oscChart, equityChart };

    // --- POPULATE PRICE CHART ---
    const candleSeries = priceChart.addSeries(CandlestickSeries, {
      upColor: isDark ? '#10b981' : '#346538',
      downColor: isDark ? '#ef4444' : '#9f2f2d',
      borderVisible: false,
      wickUpColor: isDark ? '#10b981' : '#346538',
      wickDownColor: isDark ? '#ef4444' : '#9f2f2d'
    });

    const tenkanSeries = priceChart.addSeries(LineSeries, { color: isDark ? '#f87171' : '#9f2f2d', lineWidth: 1.5, title: 'Tenkan-sen' });
    const kijunSeries = priceChart.addSeries(LineSeries, { color: isDark ? '#60a5fa' : '#1f6c9f', lineWidth: 1.8, title: 'Kijun-sen' });
    const spanASeries = priceChart.addSeries(LineSeries, { color: isDark ? 'rgba(52, 211, 153, 0.25)' : 'rgba(52, 101, 56, 0.25)', lineWidth: 1.2, title: 'Span A' });
    const spanBSeries = priceChart.addSeries(LineSeries, { color: isDark ? 'rgba(248, 113, 113, 0.25)' : 'rgba(159, 47, 45, 0.25)', lineWidth: 1.2, title: 'Span B' });
    const traditionalChikouSeries = priceChart.addSeries(LineSeries, {
      color: isDark ? 'rgba(168, 85, 247, 0.5)' : 'rgba(107, 33, 168, 0.45)', // Sleek purple pastel
      lineWidth: 1.5,
      title: 'Chikou Span (Lagged)'
    });

    // --- POPULATE OSCILLATOR CHART ---
    const imoSeries = oscChart.addSeries(LineSeries, {
      color: isDark ? '#fbbf24' : '#d97706',
      lineWidth: 1.8,
      title: 'IMO'
    });

    const threshSeries = oscChart.addSeries(LineSeries, {
      color: isDark ? '#9ca3af' : '#787774',
      lineWidth: 1.2,
      lineStyle: LineStyle.Dashed,
      title: 'Entry Threshold'
    });

    const entropySeries = oscChart.addSeries(LineSeries, {
      color: isDark ? '#a78bfa' : '#7c3aed',
      lineWidth: 1.5,
      title: 'Entropy'
    });

    const chikouSeries = oscChart.addSeries(LineSeries, {
      color: isDark ? '#22d3ee' : '#0891b2',
      lineWidth: 1.2,
      title: 'S_Chikou'
    });

    // --- POPULATE CUMULATIVE EQUITY GROWTH CHART ---
    const stratSeries = equityChart.addSeries(LineSeries, {
      color: isDark ? '#00f0ff' : '#111111',
      lineWidth: 2,
      title: 'Strategy (Net)'
    });

    const marketSeries = equityChart.addSeries(LineSeries, {
      color: '#888888',
      lineWidth: 1.5,
      title: 'BTC Buy & Hold'
    });

    seriesRef.current = {
      candle: candleSeries,
      tenkan: tenkanSeries,
      kijun: kijunSeries,
      spanA: spanASeries,
      spanB: spanBSeries,
      traditionalChikou: traditionalChikouSeries,
      imo: imoSeries,
      thresh: threshSeries,
      entropy: entropySeries,
      chikou: chikouSeries,
      strat: stratSeries,
      market: marketSeries
    };

    // --- SINKRONISASI VISIBLE LOGICAL RANGE (ZOOM / SCROLL) ---
    let isSyncing = false;

    priceChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      if (isSyncing) return;
      isSyncing = true;
      oscChart.timeScale().setVisibleLogicalRange(range);
      equityChart.timeScale().setVisibleLogicalRange(range);
      isSyncing = false;
    });

    oscChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      if (isSyncing) return;
      isSyncing = true;
      priceChart.timeScale().setVisibleLogicalRange(range);
      equityChart.timeScale().setVisibleLogicalRange(range);
      isSyncing = false;
    });

    equityChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      if (isSyncing) return;
      isSyncing = true;
      priceChart.timeScale().setVisibleLogicalRange(range);
      oscChart.timeScale().setVisibleLogicalRange(range);
      isSyncing = false;
    });

    // --- SINKRONISASI CROSSHAIR MOVE (WITH RESET ON MOUSE OUT) ---
    priceChart.subscribeCrosshairMove(param => {
      if (isSyncing) return;
      if (param && param.sourceEvent) {
        isSyncing = true;
        if (param.time) {
          oscChart.setCrosshairPosition(undefined, param.time, imoSeries);
          equityChart.setCrosshairPosition(undefined, param.time, stratSeries);
        } else {
          oscChart.clearCrosshairPosition();
          equityChart.clearCrosshairPosition();
        }
        isSyncing = false;
      } else if (!param) {
        isSyncing = true;
        oscChart.clearCrosshairPosition();
        equityChart.clearCrosshairPosition();
        isSyncing = false;
      }
    });

    oscChart.subscribeCrosshairMove(param => {
      if (isSyncing) return;
      if (param && param.sourceEvent) {
        isSyncing = true;
        if (param.time) {
          priceChart.setCrosshairPosition(undefined, param.time, candleSeries);
          equityChart.setCrosshairPosition(undefined, param.time, stratSeries);
        } else {
          priceChart.clearCrosshairPosition();
          equityChart.clearCrosshairPosition();
        }
        isSyncing = false;
      } else if (!param) {
        isSyncing = true;
        priceChart.clearCrosshairPosition();
        equityChart.clearCrosshairPosition();
        isSyncing = false;
      }
    });

    equityChart.subscribeCrosshairMove(param => {
      if (isSyncing) return;
      if (param && param.sourceEvent) {
        isSyncing = true;
        if (param.time) {
          priceChart.setCrosshairPosition(undefined, param.time, candleSeries);
          oscChart.setCrosshairPosition(undefined, param.time, imoSeries);
        } else {
          priceChart.clearCrosshairPosition();
          oscChart.clearCrosshairPosition();
        }
        isSyncing = false;
      } else if (!param) {
        isSyncing = true;
        priceChart.clearCrosshairPosition();
        oscChart.clearCrosshairPosition();
        isSyncing = false;
      }
    });

    // Resize observer to make charts fully responsive
    const resizeObserver = new ResizeObserver(entries => {
      if (entries.length === 0) return;
      const { width: newWidth, height: newHeight } = entries[0].contentRect;
      
      const heights = getChartHeights(isMaximizedRef.current);
      
      priceChart.resize(newWidth, heights.priceHeight);
      oscChart.resize(newWidth, heights.oscHeight);
      equityChart.resize(newWidth, heights.equityHeight);
    });

    if (chartContainerRef.current) {
      resizeObserver.observe(chartContainerRef.current);
    }

    return () => {
      resizeObserver.disconnect();
      priceChart.remove();
      oscChart.remove();
      equityChart.remove();
      chartsRef.current = { priceChart: null, oscChart: null, equityChart: null };
      seriesRef.current = null;
    };
  }, []);

  // Update styles on activeTheme change dynamically
  useEffect(() => {
    const { priceChart, oscChart, equityChart } = chartsRef.current;
    if (!priceChart || !oscChart || !equityChart || !seriesRef.current) return;

    const isDark = activeTheme === 'dark';
    const style = getComputedStyle(document.documentElement);
    const bgCol = style.getPropertyValue('--bg-surface').trim() || (isDark ? '#151617' : '#ffffff');
    const txtCol = style.getPropertyValue('--color-text-secondary').trim() || (isDark ? '#c7c9d3' : '#2f3437');
    const gridCol = style.getPropertyValue('--border-muted').trim() || (isDark ? '#242528' : '#eaeaea');
    const crossCol = style.getPropertyValue('--color-text-muted').trim() || (isDark ? '#6b7280' : '#888888');
    const accentCol = style.getPropertyValue('--accent-button-hover-bg').trim() || (isDark ? '#00f0ff' : '#111111');

    const layoutOptions = {
      background: { type: 'solid', color: bgCol },
      textColor: txtCol,
    };
    const gridOptions = {
      vertLines: { color: gridCol },
      horzLines: { color: gridCol }
    };
    const scaleOptions = {
      borderColor: gridCol,
      textColor: txtCol
    };
    const crosshairOptions = {
      vertLine: { color: crossCol },
      horzLine: { color: crossCol }
    };

    [priceChart, oscChart, equityChart].forEach(chart => {
      chart.applyOptions({
        layout: layoutOptions,
        grid: gridOptions,
        rightPriceScale: scaleOptions,
        timeScale: scaleOptions,
        crosshair: crosshairOptions
      });
    });

    seriesRef.current.candle.applyOptions({
      upColor: isDark ? '#10b981' : '#346538',
      downColor: isDark ? '#ef4444' : '#9f2f2d',
      wickUpColor: isDark ? '#10b981' : '#346538',
      wickDownColor: isDark ? '#ef4444' : '#9f2f2d'
    });
    seriesRef.current.tenkan.applyOptions({ color: isDark ? '#f87171' : '#9f2f2d' });
    seriesRef.current.kijun.applyOptions({ color: isDark ? '#60a5fa' : '#1f6c9f' });
    seriesRef.current.spanA.applyOptions({ color: isDark ? 'rgba(52, 211, 153, 0.25)' : 'rgba(52, 101, 56, 0.25)' });
    seriesRef.current.spanB.applyOptions({ color: isDark ? 'rgba(248, 113, 113, 0.25)' : 'rgba(159, 47, 45, 0.25)' });
    seriesRef.current.traditionalChikou.applyOptions({ color: isDark ? 'rgba(168, 85, 247, 0.5)' : 'rgba(107, 33, 168, 0.45)' });
    seriesRef.current.imo.applyOptions({ color: isDark ? '#fbbf24' : '#d97706' });
    seriesRef.current.thresh.applyOptions({ color: isDark ? '#9ca3af' : '#787774' });
    seriesRef.current.entropy.applyOptions({ color: isDark ? '#a78bfa' : '#7c3aed' });
    seriesRef.current.chikou.applyOptions({ color: isDark ? '#22d3ee' : '#0891b2' });
    seriesRef.current.strat.applyOptions({ color: accentCol });

  }, [activeTheme]);

  // Update scale type
  useEffect(() => {
    const { priceChart } = chartsRef.current;
    if (!priceChart) return;
    priceChart.priceScale('right').applyOptions({
      mode: isLogScale ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal
    });
  }, [isLogScale]);

  // Update sizes when maximized state changes
  useEffect(() => {
    const { priceChart, oscChart, equityChart } = chartsRef.current;
    if (!priceChart || !oscChart || !equityChart || !chartContainerRef.current) return;

    const width = chartContainerRef.current.clientWidth;
    const heights = getChartHeights(isMaximized);

    priceChart.resize(width, heights.priceHeight);
    oscChart.resize(width, heights.oscHeight);
    equityChart.resize(width, heights.equityHeight);

    // Toggle date axis visibility on oscillator chart based on maximized state
    oscChart.timeScale().applyOptions({
      visible: isMaximized
    });
  }, [isMaximized]);

  // Update data and thresholds dynamically
  useEffect(() => {
    const { priceChart, oscChart, equityChart } = chartsRef.current;
    if (!priceChart || !oscChart || !equityChart || !seriesRef.current || timeseries.length === 0) return;

    const isDark = activeTheme === 'dark';
    const {
      candle, tenkan, kijun, spanA, spanB,
      traditionalChikou, imo, thresh, entropy, chikou,
      strat, market
    } = seriesRef.current;

    // Set Candlestick data
    const candleData = timeseries.map(d => ({
      time: d.Date,
      open: d.Open !== null ? d.Open : d.Close,
      high: d.High !== null ? d.High : d.Close,
      low: d.Low !== null ? d.Low : d.Close,
      close: d.Close
    })).filter(d => d.open !== null);
    candle.setData(candleData);

    // Set Ichimoku lines
    tenkan.setData(timeseries.map(d => ({ time: d.Date, value: d.tenkan_sen })).filter(d => d.value !== null));
    kijun.setData(timeseries.map(d => ({ time: d.Date, value: d.kijun_sen })).filter(d => d.value !== null));
    spanA.setData(timeseries.map(d => ({ time: d.Date, value: d.senkou_span_a })).filter(d => d.value !== null));
    spanB.setData(timeseries.map(d => ({ time: d.Date, value: d.senkou_span_b })).filter(d => d.value !== null));

    // Chikou lagged data
    const chikouData = [];
    for (let i = 0; i < timeseries.length; i++) {
      if (i + params.p2 < timeseries.length) {
        chikouData.push({
          time: timeseries[i].Date,
          value: timeseries[i + params.p2].Close
        });
      }
    }
    traditionalChikou.setData(chikouData);

    // Buy/Sell Markers on Candlestick
    const markers = [];
    for (let i = 1; i < timeseries.length; i++) {
      const prev = timeseries[i - 1].Active_Pos;
      const curr = timeseries[i].Active_Pos;
      if (prev === 0 && curr === 1) {
        markers.push({
          time: timeseries[i].Date,
          position: 'belowBar',
          color: isDark ? '#10b981' : '#346538',
          shape: 'arrowUp',
          text: 'BUY'
        });
      } else if (prev === 1 && curr === 0) {
        markers.push({
          time: timeseries[i].Date,
          position: 'aboveBar',
          color: isDark ? '#ef4444' : '#9f2f2d',
          shape: 'arrowDown',
          text: 'SELL'
        });
      }
    }
    createSeriesMarkers(candle, markers);

    // Set Oscillators
    imo.setData(timeseries.map(d => ({ time: d.Date, value: d.IMO })).filter(d => d.value !== null));
    thresh.setData(timeseries.map(d => ({ time: d.Date, value: d.IMO_Std !== null ? d.IMO_Std * params.t_entry : null })).filter(d => d.value !== null));
    entropy.setData(timeseries.map(d => ({ time: d.Date, value: d.Entropy })).filter(d => d.value !== null));
    chikou.setData(timeseries.map(d => ({ time: d.Date, value: d.S_Chikou })).filter(d => d.value !== null));

    // Set Equity curve
    strat.setData(timeseries.map(d => ({ time: d.Date, value: d.Cum_Strat !== null ? parseFloat((d.Cum_Strat * 100).toFixed(2)) : null })).filter(d => d.value !== null));
    market.setData(timeseries.map(d => ({ time: d.Date, value: d.Cum_Market !== null ? parseFloat((d.Cum_Market * 100).toFixed(2)) : null })).filter(d => d.value !== null));

    // Update parameter lines dynamically
    if (priceLinesRef.current.entropyLimit) {
      entropy.removePriceLine(priceLinesRef.current.entropyLimit);
    }
    if (priceLinesRef.current.chikouExit) {
      chikou.removePriceLine(priceLinesRef.current.chikouExit);
    }

    priceLinesRef.current.entropyLimit = entropy.createPriceLine({
      price: params.entropy_thresh,
      color: isDark ? 'rgba(239, 68, 68, 0.4)' : 'rgba(159, 47, 45, 0.4)',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      axisLabelVisible: true,
      title: 'Entropy Limit'
    });

    priceLinesRef.current.chikouExit = chikou.createPriceLine({
      price: params.chikou_thresh,
      color: isDark ? 'rgba(239, 68, 68, 0.4)' : 'rgba(159, 47, 45, 0.4)',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      axisLabelVisible: true,
      title: 'Chikou Exit'
    });

    // Set default zoom to 400 bars (or fit content if dataset has fewer than 400 bars)
    const totalBars = timeseries.length;
    if (totalBars > 0) {
      const defaultZoomBars = 400;
      if (totalBars > defaultZoomBars) {
        const startIndex = totalBars - defaultZoomBars;
        const startTime = timeseries[startIndex].Date;
        const endTime = timeseries[totalBars - 1].Date;
        priceChart.timeScale().setVisibleRange({
          from: startTime,
          to: endTime
        });
      } else {
        priceChart.timeScale().fitContent();
      }
    }
  }, [timeseries, params.entropy_thresh, params.chikou_thresh, params.t_entry, params.p2, activeTheme]);

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/status');
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
      const res = await fetch('/api/backtest', {
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
      setErrorMsg("Connection to Python API refused. Ensure uvicorn server is running.");
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
        
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <div className="theme-toggle-group">
            <button 
              onClick={() => setTheme('system')} 
              className={`theme-option-btn ${theme === 'system' ? 'active' : ''}`}
              aria-label="Use system color theme"
              aria-pressed={theme === 'system'}
            >
              System
            </button>
            <button 
              onClick={() => setTheme('light')} 
              className={`theme-option-btn ${theme === 'light' ? 'active' : ''}`}
              aria-label="Use light color theme"
              aria-pressed={theme === 'light'}
            >
              Light
            </button>
            <button 
              onClick={() => setTheme('dark')} 
              className={`theme-option-btn ${theme === 'dark' ? 'active' : ''}`}
              aria-label="Use dark color theme"
              aria-pressed={theme === 'dark'}
            >
              Dark
            </button>
          </div>

          <div 
            className={`status-badge ${backendStatus.status === 'ready' ? '' : 'offline'}`} 
            onClick={fetchStatus} 
            style={{ cursor: 'pointer' }}
            tabIndex={0}
            role="button"
            aria-label={`API Backend: ${backendStatus.status === 'ready' ? 'ONLINE' : 'OFFLINE'}. Click to check connection.`}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                fetchStatus();
              }
            }}
          >
            <div className="status-dot"></div>
            <span>API Backend: {backendStatus.status === 'ready' ? 'ONLINE' : 'OFFLINE'}</span>
            {backendStatus.date_range?.bars && (
              <span style={{ color: 'var(--color-text-muted)', marginLeft: '8px' }}>
                ({backendStatus.date_range.bars} bars)
              </span>
            )}
          </div>
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
            <button 
              onClick={() => setParamsExpanded(true)} 
              className="icon-btn-toggle" 
              title="Show parameters"
              aria-label="Show strategy parameter tuning panel"
              aria-expanded={false}
            >
              <span style={{ fontSize: '16px', fontWeight: 'bold' }}>+</span>
            </button>
            <div className="vertical-text">PARAMETERS</div>
          </aside>
        ) : (
          <aside className="sidebar-expanded">
            <div className="sidebar-header">
              <span className="sidebar-title">Tuning Panel</span>
              <button 
                onClick={() => setParamsExpanded(false)} 
                className="icon-btn-toggle" 
                title="Hide parameters"
                aria-label="Hide strategy parameter tuning panel"
                aria-expanded={true}
              >
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
                  <label htmlFor="param-p1">Tenkan (p1) <span>{params.p1}</span></label>
                  <input id="param-p1" type="number" value={params.p1} onChange={e => handleInputChange('p1', parseInt(e.target.value))} />
                </div>
                <div className="param-group">
                  <label htmlFor="param-p2">Kijun (p2) <span>{params.p2}</span></label>
                  <input id="param-p2" type="number" value={params.p2} onChange={e => handleInputChange('p2', parseInt(e.target.value))} />
                </div>
                <div className="param-group">
                  <label htmlFor="param-p3">Senkou B (p3) <span>{params.p3}</span></label>
                  <input id="param-p3" type="number" value={params.p3} onChange={e => handleInputChange('p3', parseInt(e.target.value))} />
                </div>
              </div>

              {/* Denoising Windows */}
              <div>
                <span className="param-section-title">
                  <IconSettings /> Noise Filters
                </span>
                <div className="param-group">
                  <label htmlFor="param-er_len">ER Window <span>{params.er_len}</span></label>
                  <input id="param-er_len" type="number" value={params.er_len} onChange={e => handleInputChange('er_len', parseInt(e.target.value))} />
                </div>
                <div className="param-group">
                  <label htmlFor="param-std_len">IMO StdDev Window <span>{params.std_len}</span></label>
                  <input id="param-std_len" type="number" value={params.std_len} onChange={e => handleInputChange('std_len', parseInt(e.target.value))} />
                </div>
                <div className="param-group">
                  <label htmlFor="param-entropy_window">Entropy Window <span>{params.entropy_window}</span></label>
                  <input id="param-entropy_window" type="number" value={params.entropy_window} onChange={e => handleInputChange('entropy_window', parseInt(e.target.value))} />
                </div>
                <div className="param-group">
                  <label htmlFor="param-entropy_bins">Entropy Bins <span>{params.entropy_bins}</span></label>
                  <input id="param-entropy_bins" type="number" value={params.entropy_bins} onChange={e => handleInputChange('entropy_bins', parseInt(e.target.value))} />
                </div>
              </div>

              {/* Strategy Gates */}
              <div>
                <span className="param-section-title">
                  <IconSettings /> Denoising Gates
                </span>
                <div className="param-group">
                  <label htmlFor="param-entropy_thresh">Entropy Limit <span>{params.entropy_thresh}</span></label>
                  <input id="param-entropy_thresh" type="number" step="0.001" value={params.entropy_thresh} onChange={e => handleInputChange('entropy_thresh', parseFloat(e.target.value))} />
                </div>
                <div className="param-group">
                  <label htmlFor="param-chikou_thresh">Chikou Exit Limit <span>{params.chikou_thresh}</span></label>
                  <input id="param-chikou_thresh" type="number" step="0.05" value={params.chikou_thresh} onChange={e => handleInputChange('chikou_thresh', parseFloat(e.target.value))} />
                </div>
                <div className="param-group">
                  <label htmlFor="param-immunity_thresh">Immunity Threshold <span>{params.immunity_thresh}</span></label>
                  <input id="param-immunity_thresh" type="number" step="0.05" value={params.immunity_thresh} onChange={e => handleInputChange('immunity_thresh', parseFloat(e.target.value))} />
                </div>
                <div className="param-group">
                  <label htmlFor="param-imo_exit_bull">IMO Exit (Bull) <span>{params.imo_exit_bull}</span></label>
                  <input id="param-imo_exit_bull" type="number" step="0.05" value={params.imo_exit_bull} onChange={e => handleInputChange('imo_exit_bull', parseFloat(e.target.value))} />
                </div>
                <div className="param-group">
                  <label htmlFor="param-roc_gate_limit">Crash Gate (30d ROC) <span>{params.roc_gate_limit}</span></label>
                  <input id="param-roc_gate_limit" type="number" step="0.05" value={params.roc_gate_limit} onChange={e => handleInputChange('roc_gate_limit', parseFloat(e.target.value))} />
                </div>
                <div className="param-group">
                  <label htmlFor="param-transaction_cost">TC (Cost %) <span>{(params.transaction_cost * 100).toFixed(2)}%</span></label>
                  <input id="param-transaction_cost" type="number" step="0.0001" value={params.transaction_cost} onChange={e => handleInputChange('transaction_cost', parseFloat(e.target.value))} />
                </div>
              </div>

              {/* Backtest Range */}
              <div>
                <span className="param-section-title">
                  <IconSettings /> Backtest Range
                </span>
                <div className="param-group">
                  <label htmlFor="param-start_date">Start Date</label>
                  <input 
                    id="param-start_date"
                    type="date" 
                    value={params.start_date || ''} 
                    onChange={e => handleInputChange('start_date', e.target.value)} 
                  />
                </div>
                <div className="param-group">
                  <label htmlFor="param-end_date">End Date</label>
                  <input 
                    id="param-end_date"
                    type="date" 
                    value={params.end_date || ''} 
                    onChange={e => handleInputChange('end_date', e.target.value)} 
                  />
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

          {/* Multi-Pane Synchronized Charting Suite (Sticked Layout) */}
          <div className={`chart-container ${isMaximized ? 'fullscreen' : ''}`} ref={chartContainerRef} style={{ padding: 0, gap: 0, overflow: 'hidden' }}>
            <h2 className="section-title" style={{ padding: '16px 24px', borderBottom: '1px solid var(--border-muted)', margin: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div className="section-title-left">
                <IconTrending />
                <span>Multi-Pane Strategy Analytics</span>
              </div>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                {/* Log/Lin Toggle Button */}
                <div className="toggle-btn-group">
                  <button 
                    onClick={() => setIsLogScale(false)} 
                    className={`toggle-option-btn ${!isLogScale ? 'active' : ''}`}
                    aria-label="Linear chart scale"
                    aria-pressed={!isLogScale}
                  >
                    LIN
                  </button>
                  <button 
                    onClick={() => setIsLogScale(true)} 
                    className={`toggle-option-btn ${isLogScale ? 'active' : ''}`}
                    aria-label="Logarithmic chart scale"
                    aria-pressed={isLogScale}
                  >
                    LOG
                  </button>
                </div>

                {/* Maximize Toggle Button */}
                <button 
                  onClick={() => setIsMaximized(!isMaximized)}
                  className={`toggle-option-btn ${isMaximized ? 'active' : ''}`}
                  style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}
                  title={isMaximized ? 'Exit Fullscreen' : 'Fullscreen BTC & Oscillator'}
                  aria-label={isMaximized ? 'Restore screen layout' : 'Maximize charts to full screen'}
                  aria-pressed={isMaximized}
                >
                  {isMaximized ? 'RESTORE' : 'MAXIMIZE'}
                </button>
              </div>
            </h2>

            {/* 1. Price Chart Pane */}
            <div style={{ position: 'relative', width: '100%' }}>
              {/* Floating Overlay Legend for Price Chart */}
              <div style={{ position: 'absolute', top: '12px', left: '16px', zIndex: 10, pointerEvents: 'none', display: 'flex', flexDirection: 'column', gap: '4px', background: 'var(--bg-surface)', border: '1px solid var(--border-muted)', padding: '6px 12px', borderRadius: '4px', opacity: 0.9 }}>
                <div style={{ fontSize: '11px', fontWeight: 'bold', color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
                  BTC/USD Price Action & Ichimoku
                </div>
                <div style={{ display: 'flex', gap: '10px', fontSize: '10px', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', flexWrap: 'wrap' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span className="legend-color-dot" style={{ backgroundColor: '#9f2f2d', display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%' }}></span>
                    Tenkan
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span className="legend-color-dot" style={{ backgroundColor: '#1f6c9f', display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%' }}></span>
                    Kijun
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span className="legend-color-dot" style={{ backgroundColor: 'rgba(52, 101, 56, 0.45)', display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%' }}></span>
                    Span A
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span className="legend-color-dot" style={{ backgroundColor: 'rgba(159, 47, 45, 0.45)', display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%' }}></span>
                    Span B
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span className="legend-color-dot" style={{ backgroundColor: 'rgba(107, 33, 168, 0.7)', display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%' }}></span>
                    Chikou (Lagged)
                  </span>
                </div>
              </div>

              <div 
                ref={priceChartRef} 
                style={{ width: '100%', height: `${isMaximized ? Math.floor((window.innerHeight - 56) * 0.65) : 350}px` }}
              />
            </div>

            {/* Gap separator line */}
            <div style={{ height: '1px', background: 'var(--border-muted)', margin: '0' }} />

            {/* 2. Oscillator Chart Pane */}
            <div style={{ position: 'relative', width: '100%' }}>
              {/* Floating Overlay Legend for Oscillator Chart */}
              <div style={{ position: 'absolute', top: '12px', left: '16px', zIndex: 10, pointerEvents: 'none', display: 'flex', flexDirection: 'column', gap: '4px', background: 'var(--bg-surface)', border: '1px solid var(--border-muted)', padding: '6px 12px', borderRadius: '4px', opacity: 0.9 }}>
                <div style={{ fontSize: '11px', fontWeight: 'bold', color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
                  Denoising Gates & Entropy Oscillator
                </div>
                <div style={{ display: 'flex', gap: '10px', fontSize: '10px', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span className="legend-color-dot" style={{ backgroundColor: '#d97706', display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%' }}></span>
                    IMO
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span className="legend-color-dot" style={{ backgroundColor: '#787774', display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%' }}></span>
                    Threshold
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span className="legend-color-dot" style={{ backgroundColor: '#7c3aed', display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%' }}></span>
                    Entropy
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span className="legend-color-dot" style={{ backgroundColor: '#0891b2', display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%' }}></span>
                    S_Chikou
                  </span>
                </div>
              </div>

              <div 
                ref={oscChartRef} 
                style={{ width: '100%', height: `${isMaximized ? (window.innerHeight - 56 - Math.floor((window.innerHeight - 56) * 0.65)) : 200}px` }}
              />
            </div>

            {/* Gap separator line */}
            {(!isMaximized && timeseries.length > 0) && <div style={{ height: '1px', background: 'var(--border-muted)', margin: '0' }} />}

            {/* 3. Cumulative Equity Growth Pane */}
            <div style={{ position: 'relative', width: '100%', display: (isMaximized || timeseries.length === 0) ? 'none' : 'block' }}>
              {/* Floating Overlay Legend for Equity Chart */}
              <div style={{ position: 'absolute', top: '12px', left: '16px', zIndex: 10, pointerEvents: 'none', display: 'flex', flexDirection: 'column', gap: '4px', background: 'var(--bg-surface)', border: '1px solid var(--border-muted)', padding: '6px 12px', borderRadius: '4px', opacity: 0.9 }}>
                <div style={{ fontSize: '11px', fontWeight: 'bold', color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
                  Cumulative Equity Growth
                </div>
                <div style={{ display: 'flex', gap: '10px', fontSize: '10px', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span className="legend-color-dot" style={{ backgroundColor: activeTheme === 'dark' ? '#00f0ff' : '#111111', display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%' }}></span>
                    Strategy (Net)
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span className="legend-color-dot" style={{ backgroundColor: '#888888', display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%' }}></span>
                    BTC Buy & Hold
                  </span>
                </div>
              </div>

              <div 
                ref={equityChartRef} 
                style={{ width: '100%', height: '220px' }}
              />
            </div>
          </div>

          {/* Standalone Historical Trades Log Table */}
          <div className="table-card">
            <h2 className="section-title" style={{ marginBottom: '20px' }}>
              <div className="section-title-left">
                <IconDatabase />
                <span>Completed Trades Log</span>
              </div>
              {trades.length > 0 && (
                <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)' }}>
                  {trades.length} trades total
                </span>
              )}
            </h2>

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
