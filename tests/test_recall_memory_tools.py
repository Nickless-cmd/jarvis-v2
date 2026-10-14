from __future__ import annotations


def test_semantic_recall_tool_stops_before_search_when_disabled(monkeypatch) -> None:
    from core.tools import recall_memory_tools as tools

    monkeypatch.setattr(tools, "recall_enabled", lambda: False)
    monkeypatch.setattr(
        tools.semantic_memory, "search",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("search must not run")),
    )
    assert tools._exec_recall_memories({"query": "private"})["status"] == "disabled"
