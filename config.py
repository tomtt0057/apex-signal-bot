import os

# ─────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# ─────────────────────────────────────
# POCKET OPTION WEBSOCKET
# ─────────────────────────────────────
PO_WS_URL       = os.environ.get("PO_WS_URL", "")
PO_SSID         = os.environ.get("PO_SSID", "")
PO_AUTH_PAYLOAD = os.environ.get("PO_AUTH_PAYLOAD", "")

# ─────────────────────────────────────
# OPTIONAL
# ─────────────────────────────────────
GEMINI_API_KEY          = os.environ.get("GEMINI_API_KEY", "")
DATABASE_PATH           = os.environ.get("DATABASE_PATH", "trading_bot.db")
SIGNAL_INTERVAL_MINUTES = int(os.environ.get("SIGNAL_INTERVAL_MINUTES", "5"))

# ─────────────────────────────────────
# POCKET OPTION ASSETS — MAIN (non-OTC)
# ─────────────────────────────────────

FOREX_MAIN = [
    "EURUSD", "GBPUSD", "USDJPY",
    "USDCHF", "AUDUSD", "NZDUSD",
    "USDCAD", "EURGBP", "EURJPY",
    "GBPJPY", "EURCHF", "AUDJPY",
    "EURAUD", "GBPAUD", "EURCAD",
    "GBPCAD", "AUDCAD", "NZDJPY",
    "CADJPY", "CHFJPY", "GBPCHF",
    "AUDCHF", "EURNZD", "GBPNZD",
]

CRYPTO_MAIN = [
    "BTCUSD", "ETHUSD", "LTCUSD",
    "XRPUSD", "ADAUSD", "DOGEUSD",
    "BNBUSD", "SOLUSD", "DOTUSD",
    "LINKUSD", "MATICUSD", "AVAXUSD",
    "ATOMUSD", "TRXUSD", "XLMUSD",
]

COMMODITY_MAIN = [
    "XAUUSD",
    "XAGUSD",
    "USOIL",
    "UKOIL",
]

STOCKS_MAIN = [
    "AAPL", "GOOGL", "MSFT",
    "AMZN", "TSLA", "META",
    "NFLX", "NVDA", "INTC",
    "AMD",  "BABA", "JPM",
    "V",    "KO",   "DIS",
    "PYPL", "UBER", "BA",
    "WMT",  "PFE",
]

# ─────────────────────────────────────
# POCKET OPTION ASSETS — OTC
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
    "#XAUUSD_otc",
    "#XAGUSD_otc",
    "#USOIL_otc",
    "#UKOIL_otc",
]

STOCKS_OTC = [
    "#AAPL_otc",  "#GOOGL_otc", "#MSFT_otc",
    "#AMZN_otc",  "#TSLA_otc",  "#META_otc",
    "#NFLX_otc",  "#NVDA_otc",  "#INTC_otc",
    "#AMD_otc",   "#BABA_otc",  "#JPM_otc",
    "#V_otc",     "#KO_otc",    "#DIS_otc",
    "#PYPL_otc",  "#UBER_otc",  "#BA_otc",
    "#WMT_otc",   "#PFE_otc",
]

# ─────────────────────────────────────
# ALL ASSETS COMBINED
# ─────────────────────────────────────
ALL_ASSETS = (
    FOREX_MAIN + FOREX_OTC +
    CRYPTO_MAIN + CRYPTO_OTC +
    COMMODITY_MAIN + COMMODITY_OTC +
    STOCKS_MAIN + STOCKS_OTC
)

# ─────────────────────────────────────
# DISPLAY NAMES
# ─────────────────────────────────────
ASSET_NAMES = {
    # Forex Main
    "EURUSD": "EUR/USD", "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY", "USDCHF": "USD/CHF",
    "AUDUSD": "AUD/USD", "NZDUSD": "NZD/USD",
    "USDCAD": "USD/CAD", "EURGBP": "EUR/GBP",
    "EURJPY": "EUR/JPY", "GBPJPY": "GBP/JPY",
    "EURCHF": "EUR/CHF", "AUDJPY": "AUD/JPY",
    "EURAUD": "EUR/AUD", "GBPAUD": "GBP/AUD",
    "EURCAD": "EUR/CAD", "GBPCAD": "GBP/CAD",
    "AUDCAD": "AUD/CAD", "NZDJPY": "NZD/JPY",
    "CADJPY": "CAD/JPY", "CHFJPY": "CHF/JPY",
    "GBPCHF": "GBP/CHF", "AUDCHF": "AUD/CHF",
    "EURNZD": "EUR/NZD", "GBPNZD": "GBP/NZD",
    # Forex OTC
    "#EURUSD_otc": "EUR/USD OTC",
    "#GBPUSD_otc": "GBP/USD OTC",
    "#USDJPY_otc": "USD/JPY OTC",
    "#USDCHF_otc": "USD/CHF OTC",
    "#AUDUSD_otc": "AUD/USD OTC",
    "#NZDUSD_otc": "NZD/USD OTC",
    "#USDCAD_otc": "USD/CAD OTC",
    "#EURGBP_otc": "EUR/GBP OTC",
    "#EURJPY_otc": "EUR/JPY OTC",
    "#GBPJPY_otc": "GBP/JPY OTC",
    "#EURCHF_otc": "EUR/CHF OTC",
    "#AUDJPY_otc": "AUD/JPY OTC",
    "#EURAUD_otc": "EUR/AUD OTC",
    "#GBPAUD_otc": "GBP/AUD OTC",
    "#EURCAD_otc": "EUR/CAD OTC",
    "#GBPCAD_otc": "GBP/CAD OTC",
    "#AUDCAD_otc": "AUD/CAD OTC",
    "#NZDJPY_otc": "NZD/JPY OTC",
    "#CADJPY_otc": "CAD/JPY OTC",
    "#CHFJPY_otc": "CHF/JPY OTC",
    "#GBPCHF_otc": "GBP/CHF OTC",
    "#AUDCHF_otc": "AUD/CHF OTC",
    "#EURNZD_otc": "EUR/NZD OTC",
    "#GBPNZD_otc": "GBP/NZD OTC",
    # Crypto Main
    "BTCUSD": "BTC/USD", "ETHUSD": "ETH/USD",
    "LTCUSD": "LTC/USD", "XRPUSD": "XRP/USD",
    "ADAUSD": "ADA/USD", "DOGEUSD": "DOGE/USD",
    "BNBUSD": "BNB/USD", "SOLUSD": "SOL/USD",
    "DOTUSD": "DOT/USD", "LINKUSD": "LINK/USD",
    "MATICUSD": "MATIC/USD", "AVAXUSD": "AVAX/USD",
    "ATOMUSD": "ATOM/USD", "TRXUSD": "TRX/USD",
    "XLMUSD": "XLM/USD",
    # Crypto OTC
    "#BTCUSD_otc": "BTC/USD OTC",
    "#ETHUSD_otc": "ETH/USD OTC",
    "#LTCUSD_otc": "LTC/USD OTC",
    "#XRPUSD_otc": "XRP/USD OTC",
    "#ADAUSD_otc": "ADA/USD OTC",
    "#DOGEUSD_otc": "DOGE/USD OTC",
    "#BNBUSD_otc": "BNB/USD OTC",
    "#SOLUSD_otc": "SOL/USD OTC",
    "#DOTUSD_otc": "DOT/USD OTC",
    "#LINKUSD_otc": "LINK/USD OTC",
    "#MATICUSD_otc": "MATIC/USD OTC",
    "#AVAXUSD_otc": "AVAX/USD OTC",
    "#ATOMUSD_otc": "ATOM/USD OTC",
    "#TRXUSD_otc": "TRX/USD OTC",
    "#XLMUSD_otc": "XLM/USD OTC",
    # Commodity Main
    "XAUUSD": "Gold", "XAGUSD": "Silver",
    "USOIL": "Crude Oil WTI", "UKOIL": "Brent Oil",
    # Commodity OTC
    "#XAUUSD_otc": "Gold OTC",
    "#XAGUSD_otc": "Silver OTC",
    "#USOIL_otc":  "Crude Oil OTC",
    "#UKOIL_otc":  "Brent Oil OTC",
    # Stocks Main
    "AAPL": "Apple",    "GOOGL": "Google",
    "MSFT": "Microsoft","AMZN": "Amazon",
    "TSLA": "Tesla",    "META": "Meta",
    "NFLX": "Netflix",  "NVDA": "NVIDIA",
    "INTC": "Intel",    "AMD": "AMD",
    "BABA": "Alibaba",  "JPM": "JPMorgan",
    "V": "Visa",        "KO": "Coca Cola",
    "DIS": "Disney",    "PYPL": "PayPal",
    "UBER": "Uber",     "BA": "Boeing",
    "WMT": "Walmart",   "PFE": "Pfizer",
    # Stocks OTC
    "#AAPL_otc":  "Apple OTC",
    "#GOOGL_otc": "Google OTC",
    "#MSFT_otc":  "Microsoft OTC",
    "#AMZN_otc":  "Amazon OTC",
    "#TSLA_otc":  "Tesla OTC",
    "#META_otc":  "Meta OTC",
    "#NFLX_otc":  "Netflix OTC",
    "#NVDA_otc":  "NVIDIA OTC",
    "#INTC_otc":  "Intel OTC",
    "#AMD_otc":   "AMD OTC",
    "#BABA_otc":  "Alibaba OTC",
    "#JPM_otc":   "JPMorgan OTC",
    "#V_otc":     "Visa OTC",
    "#KO_otc":    "Coca Cola OTC",
    "#DIS_otc":   "Disney OTC",
    "#PYPL_otc":  "PayPal OTC",
    "#UBER_otc":  "Uber OTC",
    "#BA_otc":    "Boeing OTC",
    "#WMT_otc":   "Walmart OTC",
    "#PFE_otc":   "Pfizer OTC",
}

EXPIRY_OPTIONS = ["30s", "1m", "2m", "15m", "1H"]

EXPIRY_TO_TIMEFRAME = {
    "30s": 15,
    "1m":  30,
    "2m":  60,
    "15m": 300,
    "1H":  900,
}
