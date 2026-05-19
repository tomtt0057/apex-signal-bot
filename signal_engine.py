import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SignalEngine:
    EXPIRY_TO_TIMEFRAME = {
        "30s": 15,
        "1m":  30,
        "2m":  60,
        "15m": 300,
        "1H":  900,
    }
    ADX_PERIOD = 14
    WILLIAMS_PERIOD = 10
    ADX_THRESHOLD = 22

    def __init__(self, candle_engine, state_manager):
        self.candle_engine = candle_engine
        self.state_manager = state_manager
        self._cache = defaultdict(dict)
        self._cache_lock = asyncio.Lock()
        self._running = False

    async def start(self):
        self._running = True
        asyncio.create_task(self._background_compute())
        logger.info("SignalEngine started")

    async def stop(self):
        self._running = False

    async def _background_compute(self):
        while self._running:
            try:
                assets = await self.candle_engine.get_all_assets()
                for asset in assets:
                    for expiry, tf in self.EXPIRY_TO_TIMEFRAME.items():
                        # === FIXED: Increased threshold from 20 to 35 for ADX smoothing ===
                        if await self.candle_engine.has_enough_candles(
                            asset, tf, minimum=35
                        ):
                            sig = await self._compute_signal(asset, tf)
                            if sig:
                                async with self._cache_lock:
                                    self._cache[asset][expiry] = sig
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Background compute error: {e}")
                await asyncio.sleep(5)

    async def _compute_signal(self, asset, timeframe):
        try:
            candles = await self.candle_engine.get_closed_candles(
                asset, timeframe, count=100
            )
            if len(candles) < 20:
                return None

            highs  = [c.high  for c in candles]
            lows   = [c.low   for c in candles]
            closes = [c.close for c in candles]

            adx_data = self._calc_adx(highs, lows, closes)
            if not adx_data:
                return None

            adx      = adx_data["adx"]
            adx_prev = adx_data["adx_prev"]
            plus_di  = adx_data["plus_di"]
            minus_di = adx_data["minus_di"]

            wr = self._calc_williams_r(highs, lows, closes)
            if not wr or len(wr) < 3:
                return None

            wr_now   = wr[-1]
            wr_prev1 = wr[-2]
            wr_prev2 = wr[-3]

            adx_rising = adx > adx_prev
            adx_strong = adx > self.ADX_THRESHOLD
            wr_rising  = wr_now > wr_prev1
            wr_falling = wr_now < wr_prev1
            wr_was_oversold    = wr_prev1 < -80 or wr_prev2 < -80
            wr_was_overbought  = wr_prev1 > -20 or wr_prev2 > -20

            signal     = "HOLD"
            confidence = 1
            reasons    = []

            if (adx_strong and adx_rising
                    and plus_di > minus_di
                    and wr_was_oversold and wr_rising):
                signal = "BUY"
                score  = sum([
                    adx_strong, adx_rising,
                    plus_di > minus_di,
                    wr_was_oversold, wr_rising
                ])
                confidence = min(score, 5)
                reasons = [
                    f"ADX {adx:.1f} strong and rising ↑",
                    f"+DI {plus_di:.1f} > -DI {minus_di:.1f} — uptrend",
                    f"Williams %R {wr_now:.1f} rising from oversold zone",
                ]

            elif (adx_strong and adx_rising
                    and minus_di > plus_di
                    and wr_was_overbought and wr_falling):
                signal = "SELL"
                score  = sum([
                    adx_strong, adx_rising,
                    minus_di > plus_di,
                    wr_was_overbought, wr_falling
                ])
                confidence = min(score, 5)
                reasons = [
                    f"ADX {adx:.1f} strong and rising ↑",
                    f"-DI {minus_di:.1f} > +DI {plus_di:.1f} — downtrend",
                    f"Williams %R {wr_now:.1f} falling from overbought zone",
                ]

            else:
                reasons = []
                if not adx_strong:
                    reasons.append(
                        f"ADX {adx:.1f} too weak — need >{self.ADX_THRESHOLD}"
                    )
                if not adx_rising:
                    reasons.append("ADX not rising — no momentum")
                if abs(plus_di - minus_di) < 5:
                    reasons.append("DI lines too close — no direction")
                if not reasons:
                    reasons.append("No clear setup — wait for better entry")

            price    = await self.candle_engine.get_current_price(asset)
            payout   = await self.state_manager.get_payout(asset)
            conf_bar = "█" * confidence + "░" * (5 - confidence)
            conf_text = [
                "Very Low", "Low", "Medium", "High", "Very High"
            ][confidence - 1]

            return {
                "signal":     signal,
                "confidence": confidence,
                "conf_bar":   conf_bar,
                "conf_text":  conf_text,
                "price":      round(price, 5),
                "payout":     round(payout, 1),
                "reasons":    reasons,
                "adx":        round(adx, 2),
                "adx_prev":   round(adx_prev, 2),
                "plus_di":    round(plus_di, 2),
                "minus_di":   round(minus_di, 2),
                "williams_r": round(wr_now, 2),
                "timeframe":  timeframe,
                "timestamp":  datetime.now(timezone.utc).isoformat(),
                "candles":    len(candles),
            }

        except Exception as e:
            logger.error(f"Compute signal error {asset}: {e}")
            return None

    def _calc_adx(self, highs, lows, closes):
        try:
            period = self.ADX_PERIOD
            if len(closes) < period + 5:
                return None

            plus_dm  = []
            minus_dm = []
            tr_vals  = []

            for i in range(1, len(closes)):
                up   = highs[i]   - highs[i-1]
                down = lows[i-1]  - lows[i]
                plus_dm.append(
                    up if up > down and up > 0 else 0
                )
                minus_dm.append(
                    down if down > up and down > 0 else 0
                )
                hl = highs[i] - lows[i]
                hc = abs(highs[i] - closes[i-1])
                lc = abs(lows[i]  - closes[i-1])
                tr_vals.append(max(hl, hc, lc))

            def smooth(data, p):
                s = [sum(data[:p])]
                for i in range(p, len(data)):
                    s.append(s[-1] - s[-1] / p + data[i])
                return s

            str14  = smooth(tr_vals,  period)
            spdm14 = smooth(plus_dm,  period)
            smdm14 = smooth(minus_dm, period)

            pdi = [
                100 * p / t if t > 0 else 0
                for p, t in zip(spdm14, str14)
            ]
            mdi = [
                100 * m / t if t > 0 else 0
                for m, t in zip(smdm14, str14)
            ]

            dx = []
            for p, m in zip(pdi, mdi):
                denom = p + m
                dx.append(
                    100 * abs(p - m) / denom if denom > 0 else 0
                )

            if len(dx) < period:
                return None

            adx_vals = [sum(dx[:period]) / period]
            for i in range(period, len(dx)):
                adx_vals.append(
                    (adx_vals[-1] * (period - 1) + dx[i]) / period
                )

            if len(adx_vals) < 2:
                return None

            return {
                "adx":      adx_vals[-1],
                "adx_prev": adx_vals[-2],
                "plus_di":  pdi[-1],
                "minus_di": mdi[-1],
            }

        except Exception as e:
            logger.error(f"ADX error: {e}")
            return None

    def _calc_williams_r(self, highs, lows, closes):
        try:
            period = self.WILLIAMS_PERIOD
            if len(closes) < period:
                return None
            result = []
            for i in range(period - 1, len(closes)):
                hh = max(highs[i - period + 1: i + 1])
                ll = min(lows[i  - period + 1: i + 1])
                if hh == ll:
                    result.append(-50.0)
                else:
                    wr = -100 * (hh - closes[i]) / (hh - ll)
                    result.append(wr)
            return result
        except Exception as e:
            logger.error(f"Williams %R error: {e}")
            return None

    async def get_signal(self, asset, expiry):
        async with self._cache_lock:
            return self._cache.get(asset, {}).get(expiry)

    async def get_best_signals(self, expiry="1m", limit=8):
        async with self._cache_lock:
            results = []
            for asset, exp_map in self._cache.items():
                if expiry in exp_map:
                    sig = exp_map[expiry]
                    if sig and sig["signal"] != "HOLD":
                        results.append((asset, sig))
            results.sort(
                key=lambda x: (
                    x[1]["confidence"],
                    x[1].get("payout", 0)
                ),
                reverse=True
            )
            return results[:limit]

    async def get_all_cached_assets(self):
        async with self._cache_lock:
            return list(self._cache.keys())
