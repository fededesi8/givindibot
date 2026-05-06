# 📖 GUIDA COMPLETA — Trading Bot Setup

## 📁 Struttura File
```
trading_bot/
├── main.py          ← avvia il bot
├── config.py        ← configurazione (token, asset, soglie)
├── data_feed.py     ← scarica dati da TradingView
├── indicators.py    ← RSI, MACD, EMA, ATR, ecc.
├── smc.py           ← Supply & Demand, SMC, FVG, Order Blocks
├── filters.py       ← sessioni, volatilità, candlestick
├── scorer.py        ← sistema scoring e generazione segnali
├── telegram_bot.py  ← invio messaggi Telegram
├── requirements.txt ← librerie necessarie
└── Procfile         ← per Railway (deploy cloud)
```

---

## ⚙️ STEP 1 — Configura il bot

Apri `config.py` e inserisci:
```python
TELEGRAM_TOKEN   = "IL_TUO_TOKEN"     # da @BotFather
TELEGRAM_CHAT_ID = "IL_TUO_CHAT_ID"  # da @userinfobot
```

Per trovare il CHAT_ID:
1. Apri Telegram
2. Cerca @userinfobot
3. Premi Start
4. Copia il numero che ti dà (es. 123456789)

---

## 💻 STEP 2 — Prova in locale (sul tuo PC)

Apri il Terminale (su Windows: cerca "cmd" o "PowerShell"):

```bash
# Installa le librerie
pip install tvdatafeed pandas numpy requests

# Entra nella cartella
cd percorso/della/cartella/trading_bot

# Avvia il bot
python main.py
```

Se tutto funziona vedrai nel terminale i log e riceverai un messaggio su Telegram.

---

## ☁️ STEP 3 — Deploy su Railway (24/7 GRATIS)

### 3a. Crea account GitHub (se non ce l'hai)
- Vai su https://github.com
- Registrati gratuitamente

### 3b. Carica i file su GitHub
1. Vai su https://github.com/new
2. Crea un repository chiamato "trading-bot"
3. Carica tutti i file della cartella trading_bot

### 3c. Deploy su Railway
1. Vai su https://railway.app
2. Registrati con il tuo account GitHub
3. Clicca "New Project" → "Deploy from GitHub repo"
4. Seleziona il repository "trading-bot"
5. Railway rileva automaticamente il Procfile e avvia il bot

Il bot girerà 24/7 gratuitamente! ✅

---

## 📊 SISTEMA DI SEGNALI

### Grade A+ (Score ≥ 75/100)
Segnale istituzionale top. Setup con molte conferme allineate.
Adatto per trade con size normale.

### Grade B (Score 55-74/100)  
Segnale standard di buona qualità.
Adatto per trade con size ridotta.

### Grade Speculativo (Score 38-54/100)
Setup più rischioso ma con potenziale.
Usare size molto ridotta o saltare.

---

## 🎯 INDICATORI USATI

| Indicatore | Scopo |
|---|---|
| Market Structure (BOS/CHOCH) | Trend HTF |
| Supply & Demand Zone | Core entry |
| Order Block | Conferma istituzionale |
| Fair Value Gap (FVG) | Imbalance |
| Liquidity Sweep | Stop hunt |
| Premium/Discount | Fibonacci zone |
| EMA 20/50/200 | Trend filter |
| RSI + Divergenze | Momentum |
| MACD Cross | Momentum shift |
| Volume Spike | Conferma istituzionale |
| ADX | Forza trend |
| Candlestick Pattern | Entry precision |
| Sessione Operativa | Timing |

---

## ⚠️ DISCLAIMER

Questo bot è uno strumento di analisi tecnica automatizzata.
NON è consulenza finanziaria.
Gestisci sempre il rischio. Non investire più di quanto puoi permetterti di perdere.
