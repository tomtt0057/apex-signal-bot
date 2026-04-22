import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import (BOT_TOKEN, SIGNAL_INTERVAL_MINUTES,
    FOREX_PAIRS, FOREX_OTC_PAIRS,
    STOCK_PAIRS, STOCK_OTC_PAIRS,
    COMMODITY_PAIRS, COMMODITY_OTC_PAIRS,
    CRYPTO_PAIRS, CRYPTO_OTC_PAIRS,
    CRYPTO_STANDALONE, TIMEFRAMES)
from database import Database
from signals import analyse

logging.basicConfig(level=logging.INFO)
db = Database()

def signal_emoji(s):
    return {"BUY":"🟢 BUY","SELL":"🔴 SELL","HOLD":"⏸ HOLD"}.get(s, s)

def build_signal_msg(pair, tf_label, r):
    reasons_text = "\n".join(f"  • {reason}" for reason in r["reasons"])
    return (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *{pair}* — `{tf_label}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Signal:      *{signal_emoji(r['signal'])}*\n"
        f"Confidence:  `{r['conf_bar']}` {r['conf_text']}\n"
        f"Entry Price: `{r['price']}`\n\n"
        f"🧠 *Market Analysis:*\n"
        f"{reasons_text}\n\n"
        f"📊 *Indicators*\n"
        f"  RSI:       `{r['indicators']['rsi']}`\n"
        f"  MACD:      `{r['indicators']['macd']}`\n"
        f"  Bollinger: `{r['indicators']['bb']}`\n"
        f"  Stoch:     `{r['indicators']['stoch']}`\n"
        f"  Trend:     `{r['indicators']['ema_trend']}`\n\n"
        f"🕐 Time: `{datetime.utcnow().strftime('%H:%M UTC')}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ _Trade at your own risk._"
    )

def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀  S T A R T  T R A D I N G", callback_data="show_category")],
        [InlineKeyboardButton("🔔 Auto-Signals ON", callback_data="subscribe"),
         InlineKeyboardButton("📊 My Stats", callback_data="stats")],
        [InlineKeyboardButton("❓ Help", callback_data="help")],
    ])

def category_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💱 Forex", callback_data="cat_forex"),
         InlineKeyboardButton("💱 Forex OTC", callback_data="cat_forex_otc")],
        [InlineKeyboardButton("📈 Stocks", callback_data="cat_stocks"),
         InlineKeyboardButton("📈 Stocks OTC", callback_data="cat_stocks_otc")],
        [InlineKeyboardButton("🥇 Commodities", callback_data="cat_commodity"),
         InlineKeyboardButton("🥇 Commodities OTC", callback_data="cat_commodity_otc")],
        [InlineKeyboardButton("₿ Crypto", callback_data="cat_crypto"),
         InlineKeyboardButton("₿ Crypto OTC", callback_data="cat_crypto_otc")],
        [InlineKeyboardButton("🪙 Crypto Coins", callback_data="cat_crypto_standalone")],
        [InlineKeyboardButton("⬅ Back", callback_data="back_main")],
    ])

def pairs_kb(category):
    pairs_map = {
        "forex": FOREX_PAIRS,
        "forex_otc": FOREX_OTC_PAIRS,
        "stocks": STOCK_PAIRS,
        "stocks_otc": STOCK_OTC_PAIRS,
        "commodity": COMMODITY_PAIRS,
        "commodity_otc": COMMODITY_OTC_PAIRS,
        "crypto": CRYPTO_PAIRS,
        "crypto_otc": CRYPTO_OTC_PAIRS,
        "crypto_standalone": CRYPTO_STANDALONE,
    }
    pairs = pairs_map.get(category, [])
    rows = []
    row = []
    for i, pair in enumerate(pairs):
        row.append(InlineKeyboardButton(pair, callback_data=f"pair_{pair}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="show_category")])
    return InlineKeyboardMarkup(rows)

def timeframe_kb(pair):
    rows = []
    for label, val in TIMEFRAMES.items():
        val_str = f"{val['twelve']}|{val['binance']}"
        rows.append([InlineKeyboardButton(
            label,
            callback_data=f"tf_{pair}_{val_str}_{label}"
        )])
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="show_category")])
    return InlineKeyboardMarkup(rows)

async def cmd_start(update, context):
    user = update.effective_user
    db.add_user(user.id, user.username or user.first_name)
    await update.message.reply_text(
        f"👋 Welcome *{user.first_name}*!\n\n"
        f"🤖 *ApexSignal — Professional Trading Bot*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *322+ Trading Assets:*\n"
        f"  💱 Forex & Forex OTC\n"
        f"  📈 Stocks & Stocks OTC\n"
        f"  🥇 Commodities & OTC\n"
        f"  ₿ Crypto & Crypto OTC\n"
        f"  🪙 Crypto Standalone Coins\n\n"
        f"⚡ Crypto from Binance — Real time\n"
        f"📡 Forex/Stocks from Twelve Data\n\n"
        f"Tap *START TRADING* below 👇",
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )

async def button_cb(update, context):
    query = update.callback_query
    await query.answer()
    d = query.data

    if d == "show_category":
        await query.edit_message_text(
            "📂 *Select Market Category:*\n\n"
            "Choose what you want to trade:",
            parse_mode="Markdown",
            reply_markup=category_kb()
        )

    elif d.startswith("cat_"):
        category = d[4:]
        labels = {
            "forex": "💱 Forex Pairs",
            "forex_otc": "💱 Forex OTC Pairs",
            "stocks": "📈 Stock Pairs",
            "stocks_otc": "📈 Stock OTC Pairs",
            "commodity": "🥇 Commodity Pairs",
            "commodity_otc": "🥇 Commodity OTC Pairs",
            "crypto": "₿ Crypto Pairs",
            "crypto_otc": "₿ Crypto OTC Pairs",
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
        pair    = parts[1]
        val_str = parts[2]
        label   = parts[3] if len(parts) > 3 else "5min"
        twelve_iv, binance_iv = val_str.split("|")
        tf_data = {"twelve": twelve_iv, "binance": binance_iv}

        await query.edit_message_text(
            f"⏳ *Analysing {pair}...*\n\nFetching live market data...",
            parse_mode="Markdown"
        )

        r = analyse(pair, tf_data)

        if not r:
            await query.edit_message_text(
                f"❌ Could not fetch data for *{pair}*.\nPlease try again.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Retry", callback_data=d)],
                    [InlineKeyboardButton("⬅ Back", callback_data="show_category")]
                ])
            )
            return

        text = build_signal_msg(pair, label, r)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh Signal", callback_data=d)],
            [InlineKeyboardButton("📂 Categories", callback_data="show_category"),
             InlineKeyboardButton("🏠 Menu", callback_data="back_main")],
        ])
        await query.edit_message_text(
            text, parse_mode="Markdown", reply_markup=kb
        )
        db.log_signal(query.from_user.id, pair, twelve_iv, r["signal"])

    elif d == "subscribe":
        db.subscribe(query.from_user.id)
        await query.edit_message_text(
            f"✅ *Auto-Signals Activated!*\n\n"
            f"You'll receive the strongest signal every "
            f"*{SIGNAL_INTERVAL_MINUTES} minutes* automatically.\n\n"
            f"Use /unsubscribe to stop.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")]
            ])
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
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")]
            ])
        )

    elif d == "help":
        await query.edit_message_text(
            "❓ *How To Use ApexSignal*\n"
            "━━━━━━━━━━━━━━━\n"
            "1️⃣ Tap *START TRADING*\n"
            "2️⃣ Choose your *market category*\n"
            "3️⃣ Select your *asset/pair*\n"
            "4️⃣ Select your *expiry timeframe*\n"
            "5️⃣ Get *BUY/SELL/HOLD* signal\n"
            "6️⃣ Place trade on your broker\n\n"
            "💡 *Tips:*\n"
            "  • Only trade HIGH confidence signals\n"
            "  • Crypto signals are fastest\n"
            "  • Always test on demo first!\n\n"
            "⚠️ _Binary options involve financial risk._",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")]
            ])
        )

    elif d == "back_main":
        await query.edit_message_text(
            "🤖 *ApexSignal — Main Menu*\n\nTap *START TRADING* 👇",
            parse_mode="Markdown",
            reply_markup=main_menu_kb()
        )

async def cmd_unsubscribe(update, context):
    db.unsubscribe(update.effective_user.id)
    await update.message.reply_text("🔕 Unsubscribed from auto-signals.")

async def broadcast(context):
    subs = db.get_subscribers()
    if not subs:
        return
    best_pair, best_r, best_s = None, None, 0
    priority = ["BTC/USD", "ETH/USD", "EUR/USD", "GBP/USD", "XAU/USD"]
    for pair in priority:
        try:
            tf = {"twelve": "5min", "binance": "5m"}
            r = analyse(pair, tf)
            if r and r["signal"] != "HOLD" and r["confidence"] > best_s:
                best_s = r["confidence"]
                best_pair = pair
                best_r = r
        except:
            pass
    if not best_pair:
        return
    msg = "🚨 *AUTO-SIGNAL ALERT*\n" + build_signal_msg(best_pair, "5 min", best_r)
    for uid in subs:
        try:
            await context.bot.send_message(
                chat_id=uid, text=msg, parse_mode="Markdown"
            )
        except:
            pass

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
    app.add_handler(CallbackQueryHandler(button_cb))
    app.job_queue.run_repeating(
        broadcast,
        interval=SIGNAL_INTERVAL_MINUTES * 60,
        first=60
    )
    print("✅ ApexSignal Bot is running!")
    app.run_polling()

if __name__ == "__main__":
    main()
