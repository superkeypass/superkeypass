"""Exposure report — "what was touched, and what do I change first?"

The server only knows item IDs: names, usernames and URLs are end-to-end
encrypted and the companion never sees them. So the ranking here is by *what
happened to* each item (copied beats autofilled beats merely opened), and
each row links into the web vault, where the admin or user sees the name and
can change the password. Ranking by what an item *is* (bank before shopping)
has to happen client-side — see docs/feature-ideas.md.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from .events import EXPOSURE_WEIGHT, LABEL, TOUCHES, Ev
from .vw import Event


@dataclass
class ItemExposure:
    cipher_uuid: str
    score: int
    actions: Counter = field(default_factory=Counter)
    first: datetime | None = None
    last: datetime | None = None
    ips: set[str] = field(default_factory=set)

    @property
    def worst(self) -> str:
        worst = max(self.actions, key=lambda t: EXPOSURE_WEIGHT.get(t, 0))
        return LABEL[Ev(worst)]

    @property
    def secret_exposed(self) -> bool:
        return max(EXPOSURE_WEIGHT.get(t, 0) for t in self.actions) >= 3


def build(events: list[Event]) -> list[ItemExposure]:
    items: dict[str, ItemExposure] = {}
    for ev in events:
        if ev.type not in TOUCHES or not ev.cipher_uuid:
            continue
        it = items.setdefault(ev.cipher_uuid, ItemExposure(ev.cipher_uuid, 0))
        it.actions[ev.type] += 1
        it.score += EXPOSURE_WEIGHT.get(ev.type, 0)
        it.first = min(it.first or ev.at, ev.at)
        it.last = max(it.last or ev.at, ev.at)
        if ev.ip:
            it.ips.add(ev.ip)
    # Secrets that were exposed come first; within that, the most-handled items.
    return sorted(items.values(), key=lambda i: (not i.secret_exposed, -i.score, i.first))


def exported_in(events: list[Event]) -> list[datetime]:
    return [e.at for e in events if e.type == Ev.USER_EXPORTED_VAULT]


def to_json(ranked: list[ItemExposure], vault_url: str) -> list[dict]:
    return [
        {
            "rank": n,
            "cipher_uuid": i.cipher_uuid,
            "secret_exposed": i.secret_exposed,
            "worst_action": i.worst,
            "actions": {LABEL[Ev(t)]: c for t, c in i.actions.items()},
            "first": i.first.isoformat(),
            "last": i.last.isoformat(),
            "ips": sorted(i.ips),
            "open_url": item_url(vault_url, i.cipher_uuid),
        }
        for n, i in enumerate(ranked, 1)
    ]


def item_url(vault_url: str, cipher_uuid: str) -> str:
    return f"{vault_url}/#/vault?itemId={cipher_uuid}"
