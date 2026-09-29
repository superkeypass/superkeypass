"""Tamper detection — threat model T3, "fifteen minutes with an unlocked device".

Pure logic: events in, findings out. No I/O, so it is easy to test and reason
about. Cooldowns (not repeating an alert) are the caller's job, because they
need to survive restarts.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .events import LABEL, REVEALS, SECURITY_CHANGES, Ev
from .vw import Event


@dataclass
class Finding:
    kind: str            # "mass_reveal" | "export" | "security_change"
    user_uuid: str
    at: datetime
    summary: str
    items: list[str] = field(default_factory=list)   # cipher uuids involved
    event_types: list[int] = field(default_factory=list)


class Detector:
    def __init__(self, reveal_count: int, window: timedelta):
        self.reveal_count = reveal_count
        self.window = window
        # per user: recent reveals as (time, cipher_uuid, event_type)
        self._reveals: dict[str, deque[tuple[datetime, str, int]]] = defaultdict(deque)
        # per user: the window already reported, so one burst yields one finding
        self._burst_reported_until: dict[str, datetime] = {}

    def feed(self, events: list[Event]) -> list[Finding]:
        out: list[Finding] = []
        # Clients upload in batches and in any order; judge by when things happened.
        for ev in sorted(events, key=lambda e: (e.at, e.rowid)):
            if ev.type == Ev.USER_EXPORTED_VAULT:
                out.append(Finding("export", ev.user_uuid, ev.at, "The whole vault was exported.",
                                   event_types=[ev.type]))
            elif ev.type in SECURITY_CHANGES:
                out.append(Finding("security_change", ev.user_uuid, ev.at,
                                   f"Account security changed: {LABEL[Ev(ev.type)]}.",
                                   event_types=[ev.type]))
            elif ev.type in REVEALS and ev.cipher_uuid:
                f = self._reveal(ev)
                if f:
                    out.append(f)
        return out

    def _reveal(self, ev: Event) -> Finding | None:
        q = self._reveals[ev.user_uuid]
        q.append((ev.at, ev.cipher_uuid, ev.type))
        while q and q[0][0] < ev.at - self.window:
            q.popleft()

        items = list(dict.fromkeys(c for _, c, _ in q))
        if len(items) < self.reveal_count:
            return None
        if self._burst_reported_until.get(ev.user_uuid, datetime.min.replace(tzinfo=ev.at.tzinfo)) >= q[0][0]:
            return None  # same burst, already reported
        self._burst_reported_until[ev.user_uuid] = ev.at
        mins = max(1, round(self.window.total_seconds() / 60))
        return Finding(
            "mass_reveal", ev.user_uuid, ev.at,
            f"{len(items)} different passwords or secrets were revealed or copied within {mins} minute(s).",
            items=items,
            event_types=sorted({t for _, _, t in q}),
        )
