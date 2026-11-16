from __future__ import annotations

from types import SimpleNamespace


def test_agentic_toolbox_uses_run_scope_not_ambient_context(monkeypatch):
    """Regression: implicit scope produced 84/105 alternation in production."""
    from core.services import visible_agentic_toolbox as at

    definition_calls: list[str] = []
    builder_calls: list[dict] = []
    scoped = [{"type": "function", "function": {"name": "read_file"}}]

    def _definitions(*, scope):
        definition_calls.append(scope)
        return scoped

    def _builder(alle, **kwargs):
        builder_calls.append({"alle": alle, **kwargs})
        return list(alle)

    monkeypatch.setattr(
        "core.services.turens_vaerktoejer.vaerktoejer_for_turen", _builder,
    )
    run = SimpleNamespace(
        user_message="ret fejlen",
        session_id="chat-cache",
        autonomous=False,
        run_id="visible-cache",
    )

    assert at.build_agentic_toolbox(
        run, tool_scope="code", get_definitions=_definitions,
    ) == scoped
    assert definition_calls == ["code"]
    assert builder_calls == [{
        "alle": scoped,
        "user_message": "ret fejlen",
        "session_id": "chat-cache",
        "lane": "visible",
        "run_id": "visible-cache",
    }]


def test_agentic_toolbox_preserves_autonomous_lane(monkeypatch):
    from core.services import visible_agentic_toolbox as at

    seen: dict = {}
    monkeypatch.setattr(
        "core.services.turens_vaerktoejer.vaerktoejer_for_turen",
        lambda alle, **kwargs: seen.update(kwargs) or alle,
    )
    run = SimpleNamespace(
        user_message="fortsæt",
        session_id="auto-cache",
        autonomous=True,
        run_id="visible-auto",
    )

    at.build_agentic_toolbox(
        run, tool_scope="chat", get_definitions=lambda *, scope: [],
    )
    assert seen["lane"] == "autonomous"
    assert seen["run_id"] == "visible-auto"


def test_first_pass_and_agentic_round_are_byte_identical_for_same_scope():
    """The production invariant: no 84→105 rewrite after the first call."""
    from core.services import visible_agentic_toolbox as at
    from core.services.session_tool_pin import clear
    from core.services.turens_vaerktoejer import vaerktoejer_for_turen
    from core.tools.simple_tools import get_tool_definitions

    sid = "agentic-toolbox-byte-regression"
    run = SimpleNamespace(
        user_message="undersøg fejlen",
        session_id=sid,
        autonomous=False,
        run_id="visible-byte-regression",
    )
    clear(sid)
    try:
        first_pass = vaerktoejer_for_turen(
            get_tool_definitions(scope="chat"),
            user_message=run.user_message,
            session_id=sid,
        )
        agentic = at.build_agentic_toolbox(
            run, tool_scope="chat", get_definitions=get_tool_definitions,
        )
        assert agentic == first_pass
    finally:
        clear(sid)
