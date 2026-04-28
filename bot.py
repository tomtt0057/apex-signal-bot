import logging
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler,
    CallbackQueryHandler, ContextTypes
)
from config import (
    BOT_TOKEN, SIGNAL_INTERVAL_MINUTES,
    FOREX_PAIRS, FOREX_OTC_PAIRS,
    STOCK_PAIRS, STOCK_OTC_PAIRS,
    COMMODITY_PAIRS, COMMODITY_OTC_PAIRS,
    CRYPTO_PAIRS, CRYPTO_OTC_PAIRS,
    CRYPTO_STANDALONE, TIMEFRAMES
)
from database import Database
from signals import analyse

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()

def signal_emoji(s):
    return {"BUY": "🟢 BUY", "SELL": "🔴 SELL", "HOLD": "⏸ HOLD"}.get(s, s)

def build_signal_msg(pair, tf_label, r):
    try:
        reasons_text = "\n".join(
            f"  • {reason}" for reason in r.get("reasons", []) if reason
        )
        news_text = ""
        if r.get("news_headlines"):
            news_text = "\n📰 *Latest News:*\n"
            for h in r["news_headlines"][:2]:
                short = str(h)[:60]
                news_text += f"  • {short}\n"

        ai_section = ""
        if r.get("ai_summary"):
            ai_section = (
                f"\n🤖 *AI Verdict:*\n"
                f"  {r['ai_summary']}\n"
                f"  Risk: `{r.get('ai_risk', 'Medium')}`\n"
            )

        indicators = r.get("indicators", {})
        return (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *{pair}* — `{tf_label}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Signal:      *{signal_emoji(r.get('signal', 'HOLD'))}*\n"
            f"Confidence:  `{r.get('conf_bar', '░░░░░')}` "
            f"{r.get('conf_text', 'Low')}\n"
            f"Entry Price: `{r.get('price', 0)}`\n"
            f"News Mood:   `{r.get('news_sentiment', 'Neutral')}`\n\n"
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
        return f"Signal received for {pair}. Please try again."

def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🚀  S T A R T  T R A D I N G",
            callback_data="show_category"
        )],
        [
            InlineKeyboardButton(
                "🔔 Auto-Signals ON",
                callback_data="subscribe"
            ),
            InlineKeyboardButton(
                "📊 My Stats",
                callback_data="stats"
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
    pairs_map = {
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
    pairs = pairs_map.get(category, [])
    rows = []
    row = []
    for i, pair in enumerate(pairs):
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
        safe_pair = pair[:30]
        rows.append([InlineKeyboardButton(
            label.strip(),
            callback_data=f"tf_{safe_pair}_{val_str}_{label.strip()}"
        )])
    rows.append([InlineKeyboardButton(
        "⬅ Back", callback_data="show_category"
    )])
    return InlineKeyboardMarkup(rows)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        db.add_user(user.id, user.username or user.first_name)
        await update.message.reply_text(
            f"👋 Welcome *{user.first_name}*!\n\n"
            f"🤖 *ApexSignal — AI Trading Bot*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Powered by:\n"
            f"  🧠 Google Gemini AI\n"
            f"  📡 Deriv OTC Data\n"
            f"  ⚡ Binance Real-time\n"
            f"  📰 Finnhub News\n\n"
            f"Assets available:\n"
            f"  💱 Forex & Forex OTC\n"
            f"  📈 Stocks & Stocks OTC\n"
            f"  🥇 Commodities & OTC\n"
            f"  ₿ Crypto & Crypto OTC\n"
            f"  🪙 Crypto Coins\n\n"
            f"Tap *START TRADING* below 👇",
            parse_mode="Markdown",
            reply_markup=main_menu_kb()
        )
    except Exception as e:
        logger.error(f"cmd_start error: {e}")

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
                "commodity_otc":     "🥇 Commodity OTC Pairs",
                "crypto":            "₿ Crypto Pairs",
                "crypto_otc":        "₿ Crypto OTC Pairs",
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
                f"⏱ *Select Timeframe for {pair}:*\n\n"
                f"Choose your expiry time:",
                parse_mode="Markdown",
                reply_markup=timeframe_kb(pair)
            )

        elif d.startswith("tf_"):
            parts = d.split("_", 3)
            if len(parts) < 4:
                await query.edit_message_text(
                    "❌ Error. Please try again.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "⬅ Back",
                            callback_data="show_category"
                        )
                    ]])
                )
                return

            pair    = parts[1]
            val_str = parts[2]
            label   = parts[3]

            try:
                twelve_iv, binance_iv = val_str.split("|")
            except:
                twelve_iv  = "5min"
                binance_iv = "5m"

            tf_data = {"twelve": twelve_iv, "binance": binance_iv}

            await query.edit_message_text(
                f"⏳ *Analysing {pair}...*\n\n"
                f"🧠 AI is processing market data...\n"
                f"📰 Fetching latest news...\n"
                f"Please wait...",
                parse_mode="Markdown"
            )

            try:
                r = analyse(pair, tf_data)
            except Exception as e:
                logger.error(f"analyse error for {pair}: {e}")
                r = None

            if not r:
                await query.edit_message_text(
                    f"❌ Could not fetch data for *{pair}*.\n"
                    f"Please try again in a moment.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            "🔄 Retry", callback_data=d
                        )],
                        [InlineKeyboardButton(
                            "⬅ Back", callback_data="show_category"
                        )],
                    ])
                )
                return

            text = build_signal_msg(pair, label, r)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔄 Refresh Signal", callback_data=d
                )],
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
                text, parse_mode="Markdown", reply_markup=kb
            )
            db.log_signal(
                query.from_user.id, pair,
                twelve_iv, r.get("signal", "HOLD")
            )

        elif d == "subscribe":
            db.subscribe(query.from_user.id)
            await query.edit_message_text(
                f"✅ *Auto-Signals Activated!*\n\n"
                f"You'll receive AI-powered signals every "
                f"*{SIGNAL_INTERVAL_MINUTES} minutes*.\n\n"
                f"Use /unsubscribe to stop.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Main Menu", callback_data="back_main"
                    )
                ]])
            )

        elif d == "stats":
            s = db.get_user_stats(query.from_user.id)
            await query.edit_message_text(
                f"📊 *Your Trading Stats*\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Total Signals: `{s['total']}`\n"
                f"🟢 BUY:  `{s['calls']}`\n"
                f"🔴 SELL: `{s['puts']}`\n"
                f"⏸ HOLD: `{s['waits']}`",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Main Menu", callback_data="back_main"
                    )
                ]])
            )

        elif d == "help":
            await query.edit_message_text(
                "❓ *How To Use ApexSignal AI Bot*\n"
                "━━━━━━━━━━━━━━━\n"
                "1️⃣ Tap *START TRADING*\n"
                "2️⃣ Choose your *market category*\n"
                "3️⃣ Select your *asset*\n"
                "4️⃣ Select your *expiry time*\n"
                "5️⃣ Wait for *AI analysis*\n"
                "6️⃣ Get *BUY/SELL/HOLD* signal\n"
                "7️⃣ Place trade on your broker\n\n"
                "💡 *Tips:*\n"
                "  • Only trade HIGH confidence signals\n"
                "  • Check news sentiment before trading\n"
                "  • Always test on demo first!\n\n"
                "🔔 Use *Auto-Signals* to get alerts\n"
                "every 5 minutes automatically!\n\n"
                "⚠️ _Binary options involve financial risk._",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Main Menu", callback_data="back_main"
                    )
                ]])
            )

        elif d == "back_main":
            await query.edit_message_text(
                "🤖 *ApexSignal AI — Main Menu*\n\n"
                "Tap *START TRADING* to begin 👇",
                parse_mode="Markdown",
                reply_markup=main_menu_kb()
            )

    except Exception as e:
        logger.error(f"button_cb error: {e}")
        try:
            await query.edit_message_text(
                "❌ An error occurred. Please type /start to restart.",
            )
        except:
            pass

async def cmd_unsubscribe(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    db.unsubscribe(update.effective_user.id)
    await update.message.reply_text(
        "🔕 Unsubscribed from auto-signals.\n"
        "Type /start to return to menu."
    )

async def broadcast(context: ContextTypes.DEFAULT_TYPE):
    try:
        subs = db.get_subscribers()
        if not subs:
            return
        best_pair, best_r, best_s = None, None, 0
        priority = [
            "EUR/USD", "GBP/USD", "BTC/USD",
            "ETH/USD", "Gold", "XRP/USD"
        ]
        for pair in priority:
            try:
                tf = {"twelve": "5min", "binance": "5m"}
                r = analyse(pair, tf)
                if (r and r.get("signal") != "HOLD"
                        and r.get("confidence", 0) > best_s):
                    best_s = r["confidence"]
                    best_pair = pair
                    best_r = r
            except Exception as e:
                logger.error(f"broadcast scan error {pair}: {e}")

        if not best_pair or not best_r:
            return

        msg = (
            "🚨 *AUTO-SIGNAL ALERT*\n" +
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
                logger.warning(f"Could not send to {uid}: {e}")
    except Exception as e:
        logger.error(f"broadcast error: {e}")

def main():
    token = BOT_TOKEN
    if not token:
        logger.error("BOT_TOKEN is not set!")
        return

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
    app.add_handler(CallbackQueryHandler(button_cb))
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
