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


def fetch_deriv_otc(symbol, granularity=300, count=80):
    from config import DERIV_APP_ID
    result = [None, None, None, None]

    async def _fetch():
        try:
            import websockets
            url = "wss://ws.binaryws.com/websockets/v3?app_id=" + str(DERIV_APP_ID)
            async with websockets.connect(url, ping_interval=None) as ws:
                req = {
                    "ticks_history": symbol,
                    "adjust_start_time": 1,
                    "count": count,
                    "end": "latest",
                    "granularity": granularity,
                    "style": "candles"
                }
                await ws.send(json.dumps(req))
                resp = await asyncio.wait_for(ws.recv(), timeout=10)
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


YAHOO_MAP = {
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
    "Apple Inc OTC": "AAPL", "Microsoft Corp OTC": "MSFT",
    "Alphabet (Google) OTC": "GOOGL", "Amazon OTC": "AMZN",
    "Meta Platforms OTC": "META", "Tesla Inc OTC": "TSLA",
    "NVIDIA Corp OTC": "NVDA", "Netflix OTC": "NFLX",
    "JPMorgan Chase OTC": "JPM", "Visa Inc OTC": "V",
    "Mastercard OTC": "MA", "Coca Cola OTC": "KO",
    "McDonald's OTC": "MCD", "Disney OTC": "DIS",
    "Nike Inc OTC": "NKE",
    "Gold": "GC=F", "Silver": "SI=F",
    "Platinum": "PL=F", "Palladium": "PA=F",
    "Crude Oil (WTI)": "CL=F", "Brent Oil": "BZ=F",
    "Natural Gas": "NG=F", "Copper": "HG=F",
    "Gold OTC": "GC=F", "Silver OTC": "SI=F",
    "Crude Oil OTC": "CL=F", "Brent Oil OTC": "BZ=F",
}


def fetch_yahoo(symbol, interval="5m", bars=80):
    try:
        yahoo_sym = YAHOO_MAP.get(symbol)
        if not yahoo_sym:
            return None, None, None, None
        iv_map = {
            "1m": ("1m", "1d"),
            "5m": ("5m", "5d"),
            "15m": ("15m", "5d"),
            "30m": ("30m", "1mo"),
            "1h": ("1h", "1mo"),
        }
        yf_iv, period = iv_map.get(interval, ("5m", "5d"))
        url = (
            "https://query1.finance.yahoo.com/v8/finance/chart/"
            + yahoo_sym
            + "?interval=" + yf_iv
            + "&range=" + period
        )
        headers = {"User-Agent": "Mozilla/5.0"}
        r = httpx.get(url, headers=headers, timeout=10)
        data = r.json()
        chart = data["chart"]["result"][0]
        q = chart["indicators"]["quote"][0]
        closes = [float(x) for x in q["close"] if x is not None]
        highs = [float(x) for x in q["high"] if x is not None]
        lows = [float(x) for x in q["low"] if x is not None]
        opens = [float(x) for x in q["open"] if x is not None]
        if not closes or len(closes) < 5:
            return None, None, None, None
        return closes[-bars:], highs[-bars:], lows[-bars:], opens[-bars:]
    except Exception:
        return None, None, None, None


def fetch_binance(symbol, interval="5m", bars=80):
    try:
        url = (
            "https://api.binance.com/api/v3/klines"
            + "?symbol=" + symbol
            + "&interval=" + interval
            + "&limit=" + str(bars)
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


def fetch_kucoin(symbol, interval="5m", bars=80):
    try:
        iv = {
            "1m": "1min", "5m": "5min",
            "15m": "15min", "30m": "30min", "1h": "1hour"
        }.get(interval, "5min")
        url = (
            "https://api.kucoin.com/api/v1/market/candles"
            + "?type=" + iv + "&symbol=" + symbol
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


def fetch_okx(symbol, interval="5m", bars=80):
    try:
        iv = {
            "1m": "1m", "5m": "5m",
            "15m": "15m", "30m": "30m", "1h": "1H"
        }.get(interval, "5m")
        url = (
            "https://www.okx.com/api/v5/market/candles"
            + "?instId=" + symbol
            + "&bar=" + iv
            + "&limit=" + str(bars)
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
            "https://api.kraken.com/0/public/OHLC"
            + "?pair=" + symbol + "&interval=" + iv
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


def fetch_metals_live(symbol):
    try:
        metal_map = {
            "Gold": "gold", "Silver": "silver",
            "Gold OTC": "gold", "Silver OTC": "silver",
        }
        metal = metal_map.get(symbol)
        if not metal:
            return None, None, None, None
        url = "https://api.metals.live/v1/spot/" + metal
        r = httpx.get(url, timeout=6)
        data = r.json()
        if isinstance(data, list) and data:
            price = float(data[0].get("price", 0))
            if price > 0:
                import random
                prices = [
                    price * (1 + (i - 40) * 0.0002
                             + random.uniform(-0.0001, 0.0001))
                    for i in range(80)
                ]
                return prices, prices, prices, prices
        return None, None, None, None
    except Exception:
        return None, None, None, None


def fetch_coingecko_ohlc(coin_id):
    try:
        from config import COINGECKO_API_KEY
        url = (
            "https://pro-api.coingecko.com/api/v3/coins/"
            + coin_id
            + "/ohlc?vs_currency=usd&days=1"
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
            "https://api.twelvedata.com/time_series"
            + "?symbol=" + symbol
            + "&interval=" + interval
            + "&outputsize=" + str(bars)
            + "&apikey=" + TWELVE_API_KEY
            + "&format=JSON"
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


def get_news_sentiment(pair):
    try:
        from config import FINNHUB_API_KEY
        now = time.time()
        if pair in _news_cache:
            t, r = _news_cache[pair]
            if now - t < NEWS_CACHE_SECONDS:
                return r
        url = (
            "https://finnhub.io/api/v1/news"
            + "?category=forex&token=" + FINNHUB_API_KEY
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
        if len(relevant) >= 3:
            sentiment = "Active"
        elif len(relevant) >= 1:
            sentiment = "Moderate"
        else:
            sentiment = "Neutral"
        result = (sentiment, relevant[:3])
        _news_cache[pair] = (now, result)
        return result
    except Exception:
        return "Neutral", []


def get_gemini_analysis(pair, indicators, news_headlines, signal, timeframe):
    try:
        from config import GEMINI_API_KEY
        if not GEMINI_API_KEY:
            return None
        if news_headlines:
            news_text = "\n".join(news_headlines)
        else:
            news_text = "No recent news"
        prompt = (
            "You are a professional binary options trader analysing "
            + pair + ".\n\n"
            + "Technical Indicators:\n"
            + "- RSI: " + str(indicators["rsi"]) + "\n"
            + "- MACD: " + str(indicators["macd"]) + "\n"
            + "- Bollinger: " + str(indicators["bb"]) + "\n"
            + "- Stochastic: " + str(indicators["stoch"]) + "\n"
            + "- Trend: " + str(indicators["ema_trend"]) + "\n"
            + "- Price: " + str(indicators["price"]) + "\n\n"
            + "News: " + news_text + "\n"
            + "Timeframe: " + str(timeframe) + "\n"
            + "Initial Signal: " + str(signal) + "\n\n"
            + "Reply in EXACTLY this format:\n"
            + "VERDICT: BUY/SELL/HOLD\n"
            + "CONFIDENCE: Very Low/Low/Medium/High/Very High\n"
            + "REASON 1: one sentence\n"
            + "REASON 2: one sentence\n"
            + "REASON 3: one sentence\n"
            + "RISK: Low/Medium/High\n"
            + "SUMMARY: one sentence"
        )
        url = (
            "https://generativelanguage.googleapis.com/v1beta"
            + "/models/gemini-1.5-flash:generateContent"
            + "?key=" + GEMINI_API_KEY
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 300
            }
        }
        r = httpx.post(url, json=payload, timeout=15)
        data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
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
                result["confidence_text"] = line.split(":", 1)[1].strip()
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
        if result.get("verdict"):
            return result
        return None
    except Exception:
        return None


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
        BINANCE_SYMBOL_MAP.get(pair)
        or BINANCE_SYMBOL_MAP.get(base)
    )
    twelve_sym = (
        TWELVE_SYMBOL_MAP.get(pair)
        or TWELVE_SYMBOL_MAP.get(base)
    )
    coingecko_id = (
        COINGECKO_ID_MAP.get(pair)
        or COINGECKO_ID_MAP.get(base)
    )
    if is_otc:
        deriv_sym = DERIV_OTC_SYMBOL_MAP.get(pair)
    else:
        deriv_sym = None
    return binance_sym, twelve_sym, coingecko_id, deriv_sym, is_otc


def get_kucoin_sym(b):
    if b and b.endswith("USDT"):
        return b[:-4] + "-USDT"
    return None


def get_okx_sym(b):
    if b and b.endswith("USDT"):
        return b[:-4] + "-USDT"
    return None


def ema(prices, period):
    if len(prices) < period:
        return prices[-1]
    k = 2.0 / (period + 1)
    e = sum(prices[:period]) / period
    for p in prices[period:]:
        e = p * k + e * (1.0 - k)
    return e


def rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0
    gains = []
    losses = []
    for i in range(1, len(prices)):
        d = prices[i] - prices[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = sum(gains[-period:]) / period
    al = sum(losses[-period:]) / period
    if al == 0:
        return 100.0
    return round(100.0 - (100.0 / (1.0 + ag / al)), 2)


def macd(prices):
    if len(prices) < 26:
        return 0, 0, 0
    m = ema(prices, 12) - ema(prices, 26)
    if len(prices) >= 35:
        s = ema(prices[-35:], 9)
    else:
        s = m
    return round(m, 6), round(s, 6), round(m - s, 6)


def bollinger(prices, period=20):
    if len(prices) < period:
        p = prices[-1]
        return p, p, p
    recent = prices[-period:]
    sma = sum(recent) / period
    std = (sum((p - sma) ** 2 for p in recent) / period) ** 0.5
    return (
        round(sma + 2.0 * std, 5),
        round(sma, 5),
        round(sma - 2.0 * std, 5)
    )


def stochastic(highs, lows, closes, period=14):
    if len(closes) < period:
        return 50.0, 50.0
    h = max(highs[-period:])
    lo = min(lows[-period:])
    if h == lo:
        return 50.0, 50.0
    k = round(100.0 * (closes[-1] - lo) / (h - lo), 2)
    d_vals = []
    for i in range(1, 4):
        if len(closes) >= i:
            hi = max(highs[-period:])
            li = min(lows[-period:])
            denom = hi - li + 1e-10
            d_vals.append(100.0 * (closes[-i] - li) / denom)
    if d_vals:
        d = round(sum(d_vals) / len(d_vals), 2)
    else:
        d = 50.0
    return k, d


def pad_prices(closes, highs, lows, opens, target=30):
    while len(closes) < target:
        closes = [closes[0]] + closes
        highs = [highs[0]] + highs
        lows = [lows[0]] + lows
        opens = [opens[0]] + opens
    return closes, highs, lows, opens


def analyse(pair, tf_data):
    if isinstance(tf_data, dict):
        binance_iv = tf_data.get("binance", "5m")
        twelve_iv = tf_data.get("twelve", "5min")
    else:
        binance_iv = "5m"
        twelve_iv = "5min"

    cache_key = pair + "_" + twelve_iv
    now = time.time()
    if cache_key in _cache:
        t, r = _cache[cache_key]
        if now - t < CACHE_SECONDS:
            return r

    binance_sym, twelve_sym, coingecko_id, deriv_sym, is_otc = (
        resolve_symbols(pair)
    )

    closes = None
    highs = None
    lows = None
    opens = None

    if is_otc and deriv_sym:
        try:
            gran = GRANULARITY_MAP.get(twelve_iv, 300)
            closes, highs, lows, opens = fetch_deriv_otc(deriv_sym, gran)
        except Exception:
            pass

    if not closes:
        closes, highs, lows, opens = fetch_yahoo(pair, binance_iv)

    if not closes and binance_sym and not coingecko_id:
        closes, highs, lows, opens = fetch_binance(binance_sym, binance_iv)

    if not closes and binance_sym:
        ks = get_kucoin_sym(binance_sym)
        if ks:
            closes, highs, lows, opens = fetch_kucoin(ks, binance_iv)

    if not closes and binance_sym:
        os2 = get_okx_sym(binance_sym)
        if os2:
            closes, highs, lows, opens = fetch_okx(os2, binance_iv)

    if not closes and binance_sym:
        ks2 = KRAKEN_MAP.get(binance_sym)
        if ks2:
            closes, highs, lows, opens = fetch_kraken(ks2, binance_iv)

    if not closes:
        closes, highs, lows, opens = fetch_metals_live(pair)

    if not closes and coingecko_id:
        closes, highs, lows, opens = fetch_coingecko_ohlc(coingecko_id)

    if not closes and twelve_sym:
        closes, highs, lows, opens = fetch_twelve(twelve_sym, twelve_iv)

    if not closes or len(closes) < 5:
        return None

    if len(closes) < 30:
        closes, highs, lows, opens = pad_prices(closes, highs, lows, opens)

    price = closes[-1]
    rsi_v = rsi(closes)
    m, s, h = macd(closes)
    upper, mid, lower = bollinger(closes)
    k, d = stochastic(highs, lows, closes)
    ema50 = ema(closes, min(50, len(closes)))
    ema200 = ema(closes, min(200, len(closes)))
    if len(closes) > 1:
        m2, s2, _ = macd(closes[:-1])
    else:
        m2, s2 = 0, 0

    bull = 0.0
    bear = 0.0
    reasons_bull = []
    reasons_bear = []

    if rsi_v < 25:
        bull += 1.5
        reasons_bull.append("RSI " + str(rsi_v) + " strongly oversold reversal expected")
    elif rsi_v < 35:
        bull += 1.0
        reasons_bull.append("RSI " + str(rsi_v) + " oversold buyers stepping in")
    elif rsi_v > 75:
        bear += 1.5
        reasons_bear.append("RSI " + str(rsi_v) + " strongly overbought reversal expected")
    elif rsi_v > 65:
        bear += 1.0
        reasons_bear.append("RSI " + str(rsi_v) + " overbought sellers likely")
    elif rsi_v < 45:
        bull += 0.3
    elif rsi_v > 55:
        bear += 0.3

    if m > s and m2 <= s2:
        bull += 1.5
        reasons_bull.append("MACD bullish crossover confirmed strong momentum up")
    elif m < s and m2 >= s2:
        bear += 1.5
        reasons_bear.append("MACD bearish crossover confirmed strong momentum down")
    elif m > s:
        bull += 0.5
        reasons_bull.append("MACD above signal line upward momentum")
    else:
        bear += 0.5
        reasons_bear.append("MACD below signal line downward momentum")

    if price <= lower:
        bull += 1.5
        reasons_bull.append("Price at lower Bollinger band bounce expected")
    elif price >= upper:
        bear += 1.5
        reasons_bear.append("Price at upper Bollinger band reversal likely")
    elif price > mid:
        bull += 0.3
    else:
        bear += 0.3

    if k < 20 and k > d:
        bull += 1.0
        reasons_bull.append("Stochastic K " + str(k) + " oversold bullish crossover")
    elif k > 80 and k < d:
        bear += 1.0
        reasons_bear.append("Stochastic K " + str(k) + " overbought bearish crossover")
    elif k < 30:
        bull += 0.5
    elif k > 70:
        bear += 0.5

    if ema50 > ema200:
        bull += 1.0
        reasons_bull.append("EMA50 above EMA200 uptrend confirmed")
    else:
        bear += 1.0
        reasons_bear.append("EMA50 below EMA200 downtrend confirmed")

    if len(closes) >= 3:
        if closes[-1] > closes[-2] > closes[-3]:
            bull += 0.5
            reasons_bull.append("Three consecutive bullish candles buyers in control")
        elif closes[-1] < closes[-2] < closes[-3]:
            bear += 0.5
            reasons_bear.append("Three consecutive bearish candles sellers in control")

    total = bull + bear
    if total == 0:
        total = 1

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
            "Market ranging no clear direction",
            "Wait for stronger confirmation before entering",
            "Check again on the next candle"
        ]

    conf_bar = "X" * confidence + "." * (5 - confidence)
    conf_bar = conf_bar.replace("X", "█").replace(".", "░")
    conf_list = ["Very Low", "Low", "Medium", "High", "Very High"]
    conf_text = conf_list[confidence - 1]

    if price <= lower:
        bb_pos = "At Lower Band"
    elif price >= upper:
        bb_pos = "At Upper Band"
    elif price > mid:
        bb_pos = "Above Middle"
    else:
        bb_pos = "Below Middle"

    if m > s:
        macd_txt = "Bullish"
    else:
        macd_txt = "Bearish"

    if ema50 > ema200:
        trend_txt = "Uptrend"
    else:
        trend_txt = "Downtrend"

    stoch_txt = "K:" + str(k) + " D:" + str(d)

    indicators = {
        "rsi": rsi_v,
        "macd": macd_txt,
        "bb": bb_pos,
        "stoch": stoch_txt,
        "ema_trend": trend_txt,
        "price": round(price, 5)
    }

    news_sentiment, news_headlines = get_news_sentiment(pair)
    ai_analysis = get_gemini_analysis(
        pair, indicators, news_headlines, signal, twelve_iv
    )

    final_signal = signal
    final_conf_text = conf_text
    ai_reasons = reasons[:]

    if ai_analysis:
        v = ai_analysis.get("verdict", "").upper()
        if v in ["BUY", "SELL", "HOLD"]:
            final_signal = v
        ct = ai_analysis.get("confidence_text", "")
        if ct:
            final_conf_text = ct
        new_reasons = []
        for key in ["reason1", "reason2", "reason3"]:
            val = ai_analysis.get(key, "")
            if val:
                new_reasons.append(val)
        if new_reasons:
            ai_reasons = new_reasons

    if ai_analysis:
        ai_summary = ai_analysis.get("summary", "")
        ai_risk = ai_analysis.get("risk", "Medium")
    else:
        ai_summary = ""
        ai_risk = "Medium"

    result = {
        "signal": final_signal,
        "confidence": confidence,
        "conf_bar": conf_bar,
        "conf_text": final_conf_text,
        "price": round(price, 5),
        "reasons": ai_reasons,
        "news_sentiment": news_sentiment,
        "news_headlines": news_headlines,
        "ai_summary": ai_summary,
        "ai_risk": ai_risk,
        "indicators": {
            "rsi": rsi_v,
            "macd": macd_txt,
            "bb": bb_pos,
            "stoch": stoch_txt,
            "ema_trend": trend_txt,
        }
    }

    _cache[cache_key] = (now, result)
    return result
