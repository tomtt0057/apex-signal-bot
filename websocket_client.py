import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from config import PO_WS_URL, PO_SSID, PO_AUTH_PAYLOAD

logger = logging.getLogger(__name__)


class PocketOptionWS:
    PING_INTERVAL   = 20
    RECONNECT_DELAY = 5

    def __init__(self, candle_engine, state_manager):
        self.candle_engine   = candle_engine
        self.state_manager   = state_manager
        self._ws             = None
        self._running        = False
        self._reconnect_count = 0
        self._notify_cb      = None
        self._tick_count     = 0

        if not PO_WS_URL:
            logger.error("PO_WS_URL not set in Railway variables!")
        if not PO_SSID:
            logger.error("PO_SSID not set in Railway variables!")
        if not PO_AUTH_PAYLOAD:
            logger.error("PO_AUTH_PAYLOAD not set in Railway variables!")

    def set_notify_callback(self, cb):
        self._notify_cb = cb

    async def _notify(self, msg):
        if self._notify_cb:
            try:
                await self._notify_cb(msg)
            except Exception as e:
                logger.error(f"Notify error: {e}")

    async def start(self):
        self._running = True
        asyncio.create_task(self._connect_loop())
        logger.info("PocketOptionWS starting...")

    async def stop(self):
        self._running = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        await self.state_manager.set_connected(False)

    def get_ws(self):
        return self._ws

    async def _connect_loop(self):
        while self._running:
            try:
                await self._connect()
            except Exception as e:
                logger.error(f"WS error: {e}")
                await self.state_manager.set_connected(False)
                self._reconnect_count += 1
                if self._reconnect_count <= 5:
                    await self._notify(
                        f"⚠️ WebSocket disconnected.\n"
                        f"Reconnecting in {self.RECONNECT_DELAY}s... "
                        f"(attempt {self._reconnect_count})"
                    )
                await asyncio.sleep(self.RECONNECT_DELAY)

    async def _connect(self):
        import websockets
        logger.info(f"Connecting to PO WebSocket...")

        async with websockets.connect(
            PO_WS_URL,
            extra_headers={
                "Origin":     "https://pocketoption.com",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
                )
            },
            ping_interval=None,
            max_size=10 * 1024 * 1024
        ) as ws:
            self._ws = ws
            logger.info("WS connected — running handshake")

            # Step 1 — receive init
            init = await asyncio.wait_for(ws.recv(), timeout=10)
            logger.debug(f"Init: {str(init)[:100]}")

            # Step 2 — send upgrade
            await ws.send("40")

            # Step 3 — wait for ready
            ready = await asyncio.wait_for(ws.recv(), timeout=10)
            logger.debug(f"Ready: {str(ready)[:100]}")

            # Step 4 — send auth from env
            await ws.send(PO_AUTH_PAYLOAD)
            logger.info("Auth payload sent")

            # Connected!
            await self.state_manager.set_connected(True)
            self._reconnect_count = 0

            await self._notify(
                "✅ *Connected to Pocket Option!*\n"
                "📡 Receiving real-time market data...\n"
                "⚡ Signals will be ready in ~1 minute."
            )

            # Start heartbeat
            asyncio.create_task(self._heartbeat(ws))

            # Process all messages
            async for message in ws:
                if not self._running:
                    break
                await self._handle_message(message)

    async def _heartbeat(self, ws):
        while self._running:
            try:
                await asyncio.sleep(self.PING_INTERVAL)
                await ws.send("2")
                await self.state_manager.update_heartbeat()
                logger.debug("Ping sent ✓")
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break

    async def _handle_message(self, message):
        try:
            # Pong
            if message == "3":
                return

            # Ignore non-data messages
            if not message.startswith("42"):
                return

            data = json.loads(message[2:])
            if not isinstance(data, list) or len(data) < 2:
                return

            event   = data[0]
            payload = data[1]

            if event in ("tick", "quote", "price"):
                await self._on_tick(payload)
            elif event in ("candle", "candleGenerated"):
                await self._on_candle(payload)
            elif event in ("candles", "history"):
                await self._on_candles_batch(payload)
            elif event in ("asset", "assets", "assetsList"):
                await self._on_assets(payload)
            elif event in (
                "changeSymbol", "updateStream",
                "stream", "priceUpdate"
            ):
                await self._on_price_update(payload)
            elif event == "successauth":
                logger.info("Auth confirmed by server!")
            elif event == "connect":
                logger.info("Connection confirmed!")

        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.error(f"Message error: {e}")

    async def _on_tick(self, payload):
        try:
            asset = (
                payload.get("asset") or
                payload.get("symbol") or
                payload.get("active", "")
            )
            price = float(
                payload.get("price") or
                payload.get("value") or
                payload.get("close", 0)
            )
            ts = float(
                payload.get("time") or
                payload.get("timestamp") or
                datetime.now(timezone.utc).timestamp()
            )
            if asset and price > 0:
                await self.candle_engine.add_tick(asset, price, ts)
                await self.state_manager.set_price(asset, price)
                self._tick_count += 1
        except Exception as e:
            logger.debug(f"Tick error: {e}")

    async def _on_candle(self, payload):
        try:
            asset = (
                payload.get("asset") or
                payload.get("active", "")
            )
            price = float(
                payload.get("close") or
                payload.get("price", 0)
            )
            ts = float(
                payload.get("time") or
                payload.get("timestamp") or
                datetime.now(timezone.utc).timestamp()
            )
            if asset and price > 0:
                await self.candle_engine.add_tick(asset, price, ts)
                await self.state_manager.set_price(asset, price)
        except Exception as e:
            logger.debug(f"Candle error: {e}")

    async def _on_candles_batch(self, payload):
        try:
            asset = payload.get("asset", "")
            candles = (
                payload.get("candles") or
                payload.get("data") or []
            )
            for c in candles:
                price = float(
                    c.get("close") or c.get("price", 0)
                )
                ts = float(
                    c.get("time") or
                    c.get("timestamp", 0)
                )
                if asset and price > 0 and ts > 0:
                    await self.candle_engine.add_tick(
                        asset, price, ts
                    )
        except Exception as e:
            logger.debug(f"Batch error: {e}")

    async def _on_assets(self, payload):
        try:
            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                if not isinstance(item, dict):
                    continue
                asset = (
                    item.get("symbol") or
                    item.get("asset") or
                    item.get("name") or
                    item.get("id", "")
                )
                payout = float(
                    item.get("profit") or
                    item.get("payout") or
                    item.get("payment") or
                    item.get("yield", 0)
                )
                if asset and payout > 0:
                    await self.state_manager.set_payout(
                        asset, payout
                    )
        except Exception as e:
            logger.debug(f"Assets error: {e}")

    async def _on_price_update(self, payload):
        try:
            if isinstance(payload, dict):
                asset = (
                    payload.get("asset") or
                    payload.get("symbol", "")
                )
                price = float(
                    payload.get("price") or
                    payload.get("close") or
                    payload.get("value", 0)
                )
                ts = float(
                    payload.get("time") or
                    payload.get("timestamp") or
                    datetime.now(timezone.utc).timestamp()
                )
                if asset and price > 0:
                    await self.candle_engine.add_tick(
                        asset, price, ts
                    )
                    await self.state_manager.set_price(
                        asset, price
                    )
        except Exception as e:
            logger.debug(f"Price update error: {e}")

    def get_tick_count(self):
        return self._tick_count
