# ============================================================
#   CONFIG.PY — Configurazione centrale del sistema
# ============================================================

# --- TELEGRAM ---
TELEGRAM_TOKEN   = "8783198110:AAFaVHg0wyrJCSZktLhHh7dVzbHlTB103cY"      # <-- inserisci qui il token del tuo bot
TELEGRAM_CHAT_ID = "944987288"   # <-- inserisci qui il tuo Chat ID

# --- ASSET DA MONITORARE ---
ASSETS = [
    {"symbol": "XAUUSD",  "exchange": "OANDA",   "name": "XAU/USD 🥇", "type": "gold"},
    {"symbol": "BTCUSDT", "exchange": "BINANCE",  "name": "BTC/USD ₿",  "type": "crypto"},
    {"symbol": "ETHUSDT", "exchange": "BINANCE",  "name": "ETH/USD 🔷", "type": "crypto"},
    {"symbol": "SOLUSDT", "exchange": "BINANCE",  "name": "SOL/USD ◎",  "type": "crypto"},
    {"symbol": "BNBUSDT", "exchange": "BINANCE",  "name": "BNB/USD 🟡", "type": "crypto"},
    {"symbol": "XRPUSDT", "exchange": "BINANCE",  "name": "XRP/USD 💧", "type": "crypto"},
]

# --- TIMEFRAME ---
# Gold: HTF=4H, MID=1H, LTF=15M
# Crypto: HTF=4H, MID=1H, LTF=15M
TIMEFRAMES = {
    "gold":   {"htf": "4h", "mid": "1h", "ltf": "15m"},
    "crypto": {"htf": "4h", "mid": "1h", "ltf": "15m"},
}

# --- SCORING SOGLIE ---
# A+ = segnale istituzionale top
# B  = segnale standard buona qualità
# C  = segnale speculativo (più rischioso)
SCORE_THRESHOLD_APLUS      = 75   # >= 75 → A+
SCORE_THRESHOLD_B          = 55   # >= 55 → B
SCORE_THRESHOLD_SPECULATIVE = 38  # >= 38 → Speculativo

# --- INTERVALLO SCANSIONE (secondi) ---
SCAN_INTERVAL = 300   # ogni 5 minuti

# --- RISK MANAGEMENT ---
RISK_PER_TRADE    = 1.0   # % rischio per trade
TP1_RR            = 1.5
TP2_RR            = 2.5
TP3_RR            = 4.0
ATR_SL_MULTIPLIER = 1.5   # SL = ATR * 1.5

# --- FILTRO SESSIONI (UTC) ---
SESSIONS = {
    "london":   {"start": 7,  "end": 16},
    "new_york": {"start": 13, "end": 22},
    "asia":     {"start": 0,  "end": 7},
}

# --- FILTRO VOLATILITA ---
# Se ATR è troppo basso → mercato laterale → no segnali
ATR_MIN_THRESHOLD = 0.0005   # 0.05% del prezzo

# --- LOGGING ---
LOG_FILE = "bot.log"
