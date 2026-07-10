from __future__ import annotations
from pathlib import Path
from core.identity.workspace_bootstrap import workspace_memory_paths
from core.memory.memory_topic_migration import migrate_workspace_memory
from core.memory.memory_topic_store import topic_index_path_for, read_topic


def _seed_memory(name="default"):
    # MEMORY.md med både KEEP (identitet) og MOVE (episodisk) + duplikat-titel.
    ws = Path(workspace_memory_paths(name=name)["curated_memory"])  # <user>/MEMORY.md
    ws.parent.mkdir(parents=True, exist_ok=True)
    ws.write_text(
        "# Jarvis Memory\n\n"
        "## Who I Am\n\nJeg er Jarvis.\n\n"
        "## Hardware\n\nRTX-kort.\n\n"
        "## Dream carry-over — 2026-07-08\n\nen drøm.\n\n"
        "## Decisions\n\nbeslutning A.\n\n"
        "## Decisions\n\nbeslutning B (duplikat).\n\n"
        "## Platform-analyse\n\nnoget episodisk.\n\n"
        "## Platform-analyse\n\nendnu en (duplikat → -2).\n",
        encoding="utf-8",
    )
    return ws


def test_selective_split_keeps_identity_moves_episodic(isolated_runtime):
    mem = _seed_memory()
    res = migrate_workspace_memory(name="default")
    assert res["migrated"] is True
    assert res["kept"] >= 3          # Who I Am + Hardware + Decisions×2 (dup begge keep)
    assert res["moved"] >= 2         # Dream carry-over + Platform-analyse×2
    assert mem.with_suffix(".md.bak").exists()   # original bevaret

    # KEEP-sektioner bliver i MEMORY.md; MOVE-sektioner er VÆK derfra.
    new_mem = mem.read_text(encoding="utf-8")
    assert "Who I Am" in new_mem and "Hardware" in new_mem
    assert "Dream carry-over" not in new_mem
    assert "Platform-analyse" not in new_mem

    # MOVE-sektioner er i curated/ + topic-index.
    idx = topic_index_path_for(name="default").read_text(encoding="utf-8")
    assert "curated/" in idx and "Dream carry-over" in idx
    assert read_topic("dream-carry-over-2026-07-08", name="default") is not None


def test_duplicate_move_titles_get_unique_slugs_no_loss(isolated_runtime):
    _seed_memory()
    migrate_workspace_memory(name="default")
    # Begge Platform-analyse-sektioner bevaret under unikke slugs.
    a = read_topic("platform-analyse", name="default")
    b = read_topic("platform-analyse-2", name="default")
    assert a is not None and b is not None
    assert "noget episodisk" in a
    assert "endnu en" in b


def test_migration_idempotent(isolated_runtime):
    _seed_memory()
    migrate_workspace_memory(name="default")
    res2 = migrate_workspace_memory(name="default")     # anden kørsel = no-op
    assert res2["migrated"] is False
    assert res2["reason"] == "already-migrated"
