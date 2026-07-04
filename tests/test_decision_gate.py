

def test_evaluate_decision_conflict_grades_by_priority():
    """Grader af blok: høj-prioritets-konflikt → 'hard', lav-prioritet → 'soft'."""
    from unittest.mock import patch
    from core.services import decision_gate as dg
    hi = [{"decision_id": "d1", "directive": "ingen git push", "priority": 80}]
    lo = [{"decision_id": "d2", "directive": "ingen git push", "priority": 20}]
    with patch("core.services.behavioral_decisions.list_active_decisions", return_value=hi), \
         patch.object(dg, "_detect_conflict", return_value="konflikt"):
        sev, _ = dg.evaluate_decision_conflict("operator_bash", {"command": "git push"})
    assert sev == "hard"
    with patch("core.services.behavioral_decisions.list_active_decisions", return_value=lo), \
         patch.object(dg, "_detect_conflict", return_value="konflikt"):
        sev, _ = dg.evaluate_decision_conflict("operator_bash", {"command": "git push"})
    assert sev == "soft"
    with patch("core.services.behavioral_decisions.list_active_decisions", return_value=[]):
        sev, _ = dg.evaluate_decision_conflict("web_search")
    assert sev == "none"


def test_check_decision_gate_fail_open_records_incident(monkeypatch):
    """Fail-open synlighed: kan gaten ikke læse beslutninger → allow MEN incident flagges,
    og fail-open-adfærden (True, None) er uændret."""
    from core.services import decision_gate as dg

    def _boom(*a, **k):
        raise RuntimeError("db nede")

    monkeypatch.setattr(
        "core.services.behavioral_decisions.list_active_decisions", _boom)
    flagged: list[dict] = []
    monkeypatch.setattr(
        "core.runtime.db_central_incidents.record_central_incident",
        lambda **k: flagged.append(k))

    allowed, reason = dg.check_decision_gate("operator_bash", {"command": "git push"})

    assert allowed is True and reason is None  # adfærd uændret (fail-open)
    assert len(flagged) == 1
    assert flagged[0]["cluster"] == "commit"
    assert flagged[0]["nerve"] == "decision_gate"
    assert flagged[0]["kind"] == "fail_open"


def test_evaluate_decision_conflict_fail_open_records_incident(monkeypatch):
    """Graderet-varianten fejler også synligt til 'none' MEN med incident."""
    from core.services import decision_gate as dg

    def _boom(*a, **k):
        raise RuntimeError("db nede")

    monkeypatch.setattr(
        "core.services.behavioral_decisions.list_active_decisions", _boom)
    flagged: list[dict] = []
    monkeypatch.setattr(
        "core.runtime.db_central_incidents.record_central_incident",
        lambda **k: flagged.append(k))

    sev, reason = dg.evaluate_decision_conflict("operator_bash", {"command": "git push"})

    assert sev == "none" and reason is None  # adfærd uændret (fail-open)
    assert len(flagged) == 1
    assert flagged[0]["cluster"] == "commit"
    assert flagged[0]["kind"] == "fail_open"


def test_decision_gate_incident_failure_does_not_break_gate(monkeypatch):
    """Self-safe: kaster selve incident-loggen ændres gatens adfærd IKKE."""
    from core.services import decision_gate as dg

    def _boom(*a, **k):
        raise RuntimeError("db nede")

    def _incident_boom(**k):
        raise RuntimeError("incident-log nede")

    monkeypatch.setattr(
        "core.services.behavioral_decisions.list_active_decisions", _boom)
    monkeypatch.setattr(
        "core.runtime.db_central_incidents.record_central_incident", _incident_boom)

    allowed, reason = dg.check_decision_gate("operator_bash", {"command": "git push"})
    assert allowed is True and reason is None  # fail-open holder trods incident-fejl
