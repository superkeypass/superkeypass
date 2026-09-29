"""HTTP surface (admin-only) + the background watcher.

Every endpoint except /health requires HTTP Basic auth with the admin token
as the password: the alert log and exposure report reveal who banks where.
"""

from __future__ import annotations

import html
import logging
import os
import secrets
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from . import __version__, report, sheet
from .alerts import Notifier
from .config import Config, load
from .state import State
from .vw import Vaultwarden
from .watcher import Watcher

log = logging.getLogger("skp_companion")


def create_app(cfg: Config, start_watcher: bool = True) -> FastAPI:
    if not cfg.admin_token:
        raise SystemExit("SKP_ADMIN_TOKEN is not set — refusing to start without admin auth.")

    vw = Vaultwarden(cfg.vaultwarden_db)
    state = State(cfg.state_db)
    watcher = Watcher(cfg, vw, state, Notifier(cfg))
    stop = threading.Event()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        t = None
        if start_watcher:
            t = threading.Thread(target=watcher.run_forever, args=(stop,), daemon=True, name="watcher")
            t.start()
        yield
        stop.set()
        if t:
            t.join(timeout=5)

    app = FastAPI(title="SuperkeyPass companion", version=__version__, lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.watcher = watcher
    basic = HTTPBasic(realm="SuperkeyPass")

    def admin(creds: HTTPBasicCredentials = Depends(basic)) -> None:
        if not secrets.compare_digest(creds.password.encode(), cfg.admin_token.encode()):
            raise HTTPException(401, "bad credentials", headers={"WWW-Authenticate": 'Basic realm="SuperkeyPass"'})

    def user_or_404(email: str):
        u = vw.user_by_email(email)
        if not u:
            raise HTTPException(404, "no such user")
        return u

    def window(since: datetime | None, until: datetime | None, hours: int) -> tuple[datetime, datetime]:
        until = (until or datetime.now(timezone.utc)).astimezone(timezone.utc)
        since = (since or until - timedelta(hours=hours)).astimezone(timezone.utc)
        return since, until

    @app.get("/health")
    def health():
        # A silent watcher is a failing watcher: report staleness, not just liveness.
        # And a watcher with nowhere to send alerts is decoration, not protection.
        ok = watcher.last_poll_ok
        stale = ok is None or datetime.now(timezone.utc) - ok > timedelta(seconds=cfg.poll_seconds * 4 + 30)
        channels = [c for c, on in (("email", cfg.smtp.enabled), ("ntfy", bool(cfg.ntfy_url))) if on]
        return {
            "ok": not stale and watcher.last_error is None and bool(channels),
            "last_poll": ok.isoformat() if ok else None,
            "error": watcher.last_error or (None if channels else "no alert channel configured"),
            "alert_channels": channels,
        }

    @app.get("/api/alerts", dependencies=[Depends(admin)])
    def alerts(limit: int = 50):
        return state.recent_alerts(limit)

    @app.get("/api/report", dependencies=[Depends(admin)])
    def api_report(email: str, since: datetime | None = None, until: datetime | None = None,
                   hours: int = Query(24, ge=1, le=24 * 400)):
        u = user_or_404(email)
        s, t = window(since, until, hours)
        evs = vw.events_for_user(u.uuid, s, t)
        return {
            "user": u.email, "since": s.isoformat(), "until": t.isoformat(),
            "vault_exported_at": [d.isoformat() for d in report.exported_in(evs)],
            "items": report.to_json(report.build(evs), cfg.vault_url),
        }

    @app.get("/report", response_class=HTMLResponse, dependencies=[Depends(admin)])
    def html_report(email: str, since: datetime | None = None, until: datetime | None = None,
                    hours: int = Query(24, ge=1, le=24 * 400)):
        data = api_report(email, since, until, hours)
        return _report_html(data)

    @app.get("/sheet", response_class=HTMLResponse, dependencies=[Depends(admin)])
    def recovery_sheet(email: str):
        return sheet.render(cfg, user_or_404(email))

    return app


def _report_html(d: dict) -> str:
    e = html.escape
    rows = "".join(
        f"<tr><td><input type=checkbox></td><td>{i['rank']}</td>"
        f"<td>{'⚠️ ' if i['secret_exposed'] else ''}{e(i['worst_action'])}</td>"
        f"<td>{e(', '.join(f'{k} ×{v}' for k, v in i['actions'].items()))}</td>"
        f"<td>{e(i['first'][:16].replace('T', ' '))}</td>"
        f"<td><a href=\"{e(i['open_url'])}\">open in vault</a></td></tr>"
        for i in d["items"]
    ) or "<tr><td colspan=6>Nothing was touched in this window.</td></tr>"
    exported = (
        f"<p class=bad><strong>The whole vault was exported</strong> at {e(', '.join(d['vault_exported_at']))}. "
        "Treat every password as exposed, starting with email and banking.</p>"
        if d["vault_exported_at"] else ""
    )
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>Exposure report — {e(d['user'])}</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;max-width:60rem;margin:0 auto;padding:16px;color:#111;background:#fff}}
table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ddd;padding:6px;text-align:left;vertical-align:top}}
.bad{{border:2px solid #b00;padding:8px 12px}}</style></head><body>
<h1>Exposure report</h1>
<p><strong>{e(d['user'])}</strong> · {e(d['since'][:16])} → {e(d['until'][:16])} UTC</p>
{exported}
<p>Change passwords in this order. ⚠️ means the password or secret itself was shown or copied.
Item names are end-to-end encrypted, so open each one in the vault to see which site it is —
change email and banking logins before anything else.</p>
<table><tr><th>Done</th><th>#</th><th>Worst action</th><th>Everything that happened</th><th>First (UTC)</th><th></th></tr>
{rows}</table></body></html>"""


def main() -> None:
    import uvicorn

    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = load()
    uvicorn.run(create_app(cfg), host="0.0.0.0", port=int(os.environ.get("PORT", "8000")),
                proxy_headers=True, log_level="warning")


if __name__ == "__main__":
    main()
