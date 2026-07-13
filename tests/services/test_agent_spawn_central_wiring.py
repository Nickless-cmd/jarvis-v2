"""Integration: dispatch-seamen (execute_agent_task) skal wire udfald ind i
Agents-clusteret — note_agent_result PRÆCIS én gang pr. dispatch (både succes og
fejl), og note_agent_blocked når den typede status er blocked/needs_context.

Vi stubber HELE DB-/model-seamen på spawn-modulet, så kun wiring-adfærden testes
(ingen rigtig DB, ingen rigtig model).
"""

import core.services.agent_runtime_spawn as ars


def _stub_dispatch(monkeypatch, *, result):
    """Neutralisér al DB + model-seam; model returnerer ``result``."""
    agent = {"agent_id": "a1", "role": "researcher", "provider": "p",
             "model": "m", "goal": "g", "system_prompt": "s"}
    monkeypatch.setattr(ars, "get_agent_registry_entry", lambda *a, **k: dict(agent))
    monkeypatch.setattr(ars, "list_agent_messages", lambda *a, **k: [])
    monkeypatch.setattr(ars, "create_agent_run", lambda *a, **k: None)
    monkeypatch.setattr(ars, "update_agent_run", lambda *a, **k: None)
    monkeypatch.setattr(ars, "create_agent_message", lambda *a, **k: None)
    monkeypatch.setattr(ars, "update_agent_registry_entry", lambda *a, **k: None)
    monkeypatch.setattr(ars, "_check_budget_and_expire", lambda *a, **k: None)
    monkeypatch.setattr(ars, "build_agent_detail_surface", lambda *a, **k: {})
    monkeypatch.setattr(ars, "agent_tools_enabled", lambda: False)

    class _FakeFacade:
        def execute_with_role_or_fallback(self, **kwargs):
            return dict(result)

    monkeypatch.setattr(ars, "_facade", lambda: _FakeFacade())


def _capture(monkeypatch):
    calls = {"result": [], "blocked": []}
    import core.services.agents as agents
    monkeypatch.setattr(
        agents, "note_agent_result",
        lambda *a, **k: calls["result"].append((a, k)),
    )
    monkeypatch.setattr(
        agents, "note_agent_blocked",
        lambda *a, **k: calls["blocked"].append((a, k)),
    )
    return calls


def test_note_agent_result_fires_once_on_success(monkeypatch):
    calls = _capture(monkeypatch)
    _stub_dispatch(monkeypatch, result={
        "text": "done", "output_tokens": 50, "input_tokens": 100,
        "cost_usd": 0.0, "status": "completed",
    })

    ars.execute_agent_task(agent_id="a1")

    assert len(calls["result"]) == 1, "note_agent_result skal fyre præcis én gang"
    assert len(calls["blocked"]) == 0
    _args, kw = calls["result"][0]
    # status kommer med som positionelt eller keyword
    passed = kw.get("status") or (_args[1] if len(_args) > 1 else None)
    assert passed == "completed"


def test_note_agent_blocked_fires_when_status_blocked(monkeypatch):
    calls = _capture(monkeypatch)
    _stub_dispatch(monkeypatch, result={
        "text": "mangler container-adgang", "output_tokens": 0,
        "input_tokens": 30, "cost_usd": 0.0, "status": "blocked",
    })

    ars.execute_agent_task(agent_id="a1")

    assert len(calls["result"]) == 1, "result-nerven fyrer også ved blocked"
    assert len(calls["blocked"]) == 1, "blocked-nerven skal fyre ved status=blocked"


def test_note_agent_result_fires_once_on_failure(monkeypatch):
    calls = _capture(monkeypatch)
    _stub_dispatch(monkeypatch, result={})

    # Tving fejl-stien: model-kaldet kaster.
    class _Boom:
        def execute_with_role_or_fallback(self, **kwargs):
            raise RuntimeError("model nede")

    monkeypatch.setattr(ars, "_facade", lambda: _Boom())

    ars.execute_agent_task(agent_id="a1")

    assert len(calls["result"]) == 1, "note_agent_result skal fyre én gang på fejl-stien"
    assert len(calls["blocked"]) == 0
