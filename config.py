BOT_TOKEN = "8304682419:AAERok8xSOx-zmbPC1QQlyeTn-zTI30yGKU"
TWELVE_API_KEY = "0158f9f039684e3786de56378964a1a0"
SIGNAL_INTERVAL_MINUTES = 5
DATABASE_PATH = "trading_bot.db"

# ══════════════════════════════════════
# 💱 FOREX PAIRS (Normal)
# ══════════════════════════════════════
FOREX_PAIRS = [
    # Majors
    "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF",
    "AUD/USD", "NZD/USD", "USD/CAD", "EUR/GBP",
    # EUR Crosses
    "EUR/JPY", "EUR/CHF", "EUR/AUD", "EUR/CAD",
    "EUR/NZD", "EUR/NOK", "EUR/SEK", "EUR/DKK",
    "EUR/PLN", "EUR/HUF", "EUR/CZK", "EUR/TRY",
    # GBP Crosses
    "GBP/JPY", "GBP/CHF", "GBP/AUD", "GBP/CAD",
    "GBP/NZD", "GBP/NOK", "GBP/SEK", "GBP/PLN",
    # AUD Crosses
    "AUD/JPY", "AUD/CAD", "AUD/CHF", "AUD/NZD",
    "AUD/SGD", "AUD/HKD",
    # NZD Crosses
    "NZD/JPY", "NZD/CAD", "NZD/CHF", "NZD/SGD",
    # JPY Crosses
    "CAD/JPY", "CHF/JPY", "SGD/JPY", "HKD/JPY",
    "NOK/JPY", "SEK/JPY", "DKK/JPY",
    # USD Crosses
    "USD/NOK", "USD/SEK", "USD/DKK", "USD/SGD",
    "USD/HKD", "USD/TRY", "USD/ZAR", "USD/MXN",
    "USD/PLN", "USD/HUF", "USD/CZK", "USD/THB",
    # Other
    "CAD/CHF", "CHF/NOK", "CHF/SEK",
]

# ══════════════════════════════════════
# 💱 FOREX OTC PAIRS
# ══════════════════════════════════════
FOREX_OTC_PAIRS = [
    "EUR/USD OTC", "GBP/USD OTC", "USD/JPY OTC",
    "USD/CHF OTC", "AUD/USD OTC", "NZD/USD OTC",
    "USD/CAD OTC", "EUR/GBP OTC", "EUR/JPY OTC",
    "GBP/JPY OTC", "EUR/CHF OTC", "AUD/JPY OTC",
    "EUR/AUD OTC", "GBP/AUD OTC", "EUR/CAD OTC",
    "GBP/CAD OTC", "AUD/CAD OTC", "NZD/JPY OTC",
    "CAD/JPY OTC", "CHF/JPY OTC", "GBP/CHF OTC",
    "AUD/CHF OTC", "EUR/NZD OTC", "GBP/NZD OTC",
    "AUD/NZD OTC", "NZD/CAD OTC", "NZD/CHF OTC",
    "USD/SGD OTC", "USD/HKD OTC", "USD/NOK OTC",
    "USD/SEK OTC", "USD/DKK OTC", "USD/ZAR OTC",
    "USD/MXN OTC", "USD/TRY OTC",
]

# ══════════════════════════════════════
# 📈 STOCK PAIRS (Normal)
# ══════════════════════════════════════
STOCK_PAIRS = [
    # US Tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "TSLA", "NVDA", "NFLX", "AMD", "INTC",
    "ORCL", "CRM", "ADBE", "PYPL", "UBER",
    "SNAP", "TWTR", "SHOP", "SQ", "ZOOM",
    # US Finance
    "JPM", "BAC", "GS", "MS", "WFC",
    "C", "AXP", "V", "MA", "BRK",
    # US Other
    "AMGN", "JNJ", "PFE", "KO", "PEP",
    "MCD", "DIS", "NKE", "WMT", "COST",
    "XOM", "CVX", "BA", "CAT", "GE",
    # European Stocks
    "VOW", "BMW", "DAI", "SAP", "NESN",
    "NOVN", "ROCHE", "HSBA", "BP", "SHEL",
    # Asian Stocks
    "BABA", "JD", "BIDU", "NIO", "TCEHY",
    "SONY", "TM", "HMC", "SMSN", "TSM",
]

# ══════════════════════════════════════
# 📈 STOCK OTC PAIRS
# ══════════════════════════════════════
STOCK_OTC_PAIRS = [
    "AAPL OTC", "MSFT OTC", "GOOGL OTC",
    "AMZN OTC", "META OTC", "TSLA OTC",
    "NVDA OTC", "NFLX OTC", "AMD OTC",
    "JPM OTC", "BAC OTC", "GS OTC",
    "V OTC", "MA OTC", "KO OTC",
    "PEP OTC", "MCD OTC", "DIS OTC",
    "NKE OTC", "WMT OTC", "XOM OTC",
    "CVX OTC", "BABA OTC", "SONY OTC",
    "TM OTC", "TSM OTC",
]

# ══════════════════════════════════════
# 🥇 COMMODITY PAIRS (Normal)
# ══════════════════════════════════════
COMMODITY_PAIRS = [
    # Precious Metals
    "XAU/USD", "XAG/USD", "XPT/USD", "XPD/USD",
    # Energy
    "OIL/USD", "BRENT/USD", "NGAS/USD", "COAL/USD",
    # Agricultural
    "WHEAT/USD", "CORN/USD", "SOYA/USD", "SUGAR/USD",
    "COFFEE/USD", "COTTON/USD", "COCOA/USD",
    # Industrial Metals
    "COPPER/USD", "IRON/USD", "NICKEL/USD",
    "ZINC/USD", "ALUMINIUM/USD", "LEAD/USD",
    # Livestock
    "CATTLE/USD", "HOGS/USD",
]

# ══════════════════════════════════════
# 🥇 COMMODITY OTC PAIRS
# ══════════════════════════════════════
COMMODITY_OTC_PAIRS = [
    "XAU/USD OTC", "XAG/USD OTC", "XPT/USD OTC",
    "OIL/USD OTC", "BRENT/USD OTC", "NGAS/USD OTC",
    "WHEAT/USD OTC", "CORN/USD OTC", "SUGAR/USD OTC",
    "COFFEE/USD OTC", "COPPER/USD OTC", "NICKEL/USD OTC",
]

# ══════════════════════════════════════
# ₿ CRYPTO PAIRS (Normal — with USD)
# ══════════════════════════════════════
CRYPTO_PAIRS = [
    "BTC/USD", "ETH/USD", "BNB/USD", "SOL/USD",
    "XRP/USD", "ADA/USD", "DOGE/USD", "MATIC/USD",
    "DOT/USD", "AVAX/USD", "LINK/USD", "LTC/USD",
    "UNI/USD", "ATOM/USD", "TRX/USD", "SHIB/USD",
    "ETC/USD", "XLM/USD", "BCH/USD", "NEAR/USD",
    "APT/USD", "FIL/USD", "HBAR/USD", "ARB/USD",
    "OP/USD", "MKR/USD", "AAVE/USD", "GRT/USD",
    "SAND/USD", "MANA/USD", "AXS/USD", "FTM/USD",
    "THETA/USD", "VET/USD", "EOS/USD", "XTZ/USD",
    "ALGO/USD", "FLOW/USD", "XMR/USD", "DASH/USD",
    "ZEC/USD", "BAT/USD", "CHZ/USD", "ENJ/USD",
    "CRV/USD", "1INCH/USD", "COMP/USD", "SNX/USD",
    "SUSHI/USD", "YFI/USD",
]

# ══════════════════════════════════════
# ₿ CRYPTO STANDALONE (No pairs — just the coin)
# ══════════════════════════════════════
CRYPTO_STANDALONE = [
    "Bitcoin", "Ethereum", "BNB", "Solana",
    "XRP", "Cardano", "Dogecoin", "Polygon",
    "Polkadot", "Avalanche", "Chainlink", "Litecoin",
    "Uniswap", "Cosmos", "TRON", "Shiba Inu",
    "Ethereum Classic", "Stellar", "Bitcoin Cash", "NEAR Protocol",
    "Aptos", "Filecoin", "Hedera", "Arbitrum",
    "Optimism", "Maker", "Aave", "The Graph",
    "The Sandbox", "Decentraland", "Axie Infinity", "Fantom",
    "Theta", "VeChain", "EOS", "Tezos",
    "Algorand", "Flow", "Monero", "Dash",
    "Zcash", "Basic Attention", "Chiliz", "Enjin",
    "Curve", "1inch", "Compound", "Synthetix",
    "SushiSwap", "Yearn Finance",
]

# ══════════════════════════════════════
# ₿ CRYPTO OTC PAIRS
# ══════════════════════════════════════
CRYPTO_OTC_PAIRS = [
    "BTC/USD OTC", "ETH/USD OTC", "LTC/USD OTC",
    "XRP/USD OTC", "ADA/USD OTC", "DOGE/USD OTC",
    "SOL/USD OTC", "BNB/USD OTC", "DOT/USD OTC",
    "LINK/USD OTC", "BCH/USD OTC", "XLM/USD OTC",
    "ETC/USD OTC", "TRX/USD OTC", "MATIC/USD OTC",
]

ALL_PAIRS = (
    FOREX_PAIRS + FOREX_OTC_PAIRS +
    STOCK_PAIRS + STOCK_OTC_PAIRS +
    COMMODITY_PAIRS + COMMODITY_OTC_PAIRS +
    CRYPTO_PAIRS + CRYPTO_OTC_PAIRS +
    CRYPTO_STANDALONE
)

BINANCE_SYMBOL_MAP = {
    "BTC/USD": "BTCUSDT", "ETH/USD": "ETHUSDT",
    "BNB/USD": "BNBUSDT", "SOL/USD": "SOLUSDT",
    "XRP/USD": "XRPUSDT", "ADA/USD": "ADAUSDT",
    "DOGE/USD": "DOGEUSDT", "MATIC/USD": "MATICUSDT",
    "DOT/USD": "DOTUSDT", "AVAX/USD": "AVAXUSDT",
    "LINK/USD": "LINKUSDT", "LTC/USD": "LTCUSDT",
    "UNI/USD": "UNIUSDT", "ATOM/USD": "ATOMUSDT",
    "TRX/USD": "TRXUSDT", "SHIB/USD": "SHIBUSDT",
    "ETC/USD": "ETCUSDT", "XLM/USD": "XLMUSDT",
    "BCH/USD": "BCHUSDT", "NEAR/USD": "NEARUSDT",
    "APT/USD": "APTUSDT", "FIL/USD": "FILUSDT",
    "HBAR/USD": "HBARUSDT", "ARB/USD": "ARBUSDT",
    "OP/USD": "OPUSDT", "MKR/USD": "MKRUSDT",
    "AAVE/USD": "AAVEUSDT", "GRT/USD": "GRTUSDT",
    "SAND/USD": "SANDUSDT", "MANA/USD": "MANAUSDT",
    "AXS/USD": "AXSUSDT", "FTM/USD": "FTMUSDT",
    "THETA/USD": "THETAUSDT", "VET/USD": "VETUSDT",
    "EOS/USD": "EOSUSDT", "XTZ/USD": "XTZUSDT",
    "ALGO/USD": "ALGOUSDT", "FLOW/USD": "FLOWUSDT",
    "XMR/USD": "XMRUSDT", "DASH/USD": "DASHUSDT",
    "ZEC/USD": "ZECUSDT", "BAT/USD": "BATUSDT",
    "CHZ/USD": "CHZUSDT", "ENJ/USD": "ENJUSDT",
    "CRV/USD": "CRVUSDT", "1INCH/USD": "1INCHUSDT",
    "COMP/USD": "COMPUSDT", "SNX/USD": "SNXUSDT",
    "SUSHI/USD": "SUSHIUSDT", "YFI/USD": "YFIUSDT",
    # OTC mapped to same Binance symbols
    "BTC/USD OTC": "BTCUSDT", "ETH/USD OTC": "ETHUSDT",
    "LTC/USD OTC": "LTCUSDT", "XRP/USD OTC": "XRPUSDT",
    "ADA/USD OTC": "ADAUSDT", "DOGE/USD OTC": "DOGEUSDT",
    "SOL/USD OTC": "SOLUSDT", "BNB/USD OTC": "BNBUSDT",
    "DOT/USD OTC": "DOTUSDT", "LINK/USD OTC": "LINKUSDT",
    "BCH/USD OTC": "BCHUSDT", "XLM/USD OTC": "XLMUSDT",
    "ETC/USD OTC": "ETCUSDT", "TRX/USD OTC": "TRXUSDT",
    "MATIC/USD OTC": "MATICUSDT",
    # Standalone crypto mapped to Binance
    "Bitcoin": "BTCUSDT", "Ethereum": "ETHUSDT",
    "BNB": "BNBUSDT", "Solana": "SOLUSDT",
    "XRP": "XRPUSDT", "Cardano": "ADAUSDT",
    "Dogecoin": "DOGEUSDT", "Polygon": "MATICUSDT",
    "Polkadot": "DOTUSDT", "Avalanche": "AVAXUSDT",
    "Chainlink": "LINKUSDT", "Litecoin": "LTCUSDT",
    "Uniswap": "UNIUSDT", "Cosmos": "ATOMUSDT",
    "TRON": "TRXUSDT", "Shiba Inu": "SHIBUSDT",
    "Ethereum Classic": "ETCUSDT", "Stellar": "XLMUSDT",
    "Bitcoin Cash": "BCHUSDT", "NEAR Protocol": "NEARUSDT",
    "Aptos": "APTUSDT", "Filecoin": "FILUSDT",
    "Hedera": "HBARUSDT", "Arbitrum": "ARBUSDT",
    "Optimism": "OPUSDT", "Maker": "MKRUSDT",
    "Aave": "AAVEUSDT", "The Graph": "GRTUSDT",
    "The Sandbox": "SANDUSDT", "Decentraland": "MANAUSDT",
    "Axie Infinity": "AXSUSDT", "Fantom": "FTMUSDT",
    "Theta": "THETAUSDT", "VeChain": "VETUSDT",
    "EOS": "EOSUSDT", "Tezos": "XTZUSDT",
    "Algorand": "ALGOUSDT", "Flow": "FLOWUSDT",
    "Monero": "XMRUSDT", "Dash": "DASHUSDT",
    "Zcash": "ZECUSDT", "Basic Attention": "BATUSDT",
    "Chiliz": "CHZUSDT", "Enjin": "ENJUSDT",
    "Curve": "CRVUSDT", "1inch": "1INCHUSDT",
    "Compound": "COMPUSDT", "Synthetix": "SNXUSDT",
    "SushiSwap": "SUSHIUSDT", "Yearn Finance": "YFIUSDT",
}

TWELVE_SYMBOL_MAP = {
    "EUR/USD": "EUR/USD", "GBP/USD": "GBP/USD",
    "USD/JPY": "USD/JPY", "USD/CHF": "USD/CHF",
    "AUD/USD": "AUD/USD", "NZD/USD": "NZD/USD",
    "USD/CAD": "USD/CAD", "EUR/GBP": "EUR/GBP",
    "EUR/JPY": "EUR/JPY", "EUR/CHF": "EUR/CHF",
    "EUR/AUD": "EUR/AUD", "EUR/CAD": "EUR/CAD",
    "EUR/NZD": "EUR/NZD", "EUR/NOK": "EUR/NOK",
    "EUR/SEK": "EUR/SEK", "EUR/DKK": "EUR/DKK",
    "EUR/PLN": "EUR/PLN", "EUR/HUF": "EUR/HUF",
    "EUR/CZK": "EUR/CZK", "EUR/TRY": "EUR/TRY",
    "GBP/JPY": "GBP/JPY", "GBP/CHF": "GBP/CHF",
    "GBP/AUD": "GBP/AUD", "GBP/CAD": "GBP/CAD",
    "GBP/NZD": "GBP/NZD", "GBP/NOK": "GBP/NOK",
    "GBP/SEK": "GBP/SEK", "GBP/PLN": "GBP/PLN",
    "AUD/JPY": "AUD/JPY", "AUD/CAD": "AUD/CAD",
    "AUD/CHF": "AUD/CHF", "AUD/NZD": "AUD/NZD",
    "AUD/SGD": "AUD/SGD", "AUD/HKD": "AUD/HKD",
    "NZD/JPY": "NZD/JPY", "NZD/CAD": "NZD/CAD",
    "NZD/CHF": "NZD/CHF", "NZD/SGD": "NZD/SGD",
    "CAD/JPY": "CAD/JPY", "CHF/JPY": "CHF/JPY",
    "SGD/JPY": "SGD/JPY", "HKD/JPY": "HKD/JPY",
    "NOK/JPY": "NOK/JPY", "SEK/JPY": "SEK/JPY",
    "DKK/JPY": "DKK/JPY", "USD/NOK": "USD/NOK",
    "USD/SEK": "USD/SEK", "USD/DKK": "USD/DKK",
    "USD/SGD": "USD/SGD", "USD/HKD": "USD/HKD",
    "USD/TRY": "USD/TRY", "USD/ZAR": "USD/ZAR",
    "USD/MXN": "USD/MXN", "USD/PLN": "USD/PLN",
    "USD/HUF": "USD/HUF", "USD/CZK": "USD/CZK",
    "USD/THB": "USD/THB", "CAD/CHF": "CAD/CHF",
    "CHF/NOK": "CHF/NOK", "CHF/SEK": "CHF/SEK",
    # Stocks
    "AAPL": "AAPL", "MSFT": "MSFT", "GOOGL": "GOOGL",
    "AMZN": "AMZN", "META": "META", "TSLA": "TSLA",
    "NVDA": "NVDA", "NFLX": "NFLX", "AMD": "AMD",
    "INTC": "INTC", "ORCL": "ORCL", "CRM": "CRM",
    "ADBE": "ADBE", "PYPL": "PYPL", "UBER": "UBER",
    "JPM": "JPM", "BAC": "BAC", "GS": "GS",
    "MS": "MS", "WFC": "WFC", "V": "V",
    "MA": "MA", "JNJ": "JNJ", "PFE": "PFE",
    "KO": "KO", "PEP": "PEP", "MCD": "MCD",
    "DIS": "DIS", "NKE": "NKE", "WMT": "WMT",
    "XOM": "XOM", "CVX": "CVX", "BA": "BA",
    "BABA": "BABA", "NIO": "NIO", "TSM": "TSM",
    # Stock OTC
    "AAPL OTC": "AAPL", "MSFT OTC": "MSFT",
    "GOOGL OTC": "GOOGL", "AMZN OTC": "AMZN",
    "META OTC": "META", "TSLA OTC": "TSLA",
    "NVDA OTC": "NVDA", "NFLX OTC": "NFLX",
    "AMD OTC": "AMD", "JPM OTC": "JPM",
    "BAC OTC": "BAC", "GS OTC": "GS",
    "V OTC": "V", "MA OTC": "MA",
    "KO OTC": "KO", "PEP OTC": "PEP",
    "MCD OTC": "MCD", "DIS OTC": "DIS",
    "NKE OTC": "NKE", "WMT OTC": "WMT",
    "XOM OTC": "XOM", "CVX OTC": "CVX",
    "BABA OTC": "BABA", "SONY OTC": "SONY",
    "TM OTC": "TM", "TSM OTC": "TSM",
    # Commodities
    "XAU/USD": "XAU/USD", "XAG/USD": "XAG/USD",
    "XPT/USD": "XPT/USD", "XPD/USD": "XPD/USD",
    "OIL/USD": "WTI/USD", "BRENT/USD": "BRENT/USD",
    "NGAS/USD": "NGAS/USD", "WHEAT/USD": "WHEAT/USD",
    "CORN/USD": "CORN/USD", "SUGAR/USD": "SUGAR/USD",
    "COFFEE/USD": "COFFEE/USD", "COPPER/USD": "COPPER/USD",
    # Commodity OTC
    "XAU/USD OTC": "XAU/USD", "XAG/USD OTC": "XAG/USD",
    "OIL/USD OTC": "WTI/USD", "BRENT/USD OTC": "BRENT/USD",
    "NGAS/USD OTC": "NGAS/USD", "WHEAT/USD OTC": "WHEAT/USD",
    "CORN/USD OTC": "CORN/USD", "SUGAR/USD OTC": "SUGAR/USD",
    "COFFEE/USD OTC": "COFFEE/USD",
    "COPPER/USD OTC": "COPPER/USD",
    # OTC Forex
    "EUR/USD OTC": "EUR/USD", "GBP/USD OTC": "GBP/USD",
    "USD/JPY OTC": "USD/JPY", "USD/CHF OTC": "USD/CHF",
    "AUD/USD OTC": "AUD/USD", "NZD/USD OTC": "NZD/USD",
    "USD/CAD OTC": "USD/CAD", "EUR/GBP OTC": "EUR/GBP",
    "EUR/JPY OTC": "EUR/JPY", "GBP/JPY OTC": "GBP/JPY",
    "EUR/CHF OTC": "EUR/CHF", "AUD/JPY OTC": "AUD/JPY",
    "EUR/AUD OTC": "EUR/AUD", "GBP/AUD OTC": "GBP/AUD",
    "EUR/CAD OTC": "EUR/CAD", "GBP/CAD OTC": "GBP/CAD",
    "AUD/CAD OTC": "AUD/CAD", "NZD/JPY OTC": "NZD/JPY",
    "CAD/JPY OTC": "CAD/JPY", "CHF/JPY OTC": "CHF/JPY",
    "GBP/CHF OTC": "GBP/CHF", "AUD/CHF OTC": "AUD/CHF",
    "EUR/NZD OTC": "EUR/NZD", "GBP/NZD OTC": "GBP/NZD",
    "AUD/NZD OTC": "AUD/NZD", "NZD/CAD OTC": "NZD/CAD",
    "NZD/CHF OTC": "NZD/CHF", "USD/SGD OTC": "USD/SGD",
    "USD/HKD OTC": "USD/HKD", "USD/NOK OTC": "USD/NOK",
    "USD/SEK OTC": "USD/SEK", "USD/DKK OTC": "USD/DKK",
    "USD/ZAR OTC": "USD/ZAR", "USD/MXN OTC": "USD/MXN",
    "USD/TRY OTC": "USD/TRY",
}

TIMEFRAMES = {
    "1 min  ⚡": {"twelve": "1min",  "binance": "1m"},
    "5 min  🕐": {"twelve": "5min",  "binance": "5m"},
    "15 min 📊": {"twelve": "15min", "binance": "15m"},
    "1 hour 📈": {"twelve": "1h",    "binance": "1h"},
}
