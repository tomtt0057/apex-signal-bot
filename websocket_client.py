import asyncio
import json
import logging
from datetime import datetime, timezone
from config import PO_WS_URL, PO_AUTH_PAYLOAD

logger = logging.getLogger(__name__)

ASSETS = [
    "EURUSD_OTC", "GBPUSD_OTC", "EURGBP_OTC",
    "USDJPY_OTC", "AUDUSD_OTC", "USDCAD_OTC",
    "EURJPY_OTC", "GBPJPY_OTC", "USDCHF_OTC",
    "NZDUSD_OTC", "AUDCAD_OTC", "EURCAD_OTC",
]


class PocketOptionWS:
    PING_INTERVAL   = 20
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
                self._log(
                    f"Connect attempt #{self._reconnect_count + 1}"
                )
                await self._connect()
            except Exception as e:
                self._last_error = str(e)
                self._log(f"Connection failed: {e}")
                await self.state_manager.set_connected(False)
                self._auth_confirmed = False
                self._reconnect_count += 1
                wait = min(
                    self.RECONNECT_DELAY * self._reconnect_count, 60
                )
                self._log(f"Waiting {wait}s before retry...")
                await asyncio.sleep(wait)

    async def _connect(self):
        import websockets

        if not PO_AUTH_PAYLOAD:
            self._last_error = "PO_AUTH_PAYLOAD not set!"
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
                if isinstance(init, bytes):
                    init = init.decode("utf-8")
                self._log(f"Init: {init[:100]}")
            except asyncio.TimeoutError:
                raise Exception("Timeout on init")

            await ws.send("40")
            self._log("Sent: 40")

            try:
                ready = await asyncio.wait_for(ws.recv(), timeout=15)
                if isinstance(ready, bytes):
                    ready = ready.decode("utf-8")
                self._log(f"Ready: {ready[:100]}")
            except asyncio.TimeoutError:
                self._log("No ready message — continuing...")

            self._log("Sending auth...")
            await ws.send(PO_AUTH_PAYLOAD)
            self._log("Auth sent!")

            try:
                auth_resp = await asyncio.wait_for(
                    ws.recv(), timeout=15
                )
                if isinstance(auth_resp, bytes):
                    auth_resp = auth_resp.decode("utf-8")
                self._log(f"Auth resp: {auth_resp[:200]}")
            except asyncio.TimeoutError:
                self._log("No auth response — continuing...")

            self._auth_confirmed = True
            await self.state_manager.set_connected(True)
            self._reconnect_count = 0

            self._log("Subscribing to assets...")
            await ws.send(
                '42["changeSymbol",{"asset":"EURUSD_OTC","period":1}]'
            )
            self._log("Symbol changed to EURUSD_OTC")
            await asyncio.sleep(1)

            self._log("Requesting history...")
            for asset in ASSETS:
                hist_msg = json.dumps([
                    "loadHistoryPeriod",
                    {
                        "asset":  asset,
                        "index":  1,
                        "time":   60,
                        "offset": 100
                    }
                ])
                await ws.send(f"42{hist_msg}")
                await asyncio.sleep(0.05)

            if not self._notified_once:
                self._notified_once = True
                await self._notify(
                    "✅ *Connected to Pocket Option!*\n"
                    "📡 Subscribed to live tick data.\n"
                    "⚡ Signals loading...\n\n"
                    "Use /start to get signals."
                )

            self._log("Starting heartbeat...")
            asyncio.create_task(self._heartbeat(ws))

            msg_count = 0
            async for message in ws:
                if not self._running:
                    break
                if isinstance(message, bytes):
                    message = message.decode("utf-8")
                await self._handle_message(message)
                msg_count += 1
                if msg_count % 200 == 0:
                    self._log(
                        f"Messages: {msg_count} "
                        f"Ticks: {self._tick_count}"
                    )

        await self.state_manager.set_connected(False)
        self._auth_confirmed = False
        self._log("Disconnected")

    async def _heartbeat(self, ws):
        while self._running:
            try:
                await asyncio.sleep(self.PING_INTERVAL)
                if ws.closed:
                    break
                await ws.send("2")
                await self.state_manager.update_heartbeat()
                logger.debug("Ping ✓")
            except Exception as e:
                self._log(f"Heartbeat error: {e}")
                break

    async def _handle_message(self, message):
        try:
            if self._tick_count == 0 and self._reconnect_count == 0:
                logger.info(f"RAW MSG: {message[:150]}")

            if message == "3":
                return

            if message == "2":
                if self._ws and not self._ws.closed:
                    await self._ws.send("3")
                return

            raw = message
            for prefix in ["451-", "42"]:
                if raw.startswith(prefix):
                    raw = raw[len(prefix):]
                    break
            else:
                return

            if not raw.startswith("["):
                return

            data = json.loads(raw)
            if not isinstance(data, list) or len(data) < 1:
                return

            event   = data[0]
            payload = data[1] if len(data) > 1 else {}

            if event in (
                "tick", "quote", "price",
                "newPrice", "price_update"
            ):
                await self._on_tick(payload)

            elif event in (
                "candle", "candleGenerated", "newCandle",
                "history", "candles", "candleHistory",
                "loadHistoryPeriod"
            ):
                await self._on_candles(payload)

            elif event in (
                "updateAssets", "openOptions",
                "assetsList", "assets"
            ):
                await self._on_assets(payload)

            elif event in (
                "changeSymbol", "updateStream",
                "stream", "priceUpdate"
            ):
                await self._on_tick(payload)

            elif event in (
                "successauth", "authenticated",
                "successLogin"
            ):
                self._auth_confirmed = True
                self._log(f"✅ Auth confirmed: {event}")

            else:
                logger.info(
                    f"EVENT: {event} | {str(payload)[:100]}"
                )

        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.debug(f"Handle error: {e}")

    async def _on_tick(self, payload):
        try:
            if not isinstance(payload, dict):
                return
            asset = (
                payload.get("asset") or
                payload.get("symbol") or
                payload.get("active") or
                payload.get("pair") or
                payload.get("id", "")
            )
            price = float(
                payload.get("price") or
                payload.get("value") or
                payload.get("close") or
                payload.get("ask") or
                payload.get("c", 0)
            )
            ts = float(
                payload.get("time") or
                payload.get("timestamp") or
                payload.get("t") or
                datetime.now(timezone.utc).timestamp()
            )
            if asset and price > 0:
                asset = asset.upper()
                await self.candle_engine.add_tick(asset, price, ts)
                await self.state_manager.set_price(asset, price)
                self._tick_count += 1
                if self._tick_count == 1:
                    self._log(f"🎯 FIRST TICK! {asset}={price}")
                elif self._tick_count % 500 == 0:
                    self._log(
                        f"Tick #{self._tick_count}: {asset}={price}"
                    )
        except Exception as e:
            logger.debug(f"Tick error: {e}")

    async def _on_candles(self, payload):
        try:
            if isinstance(payload, dict):
                asset = (
                    payload.get("asset") or
                    payload.get("active") or
                    payload.get("symbol", "")
                ).upper()
                candles = (
                    payload.get("candles") or
                    payload.get("data") or
                    payload.get("history") or []
                )
                price = float(
                    payload.get("close") or
                    payload.get("price") or
                    payload.get("c", 0)
                )
                ts = float(
                    payload.get("time") or
                    payload.get("t") or
                    datetime.now(timezone.utc).timestamp()
                )
                if asset and price > 0:
                    await self.candle_engine.add_tick(asset, price, ts)
                    self._tick_count += 1
                count = 0
                for c in candles:
                    if isinstance(c, list) and len(c) >= 2:
                        t = float(c[0])
                        p = float(c[1])
                    elif isinstance(c, dict):
                        p = float(
                            c.get("close") or c.get("c") or
                            c.get("price", 0)
                        )
                        t = float(
                            c.get("time") or c.get("t") or
                            c.get("timestamp", 0)
                        )
                    else:
                        continue
                    if asset and p > 0 and t > 0:
                        await self.candle_engine.add_tick(asset, p, t)
                        count += 1
                if count > 0:
                    self._tick_count += count
                    self._log(
                        f"📊 Batch: {count} candles for {asset}"
                    )

            elif isinstance(payload, list):
                for item in payload:
                    await self._on_candles(item)

        except Exception as e:
            logger.debug(f"Candles error: {e}")

    async def _on_assets(self, payload):
        try:
            items = (
                payload if isinstance(payload, list) else [payload]
            )
            for item in items:
                if not isinstance(item, dict):
                    continue
                asset = (
                    item.get("symbol") or item.get("asset") or
                    item.get("active") or item.get("id", "")
                )
                if not asset:
                    continue
                asset = str(asset).upper()
                payout = float(
                    item.get("profit") or item.get("payout") or
                    item.get("payment") or
                    item.get("profitPercent", 0)
                )
                price = float(
                    item.get("price") or item.get("value") or
                    item.get("close", 0)
                )
                if payout > 0:
                    await self.state_manager.set_payout(asset, payout)
                if price > 0:
                    await self.state_manager.set_price(asset, price)
        except Exception as e:
            logger.debug(f"Assets error: {e}")
