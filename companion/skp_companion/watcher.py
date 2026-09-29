"""The poll loop: new Vaultwarden events → detector → cooldown → notifier."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone

from .alerts import Notifier
from .config import Config
from .detector import Detector, Finding
from .state import State
from .vw import Vaultwarden

log = logging.getLogger(__name__)


class Watcher:
    def __init__(self, cfg: Config, vw: Vaultwarden, state: State, notifier: Notifier):
        self.cfg, self.vw, self.state, self.notifier = cfg, vw, state, notifier
        t = cfg.thresholds
        self.detector = Detector(t.reveal_count, timedelta(minutes=t.window_minutes))
        self.cooldown = timedelta(minutes=t.cooldown_minutes)
        self.last_poll_ok: datetime | None = None
        self.last_error: str | None = None

    def start_cursor(self) -> int:
        cur = self.state.get_cursor()
        if cur is None:
            # First run: start from now. Alerting on months of history would
            # bury the one alert that matters under hundreds that don't.
            cur = self.vw.max_rowid()
            self.state.set_cursor(cur)
            log.info("first run: starting at event rowid %d", cur)
        return cur

    def poll_once(self) -> list[Finding]:
        cur = self.start_cursor()
        events = self.vw.events_after(cur)
        sent: list[Finding] = []
        for f in self.detector.feed(events):
            if self._handle(f):
                sent.append(f)
        if events:
            self.state.set_cursor(max(e.rowid for e in events))
        self.last_poll_ok = datetime.now(timezone.utc)
        self.last_error = None
        return sent

    def _handle(self, f: Finding) -> bool:
        last = self.state.last_alert_at(f.user_uuid, f.kind)
        # Exports always alert: each one is a complete copy of the vault.
        if f.kind != "export" and last and f.at - last < self.cooldown:
            return False
        user = self.vw.user_by_uuid(f.user_uuid)
        email, name = (user.email, user.name) if user else (f.user_uuid, "")
        delivered = self.notifier.send(f, email, name)
        self.state.record_alert(
            f.kind, f.user_uuid, email,
            {"summary": f.summary, "items": f.items, "event_types": f.event_types},
            delivered, at=f.at,
        )
        log.warning("alert %s for %s → %s", f.kind, email, delivered or "NOT DELIVERED")
        return True

    def run_forever(self, stop: threading.Event) -> None:
        while not stop.is_set():
            try:
                self.poll_once()
            except Exception as e:  # noqa: BLE001 — keep watching; surface via /health
                self.last_error = str(e)
                log.exception("poll failed")
            stop.wait(self.cfg.poll_seconds)
