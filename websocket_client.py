import asyncio
import json
import logging
from datetime import datetime, timezone
from config import PO_WS_URL, PO_SSID, PO_AUTH_PAYLOAD

logger = logging.getLogger(__name__)


class PocketOptionWS:
    PING_INTERVAL   = 20
    RECONNECT_DELAY = 5

    def __init__(self, candle_engine, state_manager):
        self.candle_engine    = candle_engine
        self.state_manager    = state_manager
        self._ws              = None
        self._running         = False
        self._reconnect_count = 0
        self._notify_cb       = None
        self._tick_count      = 0
        # Only notify user ONCE on first successful connect
        self._notified_once   = False

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

    def get_tick_count(self):
        return self._tick_count

    async def _connect_loop(self):
        while self._running:
            try:
                await self._connect()
            except Exception as e:
                logger.error(f"WS connection error: {e}")
                await self.state_manager.set_connected(False)
                self._reconnect_count += 1
                # Silent reconnect — do NOT spam user
                logger.info(
                    f"Reconnecting in {self.RECONNECT_DELAY}s "
                    f"(attempt {self._reconnect_count})"
                )
                await asyncio.sleep(self.RECONNECT_DELAY)

    async def _connect(self):
        import websockets

        if not PO_WS_URL:
            logger.error("PO_WS_URL not set! Check Railway variables.")
            await asyncio.sleep(30)
            return

        if not PO_AUTH_PAYLOAD:
            logger.error("PO_AUTH_PAYLOAD not set! Check Railway variables.")
            await asyncio.sleep(30)
            return

        logger.info("Connecting to Pocket Option WebSocket...")

        async with websockets.connect(
            PO_WS_URL,
            extra_headers={
                "Origin":     "https://pocketoption.com",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/120.0.0.0"
                )
            },
            ping_interval=None,
            max_size=10 * 1024 * 1024
        ) as ws:
            self._ws = ws
            logger.info("WebSocket connected — starting handshake")

            # Step 1 — receive init message
            try:
                init = await asyncio.wait_for(ws.recv(), timeout=10)
                logger.debug(f"Init received: {str(init)[:80]}")
            except asyncio.TimeoutError:
                logger.error("Timeout waiting for init message")
                return

            # Step 2 — send socket.io upgrade
            await ws.send("40")
            logger.debug("Sent: 40")

            # Step 3 — wait for socket.io ready
            try:
                ready = await asyncio.wait_for(ws.recv(), timeout=10)
                logger.debug(f"Ready: {str(ready)[:80]}")
            except asyncio.TimeoutError:
                logger.warning("Timeout on ready — continuing anyway")

            # Step 4 — send auth payload from Railway env
            await ws.send(PO_AUTH_PAYLOAD)
            logger.info("Auth payload sent to PO")

            # Mark connected
            await self.state_manager.set_connected(True)
            self._reconnect_count = 0

            # Only notify user on VERY FIRST connection
            # This prevents spam on reconnects
            if not self._notified_once:
                self._notified_once = True
                await self._notify(
                    "✅ *Connected to Pocket Option!*\n"
                    "📡 Real-time data active.\n"
                    "⏱ First signals ready in ~1-2 minutes."
                )

            # Start heartbeat
            asyncio.create_task(self._heartbeat(ws))

            # Process all incoming messages
            async for message in ws:
                if not self._running:
                    break
                await self._handle_message(message)

        # If we exit the context manager the connection closed
        await self.state_manager.set_connected(False)
        logger.info("WebSocket connection closed")

    async def _heartbeat(self, ws):
        while self._running:
            try:
                await asyncio.sleep(self.PING_INTERVAL)
                if ws.closed:
                    break
                await ws.send("2")
                await self.state_manager.update_heartbeat()
                logger.debug("Ping sent ✓")
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break

    async def _handle_message(self, message):
        try:
            # Pong response
            if message == "3":
                return

            # Skip non-data messages
            if not message.startswith("42"):
                return

            data = json.loads(message[2:])
            if not isinstance(data, list) or len(data) < 2:
                return

            event   = data[0]
            payload = data[1]

            handlers = {
                "tick":              self._on_tick,
                "quote":             self._on_tick,
                "price":             self._on_tick,
                "candle":            self._on_candle,
                "candleGenerated":   self._on_candle,
                "candles":           self._on_candles_batch,
                "history":           self._on_candles_batch,
                "asset":             self._on_assets,
                "assets":            self._on_assets,
                "assetsList":        self._on_assets,
                "changeSymbol":      self._on_price_update,
                "updateStream":      self._on_price_update,
                "stream":            self._on_price_update,
                "priceUpdate":       self._on_price_update,
                "successauth":       self._on_auth_success,
                "successLogin":      self._on_auth_success,
            }

            handler = handlers.get(event)
            if handler:
                await handler(payload)

        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.error(f"Message handle error: {e}")

    async def _on_auth_success(self, payload):
        logger.info(f"Auth confirmed by PO server: {str(payload)[:100]}")

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
                price = float(c.get("close") or c.get("price", 0))
                ts    = float(c.get("time") or c.get("timestamp", 0))
                if asset and price > 0 and ts > 0:
                    await self.candle_engine.add_tick(asset, price, ts)
        except Exception as e:
            logger.debug(f"Batch error: {e}")

    async def _on_assets(self, payload):
        try:
            items = (
                payload if isinstance(payload, list) else [payload]
            )
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
                    await self.state_manager.set_payout(asset, payout)
                    logger.debug(f"Payout set: {asset} = {payout}%")
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
                    await self.candle_engine.add_tick(asset, price, ts)
                    await self.state_manager.set_price(asset, price)
        except Exception as e:
            logger.debug(f"Price update error: {e}")
