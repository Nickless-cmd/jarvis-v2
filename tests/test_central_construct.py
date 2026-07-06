from unittest import mock
from core.services import central_construct as cc


def test_safe_vs_risky_vs_protected():
    fake = {
        "veto": {"cluster": "commit", "total": 500, "green": 500},           # overhead → safe
        "memory_promotion": {"cluster": "memory", "total": 400, "green": 200},  # fangster → risky
        "decision_gate": {"cluster": "commit", "total": 50, "green": 50},    # for lidt → insufficient
        "central_self_probe": {"cluster": "system", "total": 9000, "green": 9000},  # protected
    }
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake):
        assert cc.simulate_silence("veto")["risk"] == "safe"
        assert cc.simulate_silence("memory_promotion")["risk"] == "risky"
        assert cc.simulate_silence("decision_gate")["risk"] == "insufficient"
        assert cc.simulate_silence("central_self_probe")["risk"] == "protected"


def test_surface_partitions_and_observes_metadata_only():
    fake = {
        "veto": {"cluster": "commit", "total": 500, "green": 500},
        "memory_promotion": {"cluster": "memory", "total": 400, "green": 200},
    }
    obs = []
    fc = mock.MagicMock(); fc.observe.side_effect = lambda e: obs.append(e)
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake), \
            mock.patch("core.services.central_core.central", return_value=fc):
        surf = cc.record_construct()
    assert [s["nerve"] for s in surf["safe_to_silence"]] == ["veto"]
    assert [s["nerve"] for s in surf["must_keep"]] == ["memory_promotion"]
    assert set(obs[0]) <= {"cluster", "nerve", "kind", "safe_count", "risky_count"}


def test_unknown_nerve_is_insufficient():
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value={}):
        assert cc.simulate_silence("nope")["risk"] == "insufficient"
