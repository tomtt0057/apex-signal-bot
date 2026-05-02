from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import uvicorn
import threading
import logging
from signals import analyse, get_current_session, is_good_trading_time
from config import (
    FOREX_PAIRS, FOREX_OTC_PAIRS,
    CRYPTO_PAIRS, CRYPTO_OTC_PAIRS,
    COMMODITY_PAIRS, ALL_PAIRS_FLAT
)

logger = logging.getLogger(__name__)
app = FastAPI(title="ApexSignal API")

# ─── Secret key to protect your API ──────────────────────────
API_SECRET = "apexbot2026"

# ─── Health check ─────────────────────────────────────────────
@app.get("/")
def health():
    return {"status": "ApexSignal API running"}

# ─── Get signal for specific pair ─────────────────────────────
@app.get("/signal")
def get_signal(
    pair: str = Query(..., description="Trading pair"),
    timeframe: str = Query("5min", description="Timeframe"),
    key: str = Query(..., description="API secret key")
):
    # Security check
    if key != API_SECRET:
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized"}
        )

    try:
        # Map timeframe to correct format
        tf_map = {
            "1min":  {"twelve": "1min",  "binance": "1m"},
            "5min":  {"twelve": "5min",  "binance": "5m"},
            "15min": {"twelve": "15min", "binance": "15m"},
            "30min": {"twelve": "30min", "binance": "30m"},
            "1h":    {"twelve": "1h",    "binance": "1h"},
        }
        tf = tf_map.get(timeframe, {"twelve": "5min", "binance": "5m"})

        # Get signal
        result = analyse(pair, tf)
        if not result:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "No data available for this pair",
                    "pair": pair
                }
            )

        session_name, session_flag = get_current_session()

        # Return clean JSON response
        return {
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
                "bb": result.get("indicators", {}).get("bb", "N/A"),
                "stoch": result.get("indicators", {}).get("stoch", "N/A"),
            },
            "news_sentiment": result.get("news_sentiment", "Neutral"),
            "reasons": result.get("reasons", []),
            "ai_summary": result.get("ai_summary", ""),
        }

    except Exception as e:
        logger.error(f"API signal error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# ─── Auto scan — finds best signal right now ──────────────────
@app.get("/autoscan")
def auto_scan(
    key: str = Query(..., description="API secret key"),
    category: str = Query("all", description="Category")
):
    if key != API_SECRET:
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized"}
        )

    try:
        # Choose pairs based on category
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
            # Best of everything
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

        # Sort by confidence
        found.sort(key=lambda x: x["confidence"], reverse=True)

        return {
            "success": True,
            "session": session_name,
            "good_time": is_good_trading_time(),
            "signals_found": len(found),
            "signals": found[:5],
        }

    except Exception as e:
        logger.error(f"autoscan error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# ─── Start API server ─────────────────────────────────────────
def start_api():
    uvicorn.run(app, host="0.0.0.0", port=8080)

def start_api_thread():
    thread = threading.Thread(target=start_api, daemon=True)
    thread.start()
    logger.info("✅ API server started on port 8080")
