"""A4b: agent cost is logged at the execution chokepoint
(``execute_with_role_or_fallback`` / ``execute_cheap_lane_via_pool`` with
``lane="agent"`` threaded in), NOT at the ``execute_agent_task`` dispatch
seam. The prior A4 seam logs were removed because they double-counted every
dispatch that fell back to the cheap-lane pool (lane="agent" + lane="cheap"
for the same tokens).

These tests pin that removal: with the execution facade stubbed out (so the
real chokepoint never runs), ``execute_agent_task`` fires ``record_cost``
ZERO times — proving no seam log remains. Single-site coverage of the four
lanes lives in ``test_agent_cost_single_site.py``.
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


def test_success_dispatch_no_seam_cost_log(monkeypatch):
    """Facade stubbed (chokepoint bypassed) → the seam logs nothing."""
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

    assert calls == [], f"seam must not log cost anymore, got {len(calls)}"


def test_failure_dispatch_no_seam_cost_log(monkeypatch):
    """Failure before any model call → nothing to log, and no seam log."""
    _stub_db(monkeypatch)
    monkeypatch.setattr(spawn, "get_agent_registry_entry", lambda *a, **k: _agent())
    calls = _capture_record_cost(monkeypatch)

    class _Facade:
        def execute_with_role_or_fallback(self, **kw):
            raise RuntimeError("provider exploded")

    monkeypatch.setattr(spawn, "_facade", lambda: _Facade())

    spawn.execute_agent_task(agent_id="a1")

    assert calls == [], f"seam must not log cost on failure anymore, got {len(calls)}"
