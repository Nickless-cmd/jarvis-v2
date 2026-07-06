from unittest import mock
from core.services import central_architect as ca


def test_speaks_one_cut_at_high_pressure():
    surf = {"pressure": 100, "worst_files": [
        {"file": "core/runtime/db.py", "lines": 33000, "over_hard": True},
        {"file": "core/services/heartbeat_runtime.py", "lines": 7000, "over_hard": True}]}
    with mock.patch("core.services.central_excess.build_excess_surface", return_value=surf):
        a = ca.assess()
    assert a["target"] == "core/runtime/db.py"
    assert "Split" in a["recommendation"] and "33,000" in a["recommendation"]


def test_silent_at_low_pressure():
    with mock.patch("core.services.central_excess.build_excess_surface",
                    return_value={"pressure": 10, "worst_files": []}):
        a = ca.assess()
    assert a["target"] == "" and a["recommendation"] == ""


def test_record_observes_metadata_only():
    surf = {"pressure": 80, "worst_files": [{"file": "x.py", "lines": 5000, "over_hard": True}]}
    obs = []
    fc = mock.MagicMock(); fc.observe.side_effect = lambda e: obs.append(e)
    with mock.patch("core.services.central_excess.build_excess_surface", return_value=surf), \
            mock.patch("core.services.central_core.central", return_value=fc):
        ca.record_architect()
    assert obs and obs[0]["nerve"] == "architect"
    assert set(obs[0]) <= {"cluster", "nerve", "kind", "pressure", "target"}
