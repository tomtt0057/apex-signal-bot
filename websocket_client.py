import logging
import logging.handlers

# Fix Logger.warn removed in Python 3.12+
if not hasattr(logging.Logger, 'warn'):
    logging.Logger.warn = logging.Logger.warning

# Patch root logger too
root = logging.getLogger()
if not hasattr(root, 'warn'):
    root.warn = root.warning

import asyncio
import json
import re
from datetime import datetime, timezone
from config import PO_SSID, PO_AUTH_PAYLOAD

logger = logging.getLogger(__name__)

ASSETS = [
    "EURUSD_otc", "GBPUSD_otc", "EURGBP_otc",
    "USDJPY_otc", "AUDUSD_otc", "USDCAD_otc",
    "EURJPY_otc", "GBPJPY_otc", "USDCHF_otc",
    "NZDUSD_otc", "AUDCAD_otc", "EURCAD_otc",
]


class PocketOptionWS:
    RECONNECT_DELAY = 10

    def __init__(self, candle_engine, state_manager):
        self.candle_engine    = candle_engine
        self.state_manager    = state_manager
        self._running         = False
        self._reconnect_count = 0
        self._notify_cb       = None
        self._tick_count      = 0
        self._notified_once   = False
        self._auth_confirmed  = False
        self._last_error      = ""
        self._connection_log  = []
        self._client          = None

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
        await self.state_manager.set_connected(False)

    def get_ws(self):
        return None

    def get_client(self):
        return self._client

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

    def _get_ssid(self):
        # Use PO_SSID directly if set
        if PO_SSID:
            return PO_SSID
        # Otherwise extract session from PO_AUTH_PAYLOAD
        if PO_AUTH_PAYLOAD:
            try:
                match = re.search(
                    r'42\["auth",(\{.*\})\]',
                    PO_AUTH_PAYLOAD,
                    re.DOTALL
                )
                if match:
                    data = json.loads(match.group(1))
                    session = data.get("session", "")
                    if session:
                        self._log("SSID extracted from PO_AUTH_PAYLOAD")
                        return session
            except Exception as e:
                self._log(f"SSID extraction error: {e}")
        return ""

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
        from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync

        ssid = self._get_ssid()
        if not ssid:
            self._last_error = "No SSID found! Set PO_SSID in Railway variables."
            self._log(f"ERROR: {self._last_error}")
            await asyncio.sleep(60)
            return

        self._log("Connecting via BinaryOptionsToolsV2...")

        async with PocketOptionAsync(ssid=ssid) as client:
            self._client          = client
            self._auth_confirmed  = True
            self._reconnect_count = 0

            self._log("✅ Connected to Pocket Option!")
            await self.state_manager.set_connected(True)

            # ── Load historical candles immediately — instant signals
            self._log("Loading historical candles...")
            for asset in ASSETS:
                try:
                    candles = await client.get_candles(asset, 60, 100)
                    count = 0
                    for c in candles:
                        price = float(
                            c.get('close') or c.get('price') or 0
                        )
                        ts = float(
                            c.get('time') or c.get('timestamp') or
                            datetime.now(timezone.utc).timestamp()
                        )
                        if price > 0:
                            await self.candle_engine.add_tick(
                                asset.upper(), price, ts
                            )
                            count += 1
                    if count > 0:
                        self._tick_count += count
                        self._log(f"✅ {asset}: {count} candles loaded")
                except Exception as e:
                    self._log(f"History error {asset}: {e}")

            if not self._notified_once:
                self._notified_once = True
                await self._notify(
                    "✅ *Connected to Pocket Option!*\n"
                    "📊 Historical data loaded.\n"
                    "⚡ Signals are ready instantly!\n\n"
                    "Use /start to get a signal now."
                )

            # ── Subscribe to real-time ticks for all assets
            self._log("Starting real-time subscriptions...")
            tasks = [
                asyncio.create_task(self._subscribe_asset(client, asset))
                for asset in ASSETS
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

        await self.state_manager.set_connected(False)
        self._auth_confirmed = False
        self._client         = None
        self._log("Disconnected from Pocket Option")

    async def _subscribe_asset(self, client, asset):
        try:
            async for candle in await client.subscribe_symbol(asset):
                if not self._running:
                    break
                try:
                    price = float(
                        candle.get('close') or
                        candle.get('price') or 0
                    )
                    ts = float(
                        candle.get('time') or
                        candle.get('timestamp') or
                        datetime.now(timezone.utc).timestamp()
                    )
                    if price > 0:
                        await self.candle_engine.add_tick(
                            asset.upper(), price, ts
                        )
                        await self.state_manager.set_price(
                            asset.upper(), price
                        )
                        self._tick_count += 1
                        if self._tick_count == 1:
                            self._log(
                                f"🎯 First tick! {asset}={price}"
                            )
                        elif self._tick_count % 500 == 0:
                            self._log(
                                f"Tick #{self._tick_count}: "
                                f"{asset}={price}"
                            )
                except Exception as e:
                    logger.debug(f"Tick error: {e}")
        except Exception as e:
            self._log(f"Subscription error {asset}: {e}")
