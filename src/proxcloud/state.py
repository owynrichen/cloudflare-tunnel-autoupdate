import sqlite3
from contextlib import contextmanager
from typing import Optional


class State:
    def __init__(self, path: str = "state.db"):
        self.path = path
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                id TEXT PRIMARY KEY,
                ip TEXT,
                meta TEXT
            )
            """
        )
        self._conn.commit()

    def get(self, record_id: str) -> Optional[str]:
        cur = self._conn.cursor()
        cur.execute("SELECT ip FROM records WHERE id = ?", (record_id,))
        row = cur.fetchone()
        return row[0] if row else None

    def set(self, record_id: str, ip: str, meta: Optional[str] = None):
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO records (id, ip, meta) VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET ip=excluded.ip, meta=excluded.meta",
            (record_id, ip, meta),
        )
        self._conn.commit()

    def close(self):
        self._conn.close()
