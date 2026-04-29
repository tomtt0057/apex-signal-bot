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

                CREATE TABLE IF NOT EXISTS signal_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    pair TEXT,
                    timeframe TEXT,
                    signal TEXT,
                    confidence INTEGER DEFAULT 0,
                    price REAL DEFAULT 0,
                    session TEXT DEFAULT 'Unknown',
                    logged_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS trade_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    pair TEXT,
                    signal TEXT,
                    result TEXT,
                    profit_loss REAL DEFAULT 0,
                    logged_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS pair_performance (
                    pair TEXT PRIMARY KEY,
                    total_signals INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    last_updated TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    role TEXT,
                    message TEXT,
                    logged_at TEXT DEFAULT (datetime('now'))
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

    def log_signal(self, user_id, pair, timeframe,
                   signal, confidence=0, price=0, session="Unknown"):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO signal_log "
                "(user_id,pair,timeframe,signal,confidence,price,session) "
                "VALUES (?,?,?,?,?,?,?)",
                (user_id, pair, timeframe,
                 signal, confidence, price, session)
            )
        self._update_pair_performance(pair, signal)

    def _update_pair_performance(self, pair, signal):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO pair_performance (pair) VALUES (?)",
                (pair,)
            )
            conn.execute(
                "UPDATE pair_performance SET "
                "total_signals = total_signals + 1, "
                "last_updated = datetime('now') "
                "WHERE pair=?",
                (pair,)
            )

    def log_trade_result(self, user_id, pair, signal, result):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO trade_results "
                "(user_id,pair,signal,result) VALUES (?,?,?,?)",
                (user_id, pair, signal, result)
            )
            pl = 1 if result == "WIN" else -1
            conn.execute(
                "UPDATE pair_performance SET "
                "wins = wins + ?, losses = losses + ?, "
                "win_rate = CAST(wins + ? AS REAL) / "
                "CAST(total_signals AS REAL) * 100 "
                "WHERE pair=?",
                (1 if result == "WIN" else 0,
                 1 if result == "LOSS" else 0,
                 1 if result == "WIN" else 0,
                 pair)
            )

    def get_user_stats(self, user_id):
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT signal, COUNT(*) FROM signal_log "
                "WHERE user_id=? GROUP BY signal",
                (user_id,)
            ).fetchall()
            trade_rows = conn.execute(
                "SELECT result, COUNT(*) FROM trade_results "
                "WHERE user_id=? GROUP BY result",
                (user_id,)
            ).fetchall()
        counts = {r[0]: r[1] for r in rows}
        trade_counts = {r[0]: r[1] for r in trade_rows}
        return {
            "total":  sum(counts.values()),
            "calls":  counts.get("BUY",  0),
            "puts":   counts.get("SELL", 0),
            "waits":  counts.get("HOLD", 0),
            "wins":   trade_counts.get("WIN",  0),
            "losses": trade_counts.get("LOSS", 0),
        }

    def get_top_pairs(self, limit=5):
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT pair, win_rate, total_signals, wins, losses "
                "FROM pair_performance "
                "WHERE total_signals >= 3 "
                "ORDER BY win_rate DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return rows

    def get_pair_performance(self, pair):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT win_rate, total_signals, wins, losses "
                "FROM pair_performance WHERE pair=?",
                (pair,)
            ).fetchone()
        return row

    def save_chat_message(self, user_id, role, message):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO chat_history "
                "(user_id, role, message) VALUES (?,?,?)",
                (user_id, role, message)
            )

    def get_chat_history(self, user_id, limit=10):
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT role, message FROM chat_history "
                "WHERE user_id=? ORDER BY id DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
        return list(reversed(rows))

    def get_best_session_pairs(self, session):
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT pair FROM signal_log "
                "WHERE session=? AND signal != 'HOLD' "
                "GROUP BY pair ORDER BY COUNT(*) DESC LIMIT 6",
                (session,)
            ).fetchall()
        return [r[0] for r in rows]
