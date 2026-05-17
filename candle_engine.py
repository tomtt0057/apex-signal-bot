import asyncio
import logging
from collections import defaultdict, deque
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class Candle:
    def __init__(self, open_price, timestamp, timeframe):
        self.timeframe = timeframe
        self.timestamp = timestamp
        self.open  = open_price
        self.high  = open_price
        self.low   = open_price
        self.close = open_price
        self.ticks = 1
        self.closed = False

    def update(self, price):
        self.high  = max(self.high, price)
        self.low   = min(self.low,  price)
        self.close = price
        self.ticks += 1


class CandleEngine:
    TIMEFRAMES  = [15, 30, 60, 300, 900]
    MAX_CANDLES = 200

    def __init__(self):
        self._candles = defaultdict(
            lambda: defaultdict(
                lambda: deque(maxlen=self.MAX_CANDLES)
            )
        )
        self._current    = defaultdict(dict)
        self._tick_queue = None   # created in start()
        self._lock       = None   # created in start()
        self._running    = False
        self._tick_count = 0

    async def start(self):
        # Create these HERE inside the running event loop
        self._tick_queue = asyncio.Queue()
        self._lock       = asyncio.Lock()
        self._running    = True
        asyncio.create_task(self._process_ticks())
        logger.info("CandleEngine started")

    async def stop(self):
        self._running = False

    async def add_tick(self, asset, price, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).timestamp()
        if self._tick_queue is not None:
            await self._tick_queue.put((asset, price, timestamp))

    async def _process_ticks(self):
        while self._running:
            try:
                asset, price, ts = await asyncio.wait_for(
                    self._tick_queue.get(), timeout=1.0
                )
                await self._handle_tick(asset, price, ts)
                self._tick_count += 1
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Tick error: {e}")

    async def _handle_tick(self, asset, price, timestamp):
        async with self._lock:
            for tf in self.TIMEFRAMES:
                candle_start = int(timestamp // tf) * tf

                if tf not in self._current[asset]:
                    self._current[asset][tf] = Candle(price, candle_start, tf)
                else:
                    cur = self._current[asset][tf]
                    if candle_start > cur.timestamp:
                        cur.closed = True
                        self._candles[asset][tf].append(cur)
                        self._current[asset][tf] = Candle(price, candle_start, tf)
                    else:
                        cur.update(price)

    async def get_closed_candles(self, asset, timeframe, count=100):
        async with self._lock:
            candles = list(self._candles[asset][timeframe])
            return candles[-count:]

    async def get_current_price(self, asset):
        async with self._lock:
            for tf in self.TIMEFRAMES:
                if tf in self._current.get(asset, {}):
                    return self._current[asset][tf].close
            return 0.0

    async def has_enough_candles(self, asset, timeframe, minimum=20):
        async with self._lock:
            return len(self._candles[asset][timeframe]) >= minimum

    async def get_all_assets(self):
        async with self._lock:
            return list(self._candles.keys())

    async def get_candle_count(self, asset, timeframe):
        async with self._lock:
            return len(self._candles[asset][timeframe])

    def get_tick_count(self):
        return self._tick_count
