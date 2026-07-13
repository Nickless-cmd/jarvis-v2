"""A4: agent dispatch must write a ``costs`` ledger row via
``core.costing.ledger.record_cost`` with ``lane="agent"`` so agent spend is
visible to ``jc cost``.

Both the completion/success seam and the failure seam in
``execute_agent_task`` must fire ``record_cost`` exactly once with whatever
usage is available (the dispatch contract requires no dispatch without
usage + time). ``record_cost`` is patched at its definition module because the
implementation imports it lazily inside the function body.
"""

import core.costing.ledger as ledger
import core.services.agent_runtime_spawn as spawn


def _stub_db(monkeypatch):
    """Neutralise all DB/registry side effects so only record_cost matters."""
    monkeypatch.setattr(spawn, "update_agent_registry_entry", lambda *a, **k: None)
    monkeypatch.setattr(spawn, "create_agent_run", lambda *a, **k: None)
    monkeypatch.setattr(spawn, "update_agent_run", lambda *a, **k: None)
    monkeypatch.setattr(spawn, "create_agent_message", lambda *a, **k: None)
    monkeypatch.setattr(spawn, "list_agent_messages", lambda *a, **k: [])
    monkeypatch.setattr(spawn, "build_agent_detail_surface", lambda *a, **k: {})
    monkeypatch.setattr(spawn, "_check_budget_and_expire", lambda *a, **k: False)
    monkeypatch.setattr(spawn, "agent_tools_enabled", lambda: False)


def _agent():
    return {
        "agent_id": "a1", "name": "a1", "provider": "deepseek",
        "model": "deepseek-chat", "role": "researcher", "goal": "g",
        "persistent": False, "tool_policy": "", "next_wake_at": "",
    }


def _capture_record_cost(monkeypatch):
    calls = []
    monkeypatch.setattr(ledger, "record_cost", lambda **kw: calls.append(kw))
    return calls


def test_success_dispatch_logs_agent_lane_cost(monkeypatch):
    _stub_db(monkeypatch)
    monkeypatch.setattr(spawn, "get_agent_registry_entry", lambda *a, **k: _agent())
    calls = _capture_record_cost(monkeypatch)

    class _Facade:
        def execute_with_role_or_fallback(self, **kw):
            return {
                "text": "done", "provider": "deepseek", "model": "deepseek-chat",
                "input_tokens": 100, "output_tokens": 50, "cost_usd": 0.0,
                "status": "completed",
            }

    monkeypatch.setattr(spawn, "_facade", lambda: _Facade())

    spawn.execute_agent_task(agent_id="a1")

    assert len(calls) == 1, f"expected exactly one record_cost, got {len(calls)}"
    kw = calls[0]
    assert kw["lane"] == "agent"
    assert kw["provider"] == "deepseek"
    assert kw["model"] == "deepseek-chat"
    assert kw["input_tokens"] == 100
    assert kw["output_tokens"] == 50


def test_failure_dispatch_still_logs_agent_lane_cost(monkeypatch):
    _stub_db(monkeypatch)
    monkeypatch.setattr(spawn, "get_agent_registry_entry", lambda *a, **k: _agent())
    calls = _capture_record_cost(monkeypatch)

    class _Facade:
        def execute_with_role_or_fallback(self, **kw):
            raise RuntimeError("provider exploded")

    monkeypatch.setattr(spawn, "_facade", lambda: _Facade())

    spawn.execute_agent_task(agent_id="a1")

    assert len(calls) == 1, f"expected exactly one record_cost on failure, got {len(calls)}"
    kw = calls[0]
    assert kw["lane"] == "agent"
    assert kw["provider"] == "deepseek"
    assert kw["model"] == "deepseek-chat"
    # usage may be 0 on the failure path, but the keys must be present
    assert "input_tokens" in kw and "output_tokens" in kw
