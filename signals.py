import httpx
import time
import re

_cache = {}
CACHE_SECONDS = 45

# ─────────────────────────────────────────
# EMOJI STRIPPER
# ─────────────────────────────────────────

def strip_emoji(text):
    """Remove all emoji and extra spaces from text"""
    clean = re.sub(
        r'[\U00010000-\U0010ffff'
        r'\u2600-\u27BF'
        r'\u2300-\u23FF'
        r'\u20A0-\u20CF'
        r'\uFE00-\uFE0F'
        r'\u0080-\u00FF'
        r'\u2000-\u206F'
        r'\u00A0-\u00FF'
        r'\u20D0-\u20FF'
        r'\uFE30-\uFE4F'
        r'\u2100-\u214F'
        r'\u0900-\u097F'
        r'\u2190-\u21FF'
        r'\u2B00-\u2BFF'
        r'\u1F000-\u1FFFF]+',
        '', text, flags=re.UNICODE
    )
    return clean.strip()

# ─────────────────────────────────────────
# BUILD CLEAN LOOKUP MAPS
# ─────────────────────────────────────────

def get_clean_maps():
    """Build emoji-free versions of all maps for reliable lookup"""
    from config import BINANCE_SYMBOL_MAP, TWELVE_SYMBOL_MAP, COINGECKO_ID_MAP

    clean_binance = {}
    for k, v in BINANCE_SYMBOL_MAP.items():
        clean_binance[strip_emoji(k)] = v
        clean_binance[k] = v  # keep original too

    clean_twelve = {}
    for k, v in TWELVE_SYMBOL_MAP.items():
        clean_twelve[strip_emoji(k)] = v
        clean_twelve[k] = v

    clean_coingecko = {}
    for k, v in COINGECKO_ID_MAP.items():
        clean_coingecko[strip_emoji(k)] = v
        clean_coingecko[k] = v

    return clean_binance, clean_twelve, clean_coingecko

# ─────────────────────────────────────────
# SYMBOL RESOLVER
# ─────────────────────────────────────────

def resolve_symbols(pair):
    clean_binance, clean_twelve, clean_coingecko = get_clean_maps()

    # Try original pair
    binance_sym  = clean_binance.get(pair)
    twelve_sym   = clean_twelve.get(pair)
    coingecko_id = clean_coingecko.get(pair)

    # Try stripped emoji version
    if not binance_sym and not twelve_sym and not coingecko_id:
        stripped = strip_emoji(pair)
        binance_sym  = clean_binance.get(stripped)
        twelve_sym   = clean_twelve.get(stripped)
        coingecko_id = clean_coingecko.get(stripped)

    # Try without OTC suffix
    if not binance_sym and not twelve_sym and not coingecko_id:
        base = pair.replace(" OTC", "").strip()
        stripped_base = strip_emoji(base)
        binance_sym  = clean_binance.get(base) or clean_binance.get(stripped_base)
        twelve_sym   = clean_twelve.get(base)  or clean_twelve.get(stripped_base)
        coingecko_id = clean_coingecko.get(base) or clean_coingecko.get(stripped_base)

    return binance_sym, twelve_sym, coingecko_id

# ─────────────────────────────────────────
# BINANCE FETCH
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
        closes = [float(k[4]) for k in data]
        highs  = [float(k[2]) for k in data]
        lows   = [float(k[3]) for k in data]
        opens  = [float(k[1]) for k in data]
        return closes, highs, lows, opens
    except:
        return None, None, None, None

# ─────────────────────────────────────────
# COINGECKO FETCH
# ─────────────────────────────────────────

def fetch_coingecko_ohlc(coin_id):
    try:
        from config import COINGECKO_API_KEY
        url = (
            f"https://pro-api.coingecko.com/api/v3/coins"
            f"/{coin_id}/ohlc?vs_currency=usd&days=1"
        )
        headers = {
            "accept": "application/json",
            "x-cg-pro-api-key": COINGECKO_API_KEY
        }
        r = httpx.get(url, headers=headers, timeout=10)
        data = r.json()
        if not isinstance(data, list) or len(data) < 5:
            return None, None, None, None
        closes = [float(c[4]) for c in data]
        highs  = [float(c[2]) for c in data]
        lows   = [float(c[3]) for c in data]
        opens  = [float(c[1]) for c in data]
        return closes, highs, lows, opens
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
        headers = {
            "accept": "application/json",
            "x-cg-pro-api-key": COINGECKO_API_KEY
        }
        r = httpx.get(url, headers=headers, timeout=10)
        data = r.json()
        if "prices" not in data or len(data["prices"]) < 5:
            return None, None, None, None
        prices = [float(p[1]) for p in data["prices"]]
        return prices, prices, prices, prices
    except:
        return None, None, None, None

# ─────────────────────────────────────────
# TWELVE DATA FETCH
# ─────────────────────────────────────────

def fetch_twelve(symbol, interval="5min", bars=80):
    try:
        from config import TWELVE_API_KEY
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
        closes = [float(v["close"]) for v in values]
        highs  = [float(v["high"])  for v in values]
        lows   = [float(v["low"])   for v in values]
        opens  = [float(v["open"])  for v in values]
        return closes, highs, lows, opens
    except:
        return None, None, None, None

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
        d = prices[i] - prices[i-1]
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
    h = m - s
    return round(m, 6), round(s, 6), round(h, 6)

def bollinger(prices, period=20):
    if len(prices) < period:
        p = prices[-1]
        return p, p, p
    recent = prices[-period:]
    sma = sum(recent) / period
    std = (sum((p - sma)**2 for p in recent) / period) ** 0.5
    return round(sma + 2*std, 5), round(sma, 5), round(sma - 2*std, 5)

def stochastic(highs, lows, closes, period=14):
    if len(closes) < period:
        return 50.0, 50.0
    h = max(highs[-period:])
    l = min(lows[-period:])
    if h == l:
        return 50.0, 50.0
    k = round(100 * (closes[-1] - l) / (h - l), 2)
    d = round(sum([
        100*(closes[-i]-min(lows[-period:]))/
        (max(highs[-period:])-min(lows[-period:])+1e-10)
        for i in range(1, 4)
    ])/3, 2)
    return k, d

def pad_prices(closes, highs, lows, opens, target=30):
    while len(closes) < target:
        closes = [closes[0]] + closes
        highs  = [highs[0]]  + highs
        lows   = [lows[0]]   + lows
        opens  = [opens[0]]  + opens
    return closes, highs, lows, opens

# ─────────────────────────────────────────
# MAIN ANALYSE FUNCTION
# ─────────────────────────────────────────

def analyse(pair, tf_data):
    if isinstance(tf_data, dict):
        binance_interval = tf_data.get("binance", "5m")
        twelve_interval  = tf_data.get("twelve",  "5min")
    else:
        binance_interval = "5m"
        twelve_interval  = "5min"

    cache_key = f"{pair}_{twelve_interval}"
    now = time.time()
    if cache_key in _cache:
        t, r = _cache[cache_key]
        if now - t < CACHE_SECONDS:
            return r

    binance_sym, twelve_sym, coingecko_id = resolve_symbols(pair)
    closes, highs, lows, opens = None, None, None, None

    # 1. Binance — for crypto pairs (fastest)
    if binance_sym and not coingecko_id:
        closes, highs, lows, opens = fetch_binance(
            binance_sym, binance_interval
        )

    # 2. CoinGecko OHLC — for standalone coins
    if not closes and coingecko_id:
        closes, highs, lows, opens = fetch_coingecko_ohlc(coingecko_id)

    # 3. CoinGecko chart fallback
    if not closes and coingecko_id:
        closes, highs, lows, opens = fetch_coingecko_chart(coingecko_id)

    # 4. Binance fallback for crypto OTC
    if not closes and binance_sym:
        closes, highs, lows, opens = fetch_binance(
            binance_sym, binance_interval
        )

    # 5. Twelve Data — forex/stocks/commodities
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

    price      = closes[-1]
    rsi_v      = rsi(closes)
    m, s, h    = macd(closes)
    upper, mid, lower = bollinger(closes)
    k, d       = stochastic(highs, lows, closes)
    ema50      = ema(closes, min(50,  len(closes)))
    ema200     = ema(closes, min(200, len(closes)))
    m2, s2, _  = macd(closes[:-1]) if len(closes) > 1 else (0, 0, 0)

    bull, bear = 0, 0
    reasons_bull = []
    reasons_bear = []

    if rsi_v < 25:
        bull += 1.5
        reasons_bull.append(f"RSI {rsi_v} — strongly oversold, reversal expected")
    elif rsi_v < 35:
        bull += 1
        reasons_bull.append(f"RSI {rsi_v} — oversold, buyers stepping in")
    elif rsi_v > 75:
        bear += 1.5
        reasons_bear.append(f"RSI {rsi_v} — strongly overbought, reversal expected")
    elif rsi_v > 65:
        bear += 1
        reasons_bear.append(f"RSI {rsi_v} — overbought, sellers likely")
    elif rsi_v < 45:
        bull += 0.3
    elif rsi_v > 55:
        bear += 0.3

    if m > s and m2 <= s2:
        bull += 1.5
        reasons_bull.append("MACD bullish crossover — strong upward momentum")
    elif m < s and m2 >= s2:
        bear += 1.5
        reasons_bear.append("MACD bearish crossover — strong downward momentum")
    elif m > s:
        bull += 0.5
        reasons_bull.append("MACD above signal — upward momentum continues")
    else:
        bear += 0.5
        reasons_bear.append("MACD below signal — downward momentum continues")

    if price <= lower:
        bull += 1.5
        reasons_bull.append("Price at lower Bollinger band — bounce expected")
    elif price >= upper:
        bear += 1.5
        reasons_bear.append("Price at upper Bollinger band — reversal likely")
    elif price > mid:
        bull += 0.3
    else:
        bear += 0.3

    if k < 20 and k > d:
        bull += 1
        reasons_bull.append(f"Stoch K:{k} — oversold with bullish crossover")
    elif k > 80 and k < d:
        bear += 1
        reasons_bear.append(f"Stoch K:{k} — overbought with bearish crossover")
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

    if len(closes) >= 3 and closes[-1] > closes[-2] > closes[-3]:
        bull += 0.5
        reasons_bull.append("3 bullish candles — buyers in control")
    elif len(closes) >= 3 and closes[-1] < closes[-2] < closes[-3]:
        bear += 0.5
        reasons_bear.append("3 bearish candles — sellers in control")

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
            "Market ranging — no clear direction yet",
            "Wait for stronger confirmation before entering",
            "Check again in the next candle"
        ]

    conf_bar  = "█" * confidence + "░" * (5 - confidence)
    conf_text = ["Very Low","Low","Medium","High","Very High"][confidence-1]
    bb_pos    = ("At Lower Band" if price <= lower
                 else "At Upper Band" if price >= upper
                 else "Above Middle" if price > mid
                 else "Below Middle")

    result = {
        "signal":     signal,
        "confidence": confidence,
        "conf_bar":   conf_bar,
        "conf_text":  conf_text,
        "price":      round(price, 5),
        "reasons":    reasons,
        "indicators": {
            "rsi":      rsi_v,
            "macd":     "Bullish ↑" if m > s else "Bearish ↓",
            "bb":       bb_pos,
            "stoch":    f"K:{k} D:{d}",
            "ema_trend":"Uptrend ↑" if ema50 > ema200 else "Downtrend ↓",
        }
    }

    _cache[cache_key] = (now, result)
    return result
