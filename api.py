from flask import Flask, jsonify, request
import threading
import logging
from signals import analyse, get_current_session, is_good_trading_time
from config import (
    FOREX_PAIRS, FOREX_OTC_PAIRS,
    CRYPTO_PAIRS, CRYPTO_OTC_PAIRS,
    COMMODITY_PAIRS
)

logger = logging.getLogger(__name__)
app = Flask(__name__)

API_SECRET = "apexbot2026"

@app.route("/")
def health():
    return jsonify({"status": "ApexSignal API running ✅"})

@app.route("/signal")
def get_signal():
    key = request.args.get("key", "")
    if key != API_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    pair = request.args.get("pair", "EUR/USD")
    timeframe = request.args.get("timeframe", "5min")

    tf_map = {
        "1min":  {"twelve": "1min",  "binance": "1m"},
        "5min":  {"twelve": "5min",  "binance": "5m"},
        "15min": {"twelve": "15min", "binance": "15m"},
        "30min": {"twelve": "30min", "binance": "30m"},
        "1h":    {"twelve": "1h",    "binance": "1h"},
    }
    tf = tf_map.get(timeframe, {"twelve": "5min", "binance": "5m"})

    try:
        result = analyse(pair, tf)
        if not result:
            return jsonify({
                "error": "No data available",
                "pair": pair
            }), 404

        session_name, _ = get_current_session()
        return jsonify({
            "success": True,
            "pair": pair,
            "timeframe": timeframe,
            "signal": result.get("signal", "HOLD"),
            "confidence": result.get("confidence", 0),
            "confidence_text": result.get("conf_text", "Low"),
            "entry_price": result.get("price", 0),
            "session": session_name,
            "good_time": is_good_trading_time(),
            "indicators": {
                "rsi": result.get("indicators", {}).get("rsi", 0),
                "macd": result.get("indicators", {}).get("macd", "N/A"),
                "trend": result.get("indicators", {}).get("ema_trend", "N/A"),
            },
            "news_sentiment": result.get("news_sentiment", "Neutral"),
            "ai_summary": result.get("ai_summary", ""),
        })
    except Exception as e:
        logger.error(f"Signal error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/autoscan")
def auto_scan():
    key = request.args.get("key", "")
    if key != API_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    category = request.args.get("category", "all")

    # Minimum confidence threshold
    # Lower during slow sessions to find more signals
    min_confidence = 3

    if category == "forex":
        pairs = FOREX_PAIRS
    elif category == "forex_otc":
        pairs = FOREX_OTC_PAIRS
    elif category == "crypto":
        pairs = CRYPTO_PAIRS
    elif category == "crypto_otc":
        pairs = CRYPTO_OTC_PAIRS
    elif category == "commodity":
        pairs = COMMODITY_PAIRS + COMMODITY_OTC_PAIRS
    elif category == "stocks":
        pairs = STOCK_PAIRS[:10] + STOCK_OTC_PAIRS[:8]
    else:
        # ALL categories — priority pairs from everything
        pairs = (
            # Top Forex — most liquid
            ["EUR/USD", "GBP/USD", "USD/JPY",
             "AUD/USD", "USD/CAD", "NZD/USD",
             "EUR/GBP", "EUR/JPY", "GBP/JPY",
             "USD/CHF", "EUR/CHF", "AUD/JPY",
             "EUR/AUD", "GBP/AUD", "EUR/CAD"] +

            # Top Forex OTC — available 24/7
            ["EUR/USD OTC", "GBP/USD OTC", "USD/JPY OTC",
             "AUD/USD OTC", "EUR/GBP OTC", "GBP/JPY OTC",
             "EUR/JPY OTC", "USD/CAD OTC", "NZD/USD OTC",
             "EUR/CHF OTC", "AUD/JPY OTC", "EUR/AUD OTC",
             "GBP/AUD OTC", "EUR/CAD OTC", "GBP/CAD OTC"] +

            # Top Crypto — high volatility 24/7
            ["BTC/USD", "ETH/USD", "BNB/USD",
             "SOL/USD", "XRP/USD", "ADA/USD",
             "DOGE/USD", "LTC/USD", "AVAX/USD",
             "LINK/USD", "DOT/USD", "MATIC/USD",
             "ATOM/USD", "UNI/USD", "NEAR/USD"] +

            # Crypto OTC — 24/7 trading
            ["BTC/USD OTC", "ETH/USD OTC", "XRP/USD OTC",
             "LTC/USD OTC", "ADA/USD OTC", "DOGE/USD OTC",
             "SOL/USD OTC", "BNB/USD OTC", "DOT/USD OTC",
             "LINK/USD OTC"] +

            # All Commodities — always active
            ["Gold", "Silver", "Crude Oil (WTI)",
             "Brent Oil", "Natural Gas", "Copper",
             "Gold OTC", "Silver OTC",
             "Crude Oil OTC", "Brent Oil OTC"] +

            # Top Stocks OTC — available during slow hours
            ["Apple Inc OTC", "Tesla Inc OTC",
             "Microsoft Corp OTC", "Amazon OTC",
             "NVIDIA Corp OTC", "Meta Platforms OTC",
             "Netflix OTC", "Google OTC"] +

            # Standalone Crypto coins
            ["Bitcoin", "Ethereum", "Solana",
             "BNB", "XRP", "Cardano", "Dogecoin",
             "Polygon", "Avalanche", "Chainlink"]
        )

    tf = {"twelve": "5min", "binance": "5m"}
    found = []
    session_name, _ = get_current_session()
    good_time = is_good_trading_time()

    # During slow sessions lower the bar to find signals
    if not good_time:
        min_confidence = 3
    else:
        min_confidence = 4

    for pair in pairs:
        try:
            result = analyse(pair, tf)
            if (result and
                    result.get("signal") != "HOLD" and
                    result.get("confidence", 0) >= min_confidence):
                found.append({
                    "pair": pair,
                    "signal": result.get("signal"),
                    "confidence": result.get("confidence", 0),
                    "confidence_text": result.get("conf_text", ""),
                    "entry_price": result.get("price", 0),
                    "trend": result.get(
                        "indicators", {}
                    ).get("ema_trend", "N/A"),
                })
        except Exception as e:
            logger.error(f"autoscan {pair}: {e}")

    # Sort by confidence — best signal first
    found.sort(key=lambda x: x["confidence"], reverse=True)

    return jsonify({
        "success": True,
        "session": session_name,
        "good_time": good_time,
        "pairs_scanned": len(pairs),
        "signals_found": len(found),
        "signals": found[:5],
    })

def start_api():
    port = int(__import__('os').environ.get("PORT", 8080))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )

def start_api_thread():
    thread = threading.Thread(target=start_api, daemon=True)
    thread.start()
    logger.info("✅ Flask API started")
