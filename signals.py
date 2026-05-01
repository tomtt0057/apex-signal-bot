import httpx
import time
import json
import asyncio
import threading
import re

_cache = {}
CACHE_SECONDS = 45
_news_cache = {}
NEWS_CACHE_SECONDS = 300

# ─────────────────────────────────────────
# DERIV WEBSOCKET (OTC pairs)
# ─────────────────────────────────────────

def fetch_deriv_otc(symbol, granularity=300, count=80):
    from config import DERIV_APP_ID
    result = [None, None, None, None]

    async def _fetch():
        try:
            import websockets
            url = f"wss://ws.binaryws.com/websockets/v3?app_id={DERIV_APP_ID}"
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
                if "candles" in data and len(data["candles"]) > 0:
                    candles = data["candles"]
                    result[0] = [float(c["close"]) for c in candles]
                    result[1] = [float(c["high"])  for c in candles]
                    result[2] = [float(c["low"])   for c in candles]
                    result[3] = [float(c["open"])  for c in candles]
        except:
            pass

    def run():
        asyncio.run(_fetch())

    t = threading.Thread(target=run)
    t.start()
    t.join(timeout=15)
    return tuple(result)

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

        clean = pair.replace(" OTC", "").replace("/", "").strip()
        url = (
            f"https://finnhub.io/api/v1/news"
            f"?category=forex&token={FINNHUB_API_KEY}"
        )
        r = httpx.get(url, timeout=6)
        articles = r.json()

        if not isinstance(articles, list):
            return "Neutral", []

        relevant = []
        keywords = clean.lower().split()
        base = pair.replace(" OTC","").replace("/USD","").replace("/","").lower()

        for article in articles[:20]:
            headline = article.get("headline","").lower()
            summary  = article.get("summary","").lower()
            if any(kw in headline or kw in summary for kw in [base, clean.lower()]):
                relevant.append(article.get("headline",""))

        if not relevant:
            sentiment = "Neutral"
        elif len(relevant) >= 3:
            sentiment = "Active"
        else:
            sentiment = "Moderate"

        _news_cache[pair] = (now, (sentiment, relevant[:3]))
        return sentiment, relevant[:3]
    except:
        return "Neutral", []

# ─────────────────────────────────────────
# GEMINI AI ANALYSIS
# ─────────────────────────────────────────

def get_gemini_analysis(pair, indicators, news_headlines, signal, timeframe):
    try:
        from config import GEMINI_API_KEY
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models"
            f"/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        )
        news_text = "\n".join(news_headlines) if news_headlines else "No recent news"

        prompt = f"""You are a professional binary options trader analysing {pair}.

Technical Indicators:
- RSI: {indicators['rsi']}
- MACD: {indicators['macd']}
- Bollinger Bands: {indicators['bb']}
- Stochastic: {indicators['stoch']}
- EMA Trend: {indicators['ema_trend']}
- Current Price: {indicators['price']}

Recent News Headlines:
{news_text}

Timeframe: {timeframe}
Initial Signal: {signal}

Provide a brief professional trading analysis in exactly this format:
VERDICT: [BUY/SELL/HOLD]
CONFIDENCE: [Very Low/Low/Medium/High/Very High]
REASON 1: [one sentence]
REASON 2: [one sentence]
REASON 3: [one sentence]
RISK: [Low/Medium/High]
SUMMARY: [one sentence overall verdict]"""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 300,
            }
        }
        r = httpx.post(url, json=payload, timeout=15)
        data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return parse_gemini_response(text)
    except:
        return None

def parse_gemini_response(text):
    try:
        lines = text.strip().split("\n")
        result = {}
        for line in lines:
            if "VERDICT:" in line:
                result["verdict"] = line.split(":",1)[1].strip()
            elif "CONFIDENCE:" in line:
                result["confidence_text"] = line.split(":",1)[1].strip()
            elif "REASON 1:" in line:
                result["reason1"] = line.split(":",1)[1].strip()
            elif "REASON 2:" in line:
                result["reason2"] = line.split(":",1)[1].strip()
            elif "REASON 3:" in line:
                result["reason3"] = line.split(":",1)[1].strip()
            elif "RISK:" in line:
                result["risk"] = line.split(":",1)[1].strip()
            elif "SUMMARY:" in line:
                result["summary"] = line.split(":",1)[1].strip()
        return result if result.get("verdict") else None
    except:
        return None

# ─────────────────────────────────────────
# DATA FETCHERS
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
    except:
        return None, None, None, None

def fetch_kucoin(symbol, interval="5min", bars=80):
    try:
        iv_map = {"1m":"1min","5m":"5min","15m":"15min","30m":"30min","1h":"1hour"}
        url = (
            f"https://api.kucoin.com/api/v1/market/candles"
            f"?type={iv_map.get(interval,'5min')}&symbol={symbol}"
        )
        r = httpx.get(url, timeout=8)
        data = r.json()
        if data.get("code") != "200000":
            return None, None, None, None
        candles = list(reversed(data.get("data", [])))[-bars:]
        if not candles:
            return None, None, None, None
        return (
            [float(c[2]) for c in candles],
            [float(c[3]) for c in candles],
            [float(c[4]) for c in candles],
            [float(c[1]) for c in candles],
        )
    except:
        return None, None, None, None

def fetch_okx(symbol, interval="5m", bars=80):
    try:
        iv_map = {"1m":"1m","5m":"5m","15m":"15m","30m":"30m","1h":"1H"}
        url = (
            f"https://www.okx.com/api/v5/market/candles"
            f"?instId={symbol}&bar={iv_map.get(interval,'5m')}&limit={bars}"
        )
        r = httpx.get(url, timeout=8)
        data = r.json()
        if data.get("code") != "0":
            return None, None, None, None
        candles = list(reversed(data.get("data", [])))
        if not candles:
            return None, None, None, None
        return (
            [float(c[4]) for c in candles],
            [float(c[2]) for c in candles],
            [float(c[3]) for c in candles],
            [float(c[1]) for c in candles],
        )
    except:
        return None, None, None, None

def fetch_kraken(symbol, interval="5"):
    try:
        iv_map = {"1m":"1","5m":"5","15m":"15","30m":"30","1h":"60"}
        url = (
            f"https://api.kraken.com/0/public/OHLC"
            f"?pair={symbol}&interval={iv_map.get(interval,'5')}"
        )
        r = httpx.get(url, timeout=8)
        data = r.json()
        if data.get("error"):
            return None, None, None, None
        result = data.get("result", {})
        key = [k for k in result.keys() if k != "last"]
        if not key:
            return None, None, None, None
        candles = result[key[0]]
        return (
            [float(c[4]) for c in candles],
            [float(c[2]) for c in candles],
            [float(c[3]) for c in candles],
            [float(c[1]) for c in candles],
        )
    except:
        return None, None, None, None

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
    except:
        return None, None, None, None

def fetch_coingecko_chart(coin_id):
    try:
        from config import COINGECKO_API_KEY
        url = (
            f"https://pro-api.coingecko.com/api/v3/coins"
            f"/{coin_id}/market_chart"
            f"?vs_currency=usd&days=1&interval=hourly"
        )
        headers = {"x-cg-pro-api-key": COINGECKO_API_KEY}
        r = httpx.get(url, headers=headers, timeout=10)
        data = r.json()
        if "prices" not in data or len(data["prices"]) < 5:
            return None, None, None, None
        prices = [float(p[1]) for p in data["prices"]]
        return prices, prices, prices, prices
    except:
        return None, None, None, None

def fetch_twelve(symbol, interval="5min", bars=80):
    try:
        from config import TWELVE_API_KEY
        url = (
            f"https://api.twelvedata.com/time_series"
            f"?symbol={symbol}&interval={interval}"
            f"&outputsize={bars}&apikey={TWELVE_API_KEY}&format=JSON"
        )
        r = httpx.get(url, timeout=10)
        data = r.json()
        if "values" not in data:
            return None, None, None, None
        values = list(reversed(data["values"]))
        return (
            [float(v["close"]) for v in values],
            [float(v["high"])  for v in values],
            [float(v["low"])   for v in values],
            [float(v["open"])  for v in values],
        )
    except:
        return None, None, None, None

# ─────────────────────────────────────────
# MARKET SESSION AWARENESS
# ─────────────────────────────────────────

from datetime import datetime, timezone

def get_current_session():
    """Returns current active trading session"""
    now = datetime.now(timezone.utc)
    hour = now.hour

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
    """Returns True if market conditions are good for trading"""
    session, _ = get_current_session()
    good_sessions = [
        "London", "New York",
        "London/NY Overlap", "Tokyo/London Overlap"
    ]
    return session in good_sessions

# ─────────────────────────────────────────
# ALPHA VANTAGE (for commodities)
# ─────────────────────────────────────────

def fetch_alpha_vantage(symbol, interval="5min"):
    """Fetch commodity data from Alpha Vantage"""
    try:
        from config import ALPHA_VANTAGE_API_KEY
        if not ALPHA_VANTAGE_API_KEY:
            return None, None, None, None

        av_map = {
            "Silver":          "SILVER",
            "Crude Oil (WTI)": "WTI",
            "Brent Oil":       "BRENT",
            "Natural Gas":     "NATURAL_GAS",
            "Copper":          "COPPER",
            "Gold":            "GOLD",
            "Silver OTC":      "SILVER",
            "Crude Oil OTC":   "WTI",
            "Brent Oil OTC":   "BRENT",
        }

        av_symbol = av_map.get(symbol)
        if not av_symbol:
            return None, None, None, None

        url = (
            f"https://www.alphavantage.co/query"
            f"?function=COMMODITY_MONTHLY"
            f"&symbol={av_symbol}"
            f"&apikey={ALPHA_VANTAGE_API_KEY}"
        )
        r = httpx.get(url, timeout=10)
        data = r.json()

        key = None
        for k in data.keys():
            if "data" in k.lower() or "series" in k.lower():
                key = k
                break

        if not key and "data" in data:
            key = "data"

        if key:
            raw = data[key]
            if isinstance(raw, list):
                prices = [
                    float(d.get("value", 0))
                    for d in raw[:80]
                    if d.get("value") not in [None, ".", ""]
                ]
            elif isinstance(raw, dict):
                prices = [
                    float(v.get("4. close", v.get("value", 0)))
                    for v in list(raw.values())[:80]
                ]
            else:
                return None, None, None, None

            if prices and len(prices) >= 5:
                prices = list(reversed(prices))
                return prices, prices, prices, prices

        return None, None, None, None
    except Exception as e:
        return None, None, None, None

# ─────────────────────────────────────────
# SYMBOL RESOLVER
# ─────────────────────────────────────────

def resolve_symbols(pair):
    from config import (BINANCE_SYMBOL_MAP, TWELVE_SYMBOL_MAP,
                        COINGECKO_ID_MAP, DERIV_OTC_SYMBOL_MAP)

    is_otc = "OTC" in pair
    base = pair.replace(" OTC", "").strip()

    binance_sym  = BINANCE_SYMBOL_MAP.get(pair) or BINANCE_SYMBOL_MAP.get(base)
    twelve_sym   = TWELVE_SYMBOL_MAP.get(pair)  or TWELVE_SYMBOL_MAP.get(base)
    coingecko_id = COINGECKO_ID_MAP.get(pair)   or COINGECKO_ID_MAP.get(base)
    deriv_sym    = DERIV_OTC_SYMBOL_MAP.get(pair) if is_otc else None

    return binance_sym, twelve_sym, coingecko_id, deriv_sym, is_otc

def get_kucoin_sym(b): return f"{b[:-4]}-USDT" if b and b.endswith("USDT") else None
def get_okx_sym(b):    return f"{b[:-4]}-USDT" if b and b.endswith("USDT") else None
KRAKEN_MAP = {
    "BTCUSDT":"XBTUSD","ETHUSDT":"ETHUSD","XRPUSDT":"XRPUSD",
    "LTCUSDT":"LTCUSD","ADAUSDT":"ADAUSD","DOGEUSDT":"XDGUSD",
    "SOLUSDT":"SOLUSD","DOTUSDT":"DOTUSD","LINKUSDT":"LINKUSD",
    "ATOMUSDT":"ATOMUSD","XLMUSDT":"XLMUSD","BCHUSDT":"BCHUSD",
    "ETCUSDT":"ETCUSD","XMRUSDT":"XMRUSD","ZECUSDT":"ZECUSD",
}
def get_kraken_sym(b): return KRAKEN_MAP.get(b) if b else None

GRANULARITY_MAP = {"1min":60,"5min":300,"15min":900,"30min":1800,"1h":3600}

# ─────────────────────────────────────────
# INDICATORS
# ─────────────────────────────────────────

def ema(prices, period):
    if len(prices) < period: return prices[-1]
    k = 2/(period+1)
    e = sum(prices[:period])/period
    for p in prices[period:]: e = p*k + e*(1-k)
    return e

def rsi(prices, period=14):
    if len(prices) < period+1: return 50.0
    gains,losses = [],[]
    for i in range(1,len(prices)):
        d = prices[i]-prices[i-1]
        gains.append(max(d,0)); losses.append(max(-d,0))
    ag = sum(gains[-period:])/period
    al = sum(losses[-period:])/period
    if al == 0: return 100.0
    return round(100-(100/(1+ag/al)),2)

def macd(prices):
    if len(prices)<26: return 0,0,0
    m = ema(prices,12)-ema(prices,26)
    s = ema(prices[-35:],9) if len(prices)>=35 else m
    return round(m,6),round(s,6),round(m-s,6)

def bollinger(prices, period=20):
    if len(prices)<period: p=prices[-1]; return p,p,p
    recent = prices[-period:]
    sma = sum(recent)/period
    std = (sum((p-sma)**2 for p in recent)/period)**0.5
    return round(sma+2*std,5),round(sma,5),round(sma-2*std,5)

def stochastic(highs, lows, closes, period=14):
    if len(closes)<period: return 50.0,50.0
    h,l = max(highs[-period:]),min(lows[-period:])
    if h==l: return 50.0,50.0
    k = round(100*(closes[-1]-l)/(h-l),2)
    d = round(sum([100*(closes[-i]-min(lows[-period:]))/
        (max(highs[-period:])-min(lows[-period:])+1e-10)
        for i in range(1,4)])/3,2)
    return k,d

def pad_prices(closes, highs, lows, opens, target=30):
    while len(closes)<target:
        closes=[closes[0]]+closes; highs=[highs[0]]+highs
        lows=[lows[0]]+lows; opens=[opens[0]]+opens
    return closes,highs,lows,opens

# ─────────────────────────────────────────
# MAIN ANALYSE FUNCTION
# ─────────────────────────────────────────

def analyse(pair, tf_data):
    if isinstance(tf_data, dict):
        binance_interval = tf_data.get("binance","5m")
        twelve_interval  = tf_data.get("twelve","5min")
    else:
        binance_interval = "5m"
        twelve_interval  = "5min"

    cache_key = f"{pair}_{twelve_interval}"
    now = time.time()
    if cache_key in _cache:
        t,r = _cache[cache_key]
        if now-t < CACHE_SECONDS: return r

    binance_sym,twelve_sym,coingecko_id,deriv_sym,is_otc = resolve_symbols(pair)
    kucoin_sym = get_kucoin_sym(binance_sym)
    okx_sym    = get_okx_sym(binance_sym)
    kraken_sym = get_kraken_sym(binance_sym)

    closes, highs, lows, opens = None, None, None, None

    # 1. Deriv WebSocket for OTC pairs
    if is_otc and deriv_sym:
        try:
            gran = GRANULARITY_MAP.get(twelve_interval, 300)
            closes, highs, lows, opens = fetch_deriv_otc(deriv_sym, gran)
        except:
            pass

    # 2. Binance — for ALL crypto including standalone coins
    if not closes and binance_sym:
        closes, highs, lows, opens = fetch_binance(
            binance_sym, binance_interval
        )

    # 3. KuCoin fallback
    if not closes and binance_sym:
        kucoin_sym = get_kucoin_sym(binance_sym)
        if kucoin_sym:
            closes, highs, lows, opens = fetch_kucoin(
                kucoin_sym, binance_interval
            )

    # 4. OKX fallback
    if not closes and binance_sym:
        okx_sym = get_okx_sym(binance_sym)
        if okx_sym:
            closes, highs, lows, opens = fetch_okx(
                okx_sym, binance_interval
            )

    # 5. Kraken fallback
    if not closes and binance_sym:
        kraken_sym = get_kraken_sym(binance_sym)
        if kraken_sym:
            closes, highs, lows, opens = fetch_kraken(
                kraken_sym, binance_interval
            )

    # 6. CoinGecko as LAST resort only (delayed data)
    if not closes and coingecko_id:
        closes, highs, lows, opens = fetch_coingecko_ohlc(coingecko_id)

    # 7. Twelve Data for forex/stocks/commodities
    if not closes and twelve_sym:
        closes, highs, lows, opens = fetch_twelve(
            twelve_sym, twelve_interval
        )
        
    # 8. Metals Live for Gold/Silver
    if not closes:
        closes, highs, lows, opens = fetch_metals_live(pair)

    # 9. Alpha Vantage for other commodities
    if not closes:
        closes, highs, lows, opens = fetch_alpha_vantage(pair)

    if not closes or len(closes) < 5:
        return None

    if len(closes) < 30:
        closes,highs,lows,opens = pad_prices(closes,highs,lows,opens)

    price     = closes[-1]
    rsi_v     = rsi(closes)
    m,s,h     = macd(closes)
    upper,mid,lower = bollinger(closes)
    k,d       = stochastic(highs,lows,closes)
    ema50     = ema(closes, min(50,len(closes)))
    ema200    = ema(closes, min(200,len(closes)))
    m2,s2,_   = macd(closes[:-1]) if len(closes)>1 else (0,0,0)

    bull,bear = 0,0
    reasons_bull,reasons_bear = [],[]

    if rsi_v < 25:   bull+=1.5; reasons_bull.append(f"RSI {rsi_v} — strongly oversold")
    elif rsi_v < 35: bull+=1;   reasons_bull.append(f"RSI {rsi_v} — oversold, buyers entering")
    elif rsi_v > 75: bear+=1.5; reasons_bear.append(f"RSI {rsi_v} — strongly overbought")
    elif rsi_v > 65: bear+=1;   reasons_bear.append(f"RSI {rsi_v} — overbought, sellers likely")
    elif rsi_v < 45: bull+=0.3
    elif rsi_v > 55: bear+=0.3

    if m>s and m2<=s2:   bull+=1.5; reasons_bull.append("MACD bullish crossover — momentum up")
    elif m<s and m2>=s2: bear+=1.5; reasons_bear.append("MACD bearish crossover — momentum down")
    elif m>s: bull+=0.5; reasons_bull.append("MACD above signal — upward momentum")
    else:     bear+=0.5; reasons_bear.append("MACD below signal — downward momentum")

    if price<=lower:   bull+=1.5; reasons_bull.append("Price at lower Bollinger — bounce expected")
    elif price>=upper: bear+=1.5; reasons_bear.append("Price at upper Bollinger — reversal likely")
    elif price>mid:    bull+=0.3
    else:              bear+=0.3

    if k<20 and k>d:   bull+=1; reasons_bull.append(f"Stoch K:{k} — oversold bullish crossover")
    elif k>80 and k<d: bear+=1; reasons_bear.append(f"Stoch K:{k} — overbought bearish crossover")
    elif k<30: bull+=0.5
    elif k>70: bear+=0.5

    if ema50>ema200: bull+=1; reasons_bull.append("EMA50 above EMA200 — uptrend confirmed")
    else:            bear+=1; reasons_bear.append("EMA50 below EMA200 — downtrend confirmed")

    if len(closes)>=3:
        if closes[-1]>closes[-2]>closes[-3]:   bull+=0.5; reasons_bull.append("3 consecutive bullish candles")
        elif closes[-1]<closes[-2]<closes[-3]: bear+=0.5; reasons_bear.append("3 consecutive bearish candles")

    total = bull+bear if (bull+bear)>0 else 1

    if bull>=3 and bull>bear:
        signal="BUY"; confidence=min(int((bull/total)*5)+1,5); reasons=reasons_bull[:3]
    elif bear>=3 and bear>bull:
        signal="SELL"; confidence=min(int((bear/total)*5)+1,5); reasons=reasons_bear[:3]
    else:
        signal="HOLD"; confidence=2
        reasons=["Market ranging — no clear direction","Wait for stronger confirmation","Check next candle"]

    conf_bar  = "█"*confidence + "░"*(5-confidence)
    conf_text = ["Very Low","Low","Medium","High","Very High"][confidence-1]
    bb_pos    = ("At Lower Band" if price<=lower else
                 "At Upper Band" if price>=upper else
                 "Above Middle"  if price>mid    else "Below Middle")

    indicators = {
        "rsi": rsi_v, "macd": "Bullish" if m>s else "Bearish",
        "bb": bb_pos, "stoch": f"K:{k} D:{d}",
        "ema_trend": "Uptrend" if ema50>ema200 else "Downtrend",
        "price": round(price,5)
    }

   # Get news sentiment
    news_sentiment, news_headlines = get_news_sentiment(pair)

    # Get Gemini AI analysis
    tf_label = twelve_interval
    ai_analysis = get_gemini_analysis(pair, indicators, news_headlines, signal, tf_label)

    # Use AI verdict if available
    final_signal = signal
    final_conf_text = conf_text
    ai_reasons = reasons

    if ai_analysis:
        verdict = ai_analysis.get("verdict","").upper()
        if verdict in ["BUY","SELL","HOLD"]:
            final_signal = verdict
        if ai_analysis.get("confidence_text"):
            final_conf_text = ai_analysis["confidence_text"]
        ai_reasons = [
            ai_analysis.get("reason1",""),
            ai_analysis.get("reason2",""),
            ai_analysis.get("reason3",""),
        ]
        ai_reasons = [r for r in ai_reasons if r]

    result = {
        "signal":        final_signal,
        "confidence":    confidence,
        "conf_bar":      conf_bar,
        "conf_text":     final_conf_text,
        "price":         round(price,5),
        "reasons":       ai_reasons or reasons,
        "news_sentiment":news_sentiment,
        "news_headlines":news_headlines,
        "ai_summary":    ai_analysis.get("summary","") if ai_analysis else "",
        "ai_risk":       ai_analysis.get("risk","Medium") if ai_analysis else "Medium",
        "indicators":    {
            "rsi":      rsi_v,
            "macd":     "Bullish" if m>s else "Bearish",
            "bb":       bb_pos,
            "stoch":    f"K:{k} D:{d}",
            "ema_trend":"Uptrend" if ema50>ema200 else "Downtrend",
        }
    }

    _cache[cache_key] = (now, result)
    return result

