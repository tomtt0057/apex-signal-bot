BOT_TOKEN = "8304682419:AAERok8xSOx-zmbPC1QQlyeTn-zTI30yGKU"
TWELVE_API_KEY = "0158f9f039684e3786de56378964a1a0"
SIGNAL_INTERVAL_MINUTES = 5
DATABASE_PATH = "trading_bot.db"

FOREX_PAIRS = [
    "EUR/USD", "GBP/USD", "USD/JPY",
    "USD/CHF", "AUD/USD", "NZD/USD",
    "EUR/GBP", "EUR/JPY", "GBP/JPY"
]

CRYPTO_PAIRS = [
    "BTC/USD", "ETH/USD", "BNB/USD",
    "SOL/USD", "XRP/USD", "ADA/USD"
]

ALL_PAIRS = FOREX_PAIRS + CRYPTO_PAIRS

BINANCE_SYMBOL_MAP = {
    "BTC/USD": "BTCUSDT",
    "ETH/USD": "ETHUSDT",
    "BNB/USD": "BNBUSDT",
    "SOL/USD": "SOLUSDT",
    "XRP/USD": "XRPUSDT",
    "ADA/USD": "ADAUSDT",
}

TIMEFRAMES = {
    "1 min  ⚡": {"twelve": "1min",  "binance": "1m"},
    "5 min  🕐": {"twelve": "5min",  "binance": "5m"},
    "15 min 📊": {"twelve": "15min", "binance": "15m"},
    "1 hour 📈": {"twelve": "1h",    "binance": "1h"},
}
