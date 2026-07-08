import core.services.visible_runs  # noqa: F401  — prime module load order (avoids circular import)
import core.services.visible_runs_approvals as vra
import core.services.permission_classifier as pc


def test_resolve_unknown_returns_error(monkeypatch):
    monkeypatch.setattr(vra._vr, "_PENDING_APPROVALS", {})
    monkeypatch.setattr(vra._vr, "_persist_pending_approvals", lambda: None)
    monkeypatch.setattr(vra._vr, "_get_visible_approval_state", lambda aid: None)
    res = vra.resolve_pending_approval("does-not-exist", approved=True)
    assert res["status"] == "error"


def test_gold_hook_records_owner_decision_on_deny(monkeypatch):
    # Part E hook 2: resolving a surfaced approval records the GOLD outcome vs the stashed prediction.
    pc._stash.clear()
    pc.stash_prediction("appr-x", "write_file", "approve")
    pending = {"status": "pending", "tool_name": "write_file", "session_id": "s"}
    monkeypatch.setattr(vra._vr, "_PENDING_APPROVALS", {"appr-x": dict(pending)})
    monkeypatch.setattr(vra._vr, "_persist_pending_approvals", lambda: None)
    monkeypatch.setattr(vra._vr, "_get_visible_approval_state", lambda aid: None)
    monkeypatch.setattr(vra._vr, "_set_visible_approval_state", lambda aid, st: None)
    monkeypatch.setattr(vra.event_bus, "publish", lambda *a, **k: None)

    recorded = {}
    def _rec(tool, *, predicted, actual, is_owner_gold):
        recorded.update(tool=tool, predicted=predicted, actual=actual, gold=is_owner_gold)
    monkeypatch.setattr(pc, "record_prediction_outcome", _rec)

    vra.resolve_pending_approval("appr-x", approved=False)
    assert recorded == {"tool": "write_file", "predicted": "approve", "actual": "deny", "gold": True}
    # prediction consumed (popped) so a duplicate resolution can't double-count
    assert pc.pop_prediction("appr-x") is None
