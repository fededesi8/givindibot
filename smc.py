# ============================================================
#   SMC.PY — Supply & Demand + Smart Money Concepts
# ============================================================

import pandas as pd
import numpy as np


# ─────────────────────────────────────────────
#   MARKET STRUCTURE
# ─────────────────────────────────────────────

def get_swing_points(df: pd.DataFrame, lookback: int = 5) -> dict:
    """
    Identifica swing high e swing low.
    Un pivot high = massimo locale (più alto dei N precedenti e successivi).
    """
    highs  = df['high'].values
    lows   = df['low'].values
    n      = len(highs)
    pivots = {"highs": [], "lows": []}

    for i in range(lookback, n - lookback):
        if all(highs[i] > highs[i - j] for j in range(1, lookback + 1)) and \
           all(highs[i] > highs[i + j] for j in range(1, lookback + 1)):
            pivots["highs"].append((i, highs[i]))

        if all(lows[i] < lows[i - j] for j in range(1, lookback + 1)) and \
           all(lows[i] < lows[i + j] for j in range(1, lookback + 1)):
            pivots["lows"].append((i, lows[i]))

    return pivots


def detect_market_structure(df: pd.DataFrame, lookback: int = 5) -> dict:
    """
    Analizza la struttura del mercato:
    - trend: 'bullish', 'bearish', 'ranging'
    - last_bos: ultimo Break of Structure
    - last_choch: ultimo Change of Character
    """
    pivots = get_swing_points(df, lookback)
    highs  = pivots["highs"]
    lows   = pivots["lows"]

    result = {
        "trend":      "ranging",
        "last_bos":   None,
        "last_choch": None,
        "hh_hl":      False,
        "lh_ll":      False,
    }

    if len(highs) < 2 or len(lows) < 2:
        return result

    # Ultimi 2 swing high e low
    sh1, sh2 = highs[-2][1], highs[-1][1]   # penultimo, ultimo swing high
    sl1, sl2 = lows[-2][1],  lows[-1][1]    # penultimo, ultimo swing low

    # HH + HL = bullish
    if sh2 > sh1 and sl2 > sl1:
        result["trend"]  = "bullish"
        result["hh_hl"]  = True
        result["last_bos"] = ("bullish_bos", sh2)

    # LH + LL = bearish
    elif sh2 < sh1 and sl2 < sl1:
        result["trend"]  = "bearish"
        result["lh_ll"]  = True
        result["last_bos"] = ("bearish_bos", sl2)

    # CHOCH: struttura che cambia direzione
    elif sh2 > sh1 and sl2 < sl1:
        result["trend"]     = "bearish"
        result["last_choch"] = ("bearish_choch", sl2)

    elif sh2 < sh1 and sl2 > sl1:
        result["trend"]     = "bullish"
        result["last_choch"] = ("bullish_choch", sh2)

    return result


# ─────────────────────────────────────────────
#   FAIR VALUE GAP (FVG / IMBALANCE)
# ─────────────────────────────────────────────

def find_fvg(df: pd.DataFrame, lookback: int = 50) -> list:
    """
    Un FVG esiste quando:
    - Candela 1 high < Candela 3 low → FVG Bullish
    - Candela 1 low  > Candela 3 high → FVG Bearish
    Restituisce lista di FVG non ancora mitigati.
    """
    fvgs   = []
    closes = df['close'].values
    highs  = df['high'].values
    lows   = df['low'].values
    n      = len(df)

    for i in range(2, min(lookback, n)):
        idx = n - 1 - i   # partiamo dall'ultimo

        # Bullish FVG
        if highs[idx] < lows[idx + 2]:
            gap_low  = highs[idx]
            gap_high = lows[idx + 2]
            # Verifica che il gap non sia già stato mitigato
            subsequent_lows = lows[idx + 2:]
            if not any(l <= gap_low for l in subsequent_lows):
                fvgs.append({
                    "type":   "bullish",
                    "top":    gap_high,
                    "bottom": gap_low,
                    "index":  idx,
                    "size":   gap_high - gap_low,
                })

        # Bearish FVG
        if lows[idx] > highs[idx + 2]:
            gap_high = lows[idx]
            gap_low  = highs[idx + 2]
            subsequent_highs = highs[idx + 2:]
            if not any(h >= gap_high for h in subsequent_highs):
                fvgs.append({
                    "type":   "bearish",
                    "top":    gap_high,
                    "bottom": gap_low,
                    "index":  idx,
                    "size":   gap_high - gap_low,
                })

    return fvgs


def price_in_fvg(price: float, fvgs: list, direction: str) -> dict | None:
    """Verifica se il prezzo è dentro un FVG valido per la direzione."""
    for fvg in fvgs:
        if fvg["type"] == direction:
            if fvg["bottom"] <= price <= fvg["top"]:
                return fvg
    return None


# ─────────────────────────────────────────────
#   SUPPLY & DEMAND ZONES
# ─────────────────────────────────────────────

def find_sd_zones(df: pd.DataFrame, lookback: int = 80, min_impulse: float = 0.004) -> list:
    """
    Identifica zone Supply & Demand istituzionali.

    Una zona DEMAND nasce quando:
    - Base: candele di consolidamento
    - Seguito da forte impulso rialzista (displacement)
    - Il prezzo poi se ne va e non torna subito

    Una zona SUPPLY nasce in modo speculare.

    min_impulse = % minima di movimento del corpo per considerarlo impulso
    """
    zones  = []
    closes = df['close'].values
    opens  = df['open'].values
    highs  = df['high'].values
    lows   = df['low'].values
    vols   = df['volume'].values if 'volume' in df.columns else np.ones(len(df))
    n      = len(df)
    avg_vol = np.mean(vols[-50:]) if len(vols) >= 50 else np.mean(vols)

    for i in range(3, min(lookback, n - 3)):
        idx = n - 1 - i

        body       = abs(closes[idx] - opens[idx])
        body_pct   = body / closes[idx] if closes[idx] > 0 else 0
        vol_ratio  = vols[idx] / avg_vol if avg_vol > 0 else 1

        # ── ZONA DEMAND ──
        # Candela impulso rialzista forte
        if closes[idx] > opens[idx] and body_pct >= min_impulse:
            # La base è la candela precedente (o le 2 precedenti)
            base_high   = max(highs[idx - 1], highs[idx - 2])
            base_low    = min(lows[idx - 1],  lows[idx - 2])
            base_body   = abs(closes[idx - 1] - opens[idx - 1])

            # Il prezzo deve essersi allontanato dopo l'impulso
            subsequent_lows = lows[idx + 1: idx + 8]
            price_left_zone = all(l > base_low for l in subsequent_lows)

            if price_left_zone:
                # Ranking della zona
                strength = _rank_zone(body_pct, vol_ratio, base_body, body)
                zones.append({
                    "type":     "demand",
                    "top":      base_high,
                    "bottom":   base_low,
                    "impulse":  body_pct,
                    "vol_ratio": vol_ratio,
                    "strength": strength,
                    "index":    idx,
                    "mitigations": 0,
                })

        # ── ZONA SUPPLY ──
        # Candela impulso ribassista forte
        if closes[idx] < opens[idx] and body_pct >= min_impulse:
            base_high   = max(highs[idx - 1], highs[idx - 2])
            base_low    = min(lows[idx - 1],  lows[idx - 2])
            base_body   = abs(closes[idx - 1] - opens[idx - 1])

            subsequent_highs = highs[idx + 1: idx + 8]
            price_left_zone  = all(h < base_high for h in subsequent_highs)

            if price_left_zone:
                strength = _rank_zone(body_pct, vol_ratio, base_body, body)
                zones.append({
                    "type":     "supply",
                    "top":      base_high,
                    "bottom":   base_low,
                    "impulse":  body_pct,
                    "vol_ratio": vol_ratio,
                    "strength": strength,
                    "index":    idx,
                    "mitigations": 0,
                })

    return zones


def _rank_zone(body_pct: float, vol_ratio: float, base_body: float, impulse_body: float) -> str:
    """
    Classifica la zona: weak / medium / strong / institutional
    """
    score = 0
    if body_pct > 0.008:  score += 2
    elif body_pct > 0.004: score += 1

    if vol_ratio > 2.5:    score += 2
    elif vol_ratio > 1.5:  score += 1

    if base_body < impulse_body * 0.3:  score += 1   # base piccola rispetto all'impulso

    if score >= 5:   return "institutional"
    if score >= 3:   return "strong"
    if score >= 2:   return "medium"
    return "weak"


def price_near_zone(price: float, zone: dict, buffer_pct: float = 0.002) -> bool:
    """Verifica se il prezzo è dentro o molto vicino alla zona."""
    buf    = price * buffer_pct
    top    = zone["top"]    + buf
    bottom = zone["bottom"] - buf
    return bottom <= price <= top


def get_best_zone(price: float, zones: list, direction: str) -> dict | None:
    """
    Restituisce la zona più forte e più vicina al prezzo nella direzione corretta.
    direction: 'demand' per BUY, 'supply' per SELL
    """
    valid = [z for z in zones if z["type"] == direction and price_near_zone(price, z)]
    if not valid:
        return None
    # Ordina per strength
    rank_order = {"institutional": 4, "strong": 3, "medium": 2, "weak": 1}
    valid.sort(key=lambda z: rank_order.get(z["strength"], 0), reverse=True)
    return valid[0]


# ─────────────────────────────────────────────
#   LIQUIDITY SWEEP
# ─────────────────────────────────────────────

def detect_liquidity_sweep(df: pd.DataFrame, lookback: int = 30, tolerance: float = 0.001) -> dict:
    """
    Rileva se c'è stato un recente liquidity sweep (stop hunt).
    Un sweep si verifica quando il prezzo supera brevemente un livello chiave
    (equal high/low) e poi torna nella direzione opposta.

    Returns: {"bullish_sweep": bool, "bearish_sweep": bool}
    """
    result = {"bullish_sweep": False, "bearish_sweep": False}
    if len(df) < lookback + 3:
        return result

    recent = df.iloc[-lookback:]
    highs  = recent['high'].values
    lows   = recent['low'].values
    closes = recent['close'].values

    # Equal highs → potenziale sweep rialzista (stop hunt verso l'alto poi ritorno giù)
    last_high   = highs[-1]
    prior_highs = highs[:-3]
    for ph in prior_highs:
        if abs(last_high - ph) / ph < tolerance:
            # Prezzo ha toccato livello equal high ma la close è tornata sotto
            if closes[-1] < ph * (1 - tolerance):
                result["bearish_sweep"] = True

    # Equal lows → potenziale sweep ribassista
    last_low   = lows[-1]
    prior_lows = lows[:-3]
    for pl in prior_lows:
        if abs(last_low - pl) / pl < tolerance:
            if closes[-1] > pl * (1 + tolerance):
                result["bullish_sweep"] = True

    return result


# ─────────────────────────────────────────────
#   PREMIUM & DISCOUNT (Fibonacci)
# ─────────────────────────────────────────────

def get_premium_discount(df: pd.DataFrame, lookback: int = 50) -> dict:
    """
    Divide il range in 3 zone usando il 50% (equilibrium):
    - Premium:  sopra il 50% → zona per SELL
    - Discount: sotto il 50% → zona per BUY
    """
    recent    = df.iloc[-lookback:]
    range_high = recent['high'].max()
    range_low  = recent['low'].min()
    mid        = (range_high + range_low) / 2
    price      = df['close'].iloc[-1]

    if price > mid:
        zone = "premium"
    elif price < mid:
        zone = "discount"
    else:
        zone = "equilibrium"

    return {
        "zone":       zone,
        "high":       range_high,
        "low":        range_low,
        "equilibrium": mid,
        "price":      price,
    }


# ─────────────────────────────────────────────
#   ORDER BLOCKS
# ─────────────────────────────────────────────

def find_order_blocks(df: pd.DataFrame, lookback: int = 50) -> list:
    """
    Order Block = ultima candela opposta prima di un forte impulso.
    Bullish OB: ultima candela ribassista prima di un forte rialzo.
    Bearish OB: ultima candela rialzista prima di un forte ribasso.
    """
    obs    = []
    closes = df['close'].values
    opens  = df['open'].values
    highs  = df['high'].values
    lows   = df['low'].values
    n      = len(df)

    for i in range(2, min(lookback, n - 2)):
        idx = n - 1 - i

        next_body = abs(closes[idx + 1] - opens[idx + 1])
        this_body = abs(closes[idx]     - opens[idx])

        # Bullish OB: candela ribassista seguita da forte candela rialzista
        if (closes[idx] < opens[idx] and
                closes[idx + 1] > opens[idx + 1] and
                next_body > this_body * 1.5):
            obs.append({
                "type":   "bullish",
                "top":    highs[idx],
                "bottom": lows[idx],
                "index":  idx,
            })

        # Bearish OB: candela rialzista seguita da forte candela ribassista
        if (closes[idx] > opens[idx] and
                closes[idx + 1] < opens[idx + 1] and
                next_body > this_body * 1.5):
            obs.append({
                "type":   "bearish",
                "top":    highs[idx],
                "bottom": lows[idx],
                "index":  idx,
            })

    return obs


def price_in_order_block(price: float, obs: list, direction: str) -> dict | None:
    """Verifica se il prezzo è dentro un order block della direzione corretta."""
    for ob in obs:
        if ob["type"] == direction:
            if ob["bottom"] <= price <= ob["top"]:
                return ob
    return None
