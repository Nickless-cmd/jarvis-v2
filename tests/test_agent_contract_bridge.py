"""agent_contract_bridge: hvem ejer agenten, og hvornaar bindes den ikke."""
from __future__ import annotations

import pytest

from core.services.agent_contract_bridge import bind_new_agent, resolve_owner_and_session


@pytest.mark.parametrize("ctx,expected", [
    ({"user_id": " bjorn ", "parent_session_id": "s1"}, ("bjorn", "s1")),
    ({"user_id": "bjorn"}, ("bjorn", "")),
    ({"parent_session_id": "s1"}, ("", "s1")),
    ({}, ("", "")),
    (None, ("", "")),
])
def test_resolve_uses_explicit_context_and_never_invents_an_owner(ctx, expected):
    assert resolve_owner_and_session(ctx) == expected


def test_resolve_falls_back_to_the_authenticated_request_context():
    from core.identity import workspace_context as w

    tok = w.set_context(workspace_name="bjorn", user_id="u-42", session_id="sess-42")
    try:
        assert resolve_owner_and_session({}) == ("u-42", "sess-42")
        # eksplicit kontekst vinder over request-konteksten
        assert resolve_owner_and_session({"user_id": "x", "parent_session_id": "y"}) == ("x", "y")
    finally:
        w.reset_context(tok)


def test_bind_returns_a_reason_when_it_does_not_bind():
    base = dict(agent_id="x", parent_agent_id="jarvis", goal="g")
    assert bind_new_agent(**base, persistent=False, context={}) == {
        "bound": False, "reason": "no_owner_or_session"}
    assert bind_new_agent(**base, persistent=True,
                          context={"user_id": "b", "parent_session_id": "s"}) == {
        "bound": False, "reason": "persistent"}


def test_bind_never_raises_even_when_the_agent_is_unknown(isolated_runtime):
    out = bind_new_agent(agent_id="findes-ikke", parent_agent_id="jarvis", goal="g",
                         persistent=False, context={"user_id": "b", "parent_session_id": "s"})
    assert out["bound"] is False and out["reason"] == "error"
