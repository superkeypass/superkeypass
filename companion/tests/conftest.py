import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from skp_companion.config import Config, Thresholds
from skp_companion.vw import to_vw_date

# The real table from vaultwarden migrations/sqlite/2022-10-18-170602_add_events/up.sql
EVENT_DDL = """
CREATE TABLE event (
  uuid TEXT NOT NULL PRIMARY KEY, event_type INTEGER NOT NULL, user_uuid TEXT, org_uuid TEXT,
  cipher_uuid TEXT, collection_uuid TEXT, group_uuid TEXT, org_user_uuid TEXT, act_user_uuid TEXT,
  device_type INTEGER, ip_address TEXT, event_date DATETIME NOT NULL, policy_uuid TEXT,
  provider_uuid TEXT, provider_user_uuid TEXT, provider_org_uuid TEXT, UNIQUE (uuid)
);
CREATE TABLE users (uuid TEXT PRIMARY KEY, email TEXT NOT NULL, name TEXT NOT NULL);
"""

T0 = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
MOM = "11111111-1111-1111-1111-111111111111"
ORG = "99999999-9999-9999-9999-999999999999"


class FakeVW:
    def __init__(self, path):
        self.path = str(path)
        c = sqlite3.connect(self.path)
        c.executescript(EVENT_DDL)
        c.execute("INSERT INTO users VALUES (?, 'mom@example.com', 'Mom')", (MOM,))
        c.commit()
        c.close()

    def add(self, event_type, at, cipher=None, user=MOM, ip="203.0.113.7"):
        c = sqlite3.connect(self.path)
        c.execute(
            "INSERT INTO event (uuid, event_type, user_uuid, org_uuid, cipher_uuid, act_user_uuid, "
            "device_type, ip_address, event_date) VALUES (?,?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), int(event_type), cipher and ORG, ORG, cipher, user, 1, ip, to_vw_date(at)),
        )
        c.commit()
        c.close()

    def reveals(self, n, start=T0, step=timedelta(seconds=10), event_type=1111):
        for i in range(n):
            self.add(event_type, start + i * step, cipher=f"cipher-{i}")


@pytest.fixture
def vw(tmp_path):
    return FakeVW(tmp_path / "vw.sqlite3")


@pytest.fixture
def cfg(tmp_path, vw):
    return Config(
        vaultwarden_db=vw.path,
        state_db=str(tmp_path / "state.sqlite3"),
        vault_url="https://vault.example.com",
        family_name="The Test Family",
        admin_name="Vincent",
        admin_email="admin@example.com",
        admin_token="s3cret",
        thresholds=Thresholds(reveal_count=5, window_minutes=2, cooldown_minutes=30),
        default_contacts=["admin@example.com"],
        contacts={"mom@example.com": ["sis@example.com"]},
    )
