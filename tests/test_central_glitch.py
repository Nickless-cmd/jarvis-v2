from datetime import UTC, datetime, timedelta
from unittest import mock
from core.services import central_glitch as cg


def _iso(days_ago):
    return (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()


def test_always_shadow_flagged_enforce_or_retire():
    fake = {"loop_control": {"cluster": "loop", "total": 300, "green": 0, "skip": 300,
                             "last_ts": _iso(0)}}
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake):
        out = cg.detect_glitches()
    assert out["always_shadow"] == 1
    g = out["glitches"][0]
    assert g["type"] == "always_shadow" and g["action"] == "enforce_or_retire"


def test_protected_always_shadow_only_investigate():
    fake = {"cross_user_share": {"cluster": "privacy", "total": 50, "green": 0, "skip": 50,
                                 "last_ts": _iso(0)}}
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake):
        out = cg.detect_glitches()
    assert out["glitches"][0]["action"] == "investigate"   # aldrig retire på security


def test_frozen_nerve_detected():
    fake = {"old_gate": {"cluster": "commit", "total": 100, "green": 100, "skip": 0,
                         "last_ts": _iso(30)}}
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake):
        out = cg.detect_glitches()
    assert out["frozen"] == 1 and out["glitches"][0]["type"] == "frozen"


def test_live_recent_nerve_is_not_glitch():
    fake = {"veto": {"cluster": "commit", "total": 500, "green": 500, "skip": 0,
                     "last_ts": _iso(0)}}
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake):
        out = cg.detect_glitches()
    assert out["glitches"] == []


def test_low_volume_stale_is_not_frozen():
    fake = {"rare": {"cluster": "x", "total": 5, "green": 5, "skip": 0, "last_ts": _iso(60)}}
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake):
        assert cg.detect_glitches()["frozen"] == 0   # for lidt volumen til at "dø"


def test_record_observes_metadata_only():
    obs = []
    fc = mock.MagicMock(); fc.observe.side_effect = lambda e: obs.append(e)
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value={}), \
            mock.patch("core.services.central_core.central", return_value=fc):
        cg.record_glitches()
    assert obs and obs[0]["nerve"] == "glitch"
    assert set(obs[0]) <= {"cluster", "nerve", "kind", "always_shadow", "frozen"}
