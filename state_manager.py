import asyncio
from datetime import datetime, timezone, timedelta


class StateManager:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._users = {}
        self.ws_connected = False
        self.bot_start_time = datetime.now(timezone.utc)
        self.last_heartbeat = None
        self._asset_payouts = {}
        self._payout_lock = asyncio.Lock()
        self._asset_prices = {}
        self._price_lock = asyncio.Lock()

    def _default_user(self):
        return {
            "asset": None,
            "expiry": None,
            "mode": "signal",
            "account": "demo",
            "amount": "1",
            "active": False,
            "chat_id": None,
            "username": None,
            "awaiting_amount": False,
            "auto_running": False,
        }

    async def get_user(self, user_id: int) -> dict:
        async with self._lock:
            if user_id not in self._users:
                self._users[user_id] = self._default_user()
            return dict(self._users[user_id])

    async def set_user(self, user_id: int, **kwargs):
        async with self._lock:
            if user_id not in self._users:
                self._users[user_id] = self._default_user()
            self._users[user_id].update(kwargs)

    async def get_all_active_users(self) -> list:
        async with self._lock:
            return [
                (uid, dict(d))
                for uid, d in self._users.items()
                if d.get("active") and d.get("chat_id")
            ]

    async def set_payout(self, asset: str, payout: float):
        async with self._payout_lock:
            self._asset_payouts[asset] = payout

    async def get_payout(self, asset: str) -> float:
        async with self._payout_lock:
            return self._asset_payouts.get(asset, 0.0)

    async def get_all_payouts(self) -> dict:
        async with self._payout_lock:
            return dict(self._asset_payouts)

    async def get_top_payouts(self, min_payout=75, limit=10) -> list:
        async with self._payout_lock:
            filtered = [
                (a, p) for a, p in self._asset_payouts.items()
                if p >= min_payout
            ]
            return sorted(
                filtered, key=lambda x: x[1], reverse=True
            )[:limit]

    async def set_price(self, asset: str, price: float):
        async with self._price_lock:
            self._asset_prices[asset] = price

    async def get_price(self, asset: str) -> float:
        async with self._price_lock:
            return self._asset_prices.get(asset, 0.0)

    async def set_connected(self, connected: bool):
        async with self._lock:
            self.ws_connected = connected
            if connected:
                self.last_heartbeat = datetime.now(timezone.utc)

    async def is_connected(self) -> bool:
        async with self._lock:
            return self.ws_connected

    async def update_heartbeat(self):
        async with self._lock:
            self.last_heartbeat = datetime.now(timezone.utc)

    async def get_uptime(self) -> str:
        now = datetime.now(timezone.utc)
        delta = now - self.bot_start_time
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        return f"{hours}h {minutes}m"
