import logging
import os
import json
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler,
    CallbackQueryHandler, ContextTypes,
    MessageHandler, filters
)
from config import (
    BOT_TOKEN, SIGNAL_INTERVAL_MINUTES,
    FOREX_PAIRS, FOREX_OTC_PAIRS,
    STOCK_PAIRS, STOCK_OTC_PAIRS,
    COMMODITY_PAIRS, COMMODITY_OTC_PAIRS,
    CRYPTO_PAIRS, CRYPTO_OTC_PAIRS,
    CRYPTO_STANDALONE, TIMEFRAMES,
    GEMINI_API_KEY
)
from database import Database
from signals import analyse, get_current_session, is_good_trading_time
import httpx

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
db = Database()

ALL_PAIRS_MAP = {
    "forex":             FOREX_PAIRS,
    "forex_otc":         FOREX_OTC_PAIRS,
    "stocks":            STOCK_PAIRS,
    "stocks_otc":        STOCK_OTC_PAIRS,
    "commodity":         COMMODITY_PAIRS,
    "commodity_otc":     COMMODITY_OTC_PAIRS,
    "crypto":            CRYPTO_PAIRS,
    "crypto_otc":        CRYPTO_OTC_PAIRS,
    "crypto_standalone": CRYPTO_STANDALONE,
}

ALL_PAIRS_FLAT = (
    FOREX_PAIRS + FOREX_OTC_PAIRS +
    STOCK_PAIRS + STOCK_OTC_PAIRS +
    COMMODITY_PAIRS + COMMODITY_OTC_PAIRS +
    CRYPTO_PAIRS + CRYPTO_OTC_PAIRS +
    CRYPTO_STANDALONE
)

CRYPTO_KEYWORDS = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "ADA",
    "DOGE", "MATIC", "DOT", "AVAX", "LINK", "LTC",
    "UNI", "ATOM", "TRX", "SHIB", "Bitcoin", "Ethereum",
    "Cardano", "Solana", "Dogecoin", "Polygon",
    "Litecoin", "Chainlink", "Cosmos", "TRON",
    "Binance", "Ripple", "Polkadot", "Avalanche"
]

STOCK_KEYWORDS = [
    "Apple", "Microsoft", "Google", "Amazon", "Meta",
    "Tesla", "NVIDIA", "Netflix", "AMD", "Intel",
    "JPMorgan", "Visa", "Coca", "Disney", "Nike",
    "Goldman", "Morgan", "Walmart", "Boeing", "Alibaba"
]

COMMODITY_KEYWORDS = [
    "Gold", "Silver", "Oil", "Brent",
    "Platinum", "Palladium", "Natural Gas", "Copper"
]


def is_weekend():
    return datetime.now(timezone.utc).weekday() >= 5


def is_crypto_pair(pair):
    return any(c in pair for c in CRYPTO_KEYWORDS)


def is_stock_pair(pair):
    return any(s in pair for s in STOCK_KEYWORDS)


def is_commodity_pair(pair):
    return any(c in pair for c in COMMODITY_KEYWORDS)


def is_forex_pair(pair):
    return "/" in pair and not is_crypto_pair(pair)


def signal_emoji(s):
    return {
        "BUY": "🟢 BUY",
        "SELL": "🔴 SELL",
        "HOLD": "⏸ HOLD"
    }.get(s, s)


def build_signal_msg(pair, tf_label, r):
    try:
        weekend = is_weekend()

        if weekend:
            if is_forex_pair(pair):
                weekend_warning = (
                    "\n🚨 *WEEKEND WARNING*\n"
                    "❌ Real forex market is CLOSED today!\n"
                    "❌ This signal uses stale Friday data!\n"
                    "❌ DO NOT trade this pair today!\n"
                    "✅ Trade crypto pairs instead!\n\n"
                )
            elif is_stock_pair(pair):
                weekend_warning = (
                    "\n🚨 *WEEKEND WARNING*\n"
                    "❌ Stock markets are CLOSED today!\n"
                    "❌ This signal is NOT reliable!\n"
                    "✅ Trade crypto pairs instead!\n\n"
                )
            elif is_commodity_pair(pair):
                weekend_warning = (
                    "\n⚠️ *WEEKEND WARNING*\n"
                    "⚠️ Commodity markets mostly closed!\n"
                    "⚠️ Signal may not be reliable!\n"
                    "✅ Trade crypto pairs instead!\n\n"
                )
            elif is_crypto_pair(pair):
                weekend_warning = (
                    "\n✅ *WEEKEND STATUS*\n"
                    "✅ Crypto trades 24/7 — signal reliable!\n\n"
                )
            else:
                weekend_warning = ""
        else:
            weekend_warning = ""

        reasons_text = "\n".join(
            f"  • {reason}"
            for reason in r.get("reasons", []) if reason
        )
        news_text = ""
        if r.get("news_headlines"):
            news_text = "\n📰 *Latest News:*\n"
            for h in r["news_headlines"][:2]:
                news_text += f"  • {str(h)[:60]}\n"

        ai_section = ""
        if r.get("ai_summary"):
            ai_section = (
                f"\n🤖 *AI Verdict:*\n"
                f"  {r['ai_summary']}\n"
                f"  Risk: `{r.get('ai_risk', 'Medium')}`\n"
            )

        session_name, session_flag = get_current_session()
        indicators = r.get("indicators", {})
        perf = db.get_pair_performance(pair)
        perf_text = ""
        if perf and perf[1] >= 3:
            perf_text = (
                f"  Win Rate: `{perf[0]:.1f}%` "
                f"({perf[2]}W/{perf[3]}L)\n"
            )

        return (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *{pair}* — `{tf_label}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{weekend_warning}"
            f"Signal:      *{signal_emoji(r.get('signal', 'HOLD'))}*\n"
            f"Confidence:  `{r.get('conf_bar', '░░░░░')}` "
            f"{r.get('conf_text', 'Low')}\n"
            f"Entry Price: `{r.get('price', 0)}`\n"
            f"Session:     {session_flag} `{session_name}`\n"
            f"News Mood:   `{r.get('news_sentiment', 'Neutral')}`\n"
            f"{perf_text}\n"
            f"🧠 *Analysis:*\n{reasons_text}\n"
            f"{news_text}"
            f"{ai_section}"
            f"\n📈 *Indicators*\n"
            f"  RSI:    `{indicators.get('rsi', 50)}`\n"
            f"  MACD:   `{indicators.get('macd', 'N/A')}`\n"
            f"  BB:     `{indicators.get('bb', 'N/A')}`\n"
            f"  Stoch:  `{indicators.get('stoch', 'N/A')}`\n"
            f"  Trend:  `{indicators.get('ema_trend', 'N/A')}`\n\n"
            f"🕐 `{datetime.utcnow().strftime('%H:%M UTC')}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ _Trade at your own risk._"
        )
    except Exception as e:
        logger.error(f"build_signal_msg error: {e}")
        return f"Signal for {pair}. Please try again."


def main_menu_kb():
    session_name, session_flag = get_current_session()
    weekend = is_weekend()
    status = (
        "🚨 Weekend — Trade Crypto Only!"
        if weekend
        else "✅ Good time!" if is_good_trading_time()
        else "⚠️ Slow market hours"
    )
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🚀  S T A R T  T R A D I N G",
            callback_data="show_category"
        )],
        [
            InlineKeyboardButton(
                "🔔 Auto-Signals",
                callback_data="subscribe"
            ),
            InlineKeyboardButton(
                "📊 My Stats",
                callback_data="stats"
            ),
        ],
        [
            InlineKeyboardButton(
                "🏆 Top Pairs",
                callback_data="top_pairs"
            ),
            InlineKeyboardButton(
                "🌍 Sessions",
                callback_data="sessions"
            ),
        ],
        [InlineKeyboardButton("❓ Help", callback_data="help")],
    ])


def category_kb():
    weekend = is_weekend()
    if weekend:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "₿ Crypto ✅ RECOMMENDED",
                callback_data="cat_crypto"
            )],
            [InlineKeyboardButton(
                "₿ Crypto OTC ✅ RECOMMENDED",
                callback_data="cat_crypto_otc"
            )],
            [InlineKeyboardButton(
                "🪙 Crypto Coins ✅ RECOMMENDED",
                callback_data="cat_crypto_standalone"
            )],
            [
                InlineKeyboardButton(
                    "💱 Forex ⚠️ CLOSED",
                    callback_data="cat_forex"
                ),
                InlineKeyboardButton(
                    "💱 Forex OTC ⚠️",
                    callback_data="cat_forex_otc"
                ),
            ],
            [
                InlineKeyboardButton(
                    "📈 Stocks ⚠️ CLOSED",
                    callback_data="cat_stocks"
                ),
                InlineKeyboardButton(
                    "📈 Stocks OTC ⚠️",
                    callback_data="cat_stocks_otc"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🥇 Commodities ⚠️",
                    callback_data="cat_commodity"
                ),
                InlineKeyboardButton(
                    "🥇 Commodities OTC ⚠️",
                    callback_data="cat_commodity_otc"
                ),
            ],
            [InlineKeyboardButton(
                "⬅ Back", callback_data="back_main"
            )],
        ])
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💱 Forex", callback_data="cat_forex"
            ),
            InlineKeyboardButton(
                "💱 Forex OTC", callback_data="cat_forex_otc"
            ),
        ],
        [
            InlineKeyboardButton(
                "📈 Stocks", callback_data="cat_stocks"
            ),
            InlineKeyboardButton(
                "📈 Stocks OTC", callback_data="cat_stocks_otc"
            ),
        ],
        [
            InlineKeyboardButton(
                "🥇 Commodities", callback_data="cat_commodity"
            ),
            InlineKeyboardButton(
                "🥇 Commodities OTC",
                callback_data="cat_commodity_otc"
            ),
        ],
        [
            InlineKeyboardButton(
                "₿ Crypto", callback_data="cat_crypto"
            ),
            InlineKeyboardButton(
                "₿ Crypto OTC", callback_data="cat_crypto_otc"
            ),
        ],
        [InlineKeyboardButton(
            "🪙 Crypto Coins",
            callback_data="cat_crypto_standalone"
        )],
        [InlineKeyboardButton(
            "⬅ Back", callback_data="back_main"
        )],
    ])


def pairs_kb(category):
    pairs = ALL_PAIRS_MAP.get(category, [])
    rows = []
    row = []
    for pair in pairs:
        short = pair[:20] if len(pair) > 20 else pair
        row.append(InlineKeyboardButton(
            short, callback_data=f"pair_{pair}"
        ))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(
        "⬅ Back", callback_data="show_category"
    )])
    return InlineKeyboardMarkup(rows)


def timeframe_kb(pair):
    rows = []
    for label, val in TIMEFRAMES.items():
        val_str = f"{val['twelve']}|{val['binance']}"
        safe = pair[:30]
        rows.append([InlineKeyboardButton(
            label.strip(),
            callback_data=f"tf_{safe}_{val_str}_{label.strip()}"
        )])
    rows.append([InlineKeyboardButton(
        "⬅ Back", callback_data="show_category"
    )])
    return InlineKeyboardMarkup(rows)


async def handle_ai_chat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_message: str
):
    user = update.effective_user
    uid = user.id
    db.save_chat_message(uid, "user", user_message)

    thinking_msg = await update.message.reply_text(
        "🤔 *Thinking...*",
        parse_mode="Markdown"
    )

    try:
        session_name, session_flag = get_current_session()
        good_time = is_good_trading_time()
        weekend = is_weekend()
        top_pairs = db.get_top_pairs(3)
        top_text = ""
        if top_pairs:
            top_text = "Best pairs from history:\n"
            for p in top_pairs:
                top_text += f"- {p[0]}: {p[1]:.1f}% win rate\n"

        weekend_context = ""
        if weekend:
            weekend_context = (
                "IMPORTANT: Today is WEEKEND. "
                "Forex and stock markets are CLOSED. "
                "Only recommend crypto pairs today. "
                "Warn user if they ask about forex or stocks.\n"
            )

        prompt = (
            f"You are ApexSignal, a professional AI binary options "
            f"trading assistant.\n\n"
            f"{weekend_context}"
            f"Current info:\n"
            f"- Session: {session_name} {session_flag}\n"
            f"- Weekend: {'Yes — only trade crypto!' if weekend else 'No'}\n"
            f"- Good trading time: "
            f"{'Yes' if good_time else 'No'}\n"
            f"{top_text}\n"
            f"User message: {user_message}\n\n"
            f"Reply briefly and professionally. "
            f"Max 100 words. Use emojis. "
            f"If weekend and user asks forex — warn them strongly."
        )

        url = (
            f"https://generativelanguage.googleapis.com/v1beta"
            f"/models/gemini-1.5-flash:generateContent"
            f"?key={GEMINI_API_KEY}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 200,
            }
        }

        r = httpx.post(url, json=payload, timeout=15)
        data = r.json()

        if "candidates" not in data:
            raise Exception(f"Gemini error: {data}")

        ai_reply = (
            data["candidates"][0]["content"]["parts"][0]["text"]
        )
        db.save_chat_message(uid, "assistant", ai_reply)

        msg_lower = user_message.lower()
        scan_words = [
            "signal", "buy", "sell", "strong",
            "best", "scan", "which", "recommend",
            "trade", "pair", "crypto", "forex",
            "gold", "stock", "coin"
        ]
        should_scan = any(w in msg_lower for w in scan_words)
        buttons = []

        if should_scan:
            if weekend and not any(w in msg_lower for w in [
                "crypto", "bitcoin", "btc", "eth", "coin", "solana"
            ]):
                ai_reply += (
                    "\n\n🚨 *Weekend Alert!*\n"
                    "Forex and stocks are CLOSED today!\n"
                    "Scanning crypto for you instead...\n"
                )
                scan_list = CRYPTO_PAIRS[:12]
            elif any(w in msg_lower for w in [
                "crypto", "bitcoin", "coin", "btc", "eth"
            ]):
                scan_list = CRYPTO_PAIRS[:10]
            elif any(w in msg_lower for w in [
                "otc", "weekend"
            ]):
                if weekend:
                    scan_list = CRYPTO_OTC_PAIRS[:10]
                else:
                    scan_list = FOREX_OTC_PAIRS[:10]
            elif any(w in msg_lower for w in [
                "stock", "share", "apple", "tesla"
            ]):
                scan_list = STOCK_PAIRS[:8]
            elif any(w in msg_lower for w in [
                "gold", "silver", "oil", "commodity"
            ]):
                scan_list = COMMODITY_PAIRS
            else:
                if weekend:
                    scan_list = CRYPTO_PAIRS[:10]
                else:
                    scan_list = FOREX_PAIRS[:6] + CRYPTO_PAIRS[:4]

            found = []
            for pair in scan_list[:12]:
                try:
                    tf = {"twelve": "5min", "binance": "5m"}
                    res = analyse(pair, tf)
                    if (res and
                            res.get("signal") != "HOLD" and
                            res.get("confidence", 0) >= 4):
                        found.append((
                            pair,
                            res["signal"],
                            res["confidence"]
                        ))
                except Exception as e:
                    logger.error(f"chat scan {pair}: {e}")

            if found:
                scan_text = "\n\n📡 *Strong Signals Found:*\n"
                for pair, sig, conf in found[:5]:
                    bar = "█" * conf + "░" * (5 - conf)
                    icon = "🟢" if sig == "BUY" else "🔴"
                    scan_text += f"{icon} *{pair}* `{bar}`\n"
                ai_reply += scan_text
                for pair, sig, conf in found[:3]:
                    buttons.append([InlineKeyboardButton(
                        f"📊 {pair[:20]} — {sig}",
                        callback_data=f"pair_{pair}"
                    )])
            else:
                ai_reply += (
                    "\n\n🔍 No strong signals right now. "
                    "Try again soon!"
                )

        buttons.append([
            InlineKeyboardButton(
                "🚀 Start Trading",
                callback_data="show_category"
            ),
            InlineKeyboardButton(
                "🔍 Scan All",
                callback_data="scan_all"
            ),
        ])
        buttons.append([InlineKeyboardButton(
            "🏠 Menu", callback_data="back_main"
        )])

        await thinking_msg.edit_text(
            ai_reply,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logger.error(f"AI chat error: {e}")
        await thinking_msg.edit_text(
            "🤖 I had trouble with that.\n\n"
            "Try asking again or use /start!\n\n"
            "Example: _'Which crypto has strong signal?'_",
            parse_mode="Markdown"
        )


async def cmd_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    try:
        user = update.effective_user
        db.add_user(user.id, user.username or user.first_name)
        session_name, session_flag = get_current_session()
        good = (
            "✅ Good trading time!"
            if is_good_trading_time()
            else "⚠️ Slow market hours"
        )
        weekend = is_weekend()
        weekend_msg = ""
        if weekend:
            weekend_msg = (
                "\n🚨 *TODAY IS WEEKEND*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "❌ Forex markets are CLOSED\n"
                "❌ Stock markets are CLOSED\n"
                "❌ Commodities mostly CLOSED\n"
                "✅ ONLY trade Crypto today!\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
            )
        await update.message.reply_text(
            f"👋 Welcome *{user.first_name}*!\n\n"
            f"🤖 *ApexSignal — AI Trading Agent*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 Session: {session_flag} *{session_name}*\n"
            f"⏰ Status: {good}\n"
            f"{weekend_msg}\n"
            f"Powered by:\n"
            f"  🧠 Google Gemini AI\n"
            f"  📡 Deriv OTC Data\n"
            f"  ⚡ Binance Real-time\n"
            f"  📰 Finnhub News\n\n"
            f"💬 *Just chat with me naturally!*\n"
            f"  _'Which crypto has strong buy?'_\n"
            f"  _'Best pair to trade now?'_\n"
            f"  _'Scan the market'_\n\n"
            f"Or use buttons below 👇",
            parse_mode="Markdown",
            reply_markup=main_menu_kb()
        )
    except Exception as e:
        logger.error(f"cmd_start error: {e}")


async def cmd_scan(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    weekend = is_weekend()
    msg = await update.message.reply_text(
        "🔍 *Scanning markets...*\nPlease wait ⏳",
        parse_mode="Markdown"
    )
    found = []
    if weekend:
        priority = CRYPTO_PAIRS[:10] + list(CRYPTO_OTC_PAIRS[:5])
    else:
        priority = (
            FOREX_PAIRS[:6] +
            CRYPTO_PAIRS[:6] +
            COMMODITY_PAIRS
        )
    for pair in priority:
        try:
            tf = {"twelve": "5min", "binance": "5m"}
            r = analyse(pair, tf)
            if (r and r.get("signal") != "HOLD"
                    and r.get("confidence", 0) >= 4):
                found.append((
                    pair, r["signal"], r["confidence"]
                ))
        except Exception as e:
            logger.error(f"scan {pair}: {e}")

    if not found:
        await msg.edit_text(
            "🔍 No strong signals found right now.\n"
            "Market is ranging. Try again soon!"
        )
        return

    weekend_note = (
        "\n✅ _Showing crypto only — weekend mode_\n"
        if weekend else ""
    )
    text = f"📡 *Strong Signals Found:*{weekend_note}\n\n"
    buttons = []
    for pair, sig, conf in found[:8]:
        bar = "█" * conf + "░" * (5 - conf)
        icon = "🟢" if sig == "BUY" else "🔴"
        text += f"{icon} *{pair}* `{bar}`\n"
        buttons.append([InlineKeyboardButton(
            f"📊 {pair[:20]} — {sig}",
            callback_data=f"pair_{pair}"
        )])
    buttons.append([InlineKeyboardButton(
        "🏠 Menu", callback_data="back_main"
    )])
    await msg.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def cmd_stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    uid = update.effective_user.id
    s = db.get_user_stats(uid)
    top = db.get_top_pairs(5)
    top_text = ""
    if top:
        top_text = "\n🏆 *Best Pairs:*\n"
        for p in top:
            top_text += (
                f"  • {p[0]}: `{p[1]:.1f}%` "
                f"({p[2]}W/{p[3]}L)\n"
            )
    total = s["wins"] + s["losses"]
    win_rate = (s["wins"] / total * 100) if total > 0 else 0
    await update.message.reply_text(
        f"📊 *Your Trading Stats*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Total Signals: `{s['total']}`\n"
        f"🟢 BUY:  `{s['calls']}`\n"
        f"🔴 SELL: `{s['puts']}`\n"
        f"⏸ HOLD: `{s['waits']}`\n\n"
        f"📈 *Trade Results:*\n"
        f"✅ Wins:    `{s['wins']}`\n"
        f"❌ Losses:  `{s['losses']}`\n"
        f"🎯 Win Rate: `{win_rate:.1f}%`\n"
        f"{top_text}",
        parse_mode="Markdown"
    )


async def cmd_unsubscribe(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    db.unsubscribe(update.effective_user.id)
    await update.message.reply_text(
        "🔕 Unsubscribed. Type /start to return."
    )


async def button_cb(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()
    d = query.data

    try:
        if d == "show_category":
            weekend = is_weekend()
            note = (
                "\n🚨 *Weekend: Only crypto is recommended!*"
                if weekend else ""
            )
            await query.edit_message_text(
                f"📂 *Select Market Category:*{note}",
                parse_mode="Markdown",
                reply_markup=category_kb()
            )

        elif d.startswith("cat_"):
            category = d[4:]
            labels = {
                "forex":             "💱 Forex Pairs",
                "forex_otc":         "💱 Forex OTC",
                "stocks":            "📈 Stock Pairs",
                "stocks_otc":        "📈 Stock OTC",
                "commodity":         "🥇 Commodities",
                "commodity_otc":     "🥇 Commodities OTC",
                "crypto":            "₿ Crypto Pairs",
                "crypto_otc":        "₿ Crypto OTC",
                "crypto_standalone": "🪙 Crypto Coins",
            }
            label = labels.get(category, "Select Pair")
            await query.edit_message_text(
                f"*{label}*\n\nSelect an asset:",
                parse_mode="Markdown",
                reply_markup=pairs_kb(category)
            )

        elif d.startswith("pair_"):
            pair = d[5:]
            await query.edit_message_text(
                f"⏱ *Select Timeframe for {pair}:*",
                parse_mode="Markdown",
                reply_markup=timeframe_kb(pair)
            )

        elif d.startswith("tf_"):
            parts = d.split("_", 3)
            if len(parts) < 4:
                await query.edit_message_text(
                    "❌ Error. Try /start"
                )
                return

            pair = parts[1]
            val_str = parts[2]
            label = parts[3]

            try:
                twelve_iv, binance_iv = val_str.split("|")
            except Exception:
                twelve_iv = "5min"
                binance_iv = "5m"

            await query.edit_message_text(
                f"⏳ *Analysing {pair}...*\n\n"
                f"🧠 AI processing...\n"
                f"📰 Fetching news...\n"
                f"Please wait...",
                parse_mode="Markdown"
            )

            try:
                tf_data = {
                    "twelve": twelve_iv,
                    "binance": binance_iv
                }
                r = analyse(pair, tf_data)
            except Exception as e:
                logger.error(f"analyse error {pair}: {e}")
                r = None

            if not r:
                await query.edit_message_text(
                    f"❌ Could not fetch data for *{pair}*.\n"
                    f"Try again in a moment.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            "🔄 Retry", callback_data=d
                        )],
                        [InlineKeyboardButton(
                            "⬅ Back",
                            callback_data="show_category"
                        )],
                    ])
                )
                return

            conf = r.get("confidence", 0)
            sig = r.get("signal", "HOLD")

            if conf < 3 and sig != "HOLD":
                await query.edit_message_text(
                    f"⚠️ *{pair}* signal is *{sig}* but "
                    f"confidence is LOW "
                    f"`{'█' * conf}{'░' * (5 - conf)}`\n\n"
                    f"❌ Not recommended for trading.\n"
                    f"Wait for a stronger setup!",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            "🔄 Check Again",
                            callback_data=d
                        )],
                        [InlineKeyboardButton(
                            "⬅ Back",
                            callback_data="show_category"
                        )],
                    ])
                )
                return

            session_name, _ = get_current_session()
            text = build_signal_msg(pair, label, r)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔄 Refresh", callback_data=d
                )],
                [
                    InlineKeyboardButton(
                        "✅ Log WIN",
                        callback_data=f"win_{pair}"
                    ),
                    InlineKeyboardButton(
                        "❌ Log LOSS",
                        callback_data=f"loss_{pair}"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "📂 Categories",
                        callback_data="show_category"
                    ),
                    InlineKeyboardButton(
                        "🏠 Menu", callback_data="back_main"
                    ),
                ],
            ])
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=kb
            )
            db.log_signal(
                query.from_user.id, pair, twelve_iv,
                sig, conf, r.get("price", 0), session_name
            )

        elif d.startswith("win_"):
            pair = d[4:]
            db.log_trade_result(
                query.from_user.id, pair, "BUY", "WIN"
            )
            await query.edit_message_text(
                f"✅ *WIN logged for {pair}!*\n\n"
                f"Great trade! 🎉\n"
                f"Check /stats to see your progress.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Menu", callback_data="back_main"
                    )
                ]])
            )

        elif d.startswith("loss_"):
            pair = d[5:]
            db.log_trade_result(
                query.from_user.id, pair, "SELL", "LOSS"
            )
            await query.edit_message_text(
                f"❌ *LOSS logged for {pair}*\n\n"
                f"Stay disciplined! 💪\n"
                f"Only trade HIGH confidence signals!\n"
                f"Check /stats to see your progress.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Menu", callback_data="back_main"
                    )
                ]])
            )

        elif d == "scan_all":
            await query.edit_message_text(
                "🔍 *Scanning markets...*\nPlease wait ⏳",
                parse_mode="Markdown"
            )
            weekend = is_weekend()
            found = []
            if weekend:
                priority = CRYPTO_PAIRS[:10] + list(CRYPTO_OTC_PAIRS[:5])
            else:
                priority = (
                    FOREX_PAIRS[:6] +
                    CRYPTO_PAIRS[:6] +
                    COMMODITY_PAIRS
                )
            for pair in priority:
                try:
                    tf = {"twelve": "5min", "binance": "5m"}
                    r = analyse(pair, tf)
                    if (r and r.get("signal") != "HOLD"
                            and r.get("confidence", 0) >= 4):
                        found.append((
                            pair, r["signal"], r["confidence"]
                        ))
                except Exception:
                    pass

            if not found:
                await query.edit_message_text(
                    "🔍 No strong signals right now.\n"
                    "Try again soon!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "🏠 Menu", callback_data="back_main"
                        )
                    ]])
                )
                return

            weekend_note = (
                "\n✅ _Weekend mode — crypto only_\n"
                if weekend else ""
            )
            text = f"📡 *Strong Signals:*{weekend_note}\n\n"
            buttons = []
            for pair, sig, conf in found[:8]:
                bar = "█" * conf + "░" * (5 - conf)
                icon = "🟢" if sig == "BUY" else "🔴"
                text += f"{icon} *{pair}* `{bar}`\n"
                buttons.append([InlineKeyboardButton(
                    f"📊 {pair[:20]} — {sig}",
                    callback_data=f"pair_{pair}"
                )])
            buttons.append([InlineKeyboardButton(
                "🏠 Menu", callback_data="back_main"
            )])
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        elif d == "top_pairs":
            top = db.get_top_pairs(10)
            if not top:
                text = (
                    "🏆 *Top Performing Pairs*\n\n"
                    "No data yet!\n"
                    "Use ✅WIN and ❌LOSS buttons "
                    "after each trade to build history."
                )
            else:
                text = "🏆 *Your Best Pairs:*\n\n"
                for i, p in enumerate(top, 1):
                    text += (
                        f"{i}. *{p[0]}* — "
                        f"`{p[1]:.1f}%` "
                        f"({p[2]}W/{p[3]}L)\n"
                    )
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Menu", callback_data="back_main"
                    )
                ]])
            )

        elif d == "sessions":
            session_name, flag = get_current_session()
            good = is_good_trading_time()
            weekend = is_weekend()
            weekend_note = (
                "\n🚨 *Weekend — Only trade crypto!*\n"
                if weekend else ""
            )
            await query.edit_message_text(
                f"🌍 *Market Sessions*\n\n"
                f"Current: {flag} *{session_name}*\n"
                f"Status: "
                f"{'✅ Good for trading!' if good else '⚠️ Slow market'}\n"
                f"{weekend_note}\n"
                f"*Session Times (UTC):*\n"
                f"🇯🇵 Tokyo:    22:00 — 07:00\n"
                f"🇬🇧 London:   07:00 — 16:00\n"
                f"🇺🇸 New York: 13:00 — 22:00\n\n"
                f"*Best Trading Times:*\n"
                f"⭐ London Open:    07:00-09:00\n"
                f"⭐ NY Open:        13:00-15:00\n"
                f"⭐ London/NY:      13:00-16:00\n\n"
                f"💡 _Trade during overlaps for best signals!_",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Menu", callback_data="back_main"
                    )
                ]])
            )

        elif d == "subscribe":
            db.subscribe(query.from_user.id)
            await query.edit_message_text(
                f"✅ *Auto-Signals Activated!*\n\n"
                f"You'll receive HIGH confidence signals "
                f"every *{SIGNAL_INTERVAL_MINUTES} minutes*.\n\n"
                f"Only confidence 4-5 signals sent.\n"
                f"Only during active market sessions.\n"
                f"Weekend: crypto signals only.\n\n"
                f"Use /unsubscribe to stop.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Main Menu", callback_data="back_main"
                    )
                ]])
            )

        elif d == "stats":
            uid = query.from_user.id
            s = db.get_user_stats(uid)
            top = db.get_top_pairs(3)
            top_text = ""
            if top:
                top_text = "\n🏆 *Best Pairs:*\n"
                for p in top:
                    top_text += f"  • {p[0]}: `{p[1]:.1f}%`\n"
            total = s["wins"] + s["losses"]
            win_rate = (
                (s["wins"] / total * 100) if total > 0 else 0
            )
            await query.edit_message_text(
                f"📊 *Your Trading Stats*\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Total Signals: `{s['total']}`\n"
                f"🟢 BUY:  `{s['calls']}`\n"
                f"🔴 SELL: `{s['puts']}`\n"
                f"⏸ HOLD: `{s['waits']}`\n\n"
                f"📈 *Trade Results:*\n"
                f"✅ Wins:    `{s['wins']}`\n"
                f"❌ Losses:  `{s['losses']}`\n"
                f"🎯 Win Rate: `{win_rate:.1f}%`\n"
                f"{top_text}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Main Menu", callback_data="back_main"
                    )
                ]])
            )

        elif d == "help":
            await query.edit_message_text(
                "❓ *How To Use ApexSignal AI*\n"
                "━━━━━━━━━━━━━━━\n\n"
                "📱 *Button Way:*\n"
                "1️⃣ Tap START TRADING\n"
                "2️⃣ Choose market category\n"
                "3️⃣ Select asset\n"
                "4️⃣ Select expiry time\n"
                "5️⃣ Get AI signal\n"
                "6️⃣ Place trade on broker\n"
                "7️⃣ Log WIN or LOSS\n\n"
                "💬 *Chat Way:*\n"
                "Just type naturally:\n"
                "  _'Best crypto to buy now?'_\n"
                "  _'Scan forex signals'_\n"
                "  _'What is gold doing?'_\n\n"
                "📊 *Commands:*\n"
                "/start — Main menu\n"
                "/scan — Scan all markets\n"
                "/stats — Your statistics\n"
                "/unsubscribe — Stop auto-signals\n\n"
                "🚨 *Weekend Rules:*\n"
                "  • Only trade CRYPTO on weekends\n"
                "  • Forex and stocks are CLOSED\n"
                "  • OTC forex data is unreliable\n\n"
                "💡 *Tips:*\n"
                "  • Only trade confidence 4-5\n"
                "  • Trade during London/NY sessions\n"
                "  • Always log your results!\n"
                "  • Check broker chart before trading!\n\n"
                "⚠️ _Trade at your own risk._",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Main Menu", callback_data="back_main"
                    )
                ]])
            )

        elif d == "back_main":
            session_name, flag = get_current_session()
            weekend = is_weekend()
            good = (
                "🚨 Weekend — crypto only!"
                if weekend
                else "✅ Good trading time!"
                if is_good_trading_time()
                else "⚠️ Slow market hours"
            )
            await query.edit_message_text(
                f"🤖 *ApexSignal AI — Main Menu*\n\n"
                f"{flag} Session: *{session_name}*\n"
                f"Status: {good}\n\n"
                f"💬 Chat with me or tap buttons! 👇",
                parse_mode="Markdown",
                reply_markup=main_menu_kb()
            )

    except Exception as e:
        logger.error(f"button_cb error: {e}")
        try:
            await query.edit_message_text(
                "❌ Error occurred. Type /start to restart."
            )
        except Exception:
            pass


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    try:
        if not update.message or not update.message.text:
            return
        user = update.effective_user
        if not user:
            return
        db.add_user(
            user.id, user.username or user.first_name
        )
        user_message = update.message.text.strip()
        if not user_message:
            return
        logger.info(
            f"Chat from {user.id}: {user_message[:50]}"
        )
        await handle_ai_chat(update, context, user_message)
    except Exception as e:
        logger.error(f"handle_message error: {e}")
        try:
            await update.message.reply_text(
                "Sorry, try again or use /start! 🤖"
            )
        except Exception:
            pass


async def broadcast(context: ContextTypes.DEFAULT_TYPE):
    try:
        subs = db.get_subscribers()
        if not subs:
            return

        session_name, session_flag = get_current_session()
        weekend = is_weekend()

        if weekend:
            priority = [
                "BTC/USD", "ETH/USD", "XRP/USD",
                "BNB/USD", "SOL/USD", "ADA/USD",
                "BTC/USD OTC", "ETH/USD OTC",
            ]
        else:
            if not is_good_trading_time():
                logger.info("Skipping broadcast — slow market hours")
                return
            priority = [
                "EUR/USD", "GBP/USD", "USD/JPY",
                "BTC/USD", "ETH/USD", "XRP/USD",
                "EUR/USD OTC", "GBP/USD OTC",
                "Gold", "AUD/USD",
            ]

        best_pair, best_r, best_s = None, None, 0

        for pair in priority:
            try:
                tf = {"twelve": "5min", "binance": "5m"}
                r = analyse(pair, tf)
                if (r and
                        r.get("signal") != "HOLD" and
                        r.get("confidence", 0) >= 3 and
                        r.get("confidence", 0) > best_s):
                    best_s = r["confidence"]
                    best_pair = pair
                    best_r = r
            except Exception as e:
                logger.error(f"broadcast scan {pair}: {e}")

        if not best_pair or not best_r:
            logger.info("No signals found for broadcast")
            return

        weekend_note = (
            "\n✅ _Weekend crypto signal — reliable!_\n"
            if weekend else ""
        )
        msg = (
            f"🚨 *AUTO-SIGNAL ALERT*\n"
            f"{session_flag} Session: *{session_name}*"
            f"{weekend_note}\n" +
            build_signal_msg(best_pair, "5 min", best_r)
        )

        sent = 0
        for uid in subs:
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=msg,
                    parse_mode="Markdown"
                )
                sent += 1
            except Exception as e:
                logger.warning(f"Broadcast fail {uid}: {e}")

        logger.info(
            f"Broadcast sent to {sent} users — "
            f"{best_pair} {best_r.get('signal')}"
        )

    except Exception as e:
        logger.error(f"broadcast error: {e}")


def main():
    token = BOT_TOKEN
    if not token:
        logger.error("BOT_TOKEN not set!")
        return

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("scan", cmd_scan))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
    app.add_handler(CallbackQueryHandler(button_cb))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    app.job_queue.run_repeating(
        broadcast,
        interval=SIGNAL_INTERVAL_MINUTES * 60,
        first=10
    )
    logger.info("ApexSignal AI Bot started!")
    print("✅ ApexSignal AI Bot is running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
