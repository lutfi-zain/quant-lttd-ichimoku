# Code Context — Ichimoku Noise Analysis

## Files Retrieved

1. `src/ichimoku_quant/features.py` (lines 1-83) — All indicators: Ichimoku lines, normalization, Ehler SuperSmoother, Efficiency Ratio, composite IMO
2. `src/ichimoku_quant/strategy.py` (lines 1-97) — Signal generator with 6-layer denoising, state machine for entry/exit
3. `src/ichimoku_quant/backtest.py` (lines 1-72) — Vectorized PnL, transaction costs, metrics

## Component Analysis

### Traditional Ichimoku Parts (Clustering Family)

| Component | Code Location | Math Type |
|-----------|--------------|-----------|
| Tenkan-sen (p1=20) | `features.py:22` | Midpoint of highest high / lowest low over 20 bars |
| Kijun-sen (p2=60) | `features.py:23` | Same over 60 bars |
| Senkou Span A (Cloud top/bottom) | `features.py:25` | Average of Tenkan+Kijun, shifted forward p2 bars |
| Senkou Span B (Cloud) | `features.py:26` | 120-bar midpoint, shifted forward |
| Chikou (lagged close) | `features.py:31-32` | Close vs Close shifted back 60 bars, normalized by ATR |

All five traditional components present. Periods calibrated for 24/7 crypto (20/60/120 vs classic 9/26/52).

### Noise-Producing Components (Signal Churn Sources)

**1. Tenkan-sen oscillation** (`features.py:22`)

- 20-bar lookback = fast. At BTC volatility, Tenkan flips frequently.
- **Family:** Moving midpoint (windowed extremum). Not smoothing — it's a bracket average.
- **Noise role:** Drives `S_TK` whipsaws directly.

**2. S_TK raw** (`features.py:28`)

- `tanh((Tenkan - Kijun) / ATR)` — zero-crossings create entry/exit flicker.
- **Family:** Normalized distance ratio (bounded by tanh).
- **Noise role:** Primary state-change driver. Tanh helps but doesn't eliminate near-zero crossings.

**3. S_Cloud** (`features.py:29-35`)

- Discontinuous: zero when price is inside cloud, jumps when price exits cloud edge.
- **Family:** Spatial position indicator (binary-like with soft gradient).
- **Noise role:** Cloud edge proximity = flicker zone. Price bouncing cloud edge → repeated on/off.

**4. S_Future** (`features.py:37`)

- `tanh((senkou_a_raw - senkou_b_raw) / ATR)` — cloud thickness indicator.
- **Family:** Forward-projected spread measure.
- **Noise role:** Low noise (slow-moving, 60/120 periods), but sudden cloud twists cause step changes.

**5. Composite IMO averaging** (`features.py:38`)

- Simple equal-weight average of 4 components. No adaptive weighting.
- **Family:** Unweighted ensemble.
- **Noise role:** Amplifies disagreement — if 3/4 agree but 1 flickers, IMO oscillates.

### Noise Reduction Mechanisms (What's Already There)

| Mechanism | Location | Type | Effect |
|-----------|----------|------|--------|
| **Ehler SuperSmoother** on final IMO | `features.py:40` | Spectral filter (2-pole IIR) | Removes sub-7-bar oscillation without phase lag. Key denoiser. |
| **Ehler SuperSmoother** on S_Chikou | `features.py:32` | Spectral filter (length=4) | Smooths momentum signal before tanh. |
| **tanh normalization** | `features.py:28,30,37,32` | Bounded nonlinearity | Clips extreme values, prevents single component from dominating. |
| **ATR normalization** | `features.py:28,30,31,37` | Volatility scaling | Makes signals regime-independent. |
| **Efficiency Ratio gate** | `strategy.py:17` | Fractal filter (ER > 0.25) | Blocks entries in choppy markets. |
| **Adaptive threshold** | `strategy.py:18,62` | Volatility-gated entry | Entry requires IMO > T_ENTRY × rolling_std. |
| **Confirmation bars** | `strategy.py:12-13` | Signal persistence (2 for entry, 1 for exit) | Requires N consecutive bars of same signal. |
| **Minimum hold period** | `strategy.py:14` | Time lockout (10 days) | Prevents rapid exit after entry. |
| **Immunity threshold** | `strategy.py:19,75` | Override rule | Ignores Chikou drop if IMO > 0.50. |

### Remaining Noise Gaps (NOT Addressed)

1. **No regime-aware component weighting.** `features.py:38` uses `1/4 equal weight` for all 4 components. In trending markets, Cloud + Future dominate; in ranging, Tenkan + Chikou dominate. Fixed weight = suboptimal in both regimes.

2. **No Chikou-slope filter.** Exit relies on `S_Chikou < -0.30` absolute level (`strategy.py:73`). Does not check whether Chikou is *decelerating* (second derivative) — only checks level. Falling Chikou from +0.8 to -0.35 in one bar triggers exit even if overall trend intact.

3. **No ATR regime change detection.** ATR is used for normalization only (`features.py:28-37`). Sudden ATR expansion (crash/crash recovery) makes all tanh signals collapse toward zero, temporarily disabling the signal generator. No separate regime switch detector.

4. **Cloud twist detector absent.** `senkou_span_a` and `senkou_span_b` crossing = cloud twist. Currently only distance matters (`S_Future`). Twist events are historically significant entry/exit signals in traditional Ichimoku — not captured.

5. **No multi-timeframe confirmation.** All signals from single daily timeframe. Traditional Ichimoku analysis uses weekly/monthly for macro context. Single-TF system blind to higher-TF trend alignment.

6. **Confirmation bars asymmetric (2 vs 1).** Entry needs 2 bars (`strategy.py:12`), exit needs 1 (`strategy.py:13`). Exit is intentionally fast — but this means a single bad bar after 10+ days can exit. `CONFIRM_EXIT=1` provides zero noise reduction on exits.

7. **No position sizing / Kelly.** Binary in/out (`strategy.py:71,84`). No scaling based on signal strength (IMO magnitude) or confidence.

8. **Transaction cost model flat.** `backtest.py:21` uses fixed 0.1%. Real BTC costs vary with volatility, exchange, order size.

9. **p1/p2/p3 hardcoded, not adaptive.** Periods 20/60/120 are fixed (`features.py:18`). Classical Ichimoku adapts periods to timeframe. No lookback optimization or fractal period selection.

10. **ER length mismatch.** ER computed over `er_len=14` bars (`features.py:18`), but trend signal uses 60/120-bar components. Short ER window may not capture the right noise/trend ratio for the signals it gates.

## Architecture Summary

```
features.py (pure function)
  ├─ ATR(p2=60)                          ─── volatility base
  ├─ Tenkan(p1), Kijun(p2), Cloud(p2,p3) ─── traditional Ichimoku
  ├─ S_TK, S_Cloud, S_Future, S_Chikou   ─── tanh-normalized components
  ├─ IMO = avg(4 components)              ─── composite
  ├─ IMO = EhlerSupersmoother(IMO, 7)    ─── final denoise
  └─ ER = direction/volatility           ─── fractal gate

strategy.py (state machine, loop over rows)
  ├─ Entry: IMO > T_ENTRY*std AND ER > 0.25 AND 2 confirm bars
  ├─ Exit: Chikou < -0.30 (unless IMO > 0.50) OR IMO < 0
  └─ Constraints: 10-day min hold, CONFIRM_EXIT=1

backtest.py (vectorized PnL)
  ├─ Active_Pos = Pos.shift(1)           ─── signal delay
  ├─ Transaction cost = |ΔPos| * 0.001
  └─ Metrics: Sharpe, MDD, trade count
```

## Start Here

`strategy.py` — This is the decision layer. All noise gaps manifest as signal quality problems here. Fix priority:

1. Adaptive component weighting (regime detection → weighted IMO)
2. Chikou second-derivative exit filter
3. `CONFIRM_EXIT` increase from 1 to 2

## Clarification Questions for Implementation Confidence

1. **Target trade count vs return?** Current system targets ~27-31 trades over full history. Adding confirmation bars + higher CONFIRM_EXIT will reduce trades further. What's acceptable minimum?

2. **ER mismatch intentional?** ER window (14) vs Ichimoku periods (20/60/120). Should ER length match signal timeframe (60+)?

3. **Cloud twist as explicit signal?** Traditional Ichimoku uses twist as entry trigger. Add as 5th component or separate gate?

4. **Multi-TF in scope?** Weekly Ichimoku as macro filter? This would add significant complexity.

5. **Position sizing scope?** Binary is simpler. Kelly/fractional sizing adds risk management but also complexity and curve-fitting risk.

6. **Data availability?** System assumes daily OHLCV. S_Chikou uses Close.shift(60) — need 120+ bars of history before any signal. What's the minimum dataset length?
