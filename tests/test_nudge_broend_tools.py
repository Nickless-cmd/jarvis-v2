"""Matrix-nudge unaddressed-wiring i nudge-tools: dismiss tæller op, ikke-matrix rører intet.

Regression: dismiss-blokken kaldte get(nudge_id) uden at importere get → NameError blev
slugt af except → increment_unaddressed fyrede ALDRIG. Testen fanger det.
"""
from core.tools import nudge_broend_tools as t


def test_dismiss_increments_unaddressed_for_matrix_nudge(monkeypatch):
    calls = []
    monkeypatch.setattr("core.services.nudge_broend.mark_dismissed", lambda nid, reason="": True)
    monkeypatch.setattr("core.services.nudge_broend.dismiss_all", lambda reason="": 0)
    monkeypatch.setattr("core.services.nudge_broend.get",
                        lambda nid: {"source": "matrix/smith", "status": "pending"})
    monkeypatch.setattr("core.services.central_matrix_ensemble.increment_unaddressed",
                        lambda cid: calls.append(cid))
    r = t._exec_nudge_dismiss({"nudge_id": "n1"})
    assert r["status"] == "ok"
    assert calls == ["smith"]   # var dead før get-import-fix


def test_dismiss_non_matrix_nudge_does_not_increment(monkeypatch):
    calls = []
    monkeypatch.setattr("core.services.nudge_broend.mark_dismissed", lambda nid, reason="": True)
    monkeypatch.setattr("core.services.nudge_broend.dismiss_all", lambda reason="": 0)
    monkeypatch.setattr("core.services.nudge_broend.get",
                        lambda nid: {"source": "action_router/x", "status": "pending"})
    monkeypatch.setattr("core.services.central_matrix_ensemble.increment_unaddressed",
                        lambda cid: calls.append(cid))
    t._exec_nudge_dismiss({"nudge_id": "n1"})
    assert calls == []   # extract_cid("action_router/x") == None → ingen increment
