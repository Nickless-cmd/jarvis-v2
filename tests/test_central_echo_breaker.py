from unittest import mock
from core.services import central_echo_breaker as eb


def test_proposes_simpler_alternative_per_candidate():
    fake = {"chokepoint_tax_pct": 95.4, "candidates": [
        {"nerve": "veto", "cluster": "commit", "total": 500},
        {"nerve": "fact_gate", "cluster": "commit", "total": 300}]}
    with mock.patch("core.services.central_decentralization.analyze_chokepoint", return_value=fake):
        out = eb.break_echo(limit=5)
    assert out["count"] == 2
    top = out["alternatives"][0]
    assert top["process"] == "veto" and "resolve grønt lokalt" in top["simpler"]
    assert "500" in top["projected_saving"]


def test_limit_caps_alternatives():
    fake = {"chokepoint_tax_pct": 90.0,
            "candidates": [{"nerve": f"n{i}", "total": 100 - i} for i in range(10)]}
    with mock.patch("core.services.central_decentralization.analyze_chokepoint", return_value=fake):
        assert eb.break_echo(limit=3)["count"] == 3


def test_record_observes_metadata_only():
    obs = []
    fc = mock.MagicMock(); fc.observe.side_effect = lambda e: obs.append(e)
    with mock.patch("core.services.central_decentralization.analyze_chokepoint",
                    return_value={"chokepoint_tax_pct": 0.0, "candidates": []}), \
            mock.patch("core.services.central_core.central", return_value=fc):
        eb.record_echo_breaker()
    assert obs and obs[0]["nerve"] == "echo_breaker"
    assert set(obs[0]) <= {"cluster", "nerve", "kind", "count", "tax_pct"}
