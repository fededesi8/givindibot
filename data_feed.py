# ============================================================
#   DATA_FEED.PY — Scarica dati da TradingView
# ============================================================

import pandas as pd
from tvDatafeed import TvDatafeed, Interval
import logging

logger = logging.getLogger(__name__)

# Mappa stringhe → oggetti Interval di tvDatafeed
INTERVAL_MAP = {
    "1m":  Interval.in_1_minute,
    "5m":  Interval.in_5_minute,
    "15m": Interval.in_15_minute,
    "30m": Interval.in_30_minute,
    "1h":  Interval.in_1_hour,
    "4h":  Interval.in_4_hour,
    "1d":  Interval.in_daily,
    "1w":  Interval.in_weekly,
}

# Inizializza connessione TradingView (anonima, nessun account necessario)
tv = TvDatafeed()


def get_ohlcv(symbol: str, exchange: str, timeframe: str, bars: int = 300) -> pd.DataFrame | None:
    """
    Scarica dati OHLCV da TradingView.

    Args:
        symbol:    es. 'XAUUSD', 'BTCUSDT'
        exchange:  es. 'OANDA', 'BINANCE'
        timeframe: es. '1h', '4h', '15m'
        bars:      numero di candele da scaricare

    Returns:
        DataFrame con colonne: open, high, low, close, volume
        oppure None se errore
    """
    interval = INTERVAL_MAP.get(timeframe)
    if interval is None:
        logger.error(f"Timeframe non valido: {timeframe}")
        return None

    try:
        df = tv.get_hist(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            n_bars=bars
        )
        if df is None or df.empty:
            logger.warning(f"Nessun dato per {symbol} {timeframe}")
            return None

        df.dropna(inplace=True)
        df.index = pd.to_datetime(df.index)
        return df

    except Exception as e:
        logger.error(f"Errore download {symbol} {timeframe}: {e}")
        return None


def get_multi_timeframe(symbol: str, exchange: str, timeframes: dict, bars: int = 300) -> dict:
    """
    Scarica dati su più timeframe in una volta sola.

    Args:
        timeframes: dict con chiavi 'htf', 'mid', 'ltf'

    Returns:
        dict con chiavi 'htf', 'mid', 'ltf' → DataFrame
    """
    result = {}
    for key, tf in timeframes.items():
        df = get_ohlcv(symbol, exchange, tf, bars)
        result[key] = df
    return result
