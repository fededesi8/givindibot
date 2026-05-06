# ============================================================
#   TELEGRAM_BOT.PY — Invio segnali su Telegram
# ============================================================

import requests
import logging
from scorer import Signal
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


def _format_price(price: float, asset_type: str) -> str:
    """Formatta il prezzo in base all'asset."""
    if asset_type == "gold":
        return f"{price:.2f}"
    return f"{price:.4f}"


def build_signal_message(signal: Signal) -> str:
    """Costruisce il messaggio Telegram professionale."""

    fp = lambda p: _format_price(p, signal.asset_type)

    # Emoji e colori in base alla direzione
    if signal.direction == "BUY":
        dir_emoji = "🟢"
        dir_label = "BUY / LONG"
    else:
        dir_emoji = "🔴"
        dir_label = "SELL / SHORT"

    # Emoji grade
    grade_emoji = {
        "A+":          "🏆 A+ ISTITUZIONALE",
        "B":           "⭐ B STANDARD",
        "SPECULATIVE": "⚠️ SPECULATIVO",
    }.get(signal.grade, signal.grade)

    # Barra di confidenza visuale
    score = signal.score
    filled = int(score / 10)
    bar = "█" * filled + "░" * (10 - filled)

    # Conferme
    conf_text = "\n".join(signal.confirmations)

    msg = (
        f"{dir_emoji} <b>{dir_label} — {signal.asset_name}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏅 <b>Grade: {grade_emoji}</b>\n"
        f"📊 Score: <b>{score}/100</b>  [{bar}]\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Entry:</b>  {fp(signal.price)}\n"
        f"🛑 <b>Stop Loss:</b>  {fp(signal.sl)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>TP1:</b>  {fp(signal.tp1)}  (RR 1:{signal.rr * 0.6:.1f})\n"
        f"🎯 <b>TP2:</b>  {fp(signal.tp2)}  (RR 1:{signal.rr:.1f})\n"
        f"🎯 <b>TP3:</b>  {fp(signal.tp3)}  (RR 1:{signal.rr * 1.6:.1f})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 <b>Conferme ({len(signal.confirmations)}):</b>\n"
        f"{conf_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ <i>Non è consulenza finanziaria. Gestisci sempre il rischio.</i>"
    )
    return msg


def send_signal(signal: Signal) -> bool:
    """Invia il segnale su Telegram."""
    msg = build_signal_message(signal)
    return _send_message(msg)


def send_startup_message():
    """Messaggio di avvio bot."""
    msg = (
        "🤖 <b>Trading Bot Avviato!</b>\n\n"
        "Sto monitorando:\n"
        "🥇 XAU/USD\n"
        "₿ BTC/USD\n"
        "🔷 ETH/USD\n"
        "◎ SOL/USD\n"
        "🟡 BNB/USD\n"
        "💧 XRP/USD\n\n"
        "📊 Strategia: SMC + Supply & Demand\n"
        "🕐 Scansione ogni 5 minuti\n\n"
        "Riceverai segnali A+, B e Speculativi."
    )
    _send_message(msg)


def send_error_message(error: str):
    """Invia notifica di errore."""
    msg = f"⚠️ <b>Errore Bot:</b>\n<code>{error}</code>"
    _send_message(msg)


def _send_message(text: str) -> bool:
    """Invia un messaggio Telegram grezzo."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       text,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, data=payload, timeout=10)
        if resp.status_code == 200:
            return True
        else:
            logger.error(f"Telegram error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Errore invio Telegram: {e}")
        return False
