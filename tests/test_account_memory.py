import asyncio

import apps.api.jarvis_api.routes.account as acc
from apps.api.jarvis_api.routes.account import build_memory_overview


def test_build_memory_overview(tmp_path):
    (tmp_path / "MEMORY.md").write_text("- husk mælk")
    (tmp_path / "USER.md").write_text("Bjørn, ejer")
    ov = build_memory_overview(
        "u1",
        ws_dir=lambda uid: tmp_path,
        read_text=lambda p: p.read_text() if p.exists() else None,
        recent_sensory=lambda: [{"id": "s1", "content": "lyd"}],
        brain_count=lambda: 3,
    )
    assert "husk mælk" in ov["memory_md"]
    assert "Bjørn" in ov["user_md"]
    assert ov["recent_sensory"][0]["content"] == "lyd"
    assert ov["brain_count"] == 3


def test_build_memory_overview_missing_files(tmp_path):
    ov = build_memory_overview(
        "u1",
        ws_dir=lambda uid: tmp_path,
        read_text=lambda p: None,
        recent_sensory=lambda: [],
        brain_count=lambda: 0,
    )
    assert ov["memory_md"] == ""
    assert ov["user_md"] == ""


def test_memory_search_route_scopes_to_user(monkeypatch):
    captured = {}
    import core.runtime.db_sensory as ds
    monkeypatch.setattr(ds, "search_sensory_memories",
                        lambda *, query, limit=20: captured.update(q=query) or [{"id": "s1", "content": query}])
    res = asyncio.run(acc.account_memory_search(q="regn"))
    assert res["results"][0]["content"] == "regn"
    assert captured["q"] == "regn"
