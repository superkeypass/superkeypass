"""Configuration: a TOML file for family structure, env vars for secrets.

Secrets (admin token, SMTP password) never go in the TOML, so the file can be
kept in a private repo or backed up without leaking anything.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field


@dataclass
class Thresholds:
    reveal_count: int = 5        # distinct items revealed/copied…
    window_minutes: int = 2      # …within this many minutes → mass-reveal alert
    cooldown_minutes: int = 30   # don't repeat the same alert for the same person sooner


@dataclass
class Smtp:
    host: str = ""
    port: int = 587
    user: str = ""
    password: str = ""
    sender: str = ""

    @property
    def enabled(self) -> bool:
        return bool(self.host and self.sender)


@dataclass
class Config:
    vaultwarden_db: str = "/vw-data/db.sqlite3"
    state_db: str = "/data/companion.sqlite3"
    vault_url: str = "https://vault.example.com"
    family_name: str = "Our family"
    admin_name: str = ""
    admin_email: str = ""
    admin_phone: str = ""
    poll_seconds: int = 15
    admin_token: str = ""
    thresholds: Thresholds = field(default_factory=Thresholds)
    smtp: Smtp = field(default_factory=Smtp)
    ntfy_url: str = ""                                   # e.g. https://ntfy.sh/<secret-topic>
    default_contacts: list[str] = field(default_factory=list)
    contacts: dict[str, list[str]] = field(default_factory=dict)  # user email → alert recipients

    def contacts_for(self, email: str) -> list[str]:
        own = self.contacts.get(email.lower(), [])
        # Everyone in `default_contacts` (typically the admin) hears about everything.
        return list(dict.fromkeys([*own, *self.default_contacts]))


def load(path: str | None = None) -> Config:
    path = path or os.environ.get("SKP_CONFIG", "/config/companion.toml")
    raw: dict = {}
    if os.path.exists(path):
        with open(path, "rb") as f:
            raw = tomllib.load(f)

    cfg = Config(
        vaultwarden_db=raw.get("vaultwarden_db", Config.vaultwarden_db),
        state_db=raw.get("state_db", Config.state_db),
        vault_url=raw.get("vault_url", Config.vault_url).rstrip("/"),
        family_name=raw.get("family_name", Config.family_name),
        poll_seconds=int(raw.get("poll_seconds", Config.poll_seconds)),
        ntfy_url=os.environ.get("SKP_NTFY_URL", raw.get("ntfy_url", "")),
        admin_token=os.environ.get("SKP_ADMIN_TOKEN", ""),
    )
    admin = raw.get("admin", {})
    cfg.admin_name = admin.get("name", "")
    cfg.admin_email = admin.get("email", "")
    cfg.admin_phone = admin.get("phone", "")

    t = raw.get("thresholds", {})
    cfg.thresholds = Thresholds(**{k: int(v) for k, v in t.items()})

    cfg.smtp = Smtp(
        host=os.environ.get("SMTP_HOST", ""),
        port=int(os.environ.get("SMTP_PORT", "587")),
        user=os.environ.get("SMTP_USER", ""),
        password=os.environ.get("SMTP_PASS", ""),
        sender=os.environ.get("SMTP_FROM", os.environ.get("SMTP_USER", "")),
    )

    cfg.default_contacts = [e.lower() for e in raw.get("default_contacts", [])]
    for member in raw.get("members", []):
        cfg.contacts[member["email"].lower()] = [e.lower() for e in member.get("alert", [])]
    return cfg
