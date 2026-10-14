from __future__ import annotations

from types import SimpleNamespace


def test_legacy_multi_signal_wrapper_delegates_to_authoritative_recall(monkeypatch):
    from core.services import memory_recall_engine as engine
    from core.services import scoped_recall_policy

    seen: dict[str, object] = {}
    monkeypatch.setattr(scoped_recall_policy, "recall_enabled", lambda: True)

    def authoritative(query, **kwargs):
        seen["query"] = query
        return {"status": "ok", "results": [], "count": 0}

    monkeypatch.setattr("core.services.recall.recall", authoritative)
    engine.multi_signal_recall(query="current query")

    assert seen["query"] == "current query"


def test_master_killswitch_blocks_tool_prompt_and_specialized_recall(monkeypatch):
    from core.services import memory_recall_engine as engine
    from core.services import scoped_recall_policy
    from core.services.prompt_sections.memory_recall import _visible_memory_recall_bundle_section
    from core.tools.recall_tool import _exec_recall

    monkeypatch.setattr(scoped_recall_policy, "recall_enabled", lambda: False)
    monkeypatch.setattr(
        "core.services.recall.recall",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("recall must not run")),
    )

    assert _exec_recall({"query": "private"})["status"] == "disabled"
    assert engine.multi_signal_recall(query="private")["status"] == "disabled"
    assert _visible_memory_recall_bundle_section(
        session_id="s1", user_message="private", compact=False,
    ) is None


def test_member_cannot_read_personal_brain_entry_by_known_id(monkeypatch):
    from core.services import scoped_recall_policy
    from core.tools import jarvis_brain_tools as tools

    entry = SimpleNamespace(
        id="known", kind="insight", title="private", content="secret",
        visibility="personal", domain="self", created_at=SimpleNamespace(isoformat=lambda: "now"),
        salience_bumps=0, related=[], status="active", superseded_by=None,
    )
    monkeypatch.setattr(scoped_recall_policy, "recall_enabled", lambda: True)
    monkeypatch.setattr("core.services.jarvis_brain.read_entry", lambda entry_id: entry)
    monkeypatch.setattr("core.identity.workspace_context.current_role", lambda: "member")
    monkeypatch.setattr("core.identity.workspace_context.current_user_id", lambda: "member-1")
    monkeypatch.setattr("core.identity.owner_resolver.owner_user_id", lambda: "owner-1")

    assert tools.read_brain_entry("known") == {"status": "error", "error": "not_found"}
