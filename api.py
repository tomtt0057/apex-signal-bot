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

    if category == "forex":
        pairs = FOREX_PAIRS[:8]
    elif category == "forex_otc":
        pairs = FOREX_OTC_PAIRS[:8]
    elif category == "crypto":
        pairs = CRYPTO_PAIRS[:8]
    elif category == "crypto_otc":
        pairs = CRYPTO_OTC_PAIRS[:8]
    elif category == "commodity":
        pairs = COMMODITY_PAIRS
    else:
        pairs = (
            FOREX_PAIRS[:4] +
            FOREX_OTC_PAIRS[:4] +
            CRYPTO_PAIRS[:4] +
            COMMODITY_PAIRS[:2]
        )

    tf = {"twelve": "5min", "binance": "5m"}
    found = []
    session_name, _ = get_current_session()

    for pair in pairs:
        try:
            result = analyse(pair, tf)
            if (result and
                    result.get("signal") != "HOLD" and
                    result.get("confidence", 0) >= 4):
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

    found.sort(key=lambda x: x["confidence"], reverse=True)

    return jsonify({
        "success": True,
        "session": session_name,
        "good_time": is_good_trading_time(),
        "signals_found": len(found),
        "signals": found[:5],
    })

def start_api():
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)

def start_api_thread():
    thread = threading.Thread(target=start_api, daemon=True)
    thread.start()
    logger.info("✅ Flask API started on port 8080")
