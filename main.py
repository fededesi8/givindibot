# ============================================================
#   MAIN.PY — Loop principale del trading bot
# ============================================================

import time
import logging
from datetime import datetime, timezone

from config import ASSETS, TIMEFRAMES, SCAN_INTERVAL
from data_feed import get_multi_timeframe
from scorer import score_asset
from telegram_bot import send_signal, send_startup_message, send_error_message

# ── LOGGING ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# ── ANTI-SPAM: tiene traccia degli ultimi segnali inviati ──
# Evita di mandare lo stesso segnale più volte di fila
last_signals: dict = {}   # {symbol: {"direction": str, "grade": str, "time": float}}
COOLDOWN_SECONDS = 3600   # stesso segnale non inviato per 1 ora


def should_send(symbol: str, direction: str, grade: str) -> bool:
    """
    Evita spam: non inviare lo stesso segnale sullo stesso asset
    nella stessa direzione se è passata meno di 1 ora.
    """
    now = time.time()
    last = last_signals.get(symbol)
    if last is None:
        return True
    if last["direction"] != direction:
        return True   # direzione cambiata → ok
    if now - last["time"] > COOLDOWN_SECONDS:
        return True   # cooldown scaduto
    return False


def run_scan():
    """Scansiona tutti gli asset e invia segnali se trovati."""
    now_str = datetime.now(timezone.utc).strftime("%H:%M UTC")
    logger.info(f"─── Scansione in corso [{now_str}] ───")

    for asset in ASSETS:
        symbol     = asset["symbol"]
        exchange   = asset["exchange"]
        name       = asset["name"]
        asset_type = asset["type"]
        timeframes = TIMEFRAMES[asset_type]

        try:
            # Scarica dati su 3 timeframe
            data = get_multi_timeframe(symbol, exchange, timeframes, bars=300)
            df_htf = data.get("htf")
            df_mid = data.get("mid")
            df_ltf = data.get("ltf")

            if df_htf is None or df_mid is None or df_ltf is None:
                logger.warning(f"{name}: dati mancanti, salto.")
                continue

            # Calcola score e genera segnale
            signal = score_asset(asset, df_htf, df_mid, df_ltf)

            if signal is None:
                logger.info(f"{name}: nessun segnale")
                continue

            logger.info(f"{name}: {signal.direction} Grade={signal.grade} Score={signal.score}")

            # Anti-spam
            if not should_send(symbol, signal.direction, signal.grade):
                logger.info(f"{name}: segnale già inviato di recente, skip.")
                continue

            # Invia su Telegram
            sent = send_signal(signal)
            if sent:
                last_signals[symbol] = {
                    "direction": signal.direction,
                    "grade":     signal.grade,
                    "time":      time.time(),
                }
                logger.info(f"{name}: segnale inviato ✅")

        except Exception as e:
            logger.error(f"Errore su {name}: {e}")
            # Non inviare notifiche di errore per ogni asset per evitare spam

        time.sleep(2)   # piccola pausa tra un asset e l'altro


def main():
    logger.info("🚀 Trading Bot avviato!")
    send_startup_message()

    while True:
        try:
            run_scan()
        except Exception as e:
            logger.error(f"Errore critico nel loop: {e}")
            try:
                send_error_message(str(e))
            except:
                pass

        logger.info(f"Prossima scansione tra {SCAN_INTERVAL // 60} minuti.")
        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    main()
