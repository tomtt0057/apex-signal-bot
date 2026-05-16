import asyncio
import json
import logging
import random
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class TradeExecutor:
    MAX_CONCURRENT = 3
    MIN_INTERVAL   = 5
    MAX_VARIANCE   = 0.15

    EXPIRY_SECONDS = {
        "30s": 30,
        "1m":  60,
        "2m":  120,
        "15m": 900,
        "1H":  3600,
    }

    def __init__(self, state_manager):
        self.state_manager  = state_manager
        self._ws_client     = None
        self._queue         = asyncio.Queue()
        self._lock          = asyncio.Lock()
        self._active        = []
        self._total         = 0
        self._last_trade    = 0
        self._running       = False
        self._notify_cb     = None

    def set_ws_client(self, ws_client):
        self._ws_client = ws_client

    def set_notify_callback(self, cb):
        self._notify_cb = cb

    async def _notify(self, msg, user_id=None):
        if self._notify_cb:
            try:
                await self._notify_cb(msg, user_id)
            except Exception as e:
                logger.error(f"Notify error: {e}")

    async def start(self):
        self._running = True
        asyncio.create_task(self._execution_loop())
        logger.info("TradeExecutor started")

    async def stop(self):
        self._running = False

    async def queue_trade(
        self, user_id, asset, direction,
        amount, expiry, account="demo"
    ):
        trade = {
            "user_id":   user_id,
            "asset":     asset,
            "direction": direction,
            "amount":    str(amount),
            "expiry":    expiry,
            "account":   account,
            "queued_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._queue.put(trade)
        logger.info(
            f"Trade queued: {direction} {asset} "
            f"${amount} [{expiry}]"
        )

    async def _execution_loop(self):
        while self._running:
            try:
                trade = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
                await self._execute(trade)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Execution error: {e}")
                await asyncio.sleep(1)

    async def _execute(self, trade):
        async with self._lock:
            try:
                # Check concurrent limit
                if len(self._active) >= self.MAX_CONCURRENT:
                    await self._notify(
                        "⚠️ Max concurrent trades reached — skipped",
                        trade["user_id"]
                    )
                    return

                # Check interval
                now = time.time()
                since_last = now - self._last_trade
                if since_last < self.MIN_INTERVAL and self._last_trade > 0:
                    await asyncio.sleep(
                        self.MIN_INTERVAL - since_last
                    )

                # Check WebSocket
                ws = self._ws_client.get_ws() if self._ws_client else None
                if not ws or ws.closed:
                    await self._notify(
                        "❌ Cannot trade — WebSocket disconnected",
                        trade["user_id"]
                    )
                    return

                # Human-like delay
                await asyncio.sleep(random.uniform(0.35, 0.85))

                # Randomize amount
                base   = float(trade["amount"])
                extra  = random.uniform(0, self.MAX_VARIANCE)
                amount = round(base + extra, 2)

                # Build payload
                exp_sec = self.EXPIRY_SECONDS.get(
                    trade["expiry"], 60
                )
                direction_code = 1 if trade["direction"] == "BUY" else 0
                is_demo = 1 if trade["account"] == "demo" else 0

                payload = json.dumps([
                    "openOrder",
                    {
                        "asset":      trade["asset"],
                        "amount":     amount,
                        "action":     direction_code,
                        "isDemo":     is_demo,
                        "requestId":  int(time.time() * 1000),
                        "optionType": 100,
                        "time":       exp_sec,
                    }
                ])

                # Send trade
                await ws.send("42" + payload)
                self._last_trade = time.time()
                self._total += 1
                trade_id = f"T{self._total:04d}"

                self._active.append({
                    "id":        trade_id,
                    "asset":     trade["asset"],
                    "direction": trade["direction"],
                    "amount":    amount,
                    "expiry":    trade["expiry"],
                    "opened_at": datetime.now(timezone.utc).isoformat(),
                })

                icon = "🟢" if trade["direction"] == "BUY" else "🔴"
                acct = "DEMO 🎮" if trade["account"] == "demo" else "REAL 💰"

                await self._notify(
                    f"✅ *Trade Placed!*\n"
                    f"━━━━━━━━━━━━━━━━━\n"
                    f"ID:        `{trade_id}`\n"
                    f"Asset:     *{trade['asset']}*\n"
                    f"Direction: {icon} *{trade['direction']}*\n"
                    f"Amount:    `${amount}`\n"
                    f"Expiry:    `{trade['expiry']}`\n"
                    f"Account:   `{acct}`\n"
                    f"Time:      `{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC`",
                    trade["user_id"]
                )

                # Remove after expiry
                asyncio.create_task(
                    self._expire_trade(trade_id, exp_sec)
                )

            except Exception as e:
                logger.error(f"Execute error: {e}")
                await self._notify(
                    f"❌ Trade failed: {e}",
                    trade["user_id"]
                )

    async def _expire_trade(self, trade_id, seconds):
        await asyncio.sleep(seconds)
        self._active = [
            t for t in self._active if t["id"] != trade_id
        ]

    async def get_active(self):
        return list(self._active)

    def get_total(self):
        return self._total
