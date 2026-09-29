"""Read-only access to Vaultwarden's SQLite database.

The companion never writes to Vaultwarden. It opens the database with
`mode=ro`; the data volume itself must still be mounted read-write, because
SQLite in WAL mode (Vaultwarden's default) needs the -shm file even to read.

New events are found by ROWID, not by `event_date`: clients batch events and
stamp them with the *client's* time, so a late upload can carry an older date
than rows already seen. ROWID only ever grows on insert.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Event:
    rowid: int
    type: int
    user_uuid: str        # who did it
    cipher_uuid: str | None
    org_uuid: str | None
    device_type: int | None
    ip: str | None
    at: datetime          # UTC, as reported by the client


@dataclass(frozen=True)
class User:
    uuid: str
    email: str
    name: str


def parse_vw_date(s: str) -> datetime:
    # Vaultwarden stores naive UTC, e.g. "2026-09-29 07:41:12.123456"
    return datetime.fromisoformat(s.replace("T", " ").rstrip("Z")).replace(tzinfo=timezone.utc)


def to_vw_date(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


class Vaultwarden:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _event(r: sqlite3.Row) -> Event:
        return Event(
            rowid=r["rowid"],
            type=r["event_type"],
            user_uuid=r["actor"],
            cipher_uuid=r["cipher_uuid"],
            org_uuid=r["org_uuid"],
            device_type=r["device_type"],
            ip=r["ip_address"],
            at=parse_vw_date(r["event_date"]),
        )

    _COLS = ("rowid, event_type, COALESCE(act_user_uuid, user_uuid) AS actor, "
             "cipher_uuid, org_uuid, device_type, ip_address, event_date")

    def events_after(self, rowid: int, limit: int = 5000) -> list[Event]:
        with self._conn() as c:
            rows = c.execute(
                f"SELECT {self._COLS} FROM event WHERE rowid > ? ORDER BY rowid LIMIT ?",
                (rowid, limit),
            ).fetchall()
        return [self._event(r) for r in rows if r["actor"]]

    def max_rowid(self) -> int:
        with self._conn() as c:
            return c.execute("SELECT COALESCE(MAX(rowid), 0) FROM event").fetchone()[0]

    def events_for_user(self, user_uuid: str, since: datetime, until: datetime) -> list[Event]:
        with self._conn() as c:
            rows = c.execute(
                f"SELECT {self._COLS} FROM event "
                "WHERE COALESCE(act_user_uuid, user_uuid) = ? AND event_date >= ? AND event_date <= ? "
                "ORDER BY event_date",
                (user_uuid, to_vw_date(since), to_vw_date(until)),
            ).fetchall()
        return [self._event(r) for r in rows]

    def user_by_email(self, email: str) -> User | None:
        with self._conn() as c:
            r = c.execute(
                "SELECT uuid, email, name FROM users WHERE lower(email) = lower(?)", (email,)
            ).fetchone()
        return User(r["uuid"], r["email"], r["name"]) if r else None

    def user_by_uuid(self, uuid: str) -> User | None:
        with self._conn() as c:
            r = c.execute("SELECT uuid, email, name FROM users WHERE uuid = ?", (uuid,)).fetchone()
        return User(r["uuid"], r["email"], r["name"]) if r else None
