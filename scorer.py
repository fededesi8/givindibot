# ============================================================
#   SCORER.PY — Sistema di scoring e generazione segnali
# ============================================================

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

from indicators import (
    rsi, rsi_divergence, macd, macd_cross,
    atr, adx, bollinger_bands, volume_spike, volume_trend, ema
)
from smc import (
    detect_market_structure, find_sd_zones, get_best_zone,
    find_fvg, price_in_fvg, detect_liquidity_sweep,
    get_premium_discount, find_order_blocks, price_in_order_block
)
from filters import (
    is_good_session, is_volatile_enough, is_ranging_market,
    has_anomalous_candle, detect_patterns, bullish_patterns,
    bearish_patterns, ema_trend
)
from config import (
    SCORE_THRESHOLD_APLUS, SCORE_THRESHOLD_B,
    SCORE_THRESHOLD_SPECULATIVE, ATR_SL_MULTIPLIER,
    TP1_RR, TP2_RR, TP3_RR
)


@dataclass
class Signal:
    direction:    str          # 'BUY' o 'SELL'
    grade:        str          # 'A+', 'B', 'SPECULATIVE'
    score:        int
    price:        float
    sl:           float
    tp1:          float
    tp2:          float
    tp3:          float
    rr:           float
    confirmations: list        # lista di stringhe con le conferme
    asset_name:   str
    asset_type:   str
    session:      str


def score_asset(
    asset: dict,
    df_htf: pd.DataFrame,
    df_mid: pd.DataFrame,
    df_ltf: pd.DataFrame,
) -> Optional[Signal]:
    """
    Calcola lo score di un asset su 3 timeframe e genera un segnale
    se supera le soglie definite in config.py.

    Punteggi massimi:
    - Market Structure HTF:   15 pt
    - S&D Zone HTF:           20 pt
    - Order Block:            10 pt
    - FVG:                    10 pt
    - Liquidity Sweep:        15 pt
    - Premium/Discount:        5 pt
    - EMA Trend:               8 pt
    - RSI:                     8 pt
    - RSI Divergence:         10 pt
    - MACD Cross:              8 pt
    - Volume Spike:           10 pt
    - ADX Trend Strength:      5 pt
    - Candlestick Pattern:     8 pt
    - Session:                 8 pt
    TOTALE MASSIMO:          140 pt  → normalizzato a 100
    """

    name       = asset["name"]
    asset_type = asset["type"]
    price      = df_ltf['close'].iloc[-1]

    # ── FILTRI PRELIMINARI (hard stop — nessun segnale) ──
    if has_anomalous_candle(df_ltf):
        return None
    if is_ranging_market(df_mid):
        return None
    if not is_volatile_enough(df_mid):
        return None

    buy_score  = 0
    sell_score = 0
    buy_conf   = []
    sell_conf  = []

    # ──────────────────────────────────────────────
    #   1. MARKET STRUCTURE HTF (+15)
    # ──────────────────────────────────────────────
    ms_htf = detect_market_structure(df_htf)
    ms_mid = detect_market_structure(df_mid)

    if ms_htf["trend"] == "bullish":
        buy_score  += 15
        buy_conf.append("✅ HTF Bullish Structure (BOS/HH-HL)")
    elif ms_htf["trend"] == "bearish":
        sell_score += 15
        sell_conf.append("✅ HTF Bearish Structure (BOS/LH-LL)")

    if ms_htf["last_choch"]:
        choch_type = ms_htf["last_choch"][0]
        if "bullish" in choch_type:
            buy_score  += 8
            buy_conf.append("✅ Bullish CHOCH (HTF)")
        else:
            sell_score += 8
            sell_conf.append("✅ Bearish CHOCH (HTF)")

    # ──────────────────────────────────────────────
    #   2. SUPPLY & DEMAND ZONE HTF (+20)
    # ──────────────────────────────────────────────
    zones_htf = find_sd_zones(df_htf)
    zones_mid = find_sd_zones(df_mid)

    demand_zone = get_best_zone(price, zones_htf + zones_mid, "demand")
    supply_zone = get_best_zone(price, zones_htf + zones_mid, "supply")

    zone_scores = {"institutional": 20, "strong": 15, "medium": 10, "weak": 5}

    if demand_zone:
        pts = zone_scores.get(demand_zone["strength"], 5)
        buy_score += pts
        buy_conf.append(f"✅ {demand_zone['strength'].capitalize()} Demand Zone ({demand_zone['bottom']:.2f}-{demand_zone['top']:.2f})")

    if supply_zone:
        pts = zone_scores.get(supply_zone["strength"], 5)
        sell_score += pts
        sell_conf.append(f"✅ {supply_zone['strength'].capitalize()} Supply Zone ({supply_zone['bottom']:.2f}-{supply_zone['top']:.2f})")

    # ──────────────────────────────────────────────
    #   3. ORDER BLOCK (+10)
    # ──────────────────────────────────────────────
    obs = find_order_blocks(df_mid)
    bull_ob = price_in_order_block(price, obs, "bullish")
    bear_ob = price_in_order_block(price, obs, "bearish")

    if bull_ob:
        buy_score  += 10
        buy_conf.append(f"✅ Bullish Order Block ({bull_ob['bottom']:.2f}-{bull_ob['top']:.2f})")
    if bear_ob:
        sell_score += 10
        sell_conf.append(f"✅ Bearish Order Block ({bear_ob['bottom']:.2f}-{bear_ob['top']:.2f})")

    # ──────────────────────────────────────────────
    #   4. FAIR VALUE GAP / IMBALANCE (+10)
    # ──────────────────────────────────────────────
    fvgs = find_fvg(df_mid)
    bull_fvg = price_in_fvg(price, fvgs, "bullish")
    bear_fvg = price_in_fvg(price, fvgs, "bearish")

    if bull_fvg:
        buy_score  += 10
        buy_conf.append(f"✅ Bullish FVG / Imbalance ({bull_fvg['bottom']:.2f}-{bull_fvg['top']:.2f})")
    if bear_fvg:
        sell_score += 10
        sell_conf.append(f"✅ Bearish FVG / Imbalance ({bear_fvg['bottom']:.2f}-{bear_fvg['top']:.2f})")

    # ──────────────────────────────────────────────
    #   5. LIQUIDITY SWEEP (+15)
    # ──────────────────────────────────────────────
    sweep = detect_liquidity_sweep(df_mid)
    if sweep["bullish_sweep"]:
        buy_score  += 15
        buy_conf.append("✅ Bullish Liquidity Sweep (Stop Hunt)")
    if sweep["bearish_sweep"]:
        sell_score += 15
        sell_conf.append("✅ Bearish Liquidity Sweep (Stop Hunt)")

    # ──────────────────────────────────────────────
    #   6. PREMIUM & DISCOUNT (+5)
    # ──────────────────────────────────────────────
    pd_zone = get_premium_discount(df_htf)
    if pd_zone["zone"] == "discount":
        buy_score  += 5
        buy_conf.append(f"✅ Discount Zone (sotto equilibrium {pd_zone['equilibrium']:.2f})")
    elif pd_zone["zone"] == "premium":
        sell_score += 5
        sell_conf.append(f"✅ Premium Zone (sopra equilibrium {pd_zone['equilibrium']:.2f})")

    # ──────────────────────────────────────────────
    #   7. EMA TREND (+8)
    # ──────────────────────────────────────────────
    trend_htf = ema_trend(df_htf)
    trend_mid = ema_trend(df_mid)

    if trend_htf == "bullish" and trend_mid == "bullish":
        buy_score  += 8
        buy_conf.append("✅ EMA Trend Bullish (HTF + MID allineati)")
    elif trend_htf == "bearish" and trend_mid == "bearish":
        sell_score += 8
        sell_conf.append("✅ EMA Trend Bearish (HTF + MID allineati)")
    elif trend_htf == "bullish":
        buy_score  += 4
        buy_conf.append("✅ EMA Trend Bullish (HTF)")
    elif trend_htf == "bearish":
        sell_score += 4
        sell_conf.append("✅ EMA Trend Bearish (HTF)")

    # ──────────────────────────────────────────────
    #   8. RSI (+8)
    # ──────────────────────────────────────────────
    rsi_mid = rsi(df_mid['close']).iloc[-1]
    rsi_ltf = rsi(df_ltf['close']).iloc[-1]

    if rsi_mid < 35:
        buy_score  += 8
        buy_conf.append(f"✅ RSI Oversold {rsi_mid:.1f} (MID)")
    elif rsi_mid < 45:
        buy_score  += 4
        buy_conf.append(f"✅ RSI Zona Bullish {rsi_mid:.1f}")

    if rsi_mid > 65:
        sell_score += 8
        sell_conf.append(f"✅ RSI Overbought {rsi_mid:.1f} (MID)")
    elif rsi_mid > 55:
        sell_score += 4
        sell_conf.append(f"✅ RSI Zona Bearish {rsi_mid:.1f}")

    # ──────────────────────────────────────────────
    #   9. RSI DIVERGENCE (+10)
    # ──────────────────────────────────────────────
    rsi_series_mid = rsi(df_mid['close'])
    div = rsi_divergence(df_mid, rsi_series_mid)
    if div == "bullish":
        buy_score  += 10
        buy_conf.append("✅ RSI Divergenza Bullish")
    elif div == "bearish":
        sell_score += 10
        sell_conf.append("✅ RSI Divergenza Bearish")

    # ──────────────────────────────────────────────
    #   10. MACD (+8)
    # ──────────────────────────────────────────────
    macd_data = macd(df_mid['close'])
    cross     = macd_cross(macd_data)
    if cross == "bullish":
        buy_score  += 8
        buy_conf.append("✅ MACD Cross Bullish")
    elif cross == "bearish":
        sell_score += 8
        sell_conf.append("✅ MACD Cross Bearish")

    # ──────────────────────────────────────────────
    #   11. VOLUME (+10)
    # ──────────────────────────────────────────────
    vol_spike = volume_spike(df_mid)
    if vol_spike:
        buy_score  += 10
        sell_score += 10
        buy_conf.append("✅ Volume Spike (istituzionale)")
        sell_conf.append("✅ Volume Spike (istituzionale)")

    # ──────────────────────────────────────────────
    #   12. ADX — FORZA TREND (+5)
    # ──────────────────────────────────────────────
    adx_val = adx(df_mid).iloc[-1]
    if adx_val > 30:
        buy_score  += 5
        sell_score += 5
        buy_conf.append(f"✅ ADX Trend Forte {adx_val:.1f}")
        sell_conf.append(f"✅ ADX Trend Forte {adx_val:.1f}")

    # ──────────────────────────────────────────────
    #   13. CANDLESTICK PATTERN (+8)
    # ──────────────────────────────────────────────
    patterns = detect_patterns(df_ltf)
    bull_p   = bullish_patterns(patterns)
    bear_p   = bearish_patterns(patterns)

    if bull_p:
        buy_score  += 8
        buy_conf.append(f"✅ Pattern: {', '.join(bull_p).replace('_', ' ').title()}")
    if bear_p:
        sell_score += 8
        sell_conf.append(f"✅ Pattern: {', '.join(bear_p).replace('_', ' ').title()}")

    # ──────────────────────────────────────────────
    #   14. SESSIONE (+8)
    # ──────────────────────────────────────────────
    good_session, session_name = is_good_session(asset_type)
    session_pts = 8 if "Overlap" in session_name else 5 if good_session else 0

    if session_pts > 0:
        buy_score  += session_pts
        sell_score += session_pts
        buy_conf.append(f"✅ {session_name}")
        sell_conf.append(f"✅ {session_name}")

    # ──────────────────────────────────────────────
    #   NORMALIZZA SCORE (max ~140 → 100)
    # ──────────────────────────────────────────────
    max_score = 140
    buy_score_norm  = min(int((buy_score  / max_score) * 100), 100)
    sell_score_norm = min(int((sell_score / max_score) * 100), 100)

    # ──────────────────────────────────────────────
    #   DETERMINA DIREZIONE E GRADE
    # ──────────────────────────────────────────────
    direction = None
    final_score = 0
    confirmations = []

    if buy_score_norm >= sell_score_norm and buy_score_norm >= SCORE_THRESHOLD_SPECULATIVE:
        direction     = "BUY"
        final_score   = buy_score_norm
        confirmations = buy_conf
    elif sell_score_norm > buy_score_norm and sell_score_norm >= SCORE_THRESHOLD_SPECULATIVE:
        direction     = "SELL"
        final_score   = sell_score_norm
        confirmations = sell_conf

    if direction is None:
        return None

    # Grade
    if final_score >= SCORE_THRESHOLD_APLUS:
        grade = "A+"
    elif final_score >= SCORE_THRESHOLD_B:
        grade = "B"
    else:
        grade = "SPECULATIVE"

    # ──────────────────────────────────────────────
    #   CALCOLO SL / TP
    # ──────────────────────────────────────────────
    atr_val = atr(df_mid).iloc[-1]
    sl_dist = atr_val * ATR_SL_MULTIPLIER

    if direction == "BUY":
        sl  = price - sl_dist
        tp1 = price + sl_dist * TP1_RR
        tp2 = price + sl_dist * TP2_RR
        tp3 = price + sl_dist * TP3_RR
    else:
        sl  = price + sl_dist
        tp1 = price - sl_dist * TP1_RR
        tp2 = price - sl_dist * TP2_RR
        tp3 = price - sl_dist * TP3_RR

    rr = round(abs(tp2 - price) / abs(sl - price), 1)

    return Signal(
        direction=direction,
        grade=grade,
        score=final_score,
        price=price,
        sl=sl,
        tp1=tp1,
        tp2=tp2,
        tp3=tp3,
        rr=rr,
        confirmations=confirmations,
        asset_name=name,
        asset_type=asset_type,
        session=session_name,
    )
