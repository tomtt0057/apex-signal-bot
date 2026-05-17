import asyncio
import logging
from datetime import datetime, timezone, timedelta

import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

from config import (
    BOT_TOKEN, GEMINI_API_KEY,
    FOREX_MAIN, FOREX_OTC,
    CRYPTO_MAIN, CRYPTO_OTC,
    COMMODITY_MAIN, COMMODITY_OTC,
    STOCKS_MAIN, STOCKS_OTC,
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
# GLOBAL INSTANCES
# ─────────────────────────────────────
db             = Database()
state_manager  = StateManager()
candle_engine  = CandleEngine()
signal_engine  = SignalEngine(candle_engine, state_manager)
ws_client      = PocketOptionWS(candle_engine, state_manager)
trade_executor = TradeExecutor(state_manager)
app_ref        = None

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
    keys = [
        "BTC", "ETH", "LTC", "XRP", "ADA",
        "DOGE", "BNB", "SOL", "DOT", "LINK",
        "MATIC", "AVAX", "ATOM", "TRX", "XLM"
    ]
    return any(k in symbol.upper() for k in keys)


# ─────────────────────────────────────
# AI ANALYSIS
# ─────────────────────────────────────

async def get_ai_analysis(asset, sig):
    try:
        if not GEMINI_API_KEY or not sig:
            return None
        prompt = (
            f"Professional binary options analysis for "
            f"{asset_name(asset)}.\n"
            f"Signal: {sig['signal']}\n"
            f"ADX: {sig['adx']} (+DI:{sig['plus_di']} -DI:{sig['minus_di']})\n"
            f"Williams %R: {sig['williams_r']}\n"
            f"Confidence: {sig['conf_text']}\n"
            f"Payout: {sig.get('payout', 0)}%\n\n"
            f"Give exactly 2 sentences: market condition and risk level."
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
                "maxOutputTokens": 120
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
# SIGNAL MESSAGE BUILDER
# ─────────────────────────────────────

async def build_signal_msg(asset, expiry, sig, show_ai=True):
    if not sig:
        tf = signal_engine.EXPIRY_TO_TIMEFRAME.get(expiry, 30)
        count = await candle_engine.get_candle_count(asset, tf)
        price = await state_manager.get_price(asset)
        payout = await state_manager.get_payout(asset)

        pout_txt = f"\nPayout: `{payout:.0f}%`" if payout > 0 else ""
        price_txt = f"\nLive Price: `{price}`" if price > 0 else ""

        return (
            f"⏳ *{asset_name(asset)}* — `{expiry}`\n"
            f"{pout_txt}{price_txt}\n\n"
            f"Building candles from live ticks...\n"
            f"Candles collected: `{count}/20`\n\n"
            f"Please wait ~1-2 minutes for first signal.\n"
            f"_Using real-time Pocket Option data._"
        )

    icon    = signal_icon(sig["signal"])
    weekend = is_weekend()

    weekend_note = ""
    if weekend and not is_crypto(asset):
        weekend_note = "\n⚠️ *Weekend — less reliable for non-crypto*\n"

    payout  = sig.get("payout", 0)
    if payout > 0:
        stars = (
            "🔥🔥🔥" if payout >= 90 else
            "🔥🔥"  if payout >= 80 else
            "🔥"    if payout >= 70 else "⚠️"
        )
        payout_line = f"Payout:      `{payout:.0f}%` {stars}\n"
    else:
        payout_line = ""

    ai_section = ""
    if show_ai and GEMINI_API_KEY and sig["signal"] != "HOLD":
        ai_text = await get_ai_analysis(asset, sig)
        if ai_text:
            ai_section = f"\n🤖 *AI Analysis:*\n_{ai_text}_\n"

    perf = db.get_asset_performance(asset)
    perf_txt = ""
    if perf and perf[1] >= 3:
        perf_txt = (
            f"History:     `{perf[0]:.1f}%` win "
            f"({perf[2]}W/{perf[3]}L)\n"
        )

    adx_arrow = (
        "📈 Rising" if sig["adx"] > sig["adx_prev"]
        else "📉 Falling"
    )
    nigeria = datetime.now(timezone.utc) + timedelta(hours=1)

    return (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *{asset_name(asset)}* — `{expiry}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{weekend_note}"
        f"Signal:      *{icon} {sig['signal']}*\n"
        f"Confidence:  `{sig['conf_bar']}` {sig['conf_text']}\n"
        f"{payout_line}"
        f"Entry Price: `{sig['price']}`\n"
        f"{perf_txt}\n"
        f"📐 *Indicators:*\n"
        f"  ADX:        `{sig['adx']}` {adx_arrow}\n"
        f"  +DI:        `{sig['plus_di']}`\n"
        f"  -DI:        `{sig['minus_di']}`\n"
        f"  Williams%R: `{sig['williams_r']}`\n"
        f"  Candles:    `{sig['candles']}`\n\n"
        f"🧠 *Analysis:*\n" +
        "\n".join(f"  • {r}" for r in sig["reasons"]) +
        f"{ai_section}\n"
        f"📡 *Source: Pocket Option Real-Time*\n"
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
    status  = "🚨 Weekend — Crypto Only!" if weekend else "✅ Markets Open"
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
            "🔔 Auto-Signals (Subscribe)",
            callback_data="subscribe"
        )],
        [
            InlineKeyboardButton(
                "🔍 Scan Markets",
                callback_data="scan"
            ),
            InlineKeyboardButton(
                "📊 My Stats",
                callback_data="stats"
            ),
        ],
        [
            InlineKeyboardButton(
                "🌍 Sessions",
                callback_data="sessions"
            ),
            InlineKeyboardButton(
                "❓ Help",
                callback_data="help"
            ),
        ],
    ])


def category_kb(mode="signal"):
    weekend = is_weekend()
    prefix  = f"cat_{mode}_"

    if weekend:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "₿ Crypto ✅",
                callback_data=f"{prefix}crypto_main"
            )],
            [InlineKeyboardButton(
                "₿ Crypto OTC ✅",
                callback_data=f"{prefix}crypto_otc"
            )],
            [InlineKeyboardButton(
                "💱 Forex ⚠️ Weekend",
                callback_data=f"{prefix}forex_main"
            )],
            [InlineKeyboardButton(
                "💱 Forex OTC ⚠️",
                callback_data=f"{prefix}forex_otc"
            )],
            [InlineKeyboardButton(
                "🥇 Commodities ⚠️",
                callback_data=f"{prefix}commodity_main"
            )],
            [InlineKeyboardButton(
                "🥇 Commodities OTC ⚠️",
                callback_data=f"{prefix}commodity_otc"
            )],
            [InlineKeyboardButton(
                "📈 Stocks ⚠️ Weekend",
                callback_data=f"{prefix}stocks_main"
            )],
            [InlineKeyboardButton(
                "📈 Stocks OTC ⚠️",
                callback_data=f"{prefix}stocks_otc"
            )],
            [InlineKeyboardButton(
                "⬅ Back", callback_data="back_main"
            )],
        ])

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💱 Forex",
                callback_data=f"{prefix}forex_main"
            ),
            InlineKeyboardButton(
                "💱 Forex OTC",
                callback_data=f"{prefix}forex_otc"
            ),
        ],
        [
            InlineKeyboardButton(
                "₿ Crypto",
                callback_data=f"{prefix}crypto_main"
            ),
            InlineKeyboardButton(
                "₿ Crypto OTC",
                callback_data=f"{prefix}crypto_otc"
            ),
        ],
        [
            InlineKeyboardButton(
                "🥇 Commodities",
                callback_data=f"{prefix}commodity_main"
            ),
            InlineKeyboardButton(
                "🥇 Commodities OTC",
                callback_data=f"{prefix}commodity_otc"
            ),
        ],
        [
            InlineKeyboardButton(
                "📈 Stocks",
                callback_data=f"{prefix}stocks_main"
            ),
            InlineKeyboardButton(
                "📈 Stocks OTC",
                callback_data=f"{prefix}stocks_otc"
            ),
        ],
        [InlineKeyboardButton("⬅ Back", callback_data="back_main")],
    ])


def assets_kb(category, mode="signal"):
    cat_map = {
        "forex_main":      FOREX_MAIN,
        "forex_otc":       FOREX_OTC,
        "crypto_main":     CRYPTO_MAIN,
        "crypto_otc":      CRYPTO_OTC,
        "commodity_main":  COMMODITY_MAIN,
        "commodity_otc":   COMMODITY_OTC,
        "stocks_main":     STOCKS_MAIN,
        "stocks_otc":      STOCKS_OTC,
    }
    asset_list = cat_map.get(category, [])
    rows = []
    row  = []
    for a in asset_list:
        name = asset_name(a)
        row.append(InlineKeyboardButton(
            name,
            callback_data=f"asset_{mode}_{a}"
        ))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(
        "⬅ Back",
        callback_data=f"show_category_{mode}"
    )])
    return InlineKeyboardMarkup(rows)


def expiry_kb(asset, mode="signal"):
    rows = []
    row  = []
    for exp in EXPIRY_OPTIONS:
        row.append(InlineKeyboardButton(
            exp,
            callback_data=f"expiry_{mode}_{asset}_{exp}"
        ))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(
        "⬅ Back",
        callback_data=f"show_category_{mode}"
    )])
    return InlineKeyboardMarkup(rows)


def signal_action_kb(asset, expiry):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🔄 Refresh Signal",
            callback_data=f"expiry_signal_{asset}_{expiry}"
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
                callback_data="show_category_signal"
            ),
            InlineKeyboardButton(
                "🏠 Menu",
                callback_data="back_main"
            ),
        ],
    ])


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


def confirm_trade_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Confirm Trade",
                callback_data="confirm_trade"
            ),
            InlineKeyboardButton(
                "❌ Cancel",
                callback_data="back_main"
            ),
        ],
        [InlineKeyboardButton(
            "🛑 Stop Auto Trading",
            callback_data="stop_auto"
        )],
    ])


def auto_running_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🛑 Stop Auto Trading",
            callback_data="stop_auto"
        )],
        [InlineKeyboardButton(
            "📊 Get Signal",
            callback_data="mode_signal"
        )],
        [InlineKeyboardButton(
            "🏠 Menu",
            callback_data="back_main"
        )],
    ])


# ─────────────────────────────────────
# NOTIFY FUNCTIONS
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
                logger.warning(f"notify_all {uid}: {e}")


async def notify_user(message, user_id=None):
    if not user_id:
        await notify_all(message)
        return
    try:
        udata   = await state_manager.get_user(user_id)
        chat_id = udata.get("chat_id")
        if chat_id and app_ref:
            await app_ref.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.warning(f"notify_user {user_id}: {e}")


# ─────────────────────────────────────
# COMMAND HANDLERS
# ─────────────────────────────────────

async def cmd_start(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE
):
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
        uptime    = await state_manager.get_uptime()
        ticks     = ws_client.get_tick_count()
        weekend   = is_weekend()

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
            f"🤖 *ApexSignal — Real-Time PO Bot*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 PO WebSocket: "
            f"{'✅ Connected' if connected else '⏳ Connecting...'}\n"
            f"⚡ Data: Real-time Pocket Option\n"
            f"📐 Indicators: ADX + Williams %R\n"
            f"🔢 Ticks: `{ticks}`\n"
            f"⏱ Uptime: `{uptime}`\n"
            f"{weekend_msg}\n"
            f"Select what you want to do 👇",
            parse_mode="Markdown",
            reply_markup=main_menu_kb()
        )
    except Exception as e:
        logger.error(f"cmd_start error: {e}")


async def cmd_scan(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE
):
    msg = await update.message.reply_text(
        "🔍 *Scanning all markets...*\nPlease wait ⏳",
        parse_mode="Markdown"
    )
    await _do_scan(msg)


async def cmd_stop(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE
):
    uid = update.effective_user.id
    await state_manager.set_user(
        uid, auto_running=False
    )
    await update.message.reply_text(
        "🛑 *Auto-trading stopped.*\n\n"
        "Signal mode is still active.\n"
        "Type /start for main menu.",
        parse_mode="Markdown"
    )


async def cmd_status(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE
):
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
            InlineKeyboardButton(
                "🏠 Menu", callback_data="back_main"
            )
        ]])
    )


async def cmd_unsubscribe(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE
):
    db.unsubscribe(update.effective_user.id)
    await update.message.reply_text(
        "🔕 Unsubscribed from auto-signals.\n"
        "Type /start to return to menu."
    )


# ─────────────────────────────────────
# SCAN HELPER
# ─────────────────────────────────────

async def _do_scan(msg):
    try:
        weekend  = is_weekend()
        signals  = await signal_engine.get_best_signals("1m", limit=8)
        payouts  = await state_manager.get_top_payouts(min_payout=70, limit=8)
        ticks    = ws_client.get_tick_count()
        connected = await state_manager.is_connected()

        text    = "📡 *Market Scan Results:*\n\n"
        buttons = []

        if signals:
            text += "🎯 *Strong Signals:*\n"
            for asset, sig in signals:
                icon  = signal_icon(sig["signal"])
                p     = sig.get("payout", 0)
                pout  = f" `{p:.0f}%`" if p > 0 else ""
                text += (
                    f"{icon} *{asset_name(asset)}*{pout}\n"
                    f"  `{sig['conf_bar']}` "
                    f"ADX:{sig['adx']} "
                    f"W%R:{sig['williams_r']}\n\n"
                )
                buttons.append([InlineKeyboardButton(
                    f"📊 {asset_name(asset)} — {sig['signal']}",
                    callback_data=f"asset_signal_{asset}"
                )])
        else:
            if ticks == 0:
                text += (
                    "⏳ *WebSocket not yet receiving ticks.*\n\n"
                    f"Status: {'✅ Connected' if connected else '⏳ Connecting...'}\n"
                    f"Ticks received: `{ticks}`\n\n"
                    "Please wait 1-2 minutes after connecting.\n"
                    "The bot needs to collect candle data first."
                )
            else:
                text += (
                    f"⏳ Collecting data... `{ticks}` ticks received.\n\n"
                    "Signals appear after 20+ candles are built.\n"
                    "This takes ~1-2 minutes. Try again shortly."
                )

        if payouts:
            text += "\n💰 *Assets With Highest Payouts:*\n"
            for a, p in payouts[:5]:
                text += f"  • {asset_name(a)}: `{p:.0f}%`\n"

        buttons.append([InlineKeyboardButton(
            "🔄 Scan Again", callback_data="scan"
        )])
        buttons.append([InlineKeyboardButton(
            "🏠 Menu", callback_data="back_main"
        )])

        await msg.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        logger.error(f"_do_scan error: {e}")
        try:
            await msg.edit_text(
                "❌ Scan failed. Try again.\n/start"
            )
        except Exception:
            pass


# ─────────────────────────────────────
# MAIN CALLBACK HANDLER
# ─────────────────────────────────────

async def button_cb(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()
    d   = query.data
    uid = query.from_user.id

    try:

        # ── BACK TO MAIN MENU
        if d == "back_main":
            connected = await state_manager.is_connected()
            ticks     = ws_client.get_tick_count()
            await query.edit_message_text(
                f"🤖 *ApexSignal — Main Menu*\n\n"
                f"📡 WS: {'✅ Connected' if connected else '⏳ Connecting'}\n"
                f"⚡ Ticks: `{ticks}`\n"
                f"{'🚨 Weekend — Crypto Only!' if is_weekend() else '✅ Markets Open'}\n\n"
                f"Select what you want to do 👇",
                parse_mode="Markdown",
                reply_markup=main_menu_kb()
            )

        # ── SUBSCRIBE TO AUTO SIGNALS
        elif d == "subscribe":
            db.subscribe(uid)
            await query.edit_message_text(
                f"✅ *Auto-Signals Activated!*\n\n"
                f"You will receive top signals automatically "
                f"every *{SIGNAL_INTERVAL_MINUTES} minutes.*\n\n"
                f"Only HIGH confidence signals sent.\n"
                f"Weekend: crypto signals only.\n\n"
                f"Use /unsubscribe to stop.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Main Menu", callback_data="back_main"
                    )
                ]])
            )

        # ── SIGNAL MODE
        elif d == "mode_signal":
            await state_manager.set_user(uid, mode="signal")
            await query.edit_message_text(
                "📊 *Signal Mode*\n\nSelect asset category:",
                parse_mode="Markdown",
                reply_markup=category_kb("signal")
            )

        # ── AUTO TRADING MODE
        elif d == "mode_auto":
            await state_manager.set_user(uid, mode="auto")
            await query.edit_message_text(
                "🤖 *Auto Trading Mode*\n\n"
                "⚠️ Bot will place trades automatically!\n"
                "Select account type:",
                parse_mode="Markdown",
                reply_markup=account_kb()
            )

        # ── ACCOUNT SELECTION
        elif d.startswith("account_"):
            account = d[8:]
            await state_manager.set_user(uid, account=account)
            await query.edit_message_text(
                f"📂 *Select Category:*\n\n"
                f"Account: *{'Demo 🎮' if account == 'demo' else 'Real 💰'}*",
                parse_mode="Markdown",
                reply_markup=category_kb("auto")
            )

        # ── CATEGORY SELECTION
        elif d.startswith("show_category_"):
            mode = d[14:]
            await query.edit_message_text(
                "📂 *Select Category:*",
                parse_mode="Markdown",
                reply_markup=category_kb(mode)
            )

        elif d.startswith("cat_"):
            parts    = d[4:].split("_", 1)
            mode     = parts[0]
            category = parts[1] if len(parts) > 1 else ""
            await query.edit_message_text(
                f"Select asset:",
                parse_mode="Markdown",
                reply_markup=assets_kb(category, mode)
            )

        # ── ASSET SELECTION
        elif d.startswith("asset_"):
            rest  = d[6:]
            parts = rest.split("_", 1)
            mode  = parts[0]
            asset = parts[1] if len(parts) > 1 else ""

            await state_manager.set_user(uid, asset=asset)

            payout = await state_manager.get_payout(asset)
            price  = await state_manager.get_price(asset)
            pout_txt  = f"\nPayout: `{payout:.0f}%`" if payout > 0 else ""
            price_txt = f"\nPrice:  `{price}`"        if price > 0  else ""

            await query.edit_message_text(
                f"⏱ *Select Expiry:*\n"
                f"*{asset_name(asset)}*"
                f"{pout_txt}{price_txt}",
                parse_mode="Markdown",
                reply_markup=expiry_kb(asset, mode)
            )

        # ── EXPIRY SELECTION
        elif d.startswith("expiry_"):
            rest   = d[7:]
            parts  = rest.split("_", 1)
            mode   = parts[0]
            remain = parts[1] if len(parts) > 1 else ""
            # last underscore separates asset from expiry
            last_  = remain.rfind("_")
            if last_ == -1:
                return
            asset  = remain[:last_]
            expiry = remain[last_ + 1:]

            await state_manager.set_user(
                uid, asset=asset, expiry=expiry
            )

            if mode == "auto":
                await query.edit_message_text(
                    f"💰 *Enter Trade Amount ($)*\n\n"
                    f"Asset:  *{asset_name(asset)}*\n"
                    f"Expiry: *{expiry}*\n\n"
                    f"Type your amount (e.g. 1, 5, 10):",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "⬅ Back",
                            callback_data=f"show_category_auto"
                        )
                    ]])
                )
                await state_manager.set_user(
                    uid, awaiting_amount=True
                )
            else:
                await query.edit_message_text(
                    f"⏳ Getting signal for *{asset_name(asset)}*...",
                    parse_mode="Markdown"
                )
                sig  = await signal_engine.get_signal(asset, expiry)
                text = await build_signal_msg(asset, expiry, sig)
                if sig:
                    db.log_signal(
                        uid, asset, expiry,
                        sig["signal"],
                        sig["confidence"],
                        sig["price"],
                        sig["adx"],
                        sig["williams_r"]
                    )
                await query.edit_message_text(
                    text,
                    parse_mode="Markdown",
                    reply_markup=signal_action_kb(asset, expiry)
                )

        # ── CONFIRM TRADE
        elif d == "confirm_trade":
            udata   = await state_manager.get_user(uid)
            asset   = udata.get("asset", "")
            expiry  = udata.get("expiry", "1m")
            amount  = udata.get("amount", "1")
            account = udata.get("account", "demo")
            sig     = await signal_engine.get_signal(asset, expiry)

            if not sig or sig["signal"] == "HOLD":
                await query.edit_message_text(
                    "⏸ *Signal is HOLD — trade not placed.*\n\n"
                    "Wait for a stronger signal.",
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
                    f"⚠️ Confidence too low `{sig['conf_bar']}`\n\n"
                    "Wait for a stronger setup.",
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
            await state_manager.set_user(uid, auto_running=True)

            icon = signal_icon(sig["signal"])
            await query.edit_message_text(
                f"⏳ *Trade Queued!*\n\n"
                f"Asset:   *{asset_name(asset)}*\n"
                f"Signal:  {icon} *{sig['signal']}*\n"
                f"Amount:  *${amount}*\n"
                f"Expiry:  *{expiry}*\n"
                f"Account: *{'Demo 🎮' if account == 'demo' else 'Real 💰'}*\n\n"
                f"Executing with human-like delay...",
                parse_mode="Markdown",
                reply_markup=auto_running_kb()
            )

        # ── STOP AUTO TRADING ONLY
        elif d == "stop_auto":
            await state_manager.set_user(
                uid, auto_running=False
            )
            await query.edit_message_text(
                "🛑 *Auto-Trading Stopped.*\n\n"
                "Signal mode is still active.\n"
                "Choose what to do next:",
                parse_mode="Markdown",
                reply_markup=main_menu_kb()
            )

        # ── SCAN
        elif d == "scan":
            await query.edit_message_text(
                "🔍 *Scanning markets...*\nPlease wait ⏳",
                parse_mode="Markdown"
            )
            await _do_scan(query.message)

        # ── SESSIONS
        elif d == "sessions":
            now  = datetime.now(timezone.utc) + timedelta(hours=1)
            h    = now.hour
            if 22 <= h or h < 7:
                sess = "🇯🇵 Tokyo"
            elif 7 <= h < 9:
                sess = "🌏 Tokyo/London"
            elif 9 <= h < 13:
                sess = "🇬🇧 London"
            elif 13 <= h < 17:
                sess = "🌍 London/NY Overlap ⭐"
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
                f"💡 _ADX signals strongest at session opens!_",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Menu", callback_data="back_main"
                    )
                ]])
            )

        # ── STATS
        elif d == "stats":
            udata  = await state_manager.get_user(uid)
            stats  = db.get_user_stats(uid)
            top    = db.get_top_assets(5)
            trades = trade_executor.get_total()
            active = await trade_executor.get_active()

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
                f"Auto trades: `{trades}`\n"
                f"Active: `{len(active)}`",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Menu", callback_data="back_main"
                    )
                ]])
            )

        # ── HELP
        elif d == "help":
            await query.edit_message_text(
                "❓ *How To Use ApexSignal*\n"
                "━━━━━━━━━━━━━━━\n\n"
                "📊 *Signal Mode:*\n"
                "1. Tap Get Signal\n"
                "2. Choose category\n"
                "3. Select asset\n"
                "4. Select expiry time\n"
                "5. Get AI signal\n"
                "6. Trade on Pocket Option\n"
                "7. Log WIN or LOSS\n\n"
                "🤖 *Auto Trading:*\n"
                "1. Tap Auto Trading\n"
                "2. Choose Demo or Real\n"
                "3. Select asset + expiry\n"
                "4. Enter amount\n"
                "5. Confirm — bot trades!\n\n"
                "🔔 *Auto Signals:*\n"
                "Tap Subscribe to get signals\n"
                "automatically every 5 mins.\n\n"
                "📊 *Commands:*\n"
                "/start — Main menu\n"
                "/scan — Scan all markets\n"
                "/stop — Stop auto trading\n"
                "/status — Bot status\n"
                "/unsubscribe — Stop signals\n\n"
                "💡 *Tips:*\n"
                "• Only trade ADX > 22\n"
                "• Best: London/NY sessions\n"
                "• Weekend: crypto only!\n\n"
                "⚠️ _Trade at your own risk._",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Main Menu", callback_data="back_main"
                    )
                ]])
            )

        # ── LOG WIN
        elif d.startswith("win_"):
            asset = d[4:]
            udata = await state_manager.get_user(uid)
            db.log_trade_result(
                uid, asset, "BUY",
                udata.get("expiry", "1m"),
                "WIN",
                float(udata.get("amount", "1"))
            )
            await query.edit_message_text(
                f"✅ *WIN logged for {asset_name(asset)}!* 🎉\n\n"
                f"Keep it up! Check /stats.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Menu", callback_data="back_main"
                    )
                ]])
            )

        # ── LOG LOSS
        elif d.startswith("loss_"):
            asset = d[5:]
            udata = await state_manager.get_user(uid)
            db.log_trade_result(
                uid, asset, "SELL",
                udata.get("expiry", "1m"),
                "LOSS",
                float(udata.get("amount", "1"))
            )
            await query.edit_message_text(
                f"❌ *LOSS logged for {asset_name(asset)}*\n\n"
                f"Stay disciplined! 💪 Check /stats.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "🏠 Menu", callback_data="back_main"
                    )
                ]])
            )

    except Exception as e:
        logger.error(f"button_cb error [{d}]: {e}")
        try:
            await query.edit_message_text(
                "❌ Error occurred. Type /start to restart."
            )
        except Exception:
            pass


# ─────────────────────────────────────
# MESSAGE HANDLER (trade amount input)
# ─────────────────────────────────────

async def handle_message(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE
):
    try:
        uid   = update.effective_user.id
        text  = update.message.text.strip()
        udata = await state_manager.get_user(uid)

        if not udata.get("awaiting_amount"):
            return

        try:
            amount = float(text)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except (ValueError, TypeError):
            await update.message.reply_text(
                "❌ Invalid amount.\n"
                "Enter a number like: 1, 5, 10"
            )
            return

        await state_manager.set_user(
            uid, amount=str(amount), awaiting_amount=False
        )

        asset   = udata.get("asset", "")
        expiry  = udata.get("expiry", "1m")
        account = udata.get("account", "demo")
        sig     = await signal_engine.get_signal(asset, expiry)
        payout  = await state_manager.get_payout(asset)

        sig_txt = ""
        if sig:
            icon  = signal_icon(sig["signal"])
            p     = sig.get("payout", payout)
            pout  = f"\nPayout:   `{p:.0f}%`" if p > 0 else ""
            sig_txt = (
                f"\n📊 Signal: *{icon} {sig['signal']}*\n"
                f"Confidence: `{sig['conf_bar']}`{pout}\n"
            )

        await update.message.reply_text(
            f"📋 *Trade Confirmation*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Asset:   *{asset_name(asset)}*\n"
            f"Expiry:  *{expiry}*\n"
            f"Amount:  *${amount}*\n"
            f"Account: *{'Demo 🎮' if account == 'demo' else 'Real 💰'}*\n"
            f"{sig_txt}\n"
            f"Tap Confirm to execute trade:",
            parse_mode="Markdown",
            reply_markup=confirm_trade_kb()
        )

    except Exception as e:
        logger.error(f"handle_message error: {e}")


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
            scan_list = CRYPTO_OTC[:8] + CRYPTO_MAIN[:4]
        else:
            scan_list = (
                FOREX_OTC[:6] + FOREX_MAIN[:4] +
                CRYPTO_OTC[:4] + CRYPTO_MAIN[:4] +
                COMMODITY_OTC + COMMODITY_MAIN
            )

        best_asset = None
        best_sig   = None
        best_score = 0

        for asset in scan_list:
            sig = await signal_engine.get_signal(asset, "5m")
            if (sig and
                    sig["signal"] != "HOLD" and
                    sig["confidence"] >= 3 and
                    sig["confidence"] > best_score):
                best_score = sig["confidence"]
                best_asset = asset
                best_sig   = sig

        if not best_asset or not best_sig:
            logger.info("No signals for broadcast")
            return

        text = await build_signal_msg(
            best_asset, "5m", best_sig, show_ai=False
        )
        msg = "🚨 *AUTO-SIGNAL ALERT*\n\n" + text

        for uid in subs:
            try:
                udata   = await state_manager.get_user(uid)
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
# STARTUP
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

    logger.info("✅ All ApexSignal services started!")


def main():
    token = BOT_TOKEN
    if not token:
        logger.error("BOT_TOKEN not set in Railway!")
        return

    application = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )

    application.add_handler(CommandHandler("start",       cmd_start))
    application.add_handler(CommandHandler("scan",        cmd_scan))
    application.add_handler(CommandHandler("stop",        cmd_stop))
    application.add_handler(CommandHandler("status",      cmd_status))
    application.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
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

    logger.info("ApexSignal PO Bot starting...")
    print("✅ ApexSignal is LIVE!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
