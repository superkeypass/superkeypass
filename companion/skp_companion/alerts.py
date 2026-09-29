"""Alert fan-out to trusted contacts: email (SMTP) and push (ntfy).

Delivery failures are logged and recorded, never raised — an unreachable mail
relay must not stop the poller from watching. Because a silent alert channel
is exactly the failure that goes unnoticed, the alert log (/api/alerts) shows
which channels actually accepted each alert.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
import urllib.request
from email.message import EmailMessage

from .config import Config
from .detector import Finding

log = logging.getLogger(__name__)

TITLES = {
    "mass_reveal": "Many passwords were just revealed",
    "export": "A vault was exported",
    "security_change": "Account security was changed",
}


def compose(cfg: Config, finding: Finding, user_email: str, user_name: str) -> tuple[str, str]:
    who = user_name or user_email
    title = f"SuperkeyPass: {TITLES.get(finding.kind, 'Security alert')} — {who}"
    report = f"{cfg.vault_url}/skp/report?email={user_email}"
    body = f"""{finding.summary}

Account: {who} <{user_email}>
When:    {finding.at:%Y-%m-%d %H:%M} UTC

If this was {who}, you can ignore this message.

If it was NOT, act now:
  1. Call {who} and check where their phone and computer are.
  2. Ask the family admin to lock the account and sign out every device
     (Vaultwarden admin panel → Users → Deauthorize sessions).
  3. Open the exposure report to see which passwords to change first:
     {report}

— SuperkeyPass, {cfg.family_name}
"""
    return title, body


def send_email(cfg: Config, to: list[str], subject: str, body: str) -> bool:
    if not cfg.smtp.enabled or not to:
        return False
    msg = EmailMessage()
    msg["From"] = cfg.smtp.sender
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(cfg.smtp.host, cfg.smtp.port, timeout=20) as s:
            s.starttls(context=ssl.create_default_context())
            if cfg.smtp.user:
                s.login(cfg.smtp.user, cfg.smtp.password)
            s.send_message(msg)
        return True
    except Exception as e:  # noqa: BLE001 — see module docstring
        log.error("alert email failed: %s", e)
        return False


def send_ntfy(cfg: Config, title: str, body: str) -> bool:
    if not cfg.ntfy_url:
        return False
    req = urllib.request.Request(
        cfg.ntfy_url, data=body.encode(), method="POST",
        headers={"Title": title.encode("ascii", "replace").decode(), "Priority": "urgent", "Tags": "rotating_light"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return 200 <= r.status < 300
    except Exception as e:  # noqa: BLE001
        log.error("alert push failed: %s", e)
        return False


class Notifier:
    """Sends one finding to every channel; returns the channels that accepted it."""

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def send(self, finding: Finding, user_email: str, user_name: str) -> list[str]:
        title, body = compose(self.cfg, finding, user_email, user_name)
        delivered = []
        if send_email(self.cfg, self.cfg.contacts_for(user_email), title, body):
            delivered.append("email")
        if send_ntfy(self.cfg, title, body):
            delivered.append("ntfy")
        if not delivered:
            log.warning("ALERT NOT DELIVERED (no channel accepted it): %s", title)
        return delivered
