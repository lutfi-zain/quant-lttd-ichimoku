import numpy as np
import pandas as pd

def compute_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift(1)).abs()
    tr3 = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=window).mean()

def ehler_supersmoother(series: pd.Series, length: int = 7) -> pd.Series:
    """
    Ehler's SuperSmoother Filter (Spectral / Filtering family).
    Removes high-frequency noise below 'length' cycle period without lag penalty.
    """
    a1 = np.exp(-1.414 * np.pi / length)
    b1 = 2 * a1 * np.cos(np.radians(1.414 * 180.0 / length))
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3

    vals = series.ffill().fillna(0).values
    filt = np.zeros(len(vals))
    filt[0] = vals[0]
    if len(vals) > 1:
        filt[1] = vals[1]
    for i in range(2, len(vals)):
        filt[i] = c1 * (vals[i] + vals[i-1]) / 2 + c2 * filt[i-1] + c3 * filt[i-2]
    return pd.Series(filt, index=series.index)

def shannon_entropy(series: pd.Series, window: int = 15, bins: int = 6) -> pd.Series:
    """
    Shannon Entropy of rolling returns (Entropy & Information family).
    Measures the randomness/complexity of the price return distribution.
    """
    def calc_shannon(x):
        if len(x) < window:
            return np.nan
        counts, _ = np.histogram(x, bins=bins)
        probs = counts / len(x)
        probs = probs[probs > 0]
        return -np.sum(probs * np.log2(probs))
    
    returns = series.pct_change().fillna(0)
    return returns.rolling(window=window).apply(calc_shannon, raw=True)

def generate_ichimoku_features(df: pd.DataFrame, p1=20, p2=60, p3=120, er_len=14, std_len=30, entropy_window=15, entropy_bins=6) -> pd.DataFrame:
    """
    Generates hyper-tuned Ichimoku components.
    - Macro periods (20, 60, 120) calibrated for 24/7 crypto market
    - Ehler SuperSmoother applied on final IMO for noise reduction
    - Efficiency Ratio (Fractal family) for trend strength gate
    """
    df = df.copy()
    df['ATR'] = compute_atr(df, p2)

    # Base Ichimoku lines
    df['tenkan_sen'] = (df['High'].rolling(p1).max() + df['Low'].rolling(p1).min()) / 2
    df['kijun_sen'] = (df['High'].rolling(p2).max() + df['Low'].rolling(p2).min()) / 2

    df['senkou_span_a_raw'] = (df['tenkan_sen'] + df['kijun_sen']) / 2
    df['senkou_span_b_raw'] = (df['High'].rolling(p3).max() + df['Low'].rolling(p3).min()) / 2

    df['senkou_span_a'] = df['senkou_span_a_raw'].shift(p2)
    df['senkou_span_b'] = df['senkou_span_b_raw'].shift(p2)

    # Normalized components (tanh → bounded [-1, 1])
    df['S_TK'] = np.tanh((df['tenkan_sen'] - df['kijun_sen']) / df['ATR'])

    cloud_max = np.maximum(df['senkou_span_a'], df['senkou_span_b'])
    cloud_min = np.minimum(df['senkou_span_a'], df['senkou_span_b'])
    dist_cloud = np.zeros(len(df))
    above = df['Close'] > cloud_max
    below = df['Close'] < cloud_min
    dist_cloud[above] = (df['Close'] - cloud_max)[above] / df['ATR'][above]
    dist_cloud[below] = (df['Close'] - cloud_min)[below] / df['ATR'][below]
    df['S_Cloud'] = np.tanh(dist_cloud)

    df['S_Future'] = np.tanh((df['senkou_span_a_raw'] - df['senkou_span_b_raw']) / df['ATR'])
    raw_chikou_dist = (df['Close'] - df['Close'].shift(p2)) / df['ATR']
    smoothed_chikou_dist = ehler_supersmoother(raw_chikou_dist, length=4)
    df['S_Chikou'] = np.tanh(smoothed_chikou_dist)

    # Composite IMO (raw)
    imo_raw = (df['S_TK'] + df['S_Cloud'] + df['S_Future'] + df['S_Chikou']) / 4.0

    # Apply Ehler SuperSmoother (noise reduction without lag)
    df['IMO'] = ehler_supersmoother(imo_raw, length=7)
    df['IMO_Std'] = df['IMO'].rolling(std_len).std()

    # Efficiency Ratio (Fractal family — trend vs noise measure)
    change = df['Close'].diff().abs()
    volatility = change.rolling(er_len).sum()
    direction = df['Close'].diff(er_len).abs()
    df['ER'] = direction / volatility

    # Shannon Entropy (Entropy family — randomness filter)
    df['Entropy'] = shannon_entropy(df['Close'], window=entropy_window, bins=entropy_bins)

    # Price ROC for exit crash gate (30 days lookback)
    df['roc_gate'] = df['Close'].pct_change(periods=30).fillna(0)

    df['fwd_ret_1d'] = np.log(df['Close'].shift(-1) / df['Close'])
    return df
