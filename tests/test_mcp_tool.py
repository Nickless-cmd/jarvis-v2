from core.tools import mcp_tool


def test_mcp_call_publicerer_app_paa_det_synlige_run(monkeypatch):
    from core.services import mcp_apps, mcp_manager

    monkeypatch.setattr(mcp_manager, "call_with_app", lambda server, tool, arguments: (
        {"content": [{"type": "text", "text": "ok"}]},
        {
            "result": {"structuredContent": {"x": 1}},
            "html": "<html>app</html>",
        },
    ))
    captured = {}
    monkeypatch.setattr(mcp_apps, "publish", lambda **kwargs: captured.update(kwargs))

    result = mcp_tool.exec_mcp({
        "action": "call",
        "server": "vejr",
        "tool": "forecast",
        "arguments": {"by": "Svendborg"},
        "_runtime_turn_id": "run-1",
        "_runtime_tool_use_id": "tool-1",
    })

    assert result["content"][0]["text"] == "ok"
    assert captured["run_id"] == "run-1"
    assert captured["tool_use_id"] == "tool-1"
    assert captured["arguments"] == {"by": "Svendborg"}


def test_mcp_app_publiceringsfejl_bevarer_toolresultatet(monkeypatch):
    from core.services import mcp_apps, mcp_manager

    monkeypatch.setattr(mcp_manager, "call_with_app", lambda server, tool, arguments: (
        {"content": [{"type": "text", "text": "stadig sandt"}]},
        {"result": {}, "html": "<html>app</html>"},
    ))
    monkeypatch.setattr(mcp_apps, "publish", lambda **kwargs: (_ for _ in ()).throw(
        RuntimeError("defekt resource")
    ))

    result = mcp_tool.exec_mcp({"action": "call", "server": "s", "tool": "t"})

    assert result["content"][0]["text"] == "stadig sandt"
    assert "defekt resource" in result["ui_warning"]
