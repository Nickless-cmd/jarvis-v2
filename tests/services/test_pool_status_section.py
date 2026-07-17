"""Pool-status prompt-sektion: altid til stede, self-safe, nævner begge pools."""
from core.services.prompt_sections.pool_status_section import pool_status_line


def test_pool_status_mentions_both_pools_and_distinction():
    s = pool_status_line()
    assert "Agent pool" in s
    assert "Cheap lane" in s
    # the crucial distinction Jarvis kept missing:
    assert "BETALTE" in s or "betalt" in s  # agent pool has paid
    assert "GRATIS-only" in s               # cheap lane does not


def test_pool_status_self_safe_never_raises(monkeypatch):
    # even if every data source explodes, it returns a string with '?'
    import core.services.agent_pool_router as apr
    monkeypatch.setattr(apr, "route_agent_task", lambda **k: (_ for _ in ()).throw(RuntimeError("boom")))
    s = pool_status_line()
    assert "Agent pool" in s and "Cheap lane" in s
