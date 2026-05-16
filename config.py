import os

# ─────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# ─────────────────────────────────────
# POCKET OPTION WEBSOCKET
# All loaded from Railway environment variables
# NEVER hardcoded here
# ─────────────────────────────────────
PO_WS_URL = os.environ.get("PO_WS_URL", "")
PO_SSID = os.environ.get("PO_SSID", "")
PO_AUTH_PAYLOAD = os.environ.get("PO_AUTH_PAYLOAD", "")

# ─────────────────────────────────────
# GEMINI AI (optional — for AI analysis layer)
# ─────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ─────────────────────────────────────
# DATABASE
# ─────────────────────────────────────
DATABASE_PATH = os.environ.get("DATABASE_PATH", "trading_bot.db")

# ─────────────────────────────────────
# SIGNAL SETTINGS
# ─────────────────────────────────────
SIGNAL_INTERVAL_MINUTES = int(
    os.environ.get("SIGNAL_INTERVAL_MINUTES", "5")
)

# ─────────────────────────────────────
# POCKET OPTION ASSETS
# These are the EXACT symbols used by PO WebSocket
# ─────────────────────────────────────

FOREX_OTC = [
    "#EURUSD_otc", "#GBPUSD_otc", "#USDJPY_otc",
    "#USDCHF_otc", "#AUDUSD_otc", "#NZDUSD_otc",
    "#USDCAD_otc", "#EURGBP_otc", "#EURJPY_otc",
    "#GBPJPY_otc", "#EURCHF_otc", "#AUDJPY_otc",
    "#EURAUD_otc", "#GBPAUD_otc", "#EURCAD_otc",
    "#GBPCAD_otc", "#AUDCAD_otc", "#NZDJPY_otc",
    "#CADJPY_otc", "#CHFJPY_otc", "#GBPCHF_otc",
    "#AUDCHF_otc", "#EURNZD_otc", "#GBPNZD_otc",
]

CRYPTO_OTC = [
    "#BTCUSD_otc", "#ETHUSD_otc", "#LTCUSD_otc",
    "#XRPUSD_otc", "#ADAUSD_otc", "#DOGEUSD_otc",
    "#BNBUSD_otc", "#SOLUSD_otc", "#DOTUSD_otc",
    "#LINKUSD_otc", "#MATICUSD_otc", "#AVAXUSD_otc",
    "#ATOMUSD_otc", "#TRXUSD_otc", "#XLMUSD_otc",
]

COMMODITY_OTC = [
    "#XAUUSD_otc",  # Gold
    "#XAGUSD_otc",  # Silver
    "#USOIL_otc",   # Crude Oil WTI
    "#UKOIL_otc",   # Brent Oil
]

STOCKS_OTC = [
    "#AAPL_otc",    # Apple
    "#GOOGL_otc",   # Google
    "#MSFT_otc",    # Microsoft
    "#AMZN_otc",    # Amazon
    "#TSLA_otc",    # Tesla
    "#META_otc",    # Meta
    "#NFLX_otc",    # Netflix
    "#NVDA_otc",    # NVIDIA
    "#INTC_otc",    # Intel
    "#AMD_otc",     # AMD
    "#BABA_otc",    # Alibaba
    "#JPM_otc",     # JPMorgan
    "#V_otc",       # Visa
    "#KO_otc",      # Coca Cola
    "#DIS_otc",     # Disney
    "#PYPL_otc",    # PayPal
    "#UBER_otc",    # Uber
    "#BA_otc",      # Boeing
    "#WMT_otc",     # Walmart
    "#PFE_otc",     # Pfizer
]

INDICES_OTC = [
    "#AUS200_otc",   # Australia 200
    "#UK100_otc",    # UK 100
    "#NSDQ100_otc",  # NASDAQ 100
    "#SP500_otc",    # S&P 500
    "#JP225_otc",    # Nikkei 225
    "#F40_otc",      # France 40
    "#D30_otc",      # Germany 30
    "#US30_otc",     # Dow Jones
]

ALL_ASSETS = (
    FOREX_OTC +
    CRYPTO_OTC +
    COMMODITY_OTC +
    STOCKS_OTC +
    INDICES_OTC
)

# Asset display names
ASSET_NAMES = {
    "#EURUSD_otc":   "EUR/USD OTC",
    "#GBPUSD_otc":   "GBP/USD OTC",
    "#USDJPY_otc":   "USD/JPY OTC",
    "#USDCHF_otc":   "USD/CHF OTC",
    "#AUDUSD_otc":   "AUD/USD OTC",
    "#NZDUSD_otc":   "NZD/USD OTC",
    "#USDCAD_otc":   "USD/CAD OTC",
    "#EURGBP_otc":   "EUR/GBP OTC",
    "#EURJPY_otc":   "EUR/JPY OTC",
    "#GBPJPY_otc":   "GBP/JPY OTC",
    "#EURCHF_otc":   "EUR/CHF OTC",
    "#AUDJPY_otc":   "AUD/JPY OTC",
    "#EURAUD_otc":   "EUR/AUD OTC",
    "#GBPAUD_otc":   "GBP/AUD OTC",
    "#EURCAD_otc":   "EUR/CAD OTC",
    "#GBPCAD_otc":   "GBP/CAD OTC",
    "#AUDCAD_otc":   "AUD/CAD OTC",
    "#NZDJPY_otc":   "NZD/JPY OTC",
    "#CADJPY_otc":   "CAD/JPY OTC",
    "#CHFJPY_otc":   "CHF/JPY OTC",
    "#GBPCHF_otc":   "GBP/CHF OTC",
    "#AUDCHF_otc":   "AUD/CHF OTC",
    "#EURNZD_otc":   "EUR/NZD OTC",
    "#GBPNZD_otc":   "GBP/NZD OTC",
    "#BTCUSD_otc":   "BTC/USD OTC",
    "#ETHUSD_otc":   "ETH/USD OTC",
    "#LTCUSD_otc":   "LTC/USD OTC",
    "#XRPUSD_otc":   "XRP/USD OTC",
    "#ADAUSD_otc":   "ADA/USD OTC",
    "#DOGEUSD_otc":  "DOGE/USD OTC",
    "#BNBUSD_otc":   "BNB/USD OTC",
    "#SOLUSD_otc":   "SOL/USD OTC",
    "#DOTUSD_otc":   "DOT/USD OTC",
    "#LINKUSD_otc":  "LINK/USD OTC",
    "#MATICUSD_otc": "MATIC/USD OTC",
    "#AVAXUSD_otc":  "AVAX/USD OTC",
    "#ATOMUSD_otc":  "ATOM/USD OTC",
    "#TRXUSD_otc":   "TRX/USD OTC",
    "#XLMUSD_otc":   "XLM/USD OTC",
    "#XAUUSD_otc":   "Gold OTC",
    "#XAGUSD_otc":   "Silver OTC",
    "#USOIL_otc":    "Crude Oil OTC",
    "#UKOIL_otc":    "Brent Oil OTC",
    "#AAPL_otc":     "Apple OTC",
    "#GOOGL_otc":    "Google OTC",
    "#MSFT_otc":     "Microsoft OTC",
    "#AMZN_otc":     "Amazon OTC",
    "#TSLA_otc":     "Tesla OTC",
    "#META_otc":     "Meta OTC",
    "#NFLX_otc":     "Netflix OTC",
    "#NVDA_otc":     "NVIDIA OTC",
    "#INTC_otc":     "Intel OTC",
    "#AMD_otc":      "AMD OTC",
    "#BABA_otc":     "Alibaba OTC",
    "#JPM_otc":      "JPMorgan OTC",
    "#V_otc":        "Visa OTC",
    "#KO_otc":       "Coca Cola OTC",
    "#DIS_otc":      "Disney OTC",
    "#PYPL_otc":     "PayPal OTC",
    "#UBER_otc":     "Uber OTC",
    "#BA_otc":       "Boeing OTC",
    "#WMT_otc":      "Walmart OTC",
    "#PFE_otc":      "Pfizer OTC",
    "#AUS200_otc":   "AUS 200 OTC",
    "#UK100_otc":    "UK 100 OTC",
    "#NSDQ100_otc":  "NASDAQ OTC",
    "#SP500_otc":    "S&P 500 OTC",
    "#JP225_otc":    "Nikkei OTC",
    "#F40_otc":      "France 40 OTC",
    "#D30_otc":      "Germany 30 OTC",
    "#US30_otc":     "Dow Jones OTC",
}

# Expiry options
EXPIRY_OPTIONS = ["30s", "1m", "2m", "15m", "1H"]

# Expiry to candle timeframe mapping
EXPIRY_TO_TIMEFRAME = {
    "30s": 15,
    "1m":  30,
    "2m":  60,
    "15m": 300,
    "1H":  900,
}
