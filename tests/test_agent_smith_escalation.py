from __future__ import annotations

from core.services.central_agent_smith_escalation import (
    RUNG_BIND,
    RUNG_COMMENT,
    RUNG_CONFRONT,
    pattern_key,
    step_escalation,
    top_line,
)

PK = pattern_key("phrase", "vil du have")


def _det(metric: float, label: str = "vil du have", kind: str = "phrase"):
    # corroborated=True = et ægte drift-signal, så disse tests øver LADDER-MEKANISMEN
    # (bind→mint→confront→loft) uafhængigt af drift-gaten. Jævn frekvens uden drift
    # eskalerer bevidst IKKE længere — det dækkes af test_agent_smith_escalation_criteria.
    return {pattern_key(kind, label): {"kind": kind, "label": label, "metric": metric,
                                       "corroborated": True}}


def _types(actions, t):
    return [a for a in actions if a.get("type") == t]


def test_new_pattern_starts_at_comment():
    st, acts = step_escalation(None, _det(5), "t0")
    p = st["patterns"][PK]
    assert p["rung"] == RUNG_COMMENT
    assert p["decision_id"] is None
    assert _types(acts, "voice")[0]["rung"] == "comment"
    assert not _types(acts, "mint")  # ingen binding endnu


def test_persistence_escalates_to_bind_and_mints():
    st, _ = step_escalation(None, _det(5), "t0")       # rung1
    st, _ = step_escalation(st, _det(5), "t1")          # dwell (cycles_at_rung=1, ikke > 1)
    st, acts = step_escalation(st, _det(5), "t2")       # klatrer til bind
    assert st["patterns"][PK]["rung"] == RUNG_BIND
    assert _types(acts, "mint"), "Trin 2 skal auto-minte et direktiv"
    assert _types(acts, "voice")[0]["rung"] == "bind"


def test_bind_then_confront_when_still_ignored():
    st, _ = step_escalation(None, _det(5), "t0")
    st, _ = step_escalation(st, _det(5), "t1")
    st, _ = step_escalation(st, _det(5), "t2")          # bind
    st["patterns"][PK]["decision_id"] = "dec_x"          # simulér mintet direktiv
    st, _ = step_escalation(st, _det(5), "t3")          # dwell på bind
    st, acts = step_escalation(st, _det(5), "t4")       # konfrontér
    assert st["patterns"][PK]["rung"] == RUNG_CONFRONT
    assert _types(acts, "arm_confront")
    assert _types(acts, "voice")[0]["rung"] == "confront"


def test_confront_is_ceiling_no_further_climb():
    st, _ = step_escalation(None, _det(5), "t0")
    st, _ = step_escalation(st, _det(5), "t1")
    st, _ = step_escalation(st, _det(5), "t2")
    st, _ = step_escalation(st, _det(5), "t3")
    st, _ = step_escalation(st, _det(5), "t4")          # confront
    st, acts = step_escalation(st, _det(5), "t5")       # bliver på confront
    assert st["patterns"][PK]["rung"] == RUNG_CONFRONT
    assert not _types(acts, "escalate")


def test_compliance_weakened_resolves_and_revokes():
    st, _ = step_escalation(None, _det(5), "t0")
    st, _ = step_escalation(st, _det(5), "t1")
    st, _ = step_escalation(st, _det(5), "t2")          # bind, baseline=5
    st["patterns"][PK]["decision_id"] = "dec_x"
    # metric falder til 2 (< 5*0.6=3.0) → compliance
    st, acts = step_escalation(st, _det(2), "t3")
    assert PK not in st["patterns"]                      # sporing ophørt
    assert _types(acts, "revoke")[0]["decision_id"] == "dec_x"
    assert _types(acts, "voice")[0]["rung"] == "resolved"
    assert st["resolved"][-1]["label"] == "vil du have"


def test_pattern_disappears_resolves_as_full_compliance():
    st, _ = step_escalation(None, _det(5), "t0")
    st, _ = step_escalation(st, _det(5), "t1")
    st, _ = step_escalation(st, _det(5), "t2")          # bind
    st["patterns"][PK]["decision_id"] = "dec_x"
    st, acts = step_escalation(st, {}, "t3")            # mønster helt væk
    assert PK not in st["patterns"]
    assert _types(acts, "revoke")
    resolved = _types(acts, "observe")
    assert any(o.get("reason") == "disappeared" for o in resolved)


def test_max_active_directives_cap():
    # tre forskellige mønstre op til bind → tre direktiver; det fjerde binder ikke
    st = None
    labels = ["a a a", "b b b", "c c c", "d d d"]
    det_all = {}
    for lab in labels:
        det_all.update(_det(5, label=lab))
    st, _ = step_escalation(st, det_all, "t0")
    st, _ = step_escalation(st, det_all, "t1")
    st, acts = step_escalation(st, det_all, "t2")
    # sæt decision_id på de tre der nåede at minte (simulér I/O)
    minted = _types(acts, "mint")
    assert len(minted) == 3, "loft på 3 aktive auto-direktiver"


def test_top_line_prefers_confront():
    actions = [
        {"type": "voice", "rung": "comment", "line": "c"},
        {"type": "voice", "rung": "confront", "line": "CONFRONT"},
        {"type": "voice", "rung": "bind", "line": "b"},
    ]
    assert top_line(actions) == "CONFRONT"
