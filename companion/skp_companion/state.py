"""The companion's own small database: the event cursor and the alert log."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS alert (
  id          INTEGER PRIMARY KEY,
  kind        TEXT NOT NULL,
  user_uuid   TEXT NOT NULL,
  user_email  TEXT NOT NULL,
  created_at  TEXT NOT NULL,
  detail      TEXT NOT NULL,
  delivered   TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS alert_user_kind ON alert (user_uuid, kind, created_at);
"""


class State:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def get_cursor(self) -> int | None:
        r = self.conn.execute("SELECT v FROM kv WHERE k = 'cursor'").fetchone()
        return int(r["v"]) if r else None

    def set_cursor(self, rowid: int) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO kv (k, v) VALUES ('cursor', ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v",
                (str(rowid),),
            )

    def last_alert_at(self, user_uuid: str, kind: str) -> datetime | None:
        r = self.conn.execute(
            "SELECT MAX(created_at) AS t FROM alert WHERE user_uuid = ? AND kind = ?", (user_uuid, kind)
        ).fetchone()
        return datetime.fromisoformat(r["t"]) if r and r["t"] else None

    def record_alert(self, kind: str, user_uuid: str, user_email: str, detail: dict,
                     delivered: list[str], at: datetime | None = None) -> int:
        at = at or datetime.now(timezone.utc)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO alert (kind, user_uuid, user_email, created_at, detail, delivered) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (kind, user_uuid, user_email, at.isoformat(), json.dumps(detail), json.dumps(delivered)),
            )
        return cur.lastrowid

    def recent_alerts(self, limit: int = 50) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM alert ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [
            {**dict(r), "detail": json.loads(r["detail"]), "delivered": json.loads(r["delivered"])}
            for r in rows
        ]
