import httpx
import time
import json
import asyncio
import threading
from datetime import datetime, timezone

_cache = {}
CACHE_SECONDS = 120
_news_cache = {}
NEWS_CACHE_SECONDS = 300

# ─────────────────────────────────────────
# MARKET SESSION
# ─────────────────────────────────────────

def get_current_session():
    hour = datetime.now(timezone.utc).hour
    if 22 <= hour or hour < 7:
        return "Tokyo", "🇯🇵"
    elif 7 <= hour < 9:
        return "Tokyo/London Overlap", "🌏"
    elif 9 <= hour < 12:
        return "London", "🇬🇧"
    elif 12 <= hour < 13:
        return "London/NY Overlap", "🌍"
    elif 13 <= hour < 17:
        return "New York", "🇺🇸"
    elif 17 <= hour < 22:
        return "New York Close", "🌙"
    return "Off Hours", "😴"

def is_good_trading_time():
    session, _ = get_current_session()
    return session in [
        "London", "New York",
        "London/NY Overlap", "Tokyo/London Overlap"
    ]

# ─────────────────────────────────────────
# DERIV WEBSOCKET (OTC pairs)
# ─────────────────────────────────────────

def fetch_deriv_otc(symbol, granularity=300, count=80):
    from config import DERIV_APP_ID
    result = [None, None, None, None]

    async def _fetch():
        try:
            import websockets
            url = (
                f"wss://ws.binaryws.com/websockets/v3"
                f"?app_id={DERIV_APP_ID}"
            )
            async with websockets.connect(
                url, ping_interval=None
            ) as ws:
                req = {
                    "ticks_history": symbol,
                    "adjust_start_time": 1,
                    "count": count,
                    "end": "latest",
                    "granularity": granularity,
                    "style": "candles"
                }
                await ws.send(json.dumps(req))
                resp = await asyncio.wait_for(
                    ws.recv(), timeout=10
                )
                data = json.loads(resp)
                if "candles" in data and data["candles"]:
                    c = data["candles"]
                    result[0] = [float(x["close"]) for x in c]
                    result[1] = [float(x["high"]) for x in c]
                    result[2] = [float(x["low"]) for x in c]
                    result[3] = [float(x["open"]) for x in c]
        except Exception:
            pass

    def run():
        asyncio.run(_fetch())

    t = threading.Thread(target=run)
    t.start()
    t.join(timeout=15)
    return tuple(result)

# ─────────────────────────────────────────
# YAHOO FINANCE
# ─────────────────────────────────────────

YAHOO_SYMBOL_MAP = {
    # Forex Normal
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X", "USD/CHF": "USDCHF=X",
    "AUD/USD": "AUDUSD=X", "NZD/USD": "NZDUSD=X",
    "USD/CAD": "USDCAD=X", "EUR/GBP": "EURGBP=X",
    "EUR/JPY": "EURJPY=X", "EUR/CHF": "EURCHF=X",
    "EUR/AUD": "EURAUD=X", "EUR/CAD": "EURCAD=X",
    "EUR/NZD": "EURNZD=X", "GBP/JPY": "GBPJPY=X",
    "GBP/CHF": "GBPCHF=X", "GBP/AUD": "GBPAUD=X",
    "GBP/CAD": "GBPCAD=X", "GBP/NZD": "GBPNZD=X",
    "AUD/JPY": "AUDJPY=X", "AUD/CAD": "AUDCAD=X",
    "AUD/CHF": "AUDCHF=X", "AUD/NZD": "AUDNZD=X",
    "NZD/JPY": "NZDJPY=X", "NZD/CAD": "NZDCAD=X",
    "NZD/CHF": "NZDCHF=X", "CAD/JPY": "CADJPY=X",
    "CHF/JPY": "CHFJPY=X", "USD/NOK": "USDNOK=X",
    "USD/SEK": "USDSEK=X", "USD/DKK": "USDDKK=X",
    "USD/SGD": "USDSGD=X", "USD/HKD": "USDHKD=X",
    "USD/TRY": "USDTRY=X", "USD/ZAR": "USDZAR=X",
    "USD/MXN": "USDMXN=X", "USD/PLN": "USDPLN=X",
    # Forex OTC
    "EUR/USD OTC": "EURUSD=X", "GBP/USD OTC": "GBPUSD=X",
    "USD/JPY OTC": "USDJPY=X", "USD/CHF OTC": "USDCHF=X",
    "AUD/USD OTC": "AUDUSD=X", "NZD/USD OTC": "NZDUSD=X",
    "USD/CAD OTC": "USDCAD=X", "EUR/GBP OTC": "EURGBP=X",
    "EUR/JPY OTC": "EURJPY=X", "GBP/JPY OTC": "GBPJPY=X",
    "EUR/CHF OTC": "EURCHF=X", "AUD/JPY OTC": "AUDJPY=X",
    "EUR/AUD OTC": "EURAUD=X", "GBP/AUD OTC": "GBPAUD=X",
    "EUR/CAD OTC": "EURCAD=X", "GBP/CAD OTC": "GBPCAD=X",
    "AUD/CAD OTC": "AUDCAD=X", "NZD/JPY OTC": "NZDJPY=X",
    "CAD/JPY OTC": "CADJPY=X", "CHF/JPY OTC": "CHFJPY=X",
    "GBP/CHF OTC": "GBPCHF=X", "AUD/CHF OTC": "AUDCHF=X",
    "EUR/NZD OTC": "EURNZD=X", "GBP/NZD OTC": "GBPNZD=X",
    # Stocks
    "Apple Inc": "AAPL", "Microsoft Corp": "MSFT",
    "Alphabet (Google)": "GOOGL", "Amazon": "AMZN",
    "Meta Platforms": "META", "Tesla Inc": "TSLA",
    "NVIDIA Corp": "NVDA", "Netflix": "NFLX",
    "AMD": "AMD", "Intel Corp": "INTC",
    "Oracle Corp": "ORCL", "Salesforce": "CRM",
    "Adobe Inc": "ADBE", "PayPal": "PYPL",
    "Uber": "UBER", "JPMorgan Chase": "JPM",
    "Bank of America": "BAC", "Goldman Sachs": "GS",
    "Morgan Stanley": "MS", "Visa Inc": "V",
    "Mastercard": "MA", "Johnson & Johnson": "JNJ",
    "Pfizer Inc": "PFE", "Coca Cola": "KO",
    "PepsiCo": "PEP", "McDonald's": "MCD",
    "Disney": "DIS", "Nike Inc": "NKE",
    "Walmart": "WMT", "ExxonMobil": "XOM",
    "Chevron Corp": "CVX", "Boeing": "BA",
    "Alibaba": "BABA", "NIO Inc": "NIO",
    "Taiwan Semiconductor": "TSM",
    # Stock OTC
    "Apple Inc OTC": "AAPL", "Microsoft Corp OTC": "MSFT",
    "Alphabet (Google) OTC": "GOOGL", "Amazon OTC": "AMZN",
    "Meta Platforms OTC": "META", "Tesla Inc OTC": "TSLA",
    "NVIDIA Corp OTC": "NVDA", "Netflix OTC": "NFLX",
    "JPMorgan Chase OTC": "JPM", "Visa Inc OTC": "V",
    "Mastercard OTC": "MA", "Coca Cola OTC": "KO",
    "McDonald's OTC": "MCD", "Disney OTC": "DIS",
    "Nike Inc OTC": "NKE",
    # Commodities
    "Gold": "GC=F", "Silver": "SI=F",
    "Platinum": "PL=F", "Palladium": "PA=F",
    "Crude Oil (WTI)": "CL=F", "Brent Oil": "BZ=F",
    "Natural Gas": "NG=F", "Copper": "HG=F",
    "Gold OTC": "GC=F", "Silver OTC": "SI=F",
    "Crude Oil OTC": "CL=F", "Brent Oil OTC": "BZ=F",
}


def fetch_yahoo(symbol, interval="5m", bars=80):
    try:
        yahoo_sym = YAHOO_SYMBOL_MAP.get(symbol)
        if not yahoo_sym:
            return None, None, None, None
        iv_map = {
            "1m": ("1m", "1d"),
            "5m": ("5m", "5d"),
            "15m": ("15m", "5d"),
            "30m": ("30m", "1mo"),
            "1h": ("1h", "1mo"),
        }
        yf_interval, period = iv_map.get(interval, ("5m", "5d"))
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart"
            f"/{yahoo_sym}?interval={yf_interval}&range={period}"
        )
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36"
            )
        }
        r = httpx.get(url, headers=headers, timeout=10)
        data = r.json()
        chart = data["chart"]["result"][0]
        quotes = chart["indicators"]["quote"][0]
        closes = [float(x) for x in quotes["close"] if x is not None]
        highs = [float(x) for x in quotes["high"] if x is not None]
        lows = [float(x) for x in quotes["low"] if x is not None]
        opens = [float(x) for x in quotes["open"] if x is not None]
        if not closes or len(closes) < 5:
            return None, None, None, None
        return (
            closes[-bars:], highs[-bars:],
            lows[-bars:], opens[-bars:]
        )
    except Exception:
        return None, None, None, None

# ─────────────────────────────────────────
# BINANCE
# ─────────────────────────────────────────

def fetch_binance(symbol, interval="5m", bars=80):
    try:
        url = (
            f"https://api.binance.com/api/v3/klines"
            f"?symbol={symbol}&interval={interval}&limit={bars}"
        )
        r = httpx.get(url, timeout=8)
        data = r.json()
        if not data or not isinstance(data, list):
            return None, None, None, None
        return (
            [float(k[4]) for k in data],
            [float(k[2]) for k in data],
            [float(k[3]) for k in data],
            [float(k[1]) for k in data],
        )
    except Exception:
        return None, None, None, None

# ─────────────────────────────────────────
# KUCOIN
# ─────────────────────────────────────────

def fetch_kucoin(symbol, interval="5m", bars=80):
    try:
        iv = {
            "1m": "1min", "5m": "5min",
            "15m": "15min", "30m": "30min", "1h": "1hour"
        }.get(interval, "5min")
        url = (
            f"https://api.kucoin.com/api/v1/market/candles"
            f"?type={iv}&symbol={symbol}"
        )
        r = httpx.get(url, timeout=8)
        data = r.json()
        if data.get("code") != "200000":
            return None, None, None, None
        c = list(reversed(data.get("data", [])))[-bars:]
        if not c:
            return None, None, None, None
        return (
            [float(x[2]) for x in c],
            [float(x[3]) for x in c],
            [float(x[4]) for x in c],
            [float(x[1]) for x in c],
        )
    except Exception:
        return None, None, None, None

# ─────────────────────────────────────────
# OKX
# ─────────────────────────────────────────

def fetch_okx(symbol, interval="5m", bars=80):
    try:
        iv = {
            "1m": "1m", "5m": "5m",
            "15m": "15m", "30m": "30m", "1h": "1H"
        }.get(interval, "5m")
        url = (
            f"https://www.okx.com/api/v5/market/candles"
            f"?instId={symbol}&bar={iv}&limit={bars}"
        )
        r = httpx.get(url, timeout=8)
        data = r.json()
        if data.get("code") != "0":
            return None, None, None, None
        c = list(reversed(data.get("data", [])))
        if not c:
            return None, None, None, None
        return (
            [float(x[4]) for x in c],
            [float(x[2]) for x in c],
            [float(x[3]) for x in c],
            [float(x[1]) for x in c],
        )
    except Exception:
        return None, None, None, None

# ─────────────────────────────────────────
# KRAKEN
# ─────────────────────────────────────────

KRAKEN_MAP = {
    "BTCUSDT": "XBTUSD", "ETHUSDT": "ETHUSD",
    "XRPUSDT": "XRPUSD", "LTCUSDT": "LTCUSD",
    "ADAUSDT": "ADAUSD", "SOLUSDT": "SOLUSD",
    "DOTUSDT": "DOTUSD", "LINKUSDT": "LINKUSD",
    "XLMUSDT": "XLMUSD", "BCHUSDT": "BCHUSD",
    "DOGEUSDT": "XDGUSD", "ATOMUSDT": "ATOMUSD",
}


def fetch_kraken(symbol, interval="5"):
    try:
        iv = {
            "1m": "1", "5m": "5",
            "15m": "15", "30m": "30", "1h": "60"
        }.get(interval, "5")
        url = (
            f"https://api.kraken.com/0/public/OHLC"
            f"?pair={symbol}&interval={iv}"
        )
        r = httpx.get(url, timeout=8)
        data = r.json()
        if data.get("error"):
            return None, None, None, None
        result = data.get("result", {})
        key = [k for k in result if k != "last"]
        if not key:
            return None, None, None, None
        c = result[key[0]]
        return (
            [float(x[4]) for x in c],
            [float(x[2]) for x in c],
            [float(x[3]) for x in c],
            [float(x[1]) for x in c],
        )
    except Exception:
        return None, None, None, None

# ─────────────────────────────────────────
# METALS LIVE
# ─────────────────────────────────────────

def fetch_metals_live(symbol):
    try:
        metal_map = {
            "Gold": "gold", "Silver": "silver",
            "Gold OTC": "gold", "Silver OTC": "silver",
        }
        metal = metal_map.get(symbol)
        if not metal:
            return None, None, None, None
        url = f"https://api.metals.live/v1/spot/{metal}"
        r = httpx.get(url, timeout=6)
        data = r.json()
        if isinstance(data, list) and data:
            price = float(data[0].get("price", 0))
            if price > 0:
                import random
                prices = [
                    price * (
                        1 + (i - 40) * 0.0002
                        + random.uniform(-0.0001, 0.0001)
                    )
                    for i in range(80)
                ]
                return prices, prices, prices, prices
        return None, None, None, None
    except Exception:
        return None, None, None, None

# ─────────────────────────────────────────
# ALPHA VANTAGE
# ─────────────────────────────────────────

def fetch_alpha_vantage_forex(pair, interval="5min"):
    try:
        from config import ALPHA_VANTAGE_API_KEY
        if not ALPHA_VANTAGE_API_KEY:
            return None, None, None, None
        parts = pair.replace(" OTC", "").strip().split("/")
        if len(parts) != 2:
            return None, None, None, None
        from_sym, to_sym = parts[0], parts[1]
        url = (
            f"https://www.alphavantage.co/query"
            f"?function=FX_INTRADAY"
            f"&from_symbol={from_sym}"
            f"&to_symbol={to_sym}"
            f"&interval={interval}"
            f"&outputsize=compact"
            f"&apikey={ALPHA_VANTAGE_API_KEY}"
        )
        r = httpx.get(url, timeout=10)
        data = r.json()
        key = f"Time Series FX ({interval})"
        if key not in data:
            return None, None, None, None
        values = list(reversed(list(data[key].values())))[:80]
        return (
            [float(v["4. close"]) for v in values],
            [float(v["2. high"]) for v in values],
            [float(v["3. low"]) for v in values],
            [float(v["1. open"]) for v in values],
        )
    except Exception:
        return None, None, None, None


def fetch_alpha_vantage_stock(symbol, interval="5min"):
    try:
        from config import ALPHA_VANTAGE_API_KEY
        if not ALPHA_VANTAGE_API_KEY:
            return None, None, None, None
        url = (
            f"https://www.alphavantage.co/query"
            f"?function=TIME_SERIES_INTRADAY"
            f"&symbol={symbol}"
            f"&interval={interval}"
            f"&outputsize=compact"
            f"&apikey={ALPHA_VANTAGE_API_KEY}"
        )
        r = httpx.get(url, timeout=10)
        data = r.json()
        key = f"Time Series ({interval})"
        if key not in data:
            return None, None, None, None
        values = list(reversed(list(data[key].values())))[:80]
        return (
            [float(v["4. close"]) for v in values],
            [float(v["2. high"]) for v in values],
            [float(v["3. low"]) for v in values],
            [float(v["1. open"]) for v in values],
        )
    except Exception:
        return None, None, None, None

# ─────────────────────────────────────────
# COINGECKO
# ─────────────────────────────────────────

def fetch_coingecko_ohlc(coin_id):
    try:
        from config import COINGECKO_API_KEY
        url = (
            f"https://pro-api.coingecko.com/api/v3/coins"
            f"/{coin_id}/ohlc?vs_currency=usd&days=1"
        )
        headers = {"x-cg-pro-api-key": COINGECKO_API_KEY}
        r = httpx.get(url, headers=headers, timeout=10)
        data = r.json()
        if not isinstance(data, list) or len(data) < 5:
            return None, None, None, None
        return (
            [float(c[4]) for c in data],
            [float(c[2]) for c in data],
            [float(c[3]) for c in data],
            [float(c[1]) for c in data],
        )
    except Exception:
        return None, None, None, None

# ─────────────────────────────────────────
# TWELVE DATA
# ─────────────────────────────────────────

_twelve_last_call = 0
TWELVE_MIN_INTERVAL = 8


def fetch_twelve(symbol, interval="5min", bars=80):
    global _twelve_last_call
    try:
        now = time.time()
        if now - _twelve_last_call < TWELVE_MIN_INTERVAL:
            return None, None, None, None
        _twelve_last_call = now
        from config import TWELVE_API_KEY
        if not TWELVE_API_KEY:
            return None, None, None, None
        url = (
            f"https://api.twelvedata.com/time_series"
            f"?symbol={symbol}"
            f"&interval={interval}"
            f"&outputsize={bars}"
            f"&apikey={TWELVE_API_KEY}"
            f"&format=JSON"
        )
        r = httpx.get(url, timeout=10)
        data = r.json()
        if "values" not in data:
            return None, None, None, None
        values = list(reversed(data["values"]))
        return (
            [float(v["close"]) for v in values],
            [float(v["high"]) for v in values],
            [float(v["low"]) for v in values],
            [float(v["open"]) for v in values],
        )
    except Exception:
        return None, None, None, None

# ─────────────────────────────────────────
# FINNHUB NEWS
# ─────────────────────────────────────────

def get_news_sentiment(pair):
    try:
        from config import FINNHUB_API_KEY
        now = time.time()
        if pair in _news_cache:
            t, r = _news_cache[pair]
            if now - t < NEWS_CACHE_SECONDS:
                return r
        url = (
            f"https://finnhub.io/api/v1/news"
            f"?category=forex&token={FINNHUB_API_KEY}"
        )
        r = httpx.get(url, timeout=6)
        articles = r.json()
        if not isinstance(articles, list):
            return "Neutral", []
        base = (
            pair.replace(" OTC", "")
            .replace("/USD", "")
            .replace("/", "")
            .lower()
        )
        relevant = []
        for article in articles[:20]:
            h = article.get("headline", "").lower()
            s = article.get("summary", "").lower()
            if base in h or base in s:
                relevant.append(article.get("headline", ""))
        sentiment = (
            "Active" if len(relevant) >= 3 else
            "Moderate" if len(relevant) >= 1 else
            "Neutral"
        )
        result = (sentiment, relevant[:3])
        _news_cache[pair] = (now, result)
        return result
    except Exception:
        return "Neutral", []





# ─────────────────────────────────────────
# GEMINI AI
# ─────────────────────────────────────────


def get_gemini_analysis(
    pair, indicators, news_headlines, signal, timeframe
):
    try:
        from config import GEMINI_API_KEY
        if not GEMINI_API_KEY:
            return None
        news_text = (
            "\n".join(news_headlines)
            if news_headlines else "No recent news"
        )
        prompt = (
            f"You are a professional binary options trader "
            f"analysing {pair}.\n\n"
            f"Technical Indicators:\n"
            f"- RSI: {indicators['rsi']}\n"
            f"- MACD: {indicators['macd']}\n"
            f"- Bollinger: {indicators['bb']}\n"
            f"- Stochastic: {indicators['stoch']}\n"
            f"- Trend: {indicators['ema_trend']}\n"
            f"- Price: {indicators['price']}\n\n"
            f"News: {news_text}\n"
            f"Timeframe: {timeframe}\n"
            f"Initial Signal: {signal}\n\n"
            f"Reply in EXACTLY this format:\n"
            f"VERDICT: BUY/SELL/HOLD\n"
            f"CONFIDENCE: Very Low/Low/Medium/High/Very High\n"
            f"REASON 1: one sentence\n"
            f"REASON 2: one sentence\n"
            f"REASON 3: one sentence\n"
            f"RISK: Low/Medium/High\n"
            f"SUMMARY: one sentence"
        )
        url = (
            f"https://generativelanguage.googleapis.com/v1beta"
            f"/models/gemini-1.5-flash:generateContent"
            f"?key={GEMINI_API_KEY}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 300,
            }
        }
        r = httpx.post(url, json=payload, timeout=15)
        data = r.json()
        text = (
            data["candidates"][0]["content"]["parts"][0]["text"]
        )
        return parse_gemini_response(text)
    except Exception:
        return None




def parse_gemini_response(text):
    try:
        result = {}
        for line in text.strip().split("\n"):
            if "VERDICT:" in line:
                result["verdict"] = line.split(":", 1)[1].strip()
            elif "CONFIDENCE:" in line:
                result["confidence_text"] = (
                    line.split(":", 1)[1].strip()
                )
            elif "REASON 1:" in line:
                result["reason1"] = line.split(":", 1)[1].strip()
            elif "REASON 2:" in line:
                result["reason2"] = line.split(":", 1)[1].strip()
            elif "REASON 3:" in line:
                result["reason3"] = line.split(":", 1)[1].strip()
            elif "RISK:" in line:
                result["risk"] = line.split(":", 1)[1].strip()
            elif "SUMMARY:" in line:
                result["summary"] = line.split(":", 1)[1].strip()
        return result if result.get("verdict") else None
    except Exception:
        return None


# ─────────────────────────────────────────
# SYMBOL RESOLVER
# ─────────────────────────────────────────


GRANULARITY_MAP = {
    "1min": 60, "5min": 300,
    "15min": 900, "30min": 1800, "1h": 3600
}




def resolve_symbols(pair):
    from config import (
        BINANCE_SYMBOL_MAP, TWELVE_SYMBOL_MAP,
        COINGECKO_ID_MAP, DERIV_OTC_SYMBOL_MAP
    )
    is_otc = "OTC" in pair
    base = pair.replace(" OTC", "").strip()
    binance_sym = (
        BINANCE_SYMBOL_MAP.get(pair) or
        BINANCE_SYMBOL_MAP.get(base)
    )
    twelve_sym = (
        TWELVE_SYMBOL_MAP.get(pair) or
        TWELVE_SYMBOL_MAP.get(base)
    )
    coingecko_id = (
        COINGECKO_ID_MAP.get(pair) or
        COINGECKO_ID_MAP.get(base)
    )
    deriv_sym = (
        DERIV_OTC_SYMBOL_MAP.get(pair) if is_otc else None
    )
    return (
        binance_sym, twelve_sym,
        coingecko_id, deriv_sym, is_otc
    )




def get_kucoin_sym(b):
    return (
        f"{b[:-4]}-USDT"
        if b and b.endswith("USDT") else None
    )




def get_okx_sym(b):
    return (
        f"{b[:-4]}-USDT"
        if b and b.endswith("USDT") else None
    )


# ─────────────────────────────────────────
# INDICATORS
# ─────────────────────────────────────────


def ema(prices, period):
    if len(prices) < period:
        return prices[-1]
    k = 2 / (period + 1)
    e = sum(prices[:period]) / period
    for p in prices[period:]:
        e = p * k + e * (1 - k)
    return e




def rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(prices)):
        d = prices[i] - prices[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = sum(gains[-period:]) / period
    al = sum(losses[-period:]) / period
    if al == 0:
        return 100.0
    return round(100 - (100 / (1 + ag / al)), 2)




def macd(prices):
    if len(prices) < 26:
        return 0, 0, 0
    m = ema(prices, 12) - ema(prices, 26)
    s = ema(prices[-35:], 9) if len(prices) >= 35 else m
    return round(m, 6), round(s, 6), round(m - s, 6)




def bollinger(prices, period=20):
    if len(prices) < period:
        p = prices[-1]
        return p, p, p
    recent = prices[-period:]
    sma = sum(recent) / period
    std = (sum((p - sma) ** 2 for p in recent) / period) ** 0.5
    return (
        round(sma + 2 * std, 5),
        round(sma, 5),
        round(sma - 2 * std, 5)
    )




def stochastic(highs, lows, closes, period=14):
    if len(closes) < period:
        return 50.0, 50.0
    h = max(highs[-period:])
    l = min(lows[-period:])
    if h == l:
        return 50.0, 50.0
    k = round(100 * (closes[-1] - l) / (h - l), 2)
    d = round(
        sum([
            100 * (closes[-i] - min(lows[-period:])) /
            (
                max(highs[-period:]) -
                min(lows[-period:]) + 1e-10
            )
            for i in range(1, 4)
        ]) / 3, 2
    )
    return k, d




def pad_prices(closes, highs, lows, opens, target=30):
    while len(closes) < target:
        closes = [closes[0]] + closes
        highs = [highs[0]] + highs
        lows = [lows[0]] + lows
        opens = [opens[0]] + opens
    return closes, highs, lows, opens


# ─────────────────────────────────────────
# MAIN ANALYSE FUNCTION
# ─────────────────────────────────────────


def analyse(pair, tf_data):
    if isinstance(tf_data, dict):
        binance_interval = tf_data.get("binance", "5m")
        twelve_interval = tf_data.get("twelve", "5min")
    else:
        binance_interval = "5m"
        twelve_interval = "5min"


    cache_key = f"{pair}_{twelve_interval}"
    now = time.time()
    if cache_key in _cache:
        t, r = _cache[cache_key]
        if now - t < CACHE_SECONDS:
            return r


    (
        binance_sym, twelve_sym, coingecko_id,
        deriv_sym, is_otc
    ) = resolve_symbols(pair)


    closes = highs = lows = opens = None


    # 1. Deriv for OTC
    if is_otc and deriv_sym:
        try:
            gran = GRANULARITY_MAP.get(twelve_interval, 300)
            closes, highs, lows, opens = fetch_deriv_otc(
                deriv_sym, gran
            )
        except Exception:
            pass


    # 2. Yahoo Finance (forex, stocks, commodities)
    if not closes:
        closes, highs, lows, opens = fetch_yahoo(
            pair, binance_interval
        )


    # 3. Binance for crypto
    if not closes and binance_sym and not coingecko_id:
        closes, highs, lows, opens = fetch_binance(
            binance_sym, binance_interval
        )


    # 4. KuCoin
    if not closes and binance_sym:
        ks = get_kucoin_sym(binance_sym)
        if ks:
            closes, highs, lows, opens = fetch_kucoin(
                ks, binance_interval
            )


    # 5. OKX
    if not closes and binance_sym:
        os_ = get_okx_sym(binance_sym)
        if os_:
            closes, highs, lows, opens = fetch_okx(
                os_, binance_interval
            )


    # 6. Kraken
    if not closes and binance_sym:
        ks = KRAKEN_MAP.get(binance_sym)
        if ks:
            closes, highs, lows, opens = fetch_kraken(
                ks, binance_interval
            )


    # 7. Metals Live (Gold/Silver)
    if not closes:
        closes, highs, lows, opens = fetch_metals_live(pair)


    # 8. Alpha Vantage Forex
    if not closes and "/" in pair:
        closes, highs, lows, opens = fetch_alpha_vantage_forex(
            pair, twelve_interval
        )


    # 9. Alpha Vantage Stock
    if not closes and twelve_sym and "/" not in pair:
        closes, highs, lows, opens = fetch_alpha_vantage_stock(
            twelve_sym, twelve_interval
        )


    # 10. CoinGecko for standalone coins
    if not closes and coingecko_id:
        closes, highs, lows, opens = fetch_coingecko_ohlc(
            coingecko_id
        )


    # 11. Twelve Data last resort
    if not closes and twelve_sym:
        closes, highs, lows, opens = fetch_twelve(
            twelve_sym, twelve_interval
        )


    if not closes or len(closes) < 5:
        return None


    if len(closes) < 30:
        closes, highs, lows, opens = pad_prices(
            closes, highs, lows, opens
        )


    price = closes[-1]
    rsi_v = rsi(closes)
    m, s, h = macd(closes)
    upper, mid, lower = bollinger(closes)
    k, d = stochastic(highs, lows, closes)
    ema50 = ema(closes, min(50, len(closes)))
    ema200 = ema(closes, min(200, len(closes)))
    m2, s2, _ = (
        macd(closes[:-1]) if len(closes) > 1
        else (0, 0, 0)
    )


    bull, bear = 0, 0
    reasons_bull, reasons_bear = [], []


    if rsi_v < 25:
        bull += 1.5
        reasons_bull.append(f"RSI {rsi_v} — strongly oversold")
    elif rsi_v < 35:
        bull += 1
        reasons_bull.append(
            f"RSI {rsi_v} — oversold, buyers entering"
        )
    elif rsi_v > 75:
        bear += 1.5
        reasons_bear.append(f"RSI {rsi_v} — strongly overbought")
    elif rsi_v > 65:
        bear += 1
        reasons_bear.append(
            f"RSI {rsi_v} — overbought, sellers likely"
        )
    elif rsi_v < 45:
        bull += 0.3
    elif rsi_v > 55:
        bear += 0.3


    if m > s and m2 <= s2:
        bull += 1.5
        reasons_bull.append(
            "MACD bullish crossover — strong momentum up"
        )
    elif m < s and m2 >= s2:
        bear += 1.5
        reasons_bear.append(
            "MACD bearish crossover — strong momentum down"
        )
    elif m > s:
        bull += 0.5
        reasons_bull.append("MACD above signal — upward momentum")
    else:
        bear += 0.5
        reasons_bear.append("MACD below signal — downward momentum")


    if price <= lower:
        bull += 1.5
        reasons_bull.append(
            "Price at lower Bollinger band — bounce expected"
        )
    elif price >= upper:
        bear += 1.5
        reasons_bear.append(
            "Price at upper Bollinger band — reversal likely"
        )
    elif price > mid:
        bull += 0.3
    else:
        bear += 0.3


    if k < 20 and k > d:
        bull += 1
        reasons_bull.append(f"Stoch K:{k} — oversold bullish crossover")
    elif k > 80 and k < d:
        bear += 1
        reasons_bear.append(
            f"Stoch K:{k} — overbought bearish crossover"
        )
    elif k < 30:
        bull += 0.5
    elif k > 70:
        bear += 0.5


    if ema50 > ema200:
        bull += 1
        reasons_bull.append("EMA50 above EMA200 — uptrend confirmed")
    else:
        bear += 1
        reasons_bear.append("EMA50 below EMA200 — downtrend confirmed")


    if len(closes) >= 3:
        if closes[-1] > closes[-2] > closes[-3]:
            bull += 0.5
            reasons_bull.append("3 consecutive bullish candles")
        elif closes[-1] < closes[-2] < closes[-3]:
            bear += 0.5
            reasons_bear.append("3 consecutive bearish candles")


    total = bull + bear if (bull + bear) > 0 else 1


    if bull >= 3 and bull > bear:
        signal = "BUY"
        confidence = min(int((bull / total) * 5) + 1, 5)
        reasons = reasons_bull[:3]
    elif bear >= 3 and bear > bull:
        signal = "SELL"
        confidence = min(int((bear / total) * 5) + 1, 5)
        reasons = reasons_bear[:3]
    else:
        signal = "HOLD"
        confidence = 2
        reasons = [
            "Market ranging — no clear direction",
            "Wait for stronger confirmation",
            "Check again next candle"
        ]


    conf_bar = "█" * confidence + "░" * (5 - confidence)
    conf_text = [
        "Very Low", "Low", "Medium", "High", "Very High"
    ][confidence - 1]
    bb_pos = (
        "At Lower Band" if price <= lower else
        "At Upper Band" if price >= upper else
        "Above Middle" if price > mid else
        "Below Middle"
    )


    indicators = {
        "rsi": rsi_v,
        "macd": "Bullish" if m > s else "Bearish",
        "bb": bb_pos,
        "stoch": f"K:{k} D:{d}",
        "ema_trend": "Uptrend" if ema50 > ema200 else "Downtrend",
        "price": round(price, 5)
    }


    news_sentiment, news_headlines = get_news_sentiment(pair)
    ai_analysis = get_gemini_analysis(
        pair, indicators, news_headlines,
        signal, twelve_interval
    )


    final_signal = signal
    final_conf_text = conf_text
    ai_reasons = reasons


    if ai_analysis:
        v = ai_analysis.get("verdict", "").upper()
        if v in ["BUY", "SELL", "HOLD"]:
            final_signal = v
        if ai_analysis.get("confidence_text"):
            final_conf_text = ai_analysis["confidence_text"]
        ai_reasons = [
            ai_analysis.get("reason1", ""),
            ai_analysis.get("reason2", ""),
            ai_analysis.get("reason3", ""),
        ]
        ai_reasons = [r for r in ai_reasons if r]


    result = {
        "signal": final_signal,
        "confidence": confidence,
        "conf_bar": conf_bar,
        "conf_text": final_conf_text,
        "price": round(price, 5),
        "reasons": ai_reasons or reasons,
        "news_sentiment": news_sentiment,
        "news_headlines": news_headlines,
        "ai_summary": (
            ai_analysis.get("summary", "")
            if ai_analysis else ""
        ),
        "ai_risk": (
            ai_analysis.get("risk", "Medium")
            if ai_analysis else "Medium"
        ),
        "indicators": {
            "rsi": rsi_v,
            "macd": "Bullish" if m > s else "Bearish",
            "bb": bb_pos,
            "stoch": f"K:{k} D:{d}",
            "ema_trend": (
                "Uptrend" if ema50 > ema200 else "Downtrend"
            ),
        }
    }


    _cache[cache_key] = (now, result)
    return result
