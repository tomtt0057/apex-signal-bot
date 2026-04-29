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

# ─────────────────────────────────────────
# SIGNAL MESSAGE BUILDER
# ─────────────────────────────────────────

def signal_emoji(s):
    return {
        "BUY":  "🟢 BUY",
        "SELL": "🔴 SELL",
        "HOLD": "⏸ HOLD"
    }.get(s, s)

def build_signal_msg(pair, tf_label, r):
    try:
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
            perf_text = f"  Win Rate: `{perf[0]:.1f}%` ({perf[2]}W/{perf[3]}L)\n"

        return (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *{pair}* — `{tf_label}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
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

# ─────────────────────────────────────────
# KEYBOARDS
# ─────────────────────────────────────────

def main_menu_kb():
    session_name, session_flag = get_current_session()
    good = "✅ Good time" if is_good_trading_time() else "⚠️ Slow market"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🚀  S T A R T  T R A D I N G",
            callback_data="show_category"
        )],
        [
            InlineKeyboardButton(
                "🔔 Auto-Signals", callback_data="subscribe"
            ),
            InlineKeyboardButton(
                "📊 My Stats", callback_data="stats"
            ),
        ],
        [
            InlineKeyboardButton(
                "🏆 Top Pairs", callback_data="top_pairs"
            ),
            InlineKeyboardButton(
                "🌍 Sessions", callback_data="sessions"
            ),
        ],
        [InlineKeyboardButton("❓ Help", callback_data="help")],
    ])

def category_kb():
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
                "🥇 Commodities OTC", callback_data="cat_commodity_otc"
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
            "🪙 Crypto Coins", callback_data="cat_crypto_standalone"
        )],
        [InlineKeyboardButton("⬅ Back", callback_data="back_main")],
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

def result_kb(original_callback):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ WIN", callback_data=f"result_WIN_{original_callback}"
            ),
            InlineKeyboardButton(
                "❌ LOSS", callback_data=f"result_LOSS_{original_callback}"
            ),
        ],
        [InlineKeyboardButton(
            "⏭ Skip", callback_data="back_main"
        )],
    ])

# ─────────────────────────────────────────
# AI CHAT HANDLER
# ─────────────────────────────────────────

async def handle_ai_chat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_message: str
):
    """Handle plain English chat using Gemini AI"""
    user = update.effective_user
    uid  = user.id

    db.save_chat_message(uid, "user", user_message)
    history = db.get_chat_history(uid, limit=6)

    thinking_msg = await update.message.reply_text(
        "🤔 Thinking...", parse_mode="Markdown"
    )

    try:
        session_name, session_flag = get_current_session()
        good_time = is_good_trading_time()
        top_pairs = db.get_top_pairs(3)
        top_pairs_text = ""
        if top_pairs:
            top_pairs_text = "Best performing pairs from history:\n"
            for p in top_pairs:
                top_pairs_text += f"- {p[0]}: {p[1]:.1f}% win rate\n"

        system_prompt = f"""You are ApexSignal, a professional AI binary options trading assistant.

Current Market Info:
- Session: {session_name} {session_flag}
- Good trading time: {'Yes' if good_time else 'No'}
{top_pairs_text}

Available assets: Forex, Forex OTC, Stocks, Crypto, Crypto OTC, Commodities, Crypto Coins

You can help users:
1. Find strong buy/sell signals for specific pairs
2. Explain market conditions
3. Recommend best pairs to trade right now
4. Answer trading questions
5. Explain what indicators mean
6. Warn about risky market conditions

When user asks for signals, respond with a clear recommendation.
When user asks about a specific pair, scan it and give analysis.
Always be professional, concise and helpful.
Never give financial advice — only signal analysis.
Keep responses short and clear — max 150 words.
Use emojis to make responses engaging."""

        history_text = ""
        for role, msg in history[-4:]:
            prefix = "User" if role == "user" else "Assistant"
            history_text += f"{prefix}: {msg}\n"

        full_prompt = (
            f"{system_prompt}\n\n"
            f"Conversation history:\n{history_text}\n"
            f"User: {user_message}\n"
            f"Assistant:"
        )

        url = (
            f"https://generativelanguage.googleapis.com/v1beta"
            f"/models/gemini-1.5-flash:generateContent"
            f"?key={GEMINI_API_KEY}"
        )
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 300,
            }
        }

        r = httpx.post(url, json=payload, timeout=15)
        data = r.json()
        ai_reply = (
            data["candidates"][0]["content"]["parts"][0]["text"]
        )

        db.save_chat_message(uid, "assistant", ai_reply)

        msg_lower = user_message.lower()
        scan_keywords = [
            "signal", "signals", "buy", "sell",
            "strong", "best", "scan", "which",
            "what pair", "recommend", "trade now"
        ]
        should_scan = any(kw in msg_lower for kw in scan_keywords)

        buttons = []

        if should_scan:
            if any(w in msg_lower for w in [
                "crypto", "bitcoin", "ethereum", "coin", "btc", "eth"
            ]):
                scan_pairs = CRYPTO_PAIRS[:8]
            elif any(w in msg_lower for w in [
                "forex", "eur", "gbp", "usd", "currency"
            ]):
                scan_pairs = FOREX_PAIRS[:8]
            elif any(w in msg_lower for w in [
                "otc", "weekend"
            ]):
                scan_pairs = FOREX_OTC_PAIRS[:8]
            elif any(w in msg_lower for w in [
                "stock", "apple", "tesla", "shares"
            ]):
                scan_pairs = STOCK_PAIRS[:8]
            elif any(w in msg_lower for w in [
                "gold", "silver", "oil", "commodity"
            ]):
                scan_pairs = COMMODITY_PAIRS
            else:
                scan_pairs = (
                    FOREX_PAIRS[:4] +
                    CRYPTO_PAIRS[:4]
                )

            strong_signals = []
            for pair in scan_pairs[:10]:
                try:
                    tf = {"twelve": "5min", "binance": "5m"}
                    result = analyse(pair, tf)
                    if (result and
                            result.get("signal") != "HOLD" and
                            result.get("confidence", 0) >= 4):
                        strong_signals.append((
                            pair,
                            result["signal"],
                            result["confidence"],
                            result
                        ))
                except Exception as e:
                    logger.error(f"scan error {pair}: {e}")

            if strong_signals:
                signals_text = "\n\n📡 *Strong Signals Found:*\n"
                for pair, sig, conf, _ in strong_signals[:5]:
                    bar = "█" * conf + "░" * (5 - conf)
                    icon = "🟢" if sig == "BUY" else "🔴"
                    signals_text += (
                        f"{icon} *{pair}* — {sig} "
                        f"`{bar}`\n"
                    )
                ai_reply += signals_text

                for pair, sig, conf, _ in strong_signals[:3]:
                    short = pair[:20]
                    buttons.append([InlineKeyboardButton(
                        f"📊 {short} — {sig}",
                        callback_data=f"pair_{pair}"
                    )])

        buttons.append([
            InlineKeyboardButton(
                "🚀 Start Trading", callback_data="show_category"
            ),
            InlineKeyboardButton(
                "🏠 Menu", callback_data="back_main"
            ),
        ])

        await thinking_msg.edit_text(
            ai_reply,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logger.error(f"AI chat error: {e}")
        await thinking_msg.edit_text(
            "Sorry, I had trouble processing that. "
            "Try /start for the normal menu or ask me again! 🤖"
        )

# ─────────────────────────────────────────
# COMMAND HANDLERS
# ─────────────────────────────────────────

async def cmd_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    try:
        user = update.effective_user
        db.add_user(user.id, user.username or user.first_name)
        session_name, session_flag = get_current_session()
        good = "✅ Good trading time!" if is_good_trading_time() else "⚠️ Slow market hours"

        await update.message.reply_text(
            f"👋 Welcome *{user.first_name}*!\n\n"
            f"🤖 *ApexSignal — AI Trading Agent*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 Session: {session_flag} *{session_name}*\n"
            f"⏰ Status: {good}\n\n"
            f"Powered by:\n"
            f"  🧠 Google Gemini AI\n"
            f"  📡 Deriv OTC Data\n"
            f"  ⚡ Binance Real-time\n"
            f"  📰 Finnhub News\n\n"
            f"💬 *You can also chat with me naturally!*\n"
            f"Just type something like:\n"
            f"  _\"Which crypto has strong buy signal?\"_\n"
            f"  _\"Best forex pair to trade now?\"_\n"
            f"  _\"What is gold doing?\"_\n\n"
            f"Or use buttons below 👇",
            parse_mode="Markdown",
            reply_markup=main_menu_kb()
        )
    except Exception as e:
        logger.error(f"cmd_start error: {e}")

async def cmd_result(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """Allow user to log trade result"""
    await update.message.reply_text(
        "📝 *Log Your Trade Result*\n\n"
        "Which pair did you trade?",
        parse_mode="Markdown"
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
        top_text = "\n🏆 *Your Best Pairs:*\n"
        for p in top:
            top_text += (
                f"  • {p[0]}: `{p[1]:.1f}%` "
                f"({p[2]}W/{p[3]}L)\n"
            )

    total_trades = s["wins"] + s["losses"]
    win_rate = (
        (s["wins"] / total_trades * 100)
        if total_trades > 0 else 0
    )

    await update.message.reply_text(
        f"📊 *Your Trading Stats*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Total Signals: `{s['total']}`\n"
        f"🟢 BUY:  `{s['calls']}`\n"
        f"🔴 SELL: `{s['puts']}`\n"
        f"⏸ HOLD: `{s['waits']}`\n\n"
        f"📈 *Trade Results:*\n"
        f"✅ Wins:   `{s['wins']}`\n"
        f"❌ Losses: `{s['losses']}`\n"
        f"🎯 Win Rate: `{win_rate:.1f}%`\n"
        f"{top_text}",
        parse_mode="Markdown"
    )

async def cmd_scan(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """Scan all pairs and return top signals"""
    msg = await update.message.reply_text(
        "🔍 *Scanning all markets...*\n"
        "Please wait ⏳",
        parse_mode="Markdown"
    )
    strong = []
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
                strong.append((
                    pair,
                    r["signal"],
                    r["confidence"]
                ))
        except Exception as e:
            logger.error(f"scan {pair}: {e}")

    if not strong:
        await msg.edit_text(
            "🔍 No strong signals found right now.\n"
            "Market may be ranging. Try again soon!"
        )
        return

    text = "📡 *Strong Signals Found:*\n\n"
    buttons = []
    for pair, sig, conf in strong[:8]:
        bar  = "█" * conf + "░" * (5 - conf)
        icon = "🟢" if sig == "BUY" else "🔴"
        text += f"{icon} *{pair}* — {sig} `{bar}`\n"
        short = pair[:20]
        buttons.append([InlineKeyboardButton(
            f"📊 {short}",
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

async def cmd_unsubscribe(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    db.unsubscribe(update.effective_user.id)
    await update.message.reply_text(
        "🔕 Unsubscribed from auto-signals.\n"
        "Type /start to return to menu."
    )

# ─────────────────────────────────────────
# BUTTON CALLBACK HANDLER
# ─────────────────────────────────────────

async def button_cb(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()
    d = query.data

    try:
        if d == "show_category":
            await query.edit_message_text(
                "📂 *Select Market Category:*",
                parse_mode="Markdown",
                reply_markup=category_kb()
            )

        elif d.startswith("cat_"):
            category = d[4:]
            labels = {
                "forex":             "💱 Forex Pairs",
                "forex_otc":         "💱 Forex OTC Pairs",
                "stocks":            "📈 Stock Pairs",
                "stocks_otc":        "📈 Stock OTC Pairs",
                "commodity":         "🥇 Commodity Pairs",
                "commodity_otc":     "🥇 Commodity OTC",
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
                await query.edit_message_text("❌ Error. Try /start")
                return

            pair    = parts[1]
            val_str = parts[2]
            label   = parts[3]

            try:
                twelve_iv, binance_iv = val_str.split("|")
            except:
                twelve_iv  = "5min"
                binance_iv = "5m"

            conf_filter = int(
                context.user_data.get("min_confidence", 3)
            )

            await query.edit_message_text(
                f"⏳ *Analysing {pair}...*\n\n"
                f"🧠 AI processing...\n"
                f"📰 Fetching news...\n"
                f"Please wait...",
                parse_mode="Markdown"
            )

            try:
                tf_data = {
                    "twelve":  twelve_iv,
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
            sig  = r.get("signal", "HOLD")

            if conf < conf_filter and sig != "HOLD":
                await query.edit_message_text(
                    f"⚠️ *{pair}* signal is *{sig}* but confidence "
                    f"is LOW `({'█'*conf}{'░'*(5-conf)})`\n\n"
                    f"Not recommended for trading.\n"
                    f"Wait for a stronger setup!",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            "🔄 Check Again", callback_data=d
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
            uid  = query.from_user.id
            db.log_trade_result(uid, pair, "BUY", "WIN")
            await query.edit_message_text(
                f"✅ *WIN logged for {pair}!*\n\n"
                f"Great trade! Keep it up! 🎉\n"
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
            uid  = query.from_user.id
            db.log_trade_result(uid, pair, "SELL", "LOSS")
            await query.edit_message_text(
                f"❌ *LOSS logged for {pair}*\n\n"
                f"Don't worry — losses are part of trading.\n"
                f"Only trade HIGH confidence signals!\n"
                f"Check /stats to see your progress.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Menu", callback_data="back_main"
                    )
                ]])
            )

        elif d == "top_pairs":
            top = db.get_top_pairs(10)
            if not top:
                text = (
                    "🏆 *Top Performing Pairs*\n\n"
                    "No data yet — start trading to build history!\n"
                    "Use ✅WIN and ❌LOSS buttons after each trade."
                )
            else:
                text = "🏆 *Your Best Performing Pairs:*\n\n"
                for i, p in enumerate(top, 1):
                    text += (
                        f"{i}. *{p[0]}* — "
                        f"`{p[1]:.1f}%` win rate "
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
            await query.edit_message_text(
                f"🌍 *Market Sessions*\n\n"
                f"Current: {flag} *{session_name}*\n"
                f"Status: {'✅ Good for trading!' if good else '⚠️ Slow market hours'}\n\n"
                f"*Session Times (UTC):*\n"
                f"🇯🇵 Tokyo:    22:00 — 07:00\n"
                f"🇬🇧 London:   07:00 — 16:00\n"
                f"🇺🇸 New York: 13:00 — 22:00\n\n"
                f"*Best Trading Times:*\n"
                f"⭐ London Open: 07:00-09:00\n"
                f"⭐ NY Open:     13:00-15:00\n"
                f"⭐ Overlap:     13:00-16:00\n\n"
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
                f"You'll receive HIGH confidence signals every "
                f"*{SIGNAL_INTERVAL_MINUTES} minutes*.\n\n"
                f"Only signals with 4-5 confidence will be sent.\n\n"
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
            s   = db.get_user_stats(uid)
            top = db.get_top_pairs(3)
            top_text = ""
            if top:
                top_text = "\n🏆 *Best Pairs:*\n"
                for p in top:
                    top_text += (
                        f"  • {p[0]}: `{p[1]:.1f}%`\n"
                    )
            total_trades = s["wins"] + s["losses"]
            win_rate = (
                (s["wins"] / total_trades * 100)
                if total_trades > 0 else 0
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
                "📱 *Normal Way:*\n"
                "1️⃣ Tap START TRADING\n"
                "2️⃣ Choose market category\n"
                "3️⃣ Select asset\n"
                "4️⃣ Select expiry time\n"
                "5️⃣ Get AI signal\n"
                "6️⃣ Place trade on broker\n"
                "7️⃣ Log WIN or LOSS\n\n"
                "💬 *Chat Way (Natural Language):*\n"
                "Just type anything like:\n"
                "  _\"Best crypto to buy now?\"_\n"
                "  _\"Scan forex signals\"_\n"
                "  _\"What is EUR/USD doing?\"_\n\n"
                "📊 *Commands:*\n"
                "/start — Main menu\n"
                "/scan — Scan all markets\n"
                "/stats — Your statistics\n"
                "/unsubscribe — Stop auto-signals\n\n"
                "💡 *Tips:*\n"
                "  • Only trade confidence 4-5\n"
                "  • Trade during London/NY sessions\n"
                "  • Always log your results!\n\n"
                "⚠️ _Binary options involve risk._",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Main Menu", callback_data="back_main"
                    )
                ]])
            )

        elif d == "back_main":
            session_name, flag = get_current_session()
            good = (
                "✅ Good trading time!"
                if is_good_trading_time()
                else "⚠️ Slow market hours"
            )
            await query.edit_message_text(
                f"🤖 *ApexSignal AI — Main Menu*\n\n"
                f"{flag} Session: *{session_name}* — {good}\n\n"
                f"Tap *START TRADING* or just chat with me! 👇",
                parse_mode="Markdown",
                reply_markup=main_menu_kb()
            )

    except Exception as e:
        logger.error(f"button_cb error: {e}")
        try:
            await query.edit_message_text(
                "❌ Error occurred. Type /start to restart."
            )
        except:
            pass

# ─────────────────────────────────────────
# MESSAGE HANDLER (Plain English Chat)
# ─────────────────────────────────────────

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """Handle all non-command text messages as AI chat"""
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    db.add_user(user.id, user.username or user.first_name)
    user_message = update.message.text.strip()

    await handle_ai_chat(update, context, user_message)

# ─────────────────────────────────────────
# AUTO BROADCAST
# ─────────────────────────────────────────

async def broadcast(context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_good_trading_time():
            logger.info("Skipping broadcast — slow market hours")
            return

        subs = db.get_subscribers()
        if not subs:
            return

        session_name, _ = get_current_session()
        best_pair, best_r, best_s = None, None, 0

        priority = [
            "EUR/USD", "GBP/USD", "BTC/USD",
            "ETH/USD", "Gold", "XRP/USD",
            "EUR/USD OTC", "GBP/USD OTC"
        ]

        for pair in priority:
            try:
                tf = {"twelve": "5min", "binance": "5m"}
                r  = analyse(pair, tf)
                if (r and
                        r.get("signal") != "HOLD" and
                        r.get("confidence", 0) >= 4 and
                        r.get("confidence", 0) > best_s):
                    best_s    = r["confidence"]
                    best_pair = pair
                    best_r    = r
            except Exception as e:
                logger.error(f"broadcast scan {pair}: {e}")

        if not best_pair or not best_r:
            logger.info("No strong signals for broadcast")
            return

        msg = (
            f"🚨 *AUTO-SIGNAL ALERT*\n"
            f"🌍 Session: *{session_name}*\n" +
            build_signal_msg(best_pair, "5 min", best_r)
        )

        for uid in subs:
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=msg,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Broadcast fail {uid}: {e}")

    except Exception as e:
        logger.error(f"broadcast error: {e}")

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main():
    token = BOT_TOKEN
    if not token:
        logger.error("BOT_TOKEN not set!")
        return

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("scan",        cmd_scan))
    app.add_handler(CommandHandler("stats",       cmd_stats))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
    app.add_handler(CallbackQueryHandler(button_cb))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))

    app.job_queue.run_repeating(
        broadcast,
        interval=SIGNAL_INTERVAL_MINUTES * 60,
        first=60
    )

    logger.info("ApexSignal AI Bot started!")
    print("✅ ApexSignal AI Bot is running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
