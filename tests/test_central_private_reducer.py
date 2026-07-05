"""Tests for central_private_reducer.reduce_for_owner (§24.4 private-layer invariant).

Surface liveness/counts/governance-consequence to the OWNER, NEVER raw private content.
"""


def test_drops_raw_keeps_meta():
    from core.services.central_private_reducer import reduce_for_owner
    surface = {"recent_traces": [{"impulse": "x"}], "current_focus": "hemmeligt",
               "trace_count": 3, "liveness": True, "governance_consequence": "caution"}
    out = reduce_for_owner(surface, keep=("trace_count", "liveness", "governance_consequence"))
    assert out == {"trace_count": 3, "liveness": True, "governance_consequence": "caution"}
    assert "recent_traces" not in out and "current_focus" not in out


def test_blocklist_wins_over_keep():
    from core.services.central_private_reducer import reduce_for_owner
    out = reduce_for_owner({"current_focus": "secret", "liveness": True}, keep=("current_focus", "liveness"))
    assert out == {"liveness": True}  # current_focus dropped even though in keep


def test_non_dict_is_empty():
    from core.services.central_private_reducer import reduce_for_owner
    assert reduce_for_owner(None, keep=("a",)) == {}
    assert reduce_for_owner("nope", keep=("a",)) == {}


def test_missing_keep_key_is_omitted():
    from core.services.central_private_reducer import reduce_for_owner
    # keep names a key that isn't present in the surface → simply omitted, no KeyError
    out = reduce_for_owner({"liveness": True}, keep=("liveness", "trace_count", "intensity"))
    assert out == {"liveness": True}


def test_all_blocklist_fields_dropped():
    from core.services.central_private_reducer import reduce_for_owner
    surface = {
        "recent_traces": [1], "current_focus": "a", "current_tool_plan": "b",
        "memory_precedents": [2], "raw": {}, "content": "c", "text": "d", "full": "e",
        "liveness": True,
    }
    # even if every raw field is (mistakenly) asked for, none survive
    out = reduce_for_owner(surface, keep=tuple(surface.keys()))
    assert out == {"liveness": True}


def test_empty_input_and_empty_keep():
    from core.services.central_private_reducer import reduce_for_owner
    assert reduce_for_owner({}, keep=("a",)) == {}
    assert reduce_for_owner({"liveness": True}, keep=()) == {}
