# ============================================================
#   INDICATORS.PY — Calcolo indicatori tecnici avanzati
# ============================================================

import pandas as pd
import numpy as np


# ─────────────────────────────────────────────
#   EMA
# ─────────────────────────────────────────────
def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


# ─────────────────────────────────────────────
#   RSI
# ─────────────────────────────────────────────
def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    avg_g = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_l = loss.ewm(com=period - 1, min_periods=period).mean()
    rs    = avg_g / avg_l
    return 100 - (100 / (1 + rs))


def rsi_divergence(df: pd.DataFrame, rsi_series: pd.Series, lookback: int = 20) -> str | None:
    """
    Rileva divergenze RSI classiche e nascoste.
    Returns: 'bullish', 'bearish', 'hidden_bullish', 'hidden_bearish', None
    """
    price = df['close']
    if len(price) < lookback:
        return None

    # Ultimi N valori
    p = price.iloc[-lookback:]
    r = rsi_series.iloc[-lookback:]

    p_min_idx = p.idxmin()
    p_max_idx = p.idxmax()
    r_at_pmin = r.loc[p_min_idx]
    r_at_pmax = r.loc[p_max_idx]

    last_p = p.iloc[-1]
    last_r = r.iloc[-1]

    # Divergenza bullish: prezzo fa LL ma RSI fa HL
    if last_p <= p.min() * 1.002 and last_r > r_at_pmin + 3:
        return "bullish"

    # Divergenza bearish: prezzo fa HH ma RSI fa LH
    if last_p >= p.max() * 0.998 and last_r < r_at_pmax - 3:
        return "bearish"

    return None


# ─────────────────────────────────────────────
#   MACD
# ─────────────────────────────────────────────
def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    ema_fast   = ema(series, fast)
    ema_slow   = ema(series, slow)
    macd_line  = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram  = macd_line - signal_line
    return {
        "macd":      macd_line,
        "signal":    signal_line,
        "histogram": histogram,
    }


def macd_cross(macd_data: dict) -> str | None:
    """Rileva incrocio MACD recente. Returns: 'bullish', 'bearish', None"""
    h = macd_data["histogram"]
    if len(h) < 2:
        return None
    if h.iloc[-1] > 0 and h.iloc[-2] <= 0:
        return "bullish"
    if h.iloc[-1] < 0 and h.iloc[-2] >= 0:
        return "bearish"
    return None


# ─────────────────────────────────────────────
#   ATR
# ─────────────────────────────────────────────
def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high  = df['high']
    low   = df['low']
    close = df['close']
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


# ─────────────────────────────────────────────
#   ADX — Forza del trend
# ─────────────────────────────────────────────
def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high  = df['high']
    low   = df['low']
    close = df['close']

    plus_dm  = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs()
    ], axis=1).max(axis=1)

    atr_val   = tr.ewm(span=period, adjust=False).mean()
    plus_di   = 100 * plus_dm.ewm(span=period,  adjust=False).mean() / atr_val
    minus_di  = 100 * minus_dm.ewm(span=period, adjust=False).mean() / atr_val
    dx        = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di))
    return dx.ewm(span=period, adjust=False).mean()


# ─────────────────────────────────────────────
#   BOLLINGER BANDS
# ─────────────────────────────────────────────
def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> dict:
    mid   = series.rolling(period).mean()
    std   = series.rolling(period).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    width = (upper - lower) / mid   # bandwidth normalizzata
    return {"upper": upper, "mid": mid, "lower": lower, "width": width}


# ─────────────────────────────────────────────
#   VWAP
# ─────────────────────────────────────────────
def vwap(df: pd.DataFrame) -> pd.Series:
    typical = (df['high'] + df['low'] + df['close']) / 3
    vol     = df['volume'].replace(0, np.nan)
    cum_tp_vol = (typical * vol).cumsum()
    cum_vol    = vol.cumsum()
    return cum_tp_vol / cum_vol


# ─────────────────────────────────────────────
#   STOCHASTIC RSI
# ─────────────────────────────────────────────
def stoch_rsi(series: pd.Series, rsi_period: int = 14, stoch_period: int = 14) -> dict:
    r     = rsi(series, rsi_period)
    min_r = r.rolling(stoch_period).min()
    max_r = r.rolling(stoch_period).max()
    k     = 100 * (r - min_r) / (max_r - min_r + 1e-10)
    d     = k.rolling(3).mean()
    return {"k": k, "d": d}


# ─────────────────────────────────────────────
#   VOLUME ANALYSIS
# ─────────────────────────────────────────────
def volume_spike(df: pd.DataFrame, lookback: int = 20, threshold: float = 1.8) -> bool:
    """True se il volume attuale è > threshold * media volume recente"""
    if 'volume' not in df.columns:
        return False
    vol     = df['volume']
    avg_vol = vol.iloc[-lookback:-1].mean()
    if avg_vol == 0:
        return False
    return vol.iloc[-1] > avg_vol * threshold


def volume_trend(df: pd.DataFrame, lookback: int = 5) -> str:
    """Ritorna 'increasing', 'decreasing', 'flat'"""
    if 'volume' not in df.columns:
        return "flat"
    vol = df['volume'].iloc[-lookback:]
    slope = np.polyfit(range(len(vol)), vol.values, 1)[0]
    avg   = vol.mean()
    if slope > avg * 0.05:
        return "increasing"
    if slope < -avg * 0.05:
        return "decreasing"
    return "flat"
