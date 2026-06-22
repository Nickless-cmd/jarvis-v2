

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
