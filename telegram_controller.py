import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta

import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

from config import (
    BOT_TOKEN, GEMINI_API_KEY,
    FOREX_OTC, CRYPTO_OTC, COMMODITY_OTC,
    STOCKS_OTC, INDICES_OTC, ALL_ASSETS,
    ASSET_NAMES, EXPIRY_OPTIONS,
    SIGNAL_INTERVAL_MINUTES
)
from database import Database
from state_manager import StateManager
from candle_engine import CandleEngine
from signal_engine import SignalEngine
from websocket_client import PocketOptionWS
from trade_executor import TradeExecutor

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────
# INSTANCES
# ─────────────────────────────────────
db              = Database()
state_manager   = StateManager()
candle_engine   = CandleEngine()
signal_engine   = SignalEngine(candle_engine, state_manager)
ws_client       = PocketOptionWS(candle_engine, state_manager)
trade_executor  = TradeExecutor(state_manager)
app_ref         = None

# ─────────────────────────────────────
# HELPERS
# ─────────────────────────────────────

def is_weekend():
    now = datetime.now(timezone.utc) + timedelta(hours=1)
    return now.weekday() >= 5


def asset_name(symbol):
    return ASSET_NAMES.get(symbol, symbol)


def signal_icon(s):
    return {"BUY": "🟢", "SELL": "🔴", "HOLD": "⏸"}.get(s, "⏸")


def is_crypto(symbol):
    crypto_keys = ["BTC", "ETH", "LTC", "XRP",
                   "ADA", "DOGE", "BNB", "SOL",
                   "DOT", "LINK", "MATIC", "AVAX",
                   "ATOM", "TRX", "XLM"]
    return any(k in symbol.upper() for k in crypto_keys)


# ─────────────────────────────────────
# GEMINI AI ANALYSIS
# ─────────────────────────────────────

async def get_ai_analysis(asset, sig):
    try:
        if not GEMINI_API_KEY or not sig:
            return None
        prompt = (
            f"You are a professional binary options trader.\n"
            f"Asset: {asset_name(asset)}\n"
            f"Signal: {sig['signal']}\n"
            f"ADX: {sig['adx']} (prev: {sig['adx_prev']})\n"
            f"+DI: {sig['plus_di']} -DI: {sig['minus_di']}\n"
            f"Williams %R: {sig['williams_r']}\n"
            f"Payout: {sig['payout']}%\n\n"
            f"Give a brief professional analysis in exactly 2 sentences. "
            f"Be direct and mention risk level."
        )
        url = (
            "https://generativelanguage.googleapis.com/v1beta"
            "/models/gemini-1.5-flash:generateContent"
            f"?key={GEMINI_API_KEY}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 150
            }
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json=payload, timeout=10)
            data = r.json()
            return (
                data["candidates"][0]["content"]["parts"][0]["text"]
            )
    except Exception:
        return None


# ─────────────────────────────────────
# SIGNAL MESSAGE
# ─────────────────────────────────────

async def build_signal_msg(asset, expiry, sig, show_ai=True):
    if not sig:
        count = await candle_engine.get_candle_count(
            asset,
            signal_engine.EXPIRY_TO_TIMEFRAME.get(expiry, 30)
        )
        return (
            f"⏳ *{asset_name(asset)}* — `{expiry}`\n\n"
            f"Building candles from live ticks...\n"
            f"Candles collected: `{count}`\n"
            f"Need at least 20 to generate signal.\n\n"
            f"Please wait 1-2 minutes."
        )

    icon = signal_icon(sig["signal"])
    weekend = is_weekend()
    weekend_note = ""
    if weekend and not is_crypto(asset):
        weekend_note = (
            "\n⚠️ *Weekend — signal less reliable for non-crypto*\n"
        )

    payout_bar = ""
    if sig["payout"] > 0:
        p = sig["payout"]
        stars = (
            "🔥🔥🔥" if p >= 90 else
            "🔥🔥"  if p >= 80 else
            "🔥"    if p >= 70 else "⚠️"
        )
        payout_bar = f"Payout:      `{p}%` {stars}\n"

    ai_section = ""
    if show_ai and GEMINI_API_KEY and sig["signal"] != "HOLD":
        ai_text = await get_ai_analysis(asset, sig)
        if ai_text:
            ai_section = f"\n🤖 *AI Analysis:*\n_{ai_text}_\n"

    # Win/loss history
    perf = db.get_asset_performance(asset)
    perf_text = ""
    if perf and perf[1] >= 3:
        perf_text = (
            f"History:     `{perf[0]:.1f}%` win rate "
            f"({perf[2]}W/{perf[3]}L)\n"
        )

    now_utc = datetime.now(timezone.utc)
    nigeria = now_utc + timedelta(hours=1)

    return (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *{asset_name(asset)}* — `{expiry}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{weekend_note}"
        f"Signal:      *{icon} {sig['signal']}*\n"
        f"Confidence:  `{sig['conf_bar']}` {sig['conf_text']}\n"
        f"{payout_bar}"
        f"Entry Price: `{sig['price']}`\n"
        f"{perf_text}\n"
        f"📐 *Indicators:*\n"
        f"  ADX:        `{sig['adx']}` "
        f"{'📈 Rising' if sig['adx'] > sig['adx_prev'] else '📉 Falling'}\n"
        f"  +DI:        `{sig['plus_di']}`\n"
        f"  -DI:        `{sig['minus_di']}`\n"
        f"  Williams%R: `{sig['williams_r']}`\n"
        f"  Candles:    `{sig['candles']} closed`\n\n"
        f"🧠 *Reasons:*\n" +
        "\n".join(f"  • {r}" for r in sig["reasons"]) +
        f"{ai_section}\n"
        f"📡 *Source: Pocket Option WebSocket*\n"
        f"🕐 `{nigeria.strftime('%H:%M:%S')} WAT`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ _Trade at your own risk._\n"
        f"`APEXSIGNAL|{sig['signal']}|{asset_name(asset)}"
        f"|{expiry}|{sig['confidence']}|{sig['price']}`"
    )


# ─────────────────────────────────────
# KEYBOARDS
# ─────────────────────────────────────

def main_menu_kb():
    weekend = is_weekend()
    status = "🚨 Weekend — Crypto Only!" if weekend else "✅ Markets Open"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "📊 Get Signal",
            callback_data="mode_signal"
        )],
        [InlineKeyboardButton(
            "🤖 Auto Trading",
            callback_data="mode_auto"
        )],
        [InlineKeyboardButton(
            "🔍 Scan Best Assets",
            callback_data="scan"
        )],
        [
            InlineKeyboardButton(
                "📈 Sessions",
                callback_data="sessions"
            ),
            InlineKeyboardButton(
                "📊 My Stats",
                callback_data="stats"
            ),
        ],
        [InlineKeyboardButton(
            "⛔ STOP BOT",
            callback_data="stop_bot"
        )],
    ])


def category_kb():
    weekend = is_weekend()
    if weekend:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "₿ Crypto OTC ✅",
                callback_data="cat_crypto"
            )],
            [InlineKeyboardButton(
                "💱 Forex OTC ⚠️ Weekend",
                callback_data="cat_forex"
            )],
            [InlineKeyboardButton(
                "🥇 Commodities OTC ⚠️",
                callback_data="cat_commodity"
            )],
            [InlineKeyboardButton(
                "📈 Stocks OTC ⚠️ Weekend",
                callback_data="cat_stocks"
            )],
            [InlineKeyboardButton(
                "📊 Indices OTC ⚠️",
                callback_data="cat_indices"
            )],
            [InlineKeyboardButton(
                "⬅ Back", callback_data="back_main"
            )],
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "💱 Forex OTC",
            callback_data="cat_forex"
        )],
        [InlineKeyboardButton(
            "₿ Crypto OTC",
            callback_data="cat_crypto"
        )],
        [InlineKeyboardButton(
            "🥇 Commodities OTC",
            callback_data="cat_commodity"
        )],
        [InlineKeyboardButton(
            "📈 Stocks OTC",
            callback_data="cat_stocks"
        )],
        [InlineKeyboardButton(
            "📊 Indices OTC",
            callback_data="cat_indices"
        )],
        [InlineKeyboardButton(
            "⬅ Back", callback_data="back_main"
        )],
    ])


def assets_kb(category):
    cat_map = {
        "forex":     FOREX_OTC,
        "crypto":    CRYPTO_OTC,
        "commodity": COMMODITY_OTC,
        "stocks":    STOCKS_OTC,
        "indices":   INDICES_OTC,
    }
    assets = cat_map.get(category, [])
    rows = []
    row = []
    for a in assets:
        name = asset_name(a)
        row.append(InlineKeyboardButton(
            name, callback_data=f"asset_{a}"
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


def expiry_kb():
    rows = []
    row = []
    for exp in EXPIRY_OPTIONS:
        row.append(InlineKeyboardButton(
            exp, callback_data=f"expiry_{exp}"
        ))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(
        "⬅ Back", callback_data="show_category"
    )])
    return InlineKeyboardMarkup(rows)


def account_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🎮 Demo Account",
            callback_data="account_demo"
        )],
        [InlineKeyboardButton(
            "💰 Real Account",
            callback_data="account_real"
        )],
        [InlineKeyboardButton("⬅ Back", callback_data="back_main")],
    ])


def signal_action_kb(asset, expiry):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🔄 Refresh",
            callback_data=f"refresh_{asset}_{expiry}"
        )],
        [InlineKeyboardButton(
            "🤖 Auto Trade This",
            callback_data="mode_auto"
        )],
        [
            InlineKeyboardButton(
                "✅ Log WIN",
                callback_data=f"win_{asset}"
            ),
            InlineKeyboardButton(
                "❌ Log LOSS",
                callback_data=f"loss_{asset}"
            ),
        ],
        [
            InlineKeyboardButton(
                "📂 Categories",
                callback_data="show_category"
            ),
            InlineKeyboardButton(
                "🏠 Menu",
                callback_data="back_main"
            ),
        ],
    ])


def confirm_trade_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Confirm",
                callback_data="confirm_trade"
            ),
            InlineKeyboardButton(
                "❌ Cancel",
                callback_data="back_main"
            ),
        ]
    ])


# ─────────────────────────────────────
# NOTIFY
# ─────────────────────────────────────

async def notify_all(message):
    users = await state_manager.get_all_active_users()
    for uid, data in users:
        chat_id = data.get("chat_id")
        if chat_id and app_ref:
            try:
                await app_ref.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Notify {uid}: {e}")


async def notify_user(message, user_id=None):
    if not user_id:
        await notify_all(message)
        return
    try:
        udata = await state_manager.get_user(user_id)
        chat_id = udata.get("chat_id")
        if chat_id and app_ref:
            await app_ref.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.warning(f"Notify user {user_id}: {e}")


# ─────────────────────────────────────
# COMMAND HANDLERS
# ─────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        db.add_user(user.id, user.username or user.first_name)
        await state_manager.set_user(
            user.id,
            chat_id=update.effective_chat.id,
            username=user.username or user.first_name,
            active=True
        )
        connected = await state_manager.is_connected()
        uptime = await state_manager.get_uptime()
        weekend = is_weekend()
        ticks = ws_client.get_tick_count()

        weekend_msg = ""
        if weekend:
            weekend_msg = (
                "\n🚨 *TODAY IS WEEKEND*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "❌ Forex — CLOSED\n"
                "❌ Stocks — CLOSED\n"
                "✅ CRYPTO ONLY!\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
            )

        await update.message.reply_text(
            f"👋 Welcome *{user.first_name}*!\n\n"
            f"🤖 *ApexSignal — Real Time Trading Agent*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 PO WebSocket: "
            f"{'✅ Connected' if connected else '⏳ Connecting...'}\n"
            f"⚡ Data Source: *Pocket Option Only*\n"
            f"📊 Indicators: *ADX + Williams %R*\n"
            f"🔢 Ticks received: `{ticks}`\n"
            f"⏱ Uptime: `{uptime}`\n"
            f"{weekend_msg}\n"
            f"Choose your mode 👇",
            parse_mode="Markdown",
            reply_markup=main_menu_kb()
        )
    except Exception as e:
        logger.error(f"cmd_start: {e}")


async def cmd_scan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(
        "🔍 *Scanning all assets...*",
        parse_mode="Markdown"
    )
    try:
        signals = await signal_engine.get_best_signals("1m", limit=8)
        top_payouts = await state_manager.get_top_payouts(
            min_payout=80, limit=5
        )

        text = "📡 *Best Signals Right Now:*\n\n"
        buttons = []

        if signals:
            for asset, sig in signals:
                icon = signal_icon(sig["signal"])
                p = sig.get("payout", 0)
                pout = f" | `{p:.0f}%`" if p > 0 else ""
                text += (
                    f"{icon} *{asset_name(asset)}*{pout}\n"
                    f"  `{sig['conf_bar']}` "
                    f"ADX:{sig['adx']} "
                    f"W%R:{sig['williams_r']}\n\n"
                )
                buttons.append([InlineKeyboardButton(
                    f"📊 {asset_name(asset)} — {sig['signal']}",
                    callback_data=f"asset_{asset}"
                )])
        else:
            text += (
                "⏳ No strong signals yet.\n\n"
                "Waiting for PO WebSocket data...\n"
                "Give it 1-2 minutes to build candles."
            )

        if top_payouts:
            text += "💰 *Top Payouts:*\n"
            for a, p in top_payouts[:5]:
                text += f"  • {asset_name(a)}: `{p:.0f}%`\n"

        buttons.append([InlineKeyboardButton(
            "🏠 Menu", callback_data="back_main"
        )])
        await msg.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        logger.error(f"cmd_scan: {e}")
        await msg.edit_text("❌ Scan failed. Try again.")


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    connected = await state_manager.is_connected()
    uptime    = await state_manager.get_uptime()
    assets    = await candle_engine.get_all_assets()
    ticks     = ws_client.get_tick_count()
    trades    = trade_executor.get_total()
    active    = await trade_executor.get_active()

    await update.message.reply_text(
        f"📊 *ApexSignal Status*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"WebSocket:    {'✅ Connected' if connected else '❌ Down'}\n"
        f"Uptime:       `{uptime}`\n"
        f"Ticks rx:     `{ticks}`\n"
        f"Assets live:  `{len(assets)}`\n"
        f"Total trades: `{trades}`\n"
        f"Active trades:`{len(active)}`\n"
        f"Weekend:      `{'Yes ⚠️' if is_weekend() else 'No ✅'}`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Menu", callback_data="back_main")
        ]])
    )


async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await state_manager.set_user(uid, active=False, auto_running=False)
    await update.message.reply_text(
        "⛔ *Bot stopped.* Type /start to resume.",
        parse_mode="Markdown"
    )


# ─────────────────────────────────────
# CALLBACK HANDLER
# ─────────────────────────────────────

async def button_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    d = query.data
    uid = query.from_user.id

    try:
        if d == "back_main":
            connected = await state_manager.is_connected()
            ticks = ws_client.get_tick_count()
            await query.edit_message_text(
                f"🤖 *ApexSignal — Main Menu*\n\n"
                f"📡 WS: {'✅ Connected' if connected else '⏳ Connecting'}\n"
                f"⚡ Ticks: `{ticks}`\n"
                f"{'🚨 Weekend — Crypto Only!' if is_weekend() else '✅ Markets Open'}\n\n"
                f"Choose your mode 👇",
                parse_mode="Markdown",
                reply_markup=main_menu_kb()
            )

        elif d == "mode_signal":
            await state_manager.set_user(uid, mode="signal")
            await query.edit_message_text(
                "📊 *Signal Mode*\n\n"
                "Select asset category:",
                parse_mode="Markdown",
                reply_markup=category_kb()
            )

        elif d == "mode_auto":
            await state_manager.set_user(uid, mode="auto")
            await query.edit_message_text(
                "🤖 *Auto Trading Mode*\n\n"
                "⚠️ Bot will place real trades!\n"
                "Select account type first:",
                parse_mode="Markdown",
                reply_markup=account_kb()
            )

        elif d == "show_category":
            await query.edit_message_text(
                "📂 *Select Category:*",
                parse_mode="Markdown",
                reply_markup=category_kb()
            )

        elif d.startswith("cat_"):
            cat = d[4:]
            await query.edit_message_text(
                f"Select asset:",
                parse_mode="Markdown",
                reply_markup=assets_kb(cat)
            )

        elif d.startswith("asset_"):
            asset = d[6:]
            await state_manager.set_user(uid, asset=asset)
            payout = await state_manager.get_payout(asset)
            pout_txt = f"\nPayout: `{payout:.0f}%`" if payout > 0 else ""
            await query.edit_message_text(
                f"⏱ *Select Expiry for:*\n"
                f"*{asset_name(asset)}*{pout_txt}\n\n"
                f"Choose your trade expiry time:",
                parse_mode="Markdown",
                reply_markup=expiry_kb()
            )

        elif d.startswith("expiry_"):
            expiry = d[7:]
            await state_manager.set_user(uid, expiry=expiry)
            udata = await state_manager.get_user(uid)
            asset = udata.get("asset", "")
            mode  = udata.get("mode", "signal")

            if not asset:
                await query.edit_message_text(
                    "❌ No asset selected. Start over.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "⬅ Back", callback_data="back_main"
                        )
                    ]])
                )
                return

            if mode == "auto":
                await query.edit_message_text(
                    f"💰 *Enter Trade Amount*\n\n"
                    f"Asset:  *{asset_name(asset)}*\n"
                    f"Expiry: *{expiry}*\n\n"
                    f"Type your amount (e.g. 1, 5, 10):",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "⬅ Back",
                            callback_data="show_category"
                        )
                    ]])
                )
                await state_manager.set_user(
                    uid, awaiting_amount=True
                )
            else:
                await query.edit_message_text(
                    f"⏳ Fetching signal for *{asset_name(asset)}*...",
                    parse_mode="Markdown"
                )
                sig  = await signal_engine.get_signal(asset, expiry)
                text = await build_signal_msg(asset, expiry, sig)
                db.log_signal(
                    uid, asset, expiry,
                    sig["signal"] if sig else "HOLD",
                    sig["confidence"] if sig else 0,
                    sig["price"] if sig else 0,
                    sig["adx"] if sig else 0,
                    sig["williams_r"] if sig else 0,
                )
                await query.edit_message_text(
                    text,
                    parse_mode="Markdown",
                    reply_markup=signal_action_kb(asset, expiry)
                )

        elif d.startswith("refresh_"):
            parts = d.split("_", 2)
            if len(parts) >= 3:
                asset  = parts[1]
                expiry = parts[2]
                sig  = await signal_engine.get_signal(asset, expiry)
                text = await build_signal_msg(asset, expiry, sig)
                await query.edit_message_text(
                    text,
                    parse_mode="Markdown",
                    reply_markup=signal_action_kb(asset, expiry)
                )

        elif d.startswith("account_"):
            account = d[8:]
            await state_manager.set_user(uid, account=account)
            await query.edit_message_text(
                f"📂 *Select Category:*\n\n"
                f"Account: *{'Demo 🎮' if account == 'demo' else 'Real 💰'}*",
                parse_mode="Markdown",
                reply_markup=category_kb()
            )

        elif d == "confirm_trade":
            udata   = await state_manager.get_user(uid)
            asset   = udata.get("asset", "")
            expiry  = udata.get("expiry", "1m")
            amount  = udata.get("amount", "1")
            account = udata.get("account", "demo")
            sig     = await signal_engine.get_signal(asset, expiry)

            if not sig or sig["signal"] == "HOLD":
                await query.edit_message_text(
                    "⏸ *Signal is HOLD — no trade placed.*\n\n"
                    "Wait for a stronger signal setup.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "🏠 Menu", callback_data="back_main"
                        )
                    ]])
                )
                return

            if sig["confidence"] < 3:
                await query.edit_message_text(
                    f"⚠️ Confidence too low "
                    f"`{sig['conf_bar']}`\n\n"
                    "Trade not placed — wait for better setup.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "🏠 Menu", callback_data="back_main"
                        )
                    ]])
                )
                return

            await trade_executor.queue_trade(
                user_id=uid,
                asset=asset,
                direction=sig["signal"],
                amount=amount,
                expiry=expiry,
                account=account
            )

            icon = signal_icon(sig["signal"])
            await query.edit_message_text(
                f"⏳ *Trade queued!*\n\n"
                f"Asset:     *{asset_name(asset)}*\n"
                f"Signal:    {icon} *{sig['signal']}*\n"
                f"Amount:    *${amount}*\n"
                f"Expiry:    *{expiry}*\n"
                f"Account:   *{'Demo 🎮' if account == 'demo' else 'Real 💰'}*\n\n"
                f"Executing with human-like delay...",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Menu", callback_data="back_main"
                    )
                ]])
            )

        elif d == "scan":
            await query.edit_message_text(
                "🔍 *Scanning...*",
                parse_mode="Markdown"
            )
            signals = await signal_engine.get_best_signals(
                "1m", limit=8
            )
            top_payouts = await state_manager.get_top_payouts(
                min_payout=80, limit=5
            )

            text = "📡 *Best Signals:*\n\n"
            buttons = []

            if signals:
                for asset, sig in signals:
                    icon = signal_icon(sig["signal"])
                    p = sig.get("payout", 0)
                    pout = f" `{p:.0f}%`" if p > 0 else ""
                    text += (
                        f"{icon} *{asset_name(asset)}*{pout}\n"
                        f"  `{sig['conf_bar']}` "
                        f"ADX:{sig['adx']}\n\n"
                    )
                    buttons.append([InlineKeyboardButton(
                        f"📊 {asset_name(asset)}",
                        callback_data=f"asset_{asset}"
                    )])
            else:
                text += (
                    "⏳ Waiting for live tick data...\n"
                    "PO WebSocket building candles.\n"
                    "Try again in ~1 minute.\n"
                )

            if top_payouts:
                text += "\n💰 *High Payouts:*\n"
                for a, p in top_payouts[:5]:
                    text += f"  • {asset_name(a)}: `{p:.0f}%`\n"

            buttons.append([InlineKeyboardButton(
                "🏠 Menu", callback_data="back_main"
            )])
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        elif d == "sessions":
            now = datetime.now(timezone.utc) + timedelta(hours=1)
            h = now.hour
            if 22 <= h or h < 7:
                sess = "🇯🇵 Tokyo"
            elif 7 <= h < 9:
                sess = "🌏 Tokyo/London"
            elif 9 <= h < 13:
                sess = "🇬🇧 London"
            elif 13 <= h < 17:
                sess = "🌍 London/NY Overlap"
            elif 17 <= h < 22:
                sess = "🇺🇸 New York"
            else:
                sess = "🌙 Off Hours"
            await query.edit_message_text(
                f"🌍 *Market Sessions*\n\n"
                f"Current: *{sess}*\n\n"
                f"*Nigeria WAT Times:*\n"
                f"🇯🇵 Tokyo:    23:00 — 08:00\n"
                f"🇬🇧 London:   08:00 — 17:00\n"
                f"🇺🇸 New York: 14:00 — 23:00\n\n"
                f"*Best Times:*\n"
                f"⭐ London Open:   08:00-10:00\n"
                f"⭐ NY Open:       14:00-16:00\n"
                f"⭐ Overlap:       14:00-17:00\n\n"
                f"💡 _ADX signals are strongest at session opens!_",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Menu", callback_data="back_main"
                    )
                ]])
            )

        elif d == "stats":
            udata  = await state_manager.get_user(uid)
            stats  = db.get_user_stats(uid)
            top    = db.get_top_assets(5)
            trades = trade_executor.get_total()
            active = await trade_executor.get_active()
            uptime = await state_manager.get_uptime()

            top_txt = ""
            if top:
                top_txt = "\n🏆 *Best Assets:*\n"
                for row in top:
                    top_txt += (
                        f"  • {asset_name(row[0])}: "
                        f"`{row[1]:.1f}%` "
                        f"({row[2]}W/{row[3]}L)\n"
                    )

            await query.edit_message_text(
                f"📊 *Your Stats*\n"
                f"━━━━━━━━━━━━━━━\n"
                f"Total Signals: `{stats['total_signals']}`\n"
                f"Trades Placed: `{stats['total_trades']}`\n"
                f"✅ Wins:        `{stats['wins']}`\n"
                f"❌ Losses:      `{stats['losses']}`\n"
                f"🎯 Win Rate:    `{stats['win_rate']}%`\n"
                f"{top_txt}\n"
                f"🤖 *Session:*\n"
                f"Mode:    `{udata.get('mode','signal').upper()}`\n"
                f"Account: `{udata.get('account','demo').upper()}`\n"
                f"Uptime:  `{uptime}`\n"
                f"Auto trades: `{trades}`\n"
                f"Active: `{len(active)}`",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Menu", callback_data="back_main"
                    )
                ]])
            )

        elif d.startswith("win_"):
            asset = d[4:]
            udata = await state_manager.get_user(uid)
            db.log_trade_result(
                uid, asset,
                "BUY", udata.get("expiry", "1m"),
                "WIN", float(udata.get("amount", "1"))
            )
            await query.edit_message_text(
                f"✅ *WIN logged for {asset_name(asset)}!* 🎉\n\n"
                f"Check /stats to see your progress.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Menu", callback_data="back_main"
                    )
                ]])
            )

        elif d.startswith("loss_"):
            asset = d[5:]
            udata = await state_manager.get_user(uid)
            db.log_trade_result(
                uid, asset,
                "SELL", udata.get("expiry", "1m"),
                "LOSS", float(udata.get("amount", "1"))
            )
            await query.edit_message_text(
                f"❌ *LOSS logged for {asset_name(asset)}*\n\n"
                f"Stay disciplined! Only trade ADX > 22 signals! 💪",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Menu", callback_data="back_main"
                    )
                ]])
            )

        elif d == "stop_bot":
            await state_manager.set_user(
                uid, active=False, auto_running=False
            )
            await query.edit_message_text(
                "⛔ *Bot stopped for your session.*\n\n"
                "All tasks cancelled.\n"
                "Type /start to resume.",
                parse_mode="Markdown"
            )

    except Exception as e:
        logger.error(f"button_cb error: {e}")
        try:
            await query.edit_message_text(
                "❌ Error. Type /start to restart."
            )
        except Exception:
            pass


# ─────────────────────────────────────
# MESSAGE HANDLER
# ─────────────────────────────────────

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        uid  = update.effective_user.id
        text = update.message.text.strip()
        udata = await state_manager.get_user(uid)

        if udata.get("awaiting_amount"):
            try:
                amount = float(text)
                if amount <= 0:
                    raise ValueError
                await state_manager.set_user(
                    uid, amount=str(amount), awaiting_amount=False
                )
                asset   = udata.get("asset", "")
                expiry  = udata.get("expiry", "1m")
                account = udata.get("account", "demo")
                sig     = await signal_engine.get_signal(asset, expiry)

                sig_txt = ""
                if sig:
                    icon = signal_icon(sig["signal"])
                    p = sig.get("payout", 0)
                    pout = f"\nPayout:   `{p:.0f}%`" if p > 0 else ""
                    sig_txt = (
                        f"\n📊 Signal: *{icon} {sig['signal']}*\n"
                        f"Confidence: `{sig['conf_bar']}`{pout}\n"
                    )

                await update.message.reply_text(
                    f"📋 *Trade Summary*\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"Asset:   *{asset_name(asset)}*\n"
                    f"Expiry:  *{expiry}*\n"
                    f"Amount:  *${amount}*\n"
                    f"Account: *{'Demo 🎮' if account == 'demo' else 'Real 💰'}*\n"
                    f"{sig_txt}\n"
                    f"Confirm to execute:",
                    parse_mode="Markdown",
                    reply_markup=confirm_trade_kb()
                )
            except (ValueError, TypeError):
                await update.message.reply_text(
                    "❌ Invalid amount.\n"
                    "Please enter a number like: 1, 5, 10"
                )
    except Exception as e:
        logger.error(f"handle_message: {e}")


# ─────────────────────────────────────
# AUTO BROADCAST
# ─────────────────────────────────────

async def auto_broadcast(ctx):
    try:
        subs = db.get_subscribers()
        if not subs:
            return

        weekend = is_weekend()
        if weekend:
            scan_assets = CRYPTO_OTC[:8]
        else:
            scan_assets = (
                FOREX_OTC[:6] +
                CRYPTO_OTC[:4] +
                COMMODITY_OTC
            )

        best_asset = None
        best_sig   = None
        best_score = 0

        for asset in scan_assets:
            sig = await signal_engine.get_signal(asset, "5m")
            if (sig and sig["signal"] != "HOLD"
                    and sig["confidence"] >= 3
                    and sig["confidence"] > best_score):
                best_score = sig["confidence"]
                best_asset = asset
                best_sig   = sig

        if not best_asset or not best_sig:
            return

        text = await build_signal_msg(
            best_asset, "5m", best_sig, show_ai=False
        )
        msg = "🚨 *AUTO SIGNAL ALERT*\n\n" + text

        for uid in subs:
            try:
                udata = await state_manager.get_user(uid)
                chat_id = udata.get("chat_id")
                if chat_id:
                    await ctx.bot.send_message(
                        chat_id=chat_id,
                        text=msg,
                        parse_mode="Markdown"
                    )
            except Exception as e:
                logger.warning(f"Broadcast {uid}: {e}")

    except Exception as e:
        logger.error(f"Broadcast error: {e}")


# ─────────────────────────────────────
# MAIN
# ─────────────────────────────────────

async def post_init(application):
    global app_ref
    app_ref = application

    ws_client.set_notify_callback(notify_all)
    trade_executor.set_notify_callback(notify_user)
    trade_executor.set_ws_client(ws_client)

    await candle_engine.start()
    await signal_engine.start()
    await ws_client.start()
    await trade_executor.start()

    logger.info("✅ All services started!")


def main():
    token = BOT_TOKEN
    if not token:
        logger.error("BOT_TOKEN not set!")
        return

    application = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )

    application.add_handler(CommandHandler("start",  cmd_start))
    application.add_handler(CommandHandler("scan",   cmd_scan))
    application.add_handler(CommandHandler("stop",   cmd_stop))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CallbackQueryHandler(button_cb))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))

    application.job_queue.run_repeating(
        auto_broadcast,
        interval=SIGNAL_INTERVAL_MINUTES * 60,
        first=120
    )

    logger.info("ApexSignal starting...")
    print("✅ ApexSignal is running!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
