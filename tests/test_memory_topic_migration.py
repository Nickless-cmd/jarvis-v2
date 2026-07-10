from __future__ import annotations
from pathlib import Path
from core.identity.workspace_bootstrap import workspace_memory_paths
from core.memory.memory_topic_migration import migrate_workspace_memory

def _seed_monolith(name="default"):
    ws = Path(workspace_memory_paths(name=name)["workspace_dir"])
    mono = ws / "MEMORY.da.md"
    mono.write_text("## Alpha topic\n\nbody a\n\n## Beta topic\n\nbody b\n", encoding="utf-8")
    return mono

def test_migration_splits_and_backs_up(isolated_runtime):
    mono = _seed_monolith()
    res = migrate_workspace_memory(name="default")
    assert res["migrated"] is True
    assert res["topics"] >= 2
    assert mono.with_suffix(".md.bak").exists()          # original bevaret
    curated = Path(workspace_memory_paths(name="default")["curated_dir"])
    files = {p.name for p in curated.glob("*.md")}
    assert any("alpha" in f for f in files)
    idx = Path(workspace_memory_paths(name="default")["curated_memory"]).read_text("utf-8")
    assert "curated/" in idx

def test_migration_idempotent(isolated_runtime):
    _seed_monolith()
    migrate_workspace_memory(name="default")
    res2 = migrate_workspace_memory(name="default")     # anden kørsel = no-op
    assert res2["migrated"] is False
    assert res2["reason"] == "already-migrated"
