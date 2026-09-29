from datetime import timedelta

import pytest
from conftest import T0
from fastapi.testclient import TestClient

from skp_companion import alerts
from skp_companion.app import create_app
from skp_companion.detector import Finding

AUTH = ("admin", "s3cret")


@pytest.fixture
def client(cfg):
    with TestClient(create_app(cfg, start_watcher=False)) as c:
        yield c


def test_refuses_to_start_without_token(cfg):
    cfg.admin_token = ""
    with pytest.raises(SystemExit):
        create_app(cfg, start_watcher=False)


@pytest.mark.parametrize("path", ["/api/alerts", "/api/report?email=mom@example.com", "/sheet?email=mom@example.com"])
def test_everything_but_health_needs_auth(client, path):
    assert client.get(path).status_code == 401
    assert client.get(path, auth=("admin", "wrong")).status_code == 401
    assert client.get(path, auth=AUTH).status_code == 200


def test_health_reports_stale_when_watcher_never_ran(client):
    r = client.get("/health").json()
    assert r["ok"] is False and r["last_poll"] is None


def test_health_fails_with_no_alert_channel(cfg):
    with TestClient(create_app(cfg, start_watcher=False)) as c:
        c.app.state.watcher.poll_once()
        r = c.get("/health").json()
    assert r["ok"] is False and r["error"] == "no alert channel configured"
    cfg.ntfy_url = "https://ntfy.sh/test-topic"
    with TestClient(create_app(cfg, start_watcher=False)) as c:
        c.app.state.watcher.poll_once()
        assert c.get("/health").json()["ok"] is True


def test_report_ranks_exposed_secrets_first(client, vw):
    vw.add(1114, T0, cipher="shop")                      # autofilled a lot
    vw.add(1114, T0 + timedelta(seconds=1), cipher="shop")
    vw.add(1114, T0 + timedelta(seconds=2), cipher="shop")
    vw.add(1107, T0, cipher="notes")                     # just opened
    vw.add(1111, T0 + timedelta(minutes=1), cipher="bank")  # password copied
    vw.add(1007, T0 + timedelta(minutes=2))              # export
    r = client.get("/api/report", auth=AUTH, params={
        "email": "MOM@example.com", "since": (T0 - timedelta(hours=1)).isoformat(),
        "until": (T0 + timedelta(hours=1)).isoformat()}).json()
    assert [i["cipher_uuid"] for i in r["items"]] == ["bank", "shop", "notes"]
    assert r["items"][0]["secret_exposed"] and not r["items"][1]["secret_exposed"]
    assert r["items"][0]["open_url"] == "https://vault.example.com/#/vault?itemId=bank"
    assert len(r["vault_exported_at"]) == 1


def test_report_window_excludes_outside_events(client, vw):
    vw.add(1111, T0 - timedelta(days=3), cipher="old")
    r = client.get("/api/report", auth=AUTH, params={
        "email": "mom@example.com", "since": T0.isoformat(), "until": (T0 + timedelta(hours=1)).isoformat()}).json()
    assert r["items"] == []


def test_html_report_and_sheet_render(client, vw):
    vw.add(1111, T0, cipher="bank")
    html = client.get("/report", auth=AUTH, params={
        "email": "mom@example.com", "since": T0.isoformat(), "until": (T0 + timedelta(hours=1)).isoformat()}).text
    assert "password copied" in html and "open in vault" in html
    sheet = client.get("/sheet", auth=AUTH, params={"email": "mom@example.com"}).text
    assert "Nobody from SuperkeyPass" in sheet and "https://vault.example.com" in sheet and "<svg" in sheet


def test_unknown_user_404(client):
    assert client.get("/sheet", auth=AUTH, params={"email": "nobody@example.com"}).status_code == 404


def test_alert_goes_to_user_contacts_plus_admin(cfg):
    assert cfg.contacts_for("Mom@example.com".lower()) == ["sis@example.com", "admin@example.com"]
    title, body = alerts.compose(cfg, Finding("mass_reveal", "u", T0, "7 passwords revealed."), "mom@example.com", "Mom")
    assert "Mom" in title and "exposure report" in body and "/skp/report?email=mom@example.com" in body
