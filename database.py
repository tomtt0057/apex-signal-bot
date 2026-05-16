import sqlite3
from config import DATABASE_PATH


class Database:
    def __init__(self):
        self.path = DATABASE_PATH
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.path)

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    subscribed INTEGER DEFAULT 0,
                    joined_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS trade_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    asset TEXT,
                    signal TEXT,
                    expiry TEXT,
                    result TEXT,
                    amount REAL DEFAULT 0,
                    payout REAL DEFAULT 0,
                    logged_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS signal_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    asset TEXT,
                    expiry TEXT,
                    signal TEXT,
                    confidence INTEGER DEFAULT 0,
                    price REAL DEFAULT 0,
                    adx REAL DEFAULT 0,
                    williams_r REAL DEFAULT 0,
                    logged_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS asset_performance (
                    asset TEXT PRIMARY KEY,
                    total_signals INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    last_updated TEXT DEFAULT (datetime('now'))
                );
            """)

    def add_user(self, user_id, username):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users "
                "(user_id, username) VALUES (?,?)",
                (user_id, username)
            )

    def subscribe(self, user_id):
        with self._conn() as conn:
            conn.execute(
                "UPDATE users SET subscribed=1 WHERE user_id=?",
                (user_id,)
            )

    def unsubscribe(self, user_id):
        with self._conn() as conn:
            conn.execute(
                "UPDATE users SET subscribed=0 WHERE user_id=?",
                (user_id,)
            )

    def get_subscribers(self):
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT user_id FROM users WHERE subscribed=1"
            ).fetchall()
        return [r[0] for r in rows]

    def log_signal(self, user_id, asset, expiry,
                   signal, confidence=0, price=0,
                   adx=0, williams_r=0):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO signal_log "
                "(user_id,asset,expiry,signal,"
                "confidence,price,adx,williams_r) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (user_id, asset, expiry, signal,
                 confidence, price, adx, williams_r)
            )
        self._update_asset_performance(asset, signal)

    def _update_asset_performance(self, asset, signal):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO asset_performance "
                "(asset) VALUES (?)", (asset,)
            )
            conn.execute(
                "UPDATE asset_performance SET "
                "total_signals = total_signals + 1, "
                "last_updated = datetime('now') "
                "WHERE asset=?", (asset,)
            )

    def log_trade_result(self, user_id, asset,
                         signal, expiry, result,
                         amount=0, payout=0):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO trade_results "
                "(user_id,asset,signal,expiry,"
                "result,amount,payout) "
                "VALUES (?,?,?,?,?,?,?)",
                (user_id, asset, signal, expiry,
                 result, amount, payout)
            )
            win = 1 if result == "WIN" else 0
            loss = 1 if result == "LOSS" else 0
            conn.execute(
                "UPDATE asset_performance SET "
                "wins = wins + ?, "
                "losses = losses + ?, "
                "win_rate = CAST(wins + ? AS REAL) / "
                "CAST(total_signals AS REAL) * 100 "
                "WHERE asset=?",
                (win, loss, win, asset)
            )

    def get_user_stats(self, user_id):
        with self._conn() as conn:
            trades = conn.execute(
                "SELECT result, COUNT(*) FROM trade_results "
                "WHERE user_id=? GROUP BY result",
                (user_id,)
            ).fetchall()
            signals = conn.execute(
                "SELECT COUNT(*) FROM signal_log "
                "WHERE user_id=?",
                (user_id,)
            ).fetchone()
        counts = {r[0]: r[1] for r in trades}
        wins = counts.get("WIN", 0)
        losses = counts.get("LOSS", 0)
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        return {
            "wins": wins,
            "losses": losses,
            "total_trades": total,
            "total_signals": signals[0] if signals else 0,
            "win_rate": round(win_rate, 1)
        }

    def get_top_assets(self, limit=5):
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT asset, win_rate, total_signals, "
                "wins, losses FROM asset_performance "
                "WHERE total_signals >= 3 "
                "ORDER BY win_rate DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return rows

    def get_asset_performance(self, asset):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT win_rate, total_signals, wins, losses "
                "FROM asset_performance WHERE asset=?",
                (asset,)
            ).fetchone()
        return row
