# Research: Ichimoku Noise Sources & Denoising Techniques

## Summary

Ichimoku's components are **midpoint-based moving averages** — not EMA/SMA but a midpoint-of-HL statistic that acts as a simple center-of-range estimator. This makes it inherently a low-pass smoother, but its lag-to-smoothing tradeoff is poor for high-volatility 24/7 markets like crypto. Modern denoising approaches (Ehlers filters, wavelets, Kalman) can be applied *to the Ichimoku inputs* or *replacing Ichimoku's smoothing stage* to reduce whipsaw while preserving trend detection.

## Findings

### 1. Ichimoku Components: Statistical Identity

Ichimoku lines are **not** traditional moving averages. They are **midpoint-of-range statistics**: `(max(high, N) + min(low, N)) / 2`.

- **Tenkan-sen**: midpoint of 9-period high/low range
- **Kijun-sen**: midpoint of 26-period high/low range  
- **Senkou Span A**: midpoint of Tenkan and Kijun (averaged), then displaced 26 periods forward
- **Senkou Span B**: midpoint of 52-period high/low range, displaced 26 forward
- **Chikou Span**: close displaced 26 periods back

Statistical classification: These are **range-midpoint smoothers** — related to the concept of a trimmed-mean or midrange estimator. They discard closing price extremes and use only the center of the high-low range. This is a form of **nonlinear smoothing** (not FIR, not IIR in the traditional DSP sense), but resembles a **rank-order filter** limited to the 50th percentile of the range. [Wikipedia](https://en.wikipedia.org/wiki/Ichimoku_Kink%C5%8D_Hy%C5%8D) | [dummies.com](https://www.dummies.com/article/business-careers-money/personal-finance/investing/investment-vehicles/stocks/what-is-the-ichimoku-cloud-trading-strategy-266322)

**Key insight**: Ichimoku uses `(H+L)/2` instead of close. This waters down wild price extremes compared to close-based MAs, producing "stair-step" appearance. It's a deliberate noise-rejection choice — but creates a **step function** that can lag badly in fast moves. [Tradeciety](https://tradeciety.com/ichimoku-cloud-versus-moving-averages)

### 2. Known Noise Sources in Ichimoku

| Noise Source | Mechanism | Crypto Impact |
|---|---|---|
| **Whipsaw at TK crossovers** | Short-period midpoint (Tenkan) oscillates rapidly in ranging markets | Severe — crypto has extended chop periods |
| **Cloud flattening in consolidation** | Span B (52-period midpoint) produces flat lines, color flips repeatedly | Causes false buy/sell cycling |
| **Default settings mismatch** | 9-26-52 designed for 6-day Japanese stock week; meaningless for 24/7 crypto | Amplifies all noise issues |
| **Midpoint step-function lag** | Range midpoint can't track fast directional moves | Late entries on sudden pumps/dumps |
| **26-period forward displacement** | Future cloud projections are stale in volatile conditions | Support/resistance zones shift too slowly |

Sources: [Mudrex](https://mudrex.com/learn/ichimoku-cloud-crypto-trading) | [Binance Academy](https://www.binance.com/en/academy/articles/ichimoku-clouds-explained) | [StockCharts](https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/ichimoku-cloud-trading-strategies)

### 3. Practical Evidence: Ichimoku Backtest Performance

- **Journal of Technical Analysis**: 53.7% win rate on forex majors (2000-2020); risk-adjusted returns beat SMA crossovers by 18%. [TradeAlgo](https://www.tradealgo.com/trading-guides/technical-analysis/ichimoku-cloud-the-complete-guide-to-the-all-in-one-trading-indicator)
- **Daily charts**: 14% higher signal accuracy vs hourly charts; ~22% noise reduction. [TradeAlgo]
- **EconStor paper (US stocks)**: Ichimoku outperforms MA(2,12) and random entry in terms of risk-adjusted returns and R². But no statistically significant positive t-statistic found in recession periods post-2008. [EconStor PDF](https://www.econstor.eu/bitstream/10419/305863/1/id496.pdf)
- **TEJ Taiwan backtest**: 23.55% annualized return, Sharpe 1.38, β 0.66 on 5-year Taiwan stocks. [TEJ](https://www.tejwin.com/en/insight/tquant-lab-ichimoku-kinko-hyo)
- **Deng et al. (2020)**: Profitable on stock indices, NOT on currencies. Suggests combining with additional indicators. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9558011)

### 4. Denoising Approaches — Comparison

#### A. Ehlers Filters (DSP-based)

- **SuperSmoother**: 2nd/3rd order IIR low-pass filter. Near-zero lag in passband. Cuts high-frequency noise better than EMA. [MESA Software](https://www.mesasoftware.com/papers/UltimateSmoother.pdf)
- **UltimateSmoother (2024)**: Ehlers' latest — "EMA killer" with zero lag in passband. Evolution of SuperSmoother. [Traders Tips](https://www.traders.com/Documentation/FEEDbk_docs/2025/06/TradersTips.html)
- **Highpass Filter**: Removes trend, isolates cycles. Good for regime detection before Ichimoku. [Thinkorswim](https://toslc.thinkorswim.com/center/reference/Tech-Indicators/studies-library/E-F/EhlersHighpassFilter)
- **Laguerre Filters**: Exceptional smoothing for long-wavelength (trend) components. Ideal for trend trading. [MESA Software](https://www.mesasoftware.com/TechnicalArticles.htm)
- **Cybernetic Oscillator**: Combines highpass + SuperSmoother + normalizing. Filters 95% of noise per Ehlers claims. [YouTube/Trendline Project](https://www.youtube.com/watch?v=j8TvUbGYYZs)

**Application to Ichimoku**: Replace `(H+L)/2` midpoint with SuperSmoother or UltimateSmoother output. Or pre-filter price data through Ehlers Highpass+Lowpass before computing Ichimoku lines. The Rust library `advanced-ichimoku-cloud` already demonstrates Hull MA replacing the midpoint. [GitHub](https://github.com/RMANOV/advanced-ichimoku-cloud)

#### B. Kalman Filter

- Recursive estimator minimizing mean-square error of residual. Works well when system state can be modeled.
- **Limitation for finance**: Financial time series are non-stationary and nonlinear — hard to define state equations. Works better as a secondary filter than standalone. [PMC/WSEAS](https://wseas.com/journals/bae/2022/a765107-015(2022).pdf) | [PMC/NCBI](https://pmc.ncbi.nlm.nih.gov/articles/PMC8070264)
- **Best use**: Track the "true price" under Kalman, then compute Ichimoku on Kalman-smoothed price series.

#### C. Wavelet Denoising

- Decompose signal via DWT (Daubechies wavelets, order 6 common), apply shrinkage to coefficients, reconstruct.
- Preserves both time and frequency information — superior to FFT for non-stationary financial data.
- Hard/soft shrinkage thresholds remove noise while retaining trend features. [Roncalli/Amundi PDF](http://www.thierry-roncalli.com/download/lwp-tf.pdf)
- **Combined with LSTM**: Wavelet + Kalman sequential denoising improves LSTM prediction accuracy on stock data. [WSEAS](https://wseas.com/journals/bae/2022/a765107-015(2022).pdf)

#### D. Hull Moving Average (HMA)

- `HMA(n) = WMA(√n, 2×WMA(n/2, x) - WMA(n, x))`
- ~50% lag reduction vs standard MAs. Applied as direct midpoint replacement in enhanced Ichimoku. [Alan Hull](https://alanhull.com/the-hull-moving-average) | [GitHub](https://github.com/RMANOV/advanced-ichimoku-cloud)

#### E. Roncalli Framework (Academic)

Comprehensive review of trend filtering for momentum strategies. Categorizes methods as:

- **Linear**: Kalman, Hodrick-Prescott, Baxter-King, Butterworth
- **Non-linear**: Wavelet, Hodrick-Prescott with varying λ, empirical mode decomposition
- Calibrated via prediction error minimization or benchmark estimator comparison. [SSRN/Roncalli](https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID2289097_code903940.pdf?abstractid=2289097)

### 5. Crypto-Specific Limitations

1. **Default settings wrong for 24/7**: 9-26-52 was built for 6-day J-stock week. Crypto traders commonly use **10-30-60** or **20-60-120**. [Binance Academy](https://www.binance.com/en/academy/articles/ichimoku-clouds-explained) | [Changelly](https://changelly.com/blog/ichimoku-cloud-for-crypto-trading)
2. **Extreme volatility**: 5-10% intraday swings make cloud thick → larger risk exposure → position sizing must adapt. [Mudrex](https://mudrex.com/learn/ichimoku-cloud-crypto-trading)
3. **Lagging in fast moves**: Sudden pumps/liquidations outrun Ichimoku confirmation speed. Need faster entry indicators (EMA, momentum oscillators) layered on top. [Mudrex](https://mudrex.com/learn/ichimoku-cloud-crypto-trading)
4. **Flat/choppy markets**: Cloud flattens and flips color → constant false signals. ATR/Volume filters essential. [Changelly](https://changelly.com/blog/ichimoku-cloud-for-crypto-trading)
5. **Shorter timeframes**: Ichimoku on <4H charts produces excessive noise and false signals. [BingX](https://bingx.com/en/learn/article/what-is-ichimoku-cloud-strategy-how-to-use-in-crypto-trading)
6. **No volume component**: Ichimoku is purely price-based. Must supplement with OBV, VWAP, or volume filters for crypto. [Multiple sources]

### 6. Recommended Architecture for Crypto Ichimoku

Based on findings, a layered denoising approach:

```
Raw OHLC → [Stage 1: Pre-denoise] → [Stage 2: Ichimoku on denoised] → [Stage 3: Signal confirmation]

Stage 1 options:
  a) Ehlers SuperSmoother / UltimateSmoother on close
  b) Kalman filter on close → use filtered close as source
  c) Wavelet denoising (Daubechies-4/6, soft shrinkage)

Stage 2:
  - Replace (H+L)/2 with (H+L)/2 smoothed through Hull MA or Ehlers filter
  - Or compute Ichimoku on wavelet-cleaned OHLC
  - Use crypto-optimized periods: 10-30-60 or 20-60-120

Stage 3:
  - ADX filter (trend strength > 25 to confirm)
  - Volume confirmation (above moving average volume)
  - ATR-based position sizing (cloud thickness ↔ risk)
```

## Sources

- **Kept**: [Wikipedia - Ichimoku Kinkō Hyō](https://en.wikipedia.org/wiki/Ichimoku_Kink%C5%8D_Hy%C5%8D) — canonical component definitions
- **Kept**: [Mudrex - Ichimoku Crypto](https://mudrex.com/learn/ichimoku-cloud-crypto-trading) — best crypto-specific pitfalls
- **Kept**: [Binance Academy - Ichimoku Settings](https://www.binance.com/en/academy/articles/ichimoku-clouds-explained) — 10-30-60 / 20-60-120 adaptations
- **Kept**: [TradeAlgo - Complete Guide](https://www.tradealgo.com/trading-guides/technical-analysis/ichimoku-cloud-the-complete-guide-to-the-all-in-one-trading-indicator) — 53.7% win rate stat, timeframe accuracy data
- **Kept**: [EconStor - Ichimoku US stocks](https://www.econstor.eu/bitstream/10419/305863/1/id496.pdf) — academic backtest, mixed recession results
- **Kept**: [TEJ - Taiwan backtest](https://www.tejwin.com/en/insight/tquant-lab-ichimoku-kinko-hyo) — 23.5% annualized, Sharpe 1.38
- **Kept**: [GitHub - advanced-ichimoku-cloud](https://github.com/RMANOV/advanced-ichimoku-cloud) — Hull MA replacing midpoint, working reference implementation
- **Kept**: [MESA Software - Ehlers papers](https://www.mesasoftware.com/TechnicalArticles.htm) — SuperSmoother, Laguerre, UltimateSmoother
- **Kept**: [UltimateSmoother PDF](https://www.mesasoftware.com/papers/UltimateSmoother.pdf) — Ehlers filter math
- **Kept**: [Roncalli/Amundi - Trend Filtering](http://www.thierry-roncalli.com/download/lwp-tf.pdf) — comprehensive wavelet/Kalman/HP review
- **Kept**: [WSEAS - Wavelet+Kalman+LSTM](https://wseas.com/journals/bae/2022/a765107-015(2022).pdf) — noise elimination improves ML on financial data
- **Kept**: [PMC - Wavelet denoising stocks](https://pmc.ncbi.nlm.nih.gov/articles/PMC8070264) — comparative denoising methods
- **Kept**: [dummies.com - Ichimoku internals](https://www.dummies.com/article/business-careers-money/personal-finance/investing/investment-vehicles/stocks/what-is-the-ichimoku-cloud-trading-strategy-266322) — "moving midpoints" vs "moving averages" distinction
- **Kept**: [Tradeciety - Ichimoku vs MA](https://tradeciety.com/ichimoku-cloud-versus-moving-averages) — comparison analysis
- **Kept**: [StockCharts - Whipsaw examples](https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/ichimoku-cloud-trading-strategies) — concrete whipsaw examples
- **Kept**: [Alan Hull - HMA](https://alanhull.com/the-hull-moving-average) — HMA math
- **Kept**: [Thinkorswim - Ehlers Highpass](https://toslc.thinkorswim.com/center/reference/Tech-Indicators/studies-library/E-F/EhlersHighpassFilter) — filter description
- **Kept**: [Oanda - Ichimoku Guide](https://www.oanda.com/us-en/trade-tap-blog/analysis/technical/ichimoku-cloud-trading-guide-key-strategies) — noise filtering claims
- **Kept**: [Changelly - Crypto Ichimoku](https://changelly.com/blog/ichimoku-cloud-for-crypto-trading) — 24/7 specific advice
- **Dropped**: Investopedia — repetitive, no additional data beyond what others provide
- **Dropped**: BingX — generic FAQ, no unique research value
- **Dropped**: Bitsgap — marketing-focused, thin on methodology
- **Dropped**: LuxAlgo — promotional, no backtest data

## Gaps

1. **No dedicated academic paper on Ichimoku + noise reduction found.** All noise-reduction literature (wavelet, Kalman, Ehlers) exists independently of Ichimoku. The combination is practitioner/trading-view territory only. This is a genuine research gap — opportunity for original contribution.

2. **No backtest comparing raw Ichimoku vs denoised-Ichimoku on BTC.** The `advanced-ichimoku-cloud` GitHub repo exists but lacks published benchmark results. Need to build our own backtest.

3. **Optimal crypto-period calibration unclear.** Sources suggest 10-30-60 and 20-60-120 but no rigorous optimization study exists. Our project should grid-search these.

4. **Wavelet mother-function selection for crypto price data** not established. Most finance papers use Daubechies order 4-6, but crypto's extreme kurtosis may favor different choices.

5. **Real-time feasibility of Kalman/wavelet** on streaming 1-min BTC data — latency implications unknown. Ehlers filters (IIR-based) are likely more practical for live trading.

## Supervisor coordination

None needed — research complete. Ready for backtest design phase.
