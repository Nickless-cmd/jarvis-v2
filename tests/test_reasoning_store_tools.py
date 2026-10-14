from __future__ import annotations


def test_reasoning_tool_preserves_standard_disabled_shape(monkeypatch) -> None:
    from core.tools import reasoning_store_tools as tools

    disabled = {"status": "disabled", "path": "reasoning_recall", "results": [], "count": 0}
    monkeypatch.setattr(tools, "recall_reasoning", lambda **kwargs: disabled)
    assert tools._exec_recall_reasoning({"query": "x"}) == disabled
