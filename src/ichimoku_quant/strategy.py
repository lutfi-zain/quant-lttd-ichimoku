import pandas as pd
import numpy as np

# === HYPER-TUNED DENOISING PARAMETERS ===
# Derived from combining Ichimoku Filtering with Momentum Exit (Chikou)
SMOOTH_LEN = 7          # Ehler SuperSmoother window (baked into features.py)
CONFIRM_ENTRY = 2       # Consecutive bars confirming entry signal
CONFIRM_EXIT = 1        # Fast exit (no delay once momentum drops)
MIN_HOLD_DAYS = 10      # Minimum holding period before exit allowed
ER_ENTRY = 0.25         # Efficiency Ratio minimum for entry (fractal filter)
T_ENTRY = 0.40          # Entry threshold: IMO > T_ENTRY * rolling_std

# Momentum Exit Parameters
CHIKOU_THRESH = -0.30   # Exit if S_Chikou (momentum relative to 60 days) drops below this
IMMUNITY_THRESH = 0.50  # Ignore S_Chikou drops if IMO > 0.50 (Extreme Bull Market)

# Entropy Noise Gate (Entropy & Information Family)
ENTROPY_THRESH = 2.271  # Block entry signals if rolling 15d return entropy > this (6 bins)

# Cloud-based dynamic exit parameters
IMO_MIN_LIMIT = -0.30      # Maintain exit immunity above cloud if IMO >= this
IMO_EXIT_BULL = -0.30      # Lower macro exit threshold above cloud
ROC_GATE_LIMIT = -0.20     # Disable immunity if 30d ROC is below this (crash gate)

def generate_signals(df: pd.DataFrame,
                     confirm_entry=2,
                     confirm_exit=1,
                     min_hold_days=10,
                     er_entry=0.25,
                     t_entry=0.40,
                     chikou_thresh=-0.30,
                     immunity_thresh=0.50,
                     entropy_thresh=2.271,
                     imo_min_limit=-0.30,
                     imo_exit_bull=-0.30,
                     roc_gate_limit=-0.20) -> pd.DataFrame:
    """
    Clean binary denoised signal generator.

    Architecture (multi-principle, from lz-technical-indicator-architect):
    - Layer 1: Ehler SuperSmoother (spectral/filtering) — baked in features.py
    - Layer 2: Efficiency Ratio gate (fractal family) — entry only
    - Layer 3: Adaptive Volatility Threshold — entry level
    - Layer 4: S_Chikou Momentum Drop (volatility/momentum family) — exit level
    - Layer 5: Signal Persistence / Confirmation bars — reduces whipsaws
    - Layer 6: Minimum Hold Period — prevents rapid exit after entry

    Result: Binary Pos (0.0 = flat, 1.0 = positioned).
    Target profile: High return (~69,000%) with ~27-31 trades and very low exit lag.
    """
    if 'IMO' not in df.columns or 'ER' not in df.columns or 'IMO_Std' not in df.columns or 'Entropy' not in df.columns or 'senkou_span_a' not in df.columns or 'senkou_span_b' not in df.columns:
        raise ValueError("Required columns (IMO, ER, IMO_Std, Entropy, senkou_span_a, senkou_span_b) not found.")

    df = df.copy()

    pos = 0.0
    signals = []
    regimes = []
    confirm_count = 0
    hold_days = 0
    intent = None

    for _, row in df.iterrows():
        imo = row['IMO']
        er = row['ER']
        std = row['IMO_Std']
        chikou = row.get('S_Chikou', 0.0)
        entropy = row.get('Entropy', 0.0)
        close = row['Close']
        cloud_a = row['senkou_span_a']
        cloud_b = row['senkou_span_b']

        if pd.isna(imo) or pd.isna(er) or pd.isna(std) or pd.isna(entropy):
            signals.append(pos)
            regimes.append('Neutral' if pos == 0 else 'Positioned')
            continue

        threshold = std * t_entry

        if pos > 0:
            hold_days += 1
        else:
            hold_days = 0

        can_exit = hold_days >= min_hold_days

        if pos == 0.0:
            # ENTRY: requires IMO above adaptive threshold AND sufficient ER AND low entropy
            # AND price must be above the bottom of the Ichimoku Cloud (Cloud Gate trend filter)
            cloud_min = np.minimum(cloud_a, cloud_b) if (not pd.isna(cloud_a) and not pd.isna(cloud_b)) else (cloud_a if not pd.isna(cloud_a) else (cloud_b if not pd.isna(cloud_b) else np.nan))
            gate_pass = True
            if not pd.isna(cloud_min):
                gate_pass = (close >= cloud_min)

            if imo > threshold and er > er_entry and entropy < entropy_thresh and gate_pass:
                if intent != 1.0:
                    intent = 1.0
                    confirm_count = 1
                else:
                    confirm_count += 1
                if confirm_count >= confirm_entry:
                    pos = 1.0
                    confirm_count = 0
                    hold_days = 0
                    intent = None
            else:
                intent = None
                confirm_count = 0

        else:  # pos == 1.0
            # EXIT: Early exit if momentum drops (S_Chikou) OR macro trend dies
            exit_signal = False
            if can_exit:
                cloud_max = np.maximum(cloud_a, cloud_b) if (not pd.isna(cloud_a) and not pd.isna(cloud_b)) else np.nan
                is_above_cloud = (not pd.isna(cloud_max) and close >= cloud_max)
                
                # Check crash gate
                roc_gate = row.get('roc_gate', 0.0)
                is_not_crashing = (roc_gate >= roc_gate_limit)
                
                # Dynamic immunity
                is_immune = (imo >= immunity_thresh)
                if is_above_cloud and is_not_crashing:
                    is_immune = is_immune or (imo >= imo_min_limit)
                
                # Dynamic macro exit threshold
                current_macro_exit_th = 0.0
                if is_above_cloud and is_not_crashing:
                    current_macro_exit_th = imo_exit_bull
                
                if chikou < chikou_thresh and not is_immune:
                    exit_signal = True
                elif imo < current_macro_exit_th:
                    exit_signal = True
            
            if exit_signal:
                if intent != 0.0:
                    intent = 0.0
                    confirm_count = 1
                else:
                    confirm_count += 1
                if confirm_count >= confirm_exit:
                    pos = 0.0
                    confirm_count = 0
                    hold_days = 0
                    intent = None
            else:
                intent = None
                confirm_count = 0

        signals.append(pos)

        # Regime label for display
        if pos == 1.0:
            regime = 'Strong Bull' if imo > threshold else 'Weak Bull'
        else:
            regime = 'Neutral'
        regimes.append(regime)

    df['Pos'] = signals
    df['Regime'] = regimes
    return df
