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
                    subscribed INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS signal_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER, pair TEXT,
                    timeframe TEXT, signal TEXT,
                    logged_at TEXT DEFAULT (datetime('now'))
                );
            """)

    def add_user(self, user_id, username):
        with self._conn() as conn:
            conn.execute("INSERT OR IGNORE INTO users (user_id,username) VALUES (?,?)",(user_id,username))

    def subscribe(self, user_id):
        with self._conn() as conn:
            conn.execute("UPDATE users SET subscribed=1 WHERE user_id=?",(user_id,))

    def unsubscribe(self, user_id):
        with self._conn() as conn:
            conn.execute("UPDATE users SET subscribed=0 WHERE user_id=?",(user_id,))

    def get_subscribers(self):
        with self._conn() as conn:
            rows = conn.execute("SELECT user_id FROM users WHERE subscribed=1").fetchall()
        return [r[0] for r in rows]

    def log_signal(self, user_id, pair, timeframe, signal):
        with self._conn() as conn:
            conn.execute("INSERT INTO signal_log (user_id,pair,timeframe,signal) VALUES (?,?,?,?)",
                         (user_id,pair,timeframe,signal))

    def get_user_stats(self, user_id):
        with self._conn() as conn:
            rows = conn.execute("SELECT signal,COUNT(*) FROM signal_log WHERE user_id=? GROUP BY signal",(user_id,)).fetchall()
        counts = {r[0]:r[1] for r in rows}
        return {"total":sum(counts.values()),"calls":counts.get("BUY",0),"puts":counts.get("SELL",0),"waits":counts.get("HOLD",0)}
