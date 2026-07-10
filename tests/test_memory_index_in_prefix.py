from __future__ import annotations
from pathlib import Path
from core.identity.workspace_bootstrap import workspace_memory_paths


def test_index_appears_in_stable_prefix_after_migration(isolated_runtime):
    # Post-migration state: index MEMORY.md + mindst én curated topic-fil.
    paths = workspace_memory_paths(name="default")
    idx = Path(paths["curated_memory"])
    idx.parent.mkdir(parents=True, exist_ok=True)
    idx.write_text("- [Alpha](curated/alpha.md) — om alpha\n", encoding="utf-8")
    # Migration-guard kræver at curated/ indeholder topic-filer.
    curated = Path(paths["curated_dir"])
    curated.mkdir(parents=True, exist_ok=True)
    (curated / "alpha.md").write_text("# Alpha\n\nkrop", encoding="utf-8")

    from core.services.prompt_contract import build_visible_stable_prefix
    prefix = build_visible_stable_prefix(name="default")
    text = prefix if isinstance(prefix, str) else str(prefix)
    assert "curated/alpha.md" in text          # index one-liner er med
    assert "Alpha" in text


def test_index_is_noop_before_migration(isolated_runtime):
    # FØR migration: MEMORY.md findes (monolit) men curated/ har ingen topic-filer
    # → migration-guarden skal returnere no-op (index'et vises IKKE), så deploy
    # ikke bloater/duplikerer prompten før owner kører migration.
    paths = workspace_memory_paths(name="default")
    idx = Path(paths["curated_memory"])
    idx.parent.mkdir(parents=True, exist_ok=True)
    idx.write_text("en hel monolit-tekstvæg her\n", encoding="utf-8")
    # curated_dir eksisterer (bootstrap) men er tom → ingen topic-filer.

    from core.services.prompt_contract import _curated_memory_index_section
    assert _curated_memory_index_section(name="default") == ""
