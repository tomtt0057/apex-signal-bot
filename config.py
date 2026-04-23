BOT_TOKEN = "8304682419:AAERok8xSOx-zmbPC1QQlyeTn-zTI30yGKU"
TWELVE_API_KEY = "0158f9f039684e3786de56378964a1a0"
COINGECKO_API_KEY = "CG-hEamcYsBADegxRvZCmVZb1xi"
SIGNAL_INTERVAL_MINUTES = 5
DATABASE_PATH = "trading_bot.db"

# ══════════════════════════════════════
# 💱 FOREX PAIRS
# ══════════════════════════════════════
FOREX_PAIRS = [
    "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF",
    "AUD/USD", "NZD/USD", "USD/CAD", "EUR/GBP",
    "EUR/JPY", "EUR/CHF", "EUR/AUD", "EUR/CAD",
    "EUR/NZD", "GBP/JPY", "GBP/CHF", "GBP/AUD",
    "GBP/CAD", "GBP/NZD", "AUD/JPY", "AUD/CAD",
    "AUD/CHF", "AUD/NZD", "NZD/JPY", "NZD/CAD",
    "NZD/CHF", "CAD/JPY", "CHF/JPY", "USD/NOK",
    "USD/SEK", "USD/DKK", "USD/SGD", "USD/HKD",
    "USD/TRY", "USD/ZAR", "USD/MXN", "USD/PLN",
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
]

# ══════════════════════════════════════
# 📈 STOCKS (Full names + emoji icons)
# ══════════════════════════════════════
STOCK_PAIRS = [
    "🍎 Apple Inc",
    "🪟 Microsoft Corp",
    "🔍 Alphabet (Google)",
    "📦 Amazon",
    "📘 Meta Platforms",
    "⚡ Tesla Inc",
    "💚 NVIDIA Corp",
    "🎬 Netflix",
    "💻 AMD",
    "🔵 Intel Corp",
    "🔴 Oracle Corp",
    "☁️ Salesforce",
    "🎨 Adobe Inc",
    "💳 PayPal",
    "🚗 Uber",
    "🏦 JPMorgan Chase",
    "🏦 Bank of America",
    "🏦 Goldman Sachs",
    "🏦 Morgan Stanley",
    "💳 Visa Inc",
    "💳 Mastercard",
    "💊 Johnson & Johnson",
    "💊 Pfizer Inc",
    "🥤 Coca Cola",
    "🥤 PepsiCo",
    "🍔 McDonald's",
    "🎪 Disney",
    "👟 Nike Inc",
    "🛒 Walmart",
    "🛢️ ExxonMobil",
    "🛢️ Chevron Corp",
    "✈️ Boeing",
    "🛍️ Alibaba",
    "🚗 NIO Inc",
    "💾 Taiwan Semiconductor",
]

# ══════════════════════════════════════
# 📈 STOCK OTC PAIRS
# ══════════════════════════════════════
STOCK_OTC_PAIRS = [
    "🍎 Apple Inc OTC",
    "🪟 Microsoft Corp OTC",
    "🔍 Alphabet (Google) OTC",
    "📦 Amazon OTC",
    "📘 Meta Platforms OTC",
    "⚡ Tesla Inc OTC",
    "💚 NVIDIA Corp OTC",
    "🎬 Netflix OTC",
    "🏦 JPMorgan Chase OTC",
    "💳 Visa Inc OTC",
    "💳 Mastercard OTC",
    "🥤 Coca Cola OTC",
    "🍔 McDonald's OTC",
    "🎪 Disney OTC",
    "👟 Nike Inc OTC",
]

# ══════════════════════════════════════
# 🥇 COMMODITY PAIRS (6 working only)
# ══════════════════════════════════════
COMMODITY_PAIRS = [
    "🥇 Gold",
    "🥈 Silver",
    "⚪ Platinum",
    "🔮 Palladium",
    "🛢️ Crude Oil (WTI)",
    "🛢️ Brent Oil",
]

# ══════════════════════════════════════
# 🥇 COMMODITY OTC PAIRS
# ══════════════════════════════════════
COMMODITY_OTC_PAIRS = [
    "🥇 Gold OTC",
    "🥈 Silver OTC",
    "⚪ Platinum OTC",
    "🔮 Palladium OTC",
    "🛢️ Crude Oil OTC",
    "🛢️ Brent Oil OTC",
]

# ══════════════════════════════════════
# ₿ CRYPTO PAIRS (with emoji icons)
# ══════════════════════════════════════
CRYPTO_PAIRS = [
    "₿ BTC/USD", "Ξ ETH/USD", "🔶 BNB/USD",
    "☀️ SOL/USD", "💧 XRP/USD", "🔵 ADA/USD",
    "🐕 DOGE/USD", "🔷 MATIC/USD", "🔴 DOT/USD",
    "🔺 AVAX/USD", "🔗 LINK/USD", "Ł LTC/USD",
    "🦄 UNI/USD", "⚛️ ATOM/USD", "⚡ TRX/USD",
    "🐕 SHIB/USD", "🔷 ETC/USD", "⭐ XLM/USD",
    "💚 BCH/USD", "🟢 NEAR/USD", "🅰️ APT/USD",
    "📁 FIL/USD", "ℏ HBAR/USD", "🔵 ARB/USD",
    "🔴 OP/USD", "🏛️ MKR/USD", "👻 AAVE/USD",
    "📊 GRT/USD", "🏖️ SAND/USD", "🌐 MANA/USD",
    "🪓 AXS/USD", "👻 FTM/USD", "📺 THETA/USD",
    "✅ VET/USD", "🌿 EOS/USD", "🏛️ XTZ/USD",
    "🔷 ALGO/USD", "🌊 FLOW/USD", "🔒 XMR/USD",
    "💨 DASH/USD", "🛡️ ZEC/USD", "🦇 BAT/USD",
]

# ══════════════════════════════════════
# ₿ CRYPTO OTC PAIRS
# ══════════════════════════════════════
CRYPTO_OTC_PAIRS = [
    "₿ BTC/USD OTC", "Ξ ETH/USD OTC",
    "Ł LTC/USD OTC", "💧 XRP/USD OTC",
    "🔵 ADA/USD OTC", "🐕 DOGE/USD OTC",
    "☀️ SOL/USD OTC", "🔶 BNB/USD OTC",
    "🔴 DOT/USD OTC", "🔗 LINK/USD OTC",
    "💚 BCH/USD OTC", "⭐ XLM/USD OTC",
    "🔷 ETC/USD OTC", "⚡ TRX/USD OTC",
    "🔷 MATIC/USD OTC",
]

# ══════════════════════════════════════
# 🪙 CRYPTO STANDALONE COINS
# ══════════════════════════════════════
CRYPTO_STANDALONE = [
    "₿ Bitcoin", "Ξ Ethereum", "🔶 BNB",
    "☀️ Solana", "💧 XRP", "🔵 Cardano",
    "🐕 Dogecoin", "🔷 Polygon", "🔴 Polkadot",
    "🔺 Avalanche", "🔗 Chainlink", "Ł Litecoin",
    "🦄 Uniswap", "⚛️ Cosmos", "⚡ TRON",
    "🐕 Shiba Inu", "🔷 Ethereum Classic", "⭐ Stellar",
    "💚 Bitcoin Cash", "🟢 NEAR Protocol",
    "🅰️ Aptos", "📁 Filecoin", "ℏ Hedera",
    "🔵 Arbitrum", "🔴 Optimism", "🏛️ Maker",
    "👻 Aave", "📊 The Graph", "🏖️ The Sandbox",
    "🌐 Decentraland", "🪓 Axie Infinity", "👻 Fantom",
    "📺 Theta Network", "✅ VeChain", "🌿 EOS",
    "🏛️ Tezos", "🔷 Algorand", "🌊 Flow",
    "🔒 Monero", "💨 Dash", "🛡️ Zcash",
    "🦇 Basic Attention", "🌶️ Chiliz", "💎 Enjin",
    "📈 Curve", "🔁 1inch", "🏦 Compound",
    "⚡ Synthetix", "🍣 SushiSwap", "🌾 Yearn Finance",
]

ALL_PAIRS = (
    FOREX_PAIRS + FOREX_OTC_PAIRS +
    STOCK_PAIRS + STOCK_OTC_PAIRS +
    COMMODITY_PAIRS + COMMODITY_OTC_PAIRS +
    CRYPTO_PAIRS + CRYPTO_OTC_PAIRS +
    CRYPTO_STANDALONE
)

# ══════════════════════════════════════
# BINANCE SYMBOL MAP
# ══════════════════════════════════════
BINANCE_SYMBOL_MAP = {
    "₿ BTC/USD": "BTCUSDT",
    "Ξ ETH/USD": "ETHUSDT",
    "🔶 BNB/USD": "BNBUSDT",
    "☀️ SOL/USD": "SOLUSDT",
    "💧 XRP/USD": "XRPUSDT",
    "🔵 ADA/USD": "ADAUSDT",
    "🐕 DOGE/USD": "DOGEUSDT",
    "🔷 MATIC/USD": "MATICUSDT",
    "🔴 DOT/USD": "DOTUSDT",
    "🔺 AVAX/USD": "AVAXUSDT",
    "🔗 LINK/USD": "LINKUSDT",
    "Ł LTC/USD": "LTCUSDT",
    "🦄 UNI/USD": "UNIUSDT",
    "⚛️ ATOM/USD": "ATOMUSDT",
    "⚡ TRX/USD": "TRXUSDT",
    "🐕 SHIB/USD": "SHIBUSDT",
    "🔷 ETC/USD": "ETCUSDT",
    "⭐ XLM/USD": "XLMUSDT",
    "💚 BCH/USD": "BCHUSDT",
    "🟢 NEAR/USD": "NEARUSDT",
    "🅰️ APT/USD": "APTUSDT",
    "📁 FIL/USD": "FILUSDT",
    "ℏ HBAR/USD": "HBARUSDT",
    "🔵 ARB/USD": "ARBUSDT",
    "🔴 OP/USD": "OPUSDT",
    "🏛️ MKR/USD": "MKRUSDT",
    "👻 AAVE/USD": "AAVEUSDT",
    "📊 GRT/USD": "GRTUSDT",
    "🏖️ SAND/USD": "SANDUSDT",
    "🌐 MANA/USD": "MANAUSDT",
    "🪓 AXS/USD": "AXSUSDT",
    "👻 FTM/USD": "FTMUSDT",
    "📺 THETA/USD": "THETAUSDT",
    "✅ VET/USD": "VETUSDT",
    "🌿 EOS/USD": "EOSUSDT",
    "🏛️ XTZ/USD": "XTZUSDT",
    "🔷 ALGO/USD": "ALGOUSDT",
    "🌊 FLOW/USD": "FLOWUSDT",
    "🔒 XMR/USD": "XMRUSDT",
    "💨 DASH/USD": "DASHUSDT",
    "🛡️ ZEC/USD": "ZECUSDT",
    "🦇 BAT/USD": "BATUSDT",
    # Crypto OTC
    "₿ BTC/USD OTC": "BTCUSDT",
    "Ξ ETH/USD OTC": "ETHUSDT",
    "Ł LTC/USD OTC": "LTCUSDT",
    "💧 XRP/USD OTC": "XRPUSDT",
    "🔵 ADA/USD OTC": "ADAUSDT",
    "🐕 DOGE/USD OTC": "DOGEUSDT",
    "☀️ SOL/USD OTC": "SOLUSDT",
    "🔶 BNB/USD OTC": "BNBUSDT",
    "🔴 DOT/USD OTC": "DOTUSDT",
    "🔗 LINK/USD OTC": "LINKUSDT",
    "💚 BCH/USD OTC": "BCHUSDT",
    "⭐ XLM/USD OTC": "XLMUSDT",
    "🔷 ETC/USD OTC": "ETCUSDT",
    "⚡ TRX/USD OTC": "TRXUSDT",
    "🔷 MATIC/USD OTC": "MATICUSDT",
}

# ══════════════════════════════════════
# COINGECKO ID MAP
# ══════════════════════════════════════
COINGECKO_ID_MAP = {
    "₿ Bitcoin": "bitcoin",
    "Ξ Ethereum": "ethereum",
    "🔶 BNB": "binancecoin",
    "☀️ Solana": "solana",
    "💧 XRP": "ripple",
    "🔵 Cardano": "cardano",
    "🐕 Dogecoin": "dogecoin",
    "🔷 Polygon": "matic-network",
    "🔴 Polkadot": "polkadot",
    "🔺 Avalanche": "avalanche-2",
    "🔗 Chainlink": "chainlink",
    "Ł Litecoin": "litecoin",
    "🦄 Uniswap": "uniswap",
    "⚛️ Cosmos": "cosmos",
    "⚡ TRON": "tron",
    "🐕 Shiba Inu": "shiba-inu",
    "🔷 Ethereum Classic": "ethereum-classic",
    "⭐ Stellar": "stellar",
    "💚 Bitcoin Cash": "bitcoin-cash",
    "🟢 NEAR Protocol": "near",
    "🅰️ Aptos": "aptos",
    "📁 Filecoin": "filecoin",
    "ℏ Hedera": "hedera-hashgraph",
    "🔵 Arbitrum": "arbitrum",
    "🔴 Optimism": "optimism",
    "🏛️ Maker": "maker",
    "👻 Aave": "aave",
    "📊 The Graph": "the-graph",
    "🏖️ The Sandbox": "the-sandbox",
    "🌐 Decentraland": "decentraland",
    "🪓 Axie Infinity": "axie-infinity",
    "👻 Fantom": "fantom",
    "📺 Theta Network": "theta-token",
    "✅ VeChain": "vechain",
    "🌿 EOS": "eos",
    "🏛️ Tezos": "tezos",
    "🔷 Algorand": "algorand",
    "🌊 Flow": "flow",
    "🔒 Monero": "monero",
    "💨 Dash": "dash",
    "🛡️ Zcash": "zcash",
    "🦇 Basic Attention": "basic-attention-token",
    "🌶️ Chiliz": "chiliz",
    "💎 Enjin": "enjincoin",
    "📈 Curve": "curve-dao-token",
    "🔁 1inch": "1inch",
    "🏦 Compound": "compound-governance-token",
    "⚡ Synthetix": "havven",
    "🍣 SushiSwap": "sushi",
    "🌾 Yearn Finance": "yearn-finance",
}

# ══════════════════════════════════════
# TWELVE DATA SYMBOL MAP
# ══════════════════════════════════════
TWELVE_SYMBOL_MAP = {
    # Forex Normal
    "EUR/USD": "EUR/USD", "GBP/USD": "GBP/USD",
    "USD/JPY": "USD/JPY", "USD/CHF": "USD/CHF",
    "AUD/USD": "AUD/USD", "NZD/USD": "NZD/USD",
    "USD/CAD": "USD/CAD", "EUR/GBP": "EUR/GBP",
    "EUR/JPY": "EUR/JPY", "EUR/CHF": "EUR/CHF",
    "EUR/AUD": "EUR/AUD", "EUR/CAD": "EUR/CAD",
    "EUR/NZD": "EUR/NZD", "GBP/JPY": "GBP/JPY",
    "GBP/CHF": "GBP/CHF", "GBP/AUD": "GBP/AUD",
    "GBP/CAD": "GBP/CAD", "GBP/NZD": "GBP/NZD",
    "AUD/JPY": "AUD/JPY", "AUD/CAD": "AUD/CAD",
    "AUD/CHF": "AUD/CHF", "AUD/NZD": "AUD/NZD",
    "NZD/JPY": "NZD/JPY", "NZD/CAD": "NZD/CAD",
    "NZD/CHF": "NZD/CHF", "CAD/JPY": "CAD/JPY",
    "CHF/JPY": "CHF/JPY", "USD/NOK": "USD/NOK",
    "USD/SEK": "USD/SEK", "USD/DKK": "USD/DKK",
    "USD/SGD": "USD/SGD", "USD/HKD": "USD/HKD",
    "USD/TRY": "USD/TRY", "USD/ZAR": "USD/ZAR",
    "USD/MXN": "USD/MXN", "USD/PLN": "USD/PLN",
    # Forex OTC
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
    # Stocks
    "🍎 Apple Inc": "AAPL",
    "🪟 Microsoft Corp": "MSFT",
    "🔍 Alphabet (Google)": "GOOGL",
    "📦 Amazon": "AMZN",
    "📘 Meta Platforms": "META",
    "⚡ Tesla Inc": "TSLA",
    "💚 NVIDIA Corp": "NVDA",
    "🎬 Netflix": "NFLX",
    "💻 AMD": "AMD",
    "🔵 Intel Corp": "INTC",
    "🔴 Oracle Corp": "ORCL",
    "☁️ Salesforce": "CRM",
    "🎨 Adobe Inc": "ADBE",
    "💳 PayPal": "PYPL",
    "🚗 Uber": "UBER",
    "🏦 JPMorgan Chase": "JPM",
    "🏦 Bank of America": "BAC",
    "🏦 Goldman Sachs": "GS",
    "🏦 Morgan Stanley": "MS",
    "💳 Visa Inc": "V",
    "💳 Mastercard": "MA",
    "💊 Johnson & Johnson": "JNJ",
    "💊 Pfizer Inc": "PFE",
    "🥤 Coca Cola": "KO",
    "🥤 PepsiCo": "PEP",
    "🍔 McDonald's": "MCD",
    "🎪 Disney": "DIS",
    "👟 Nike Inc": "NKE",
    "🛒 Walmart": "WMT",
    "🛢️ ExxonMobil": "XOM",
    "🛢️ Chevron Corp": "CVX",
    "✈️ Boeing": "BA",
    "🛍️ Alibaba": "BABA",
    "🚗 NIO Inc": "NIO",
    "💾 Taiwan Semiconductor": "TSM",
    # Stock OTC
    "🍎 Apple Inc OTC": "AAPL",
    "🪟 Microsoft Corp OTC": "MSFT",
    "🔍 Alphabet (Google) OTC": "GOOGL",
    "📦 Amazon OTC": "AMZN",
    "📘 Meta Platforms OTC": "META",
    "⚡ Tesla Inc OTC": "TSLA",
    "💚 NVIDIA Corp OTC": "NVDA",
    "🎬 Netflix OTC": "NFLX",
    "🏦 JPMorgan Chase OTC": "JPM",
    "💳 Visa Inc OTC": "V",
    "💳 Mastercard OTC": "MA",
    "🥤 Coca Cola OTC": "KO",
    "🍔 McDonald's OTC": "MCD",
    "🎪 Disney OTC": "DIS",
    "👟 Nike Inc OTC": "NKE",
    # Commodities (6 working only)
    "🥇 Gold": "XAU/USD",
    "🥈 Silver": "XAG/USD",
    "⚪ Platinum": "XPT/USD",
    "🔮 Palladium": "XPD/USD",
    "🛢️ Crude Oil (WTI)": "WTI/USD",
    "🛢️ Brent Oil": "BRENT/USD",
    # Commodity OTC
    "🥇 Gold OTC": "XAU/USD",
    "🥈 Silver OTC": "XAG/USD",
    "⚪ Platinum OTC": "XPT/USD",
    "🔮 Palladium OTC": "XPD/USD",
    "🛢️ Crude Oil OTC": "WTI/USD",
    "🛢️ Brent Oil OTC": "BRENT/USD",
}

# ══════════════════════════════════════
# TIMEFRAMES (Updated with short expiry)
# ══════════════════════════════════════
TIMEFRAMES = {
    "3 sec  ⚡": {"twelve": "1min",  "binance": "1m"},
    "15 sec ⚡": {"twelve": "1min",  "binance": "1m"},
    "30 sec ⚡": {"twelve": "1min",  "binance": "1m"},
    "1 min  🕐": {"twelve": "1min",  "binance": "1m"},
    "2 min  🕑": {"twelve": "1min",  "binance": "1m"},
    "5 min  🕔": {"twelve": "5min",  "binance": "5m"},
    "15 min 📊": {"twelve": "15min", "binance": "15m"},
    "30 min 📈": {"twelve": "30min", "binance": "30m"},
    "1 hour ⏰": {"twelve": "1h",    "binance": "1h"},
}
