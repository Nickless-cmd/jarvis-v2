from core.tools.simple_tools import execute_tool


def test_load_more_tools_unknown_name_returns_error():
    out = execute_tool("load_more_tools", {"names": ["this_does_not_exist_definitely"]})
    assert out["status"] == "error"
    assert "not found" in str(out).lower()


def test_load_more_tools_known_name_returns_ok():
    out = execute_tool("load_more_tools", {"names": ["read_file"]})
    assert out["status"] == "ok"
    assert "read_file" in out.get("added", [])


def test_load_more_tools_query_returns_matches(monkeypatch):
    import core.services.tool_embeddings as te
    monkeypatch.setattr(te, "top_k_similar", lambda q, k=10: [("read_file", 0.9), ("grep", 0.85)])
    out = execute_tool("load_more_tools", {"query": "read a file please"})
    assert out["status"] == "ok"
    assert "read_file" in out.get("added", [])


def test_load_more_tools_empty_args_returns_ok_no_matches():
    out = execute_tool("load_more_tools", {})
    # Empty input is a valid degenerate case
    assert out["status"] == "ok"
    assert out.get("added") == []
