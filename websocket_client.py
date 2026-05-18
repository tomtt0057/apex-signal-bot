import asyncio
import json
import logging
from datetime import datetime, timezone
from config import PO_WS_URL, PO_SSID, PO_AUTH_PAYLOAD

logger = logging.getLogger(__name__)


class PocketOptionWS:
    PING_INTERVAL   = 25
    RECONNECT_DELAY = 10

    def __init__(self, candle_engine, state_manager):
        self.candle_engine    = candle_engine
        self.state_manager    = state_manager
        self._ws              = None
        self._running         = False
        self._reconnect_count = 0
        self._notify_cb       = None
        self._tick_count      = 0
        self._notified_once   = False
        self._auth_confirmed  = False
        self._last_error      = ""
        self._connection_log  = []

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

    def get_last_error(self):
        return self._last_error

    def get_connection_log(self):
        return list(self._connection_log)

    def is_auth_confirmed(self):
        return self._auth_confirmed

    def _log(self, msg):
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        entry = f"[{timestamp}] {msg}"
        self._connection_log.append(entry)
        if len(self._connection_log) > 20:
            self._connection_log.pop(0)
        logger.info(msg)

    async def _connect_loop(self):
        while self._running:
            try:
                self._log(f"Connect attempt #{self._reconnect_count + 1}")
                await self._connect()
            except Exception as e:
                self._last_error = str(e)
                self._log(f"Connection failed: {e}")
                await self.state_manager.set_connected(False)
                self._auth_confirmed = False
                self._reconnect_count += 1
                wait = min(self.RECONNECT_DELAY * self._reconnect_count, 60)
                self._log(f"Waiting {wait}s before retry...")
                await asyncio.sleep(wait)

    async def _connect(self):
        import websockets

        if not PO_WS_URL:
            self._last_error = "PO_WS_URL not set in Railway variables!"
            self._log(f"ERROR: {self._last_error}")
            await asyncio.sleep(60)
            return

        if not PO_AUTH_PAYLOAD:
            self._last_error = "PO_AUTH_PAYLOAD not set in Railway variables!"
            self._log(f"ERROR: {self._last_error}")
            await asyncio.sleep(60)
            return

        self._log(f"Connecting to: {PO_WS_URL[:50]}...")

        async with websockets.connect(
            PO_WS_URL,
            extra_headers={
                "Origin":     "https://pocketoption.com",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Cache-Control": "no-cache",
                "Pragma":        "no-cache",
            },
            ping_interval=None,
            max_size=10 * 1024 * 1024,
            open_timeout=15,
        ) as ws:
            self._ws = ws
            self._log("TCP connection established")

            try:
                init = await asyncio.wait_for(ws.recv(), timeout=15)
                self._log(f"Received init: {str(init)[:120]}")
            except asyncio.TimeoutError:
                raise Exception("Timeout waiting for init message")

            await ws.send("40")
            self._log("Sent: 40 (socket.io upgrade)")

            try:
                ready = await asyncio.wait_for(ws.recv(), timeout=15)
                self._log(f"Received ready: {str(ready)[:120]}")
            except asyncio.TimeoutError:
                self._log("Warning: timeout on ready message, continuing...")

            self._log(f"Sending auth payload ({len(PO_AUTH_PAYLOAD)} chars)...")
            self._log(f"Auth preview: {PO_AUTH_PAYLOAD[:80]}...")
            await ws.send(PO_AUTH_PAYLOAD)
            self._log("Auth payload sent — waiting for confirmation...")

            try:
                auth_resp = await asyncio.wait_for(ws.recv(), timeout=15)
                self._log(f"Auth response: {str(auth_resp)[:200]}")
                if "success" in str(auth_resp).lower():
                    self._auth_confirmed = True
                    self._log("✅ AUTH CONFIRMED by server!")
                elif "error" in str(auth_resp).lower():
                    self._log("❌ AUTH ERROR from server!")
                    self._last_error = f"Auth rejected: {str(auth_resp)[:100]}"
                    raise Exception(self._last_error)
                else:
                    self._log("Auth response received (processing...)")
                    await self._handle_message(auth_resp)
            except asyncio.TimeoutError:
                self._log("Warning: no auth response — may still work")

            await self.state_manager.set_connected(True)
            self._reconnect_count = 0

            if not self._notified_once:
                self._notified_once = True
                await self._notify(
                    "✅ *Connected to Pocket Option!*\n"
                    "📡 Receiving real-time tick data.\n"
                    "⏱ First signals ready in ~2 minutes.\n\n"
                    "Use /scan to check signals."
                )

            self._log("Starting heartbeat and message processing...")
            asyncio.create_task(self._heartbeat(ws))

            msg_count = 0
            async for message in ws:
                if not self._running:
                    break
                await self._handle_message(message)
                msg_count += 1
                if msg_count % 100 == 0:
                    self._log(f"Processed {msg_count} messages, {self._tick_count} ticks")

        await self.state_manager.set_connected(False)
        self._auth_confirmed = False
        self._log("WebSocket connection closed cleanly")

    async def _heartbeat(self, ws):
        while self._running:
            try:
                await asyncio.sleep(self.PING_INTERVAL)
                if ws.closed:
                    self._log("WebSocket closed — stopping heartbeat")
                    break
                await ws.send("2")
                await self.state_manager.update_heartbeat()
                logger.debug("Ping sent ✓")
            except Exception as e:
                self._log(f"Heartbeat error: {e}")
                break

    async def _handle_message(self, message):
        try:
            # ── Fix: handle binary frames from Pocket Option
            if isinstance(message, bytes):
                message = message.decode('utf-8')

            # Pong
            if message == "3":
                return

            # Socket.io ping — respond with pong
            if message == "2":
                if self._ws and not self._ws.closed:
                    await self._ws.send("3")
                return

            # Non-data messages
            if not message.startswith("42"):
                return

            raw = message[2:]
            if not raw.startswith("["):
                return

            data = json.loads(raw)
            if not isinstance(data, list) or len(data) < 1:
                return

            event   = data[0]
            payload = data[1] if len(data) > 1 else {}

            if event in ("tick", "quote", "price"):
                await self._on_tick(payload)

            elif event in ("candle", "candleGenerated", "newCandle"):
                await self._on_candle(payload)

            elif event in ("candles", "history", "candleHistory"):
                await self._on_candles_batch(payload)

            elif event in (
                "asset", "assets", "assetsList",
                "openOptions", "loadHistoryPeriod"
            ):
                await self._on_assets(payload)

            elif event in (
                "changeSymbol", "updateStream", "stream",
                "priceUpdate", "symbolUpdate"
            ):
                await self._on_price_update(payload)

            elif event in ("successauth", "successLogin", "authenticated"):
                self._auth_confirmed = True
                self._log(f"✅ Auth success event: {event}")

            elif event in ("reconnect", "connect"):
                self._log(f"Server event: {event}")

            else:
                logger.debug(f"Unhandled event: {event}")

        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.error(f"Message handle error: {e}")

    async def _on_tick(self, payload):
        try:
            asset = (
                payload.get("asset") or
                payload.get("symbol") or
                payload.get("active") or
                payload.get("pair", "")
            )
            price = float(
                payload.get("price") or
                payload.get("value") or
                payload.get("close") or
                payload.get("ask", 0)
            )
            ts = float(
                payload.get("time") or
                payload.get("timestamp") or
                payload.get("t") or
                datetime.now(timezone.utc).timestamp()
            )
            if asset and price > 0:
                await self.candle_engine.add_tick(asset, price, ts)
                await self.state_manager.set_price(asset, price)
                self._tick_count += 1
                if self._tick_count == 1:
                    self._log(f"First tick received! Asset:{asset} Price:{price}")
                elif self._tick_count % 500 == 0:
                    self._log(f"Tick #{self._tick_count}: {asset}={price}")
        except Exception as e:
            logger.debug(f"Tick error: {e}")

    async def _on_candle(self, payload):
        try:
            asset = (
                payload.get("asset") or
                payload.get("active") or
                payload.get("symbol", "")
            )
            price = float(
                payload.get("close") or
                payload.get("price") or
                payload.get("c", 0)
            )
            ts = float(
                payload.get("time") or
                payload.get("timestamp") or
                payload.get("t") or
                datetime.now(timezone.utc).timestamp()
            )
            payout = float(payload.get("profit") or payload.get("payout", 0))

            if asset and price > 0:
                await self.candle_engine.add_tick(asset, price, ts)
                await self.state_manager.set_price(asset, price)
                self._tick_count += 1

            if asset and payout > 0:
                await self.state_manager.set_payout(asset, payout)

        except Exception as e:
            logger.debug(f"Candle error: {e}")

    async def _on_candles_batch(self, payload):
        try:
            asset   = payload.get("asset") or payload.get("active", "")
            candles = (
                payload.get("candles") or
                payload.get("data") or
                payload.get("history") or []
            )

            count = 0
            for c in candles:
                price = float(
                    c.get("close") or c.get("c") or
                    c.get("price", 0)
                )
                ts = float(
                    c.get("time") or c.get("t") or
                    c.get("timestamp", 0)
                )
                if asset and price > 0 and ts > 0:
                    await self.candle_engine.add_tick(asset, price, ts)
                    count += 1

            if count > 0:
                self._tick_count += count
                self._log(f"Batch loaded: {count} candles for {asset}")

        except Exception as e:
            logger.debug(f"Batch error: {e}")

    async def _on_assets(self, payload):
        try:
            items = payload if isinstance(payload, list) else [payload]
            count = 0
            for item in items:
                if not isinstance(item, dict):
                    continue
                asset = (
                    item.get("symbol") or item.get("asset") or
                    item.get("name") or item.get("id") or
                    item.get("active", "")
                )
                payout = float(
                    item.get("profit") or item.get("payout") or
                    item.get("payment") or item.get("yield") or
                    item.get("profitPercent", 0)
                )
                if asset and payout > 0:
                    await self.state_manager.set_payout(asset, payout)
                    count += 1

                price = float(
                    item.get("price") or item.get("value") or
                    item.get("close", 0)
                )
                if asset and price > 0:
                    await self.state_manager.set_price(asset, price)

            if count > 0:
                self._log(f"Payouts updated for {count} assets")

        except Exception as e:
            logger.debug(f"Assets error: {e}")

    async def _on_price_update(self, payload):
        try:
            if isinstance(payload, dict):
                asset = (
                    payload.get("asset") or
                    payload.get("symbol") or
                    payload.get("active", "")
                )
                price = float(
                    payload.get("price") or
                    payload.get("close") or
                    payload.get("value") or
                    payload.get("ask", 0)
                )
                ts = float(
                    payload.get("time") or
                    payload.get("timestamp") or
                    datetime.now(timezone.utc).timestamp()
                )
                payout = float(
                    payload.get("profit") or
                    payload.get("payout", 0)
                )
                if asset and price > 0:
                    await self.candle_engine.add_tick(asset, price, ts)
                    await self.state_manager.set_price(asset, price)
                    self._tick_count += 1
                if asset and payout > 0:
                    await self.state_manager.set_payout(asset, payout)

        except Exception as e:
            logger.debug(f"Price update error: {e}")
