import httpx
import time

_cache = {}
CACHE_SECONDS = 45

def clean_pair(pair):
    """Remove OTC suffix and return base pair"""
    return pair.replace(" OTC", "").strip()

def resolve_symbols(pair):
    """Smart symbol resolver — handles OTC, standalone coins, stocks, commodities"""
    from config import BINANCE_SYMBOL_MAP, TWELVE_SYMBOL_MAP

    # Try exact match first
    binance_sym = BINANCE_SYMBOL_MAP.get(pair)
    twelve_sym  = TWELVE_SYMBOL_MAP.get(pair)

    # If not found, try without OTC suffix
    if not binance_sym and not twelve_sym:
        base = clean_pair(pair)
        binance_sym = BINANCE_SYMBOL_MAP.get(base)
        twelve_sym  = TWELVE_SYMBOL_MAP.get(base)

    return binance_sym, twelve_sym

def fetch_binance(symbol, interval="5m", bars=80):
    try:
        url = (
            f"https://api.binance.com/api/v3/klines"
            f"?symbol={symbol}&interval={interval}&limit={bars}"
        )
        r = httpx.get(url, timeout=6)
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

    binance_sym, twelve_sym = resolve_symbols(pair)

    closes, highs, lows, opens = None, None, None, None

    # Try Binance first (fastest)
    if binance_sym:
        closes, highs, lows, opens = fetch_binance(
            binance_sym, binance_interval
        )

    # Fall back to Twelve Data
    if not closes and twelve_sym:
        closes, highs, lows, opens = fetch_twelve(
            twelve_sym, twelve_interval
        )

    if not closes or len(closes) < 30:
        return None

    price    = closes[-1]
    rsi_v    = rsi(closes)
    m, s, h  = macd(closes)
    upper, mid, lower = bollinger(closes)
    k, d     = stochastic(highs, lows, closes)
    ema50    = ema(closes, min(50,  len(closes)))
    ema200   = ema(closes, min(200, len(closes)))
    m2, s2, _ = macd(closes[:-1])

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

    if closes[-1] > closes[-2] > closes[-3]:
        bull += 0.5
        reasons_bull.append("3 consecutive bullish candles — buyers in control")
    elif closes[-1] < closes[-2] < closes[-3]:
        bear += 0.5
        reasons_bear.append("3 consecutive bearish candles — sellers in control")

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
