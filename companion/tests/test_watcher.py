from datetime import timedelta

from conftest import MOM, T0

from skp_companion.state import State
from skp_companion.vw import Vaultwarden
from skp_companion.watcher import Watcher


class RecordingNotifier:
    def __init__(self):
        self.sent = []

    def send(self, finding, email, name):
        self.sent.append((finding.kind, email, name, finding))
        return ["test"]


def make(cfg):
    n = RecordingNotifier()
    w = Watcher(cfg, Vaultwarden(cfg.vaultwarden_db), State(cfg.state_db), n)
    return w, n


def test_first_run_ignores_history(cfg, vw):
    vw.reveals(10)                       # a busy past
    w, n = make(cfg)
    assert w.poll_once() == []
    assert n.sent == []


def test_mass_reveal_alerts_once_per_burst(cfg, vw):
    w, n = make(cfg)
    w.poll_once()
    vw.reveals(12, step=timedelta(seconds=5))   # one burst, well over threshold
    w.poll_once()
    assert [s[0] for s in n.sent] == ["mass_reveal"]
    kind, email, name, f = n.sent[0]
    assert (email, name) == ("mom@example.com", "Mom")
    assert len(f.items) >= 5


def test_below_threshold_is_quiet(cfg, vw):
    w, n = make(cfg)
    w.poll_once()
    vw.reveals(4)                                   # normal use
    vw.reveals(4, start=T0 + timedelta(hours=1))
    w.poll_once()
    assert n.sent == []


def test_slow_reveals_do_not_trip(cfg, vw):
    w, n = make(cfg)
    w.poll_once()
    vw.reveals(20, step=timedelta(minutes=1))       # 2 per window
    w.poll_once()
    assert n.sent == []


def test_same_item_repeatedly_is_not_mass_reveal(cfg, vw):
    w, n = make(cfg)
    w.poll_once()
    for i in range(10):
        vw.add(1111, T0 + timedelta(seconds=i), cipher="bank")
    w.poll_once()
    assert n.sent == []


def test_cooldown_survives_restart(cfg, vw):
    w, n = make(cfg)
    w.poll_once()
    vw.reveals(6)
    w.poll_once()
    w2, n2 = make(cfg)                              # restart: fresh detector, same state db
    vw.reveals(6, start=T0 + timedelta(minutes=10))
    w2.poll_once()
    assert len(n.sent) == 1 and n2.sent == []
    vw.reveals(6, start=T0 + timedelta(minutes=45))  # past the 30-min cooldown
    w2.poll_once()
    assert [s[0] for s in n2.sent] == ["mass_reveal"]


def test_export_always_alerts(cfg, vw):
    w, n = make(cfg)
    w.poll_once()
    vw.add(1007, T0)
    vw.add(1007, T0 + timedelta(minutes=1))
    w.poll_once()
    assert [s[0] for s in n.sent] == ["export", "export"]


def test_security_change_alerts(cfg, vw):
    w, n = make(cfg)
    w.poll_once()
    vw.add(1003, T0)                                # 2FA disabled
    w.poll_once()
    assert n.sent[0][0] == "security_change"
    assert "two-step login disabled" in n.sent[0][3].summary


def test_late_batch_with_older_dates_is_still_seen(cfg, vw):
    w, n = make(cfg)
    w.poll_once()
    vw.add(1000, T0 + timedelta(hours=2))           # a newer row lands first
    w.poll_once()
    vw.reveals(6, start=T0)                         # then an offline client uploads older events
    w.poll_once()
    assert [s[0] for s in n.sent] == ["mass_reveal"]


def test_alert_is_logged_with_delivery(cfg, vw):
    w, _ = make(cfg)
    w.poll_once()
    vw.reveals(6)
    w.poll_once()
    [a] = w.state.recent_alerts()
    assert a["kind"] == "mass_reveal" and a["user_uuid"] == MOM and a["delivered"] == ["test"]
