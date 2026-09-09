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


# ── K5: overtagelsen haandhaeves lige foer udbyder-graensen ──────────────

def _pending(monkeypatch, approval_id, tool="bash", args=None):
    """Laeg en ventende godkendelse i den delte tilstand funktionen laeser."""
    import core.services.visible_runs_approvals as A
    p = {"tool_name": tool, "arguments": args or {"command": "ls"},
         "run_id": "r1", "session_id": "s1", "status": "pending"}
    A._vr._PENDING_APPROVALS[approval_id] = p
    return p


def _fang_kald(monkeypatch, kaldt):
    """`execute_tool_force` importeres INDE i funktionen, saa den skal patches
    paa sit hjem-modul, ikke paa kaldestedet."""
    import core.tools.simple_tools as ST
    monkeypatch.setattr(ST, "execute_tool_force",
                        lambda n, a, **k: (kaldt.append(n), {"status": "ok"})[1])
    monkeypatch.setattr(ST, "format_tool_result_for_model", lambda n, r: "ok")


def test_i_SKYGGE_koerer_kaldet_selv_om_broen_siger_nej(isolated_runtime,
                                                        monkeypatch):
    """Skyggen afgoer intet. Et nej maa ikke stoppe noget foer broen er aktiv."""
    import core.services.visible_runs_approvals as A
    import core.services.approval_bridge_shadow as S
    import core.tools.approval_rollout_gate as G

    monkeypatch.setattr(S, "note_claim", lambda *a, **k: (False, "nej"))
    monkeypatch.setattr(G, "bridge_active", lambda: False)
    kaldt = []
    _fang_kald(monkeypatch, kaldt)
    _pending(monkeypatch, "appr-1")

    A.resolve_pending_approval("appr-1", approved=True)
    assert kaldt == ["bash"]


def test_naar_broen_HAANDHAEVER_stopper_et_nej_kaldet(isolated_runtime,
                                                      monkeypatch):
    """Hele K5: det afviste kald maa ikke krydse udbyder-graensen."""
    import core.services.visible_runs_approvals as A
    import core.services.approval_bridge_shadow as S
    import core.tools.approval_rollout_gate as G

    monkeypatch.setattr(S, "note_claim",
                        lambda *a, **k: (False, "allerede overtaget"))
    monkeypatch.setattr(G, "bridge_active", lambda: True)
    kaldt = []
    _fang_kald(monkeypatch, kaldt)
    _pending(monkeypatch, "appr-2")

    ud = A.resolve_pending_approval("appr-2", approved=True)
    assert kaldt == [], "kaldet krydsede graensen trods et nej"
    assert ud["status"] == "error" and "kunne ikke overtages" in ud["error"]
    assert ud["tool"] == "bash" and ud["chat_persisted"] is False


def test_naar_broen_HAANDHAEVER_slipper_et_ja_igennem(isolated_runtime,
                                                      monkeypatch):
    import core.services.visible_runs_approvals as A
    import core.services.approval_bridge_shadow as S
    import core.tools.approval_rollout_gate as G

    monkeypatch.setattr(S, "note_claim", lambda *a, **k: (True, ""))
    monkeypatch.setattr(G, "bridge_active", lambda: True)
    kaldt = []
    _fang_kald(monkeypatch, kaldt)
    _pending(monkeypatch, "appr-3")

    A.resolve_pending_approval("appr-3", approved=True)
    assert kaldt == ["bash"]


def test_en_skygge_der_KASTER_stopper_ingenting(isolated_runtime, monkeypatch):
    """Maaleredskabet maa ikke kunne naegte en godkendelse brugeren gav."""
    import core.services.visible_runs_approvals as A
    import core.services.approval_bridge_shadow as S
    import core.tools.approval_rollout_gate as G

    monkeypatch.setattr(S, "note_claim",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("i stykker")))
    monkeypatch.setattr(G, "bridge_active", lambda: True)
    kaldt = []
    _fang_kald(monkeypatch, kaldt)
    _pending(monkeypatch, "appr-4")

    A.resolve_pending_approval("appr-4", approved=True)
    assert kaldt == ["bash"]
