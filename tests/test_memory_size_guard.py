from __future__ import annotations
from pathlib import Path
from core.identity.workspace_bootstrap import workspace_memory_paths
from core.memory import memory_size_guard as g
from core.memory.memory_topic_store import read_topic


def test_check_flags_oversized(isolated_runtime, monkeypatch):
    mem = Path(workspace_memory_paths(name="default")["curated_memory"])
    ws_name = mem.parent.name  # resolved workspace-navn (kan afvige fra "default")
    mem.parent.mkdir(parents=True, exist_ok=True)
    mem.write_text("x" * (26 * 1024), encoding="utf-8")
    over = g.check_memory_sizes()
    assert any(o["workspace"] == ws_name and o["bytes"] > g._CAP_BYTES for o in over)


def test_prune_moves_non_identity_section(isolated_runtime):
    mem = Path(workspace_memory_paths(name="default")["curated_memory"])
    mem.parent.mkdir(parents=True, exist_ok=True)
    mem.write_text("# Jarvis Memory\n\n## Who I Am\n\nkerne.\n\n## Old Episode\n\nnoget gammelt.\n", encoding="utf-8")
    r = g.prune_memory_section("default", "Old Episode")
    assert r["pruned"] is True
    # sektion væk fra MEMORY.md, identitet bevaret
    txt = mem.read_text(encoding="utf-8")
    assert "Old Episode" not in txt and "Who I Am" in txt
    # havnet i topic
    assert "noget gammelt" in (read_topic(r["slug"], name="default") or "")


def test_prune_refuses_identity_section(isolated_runtime):
    mem = Path(workspace_memory_paths(name="default")["curated_memory"])
    mem.parent.mkdir(parents=True, exist_ok=True)
    mem.write_text("# Jarvis Memory\n\n## Who I Am\n\nkerne.\n", encoding="utf-8")
    r = g.prune_memory_section("default", "Who I Am")
    assert r["pruned"] is False
    assert r["reason"] == "identity-section-protected"
    assert "Who I Am" in mem.read_text(encoding="utf-8")
