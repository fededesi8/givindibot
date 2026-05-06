# ============================================================
#   FILTERS.PY — Sessioni, volatilità, pattern, filtri
# ============================================================

import pandas as pd
import numpy as np
from datetime import datetime, timezone


# ─────────────────────────────────────────────
#   SESSIONI OPERATIVE
# ─────────────────────────────────────────────

def get_current_session() -> list:
    """Restituisce le sessioni attive in questo momento (UTC)."""
    hour = datetime.now(timezone.utc).hour
    active = []
    if 7  <= hour < 16: active.append("london")
    if 13 <= hour < 22: active.append("new_york")
    if 0  <= hour < 7:  active.append("asia")
    if 13 <= hour < 16: active.append("london_ny_overlap")  # overlap = massima liquidità
    return active


def is_good_session(asset_type: str) -> tuple[bool, str]:
    """
    Verifica se la sessione attuale è adatta per fare trading.
    Returns: (is_good: bool, session_name: str)
    """
    sessions = get_current_session()

    if asset_type == "gold":
        # XAU/USD: ottimo durante Londra e NY, specialmente overlap
        if "london_ny_overlap" in sessions:
            return True, "London-NY Overlap 🔥"
        if "london" in sessions:
            return True, "London Session 🇬🇧"
        if "new_york" in sessions:
            return True, "New York Session 🗽"
        return False, "Low Liquidity"

    elif asset_type == "crypto":
        # Crypto: attivo 24/7 ma meglio durante apertura NY e overlap
        if "london_ny_overlap" in sessions:
            return True, "London-NY Overlap 🔥"
        if "new_york" in sessions:
            return True, "New York Session 🗽"
        if "london" in sessions:
            return True, "London Session 🇬🇧"
        # Crypto accettabile anche in Asia ma con score ridotto
        if "asia" in sessions:
            return True, "Asia Session 🌏"
        return True, "Off Session"   # crypto sempre attivo

    return False, "Unknown"


# ─────────────────────────────────────────────
#   FILTRO VOLATILITÀ
# ─────────────────────────────────────────────

def is_volatile_enough(df: pd.DataFrame, min_atr_pct: float = 0.001) -> bool:
    """
    Verifica che il mercato non sia in una fase piatta/laterale.
    min_atr_pct = ATR minimo espresso come % del prezzo.
    """
    from indicators import atr as calc_atr
    atr_val = calc_atr(df).iloc[-1]
    price   = df['close'].iloc[-1]
    return (atr_val / price) >= min_atr_pct


def is_ranging_market(df: pd.DataFrame, lookback: int = 20) -> bool:
    """
    True se il mercato è laterale (bassa direzionalità).
    Usa ADX < 20 come filtro anti-ranging.
    """
    from indicators import adx as calc_adx
    adx_val = calc_adx(df).iloc[-1]
    return adx_val < 20


# ─────────────────────────────────────────────
#   FILTRO SPREAD / CANDELE ANOMALE
# ─────────────────────────────────────────────

def has_anomalous_candle(df: pd.DataFrame) -> bool:
    """
    True se la candela attuale è anomala (spike, doji gigante, ecc.).
    Evita entrate in momenti di manipolazione.
    """
    c     = df.iloc[-1]
    body  = abs(c['close'] - c['open'])
    total = c['high'] - c['low']
    if total == 0:
        return True

    # Candela con shadow > 4x il corpo → spike anomalo
    upper = c['high'] - max(c['close'], c['open'])
    lower = min(c['close'], c['open']) - c['low']
    if upper > body * 4 or lower > body * 4:
        return True

    # Volume 0 su una candela grande → dati anomali
    if 'volume' in df.columns and df['volume'].iloc[-1] == 0 and total > 0:
        return True

    return False


# ─────────────────────────────────────────────
#   CANDLESTICK PATTERNS
# ─────────────────────────────────────────────

def detect_patterns(df: pd.DataFrame) -> list:
    """
    Rileva pattern di conferma sull'ultima candela.
    Returns: lista di pattern trovati (stringhe)
    """
    patterns = []
    if len(df) < 3:
        return patterns

    c    = df.iloc[-1]
    prev = df.iloc[-2]
    pp   = df.iloc[-3]

    body  = abs(c['close'] - c['open'])
    total = c['high'] - c['low']
    if total == 0:
        return patterns

    upper_shadow = c['high'] - max(c['close'], c['open'])
    lower_shadow = min(c['close'], c['open']) - c['low']

    # ── PIN BAR BULLISH ──
    if (lower_shadow > body * 2.5 and
            lower_shadow > upper_shadow * 2 and
            c['close'] > c['open']):
        patterns.append("bullish_pin_bar")

    # ── PIN BAR BEARISH ──
    if (upper_shadow > body * 2.5 and
            upper_shadow > lower_shadow * 2 and
            c['close'] < c['open']):
        patterns.append("bearish_pin_bar")

    # ── ENGULFING BULLISH ──
    if (c['close'] > c['open'] and
            prev['close'] < prev['open'] and
            c['open']  < prev['close'] and
            c['close'] > prev['open']):
        patterns.append("bullish_engulfing")

    # ── ENGULFING BEARISH ──
    if (c['close'] < c['open'] and
            prev['close'] > prev['open'] and
            c['open']  > prev['close'] and
            c['close'] < prev['open']):
        patterns.append("bearish_engulfing")

    # ── HAMMER ──
    if (lower_shadow >= body * 2 and
            upper_shadow <= body * 0.5 and
            body > 0):
        patterns.append("hammer")

    # ── SHOOTING STAR ──
    if (upper_shadow >= body * 2 and
            lower_shadow <= body * 0.5 and
            body > 0):
        patterns.append("shooting_star")

    # ── DOJI (indecisione — non usare come entry) ──
    if body <= total * 0.1:
        patterns.append("doji")

    return patterns


def bullish_patterns(patterns: list) -> list:
    return [p for p in patterns if p in ("bullish_pin_bar", "bullish_engulfing", "hammer")]


def bearish_patterns(patterns: list) -> list:
    return [p for p in patterns if p in ("bearish_pin_bar", "bearish_engulfing", "shooting_star")]


# ─────────────────────────────────────────────
#   EMA TREND FILTER
# ─────────────────────────────────────────────

def ema_trend(df: pd.DataFrame) -> str:
    """
    Analizza il trend basandosi su EMA 20/50/200.
    Returns: 'bullish', 'bearish', 'neutral'
    """
    from indicators import ema as calc_ema
    e20  = calc_ema(df['close'], 20).iloc[-1]
    e50  = calc_ema(df['close'], 50).iloc[-1]
    e200 = calc_ema(df['close'], 200).iloc[-1]
    price = df['close'].iloc[-1]

    if price > e20 > e50 > e200:
        return "bullish"
    if price < e20 < e50 < e200:
        return "bearish"
    if price > e20 > e50:
        return "bullish"
    if price < e20 < e50:
        return "bearish"
    return "neutral"
