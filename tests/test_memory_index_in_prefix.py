from __future__ import annotations
from pathlib import Path
from core.identity.workspace_bootstrap import workspace_memory_paths
from core.memory.memory_topic_store import topic_index_path_for


def test_index_appears_in_stable_prefix_after_migration(isolated_runtime):
    # Post-migration state: topic-index memory/INDEX.md + mindst én curated topic-fil.
    paths = workspace_memory_paths(name="default")
    idx = topic_index_path_for(name="default")
    idx.parent.mkdir(parents=True, exist_ok=True)
    idx.write_text("- [Alpha](curated/alpha.md) — om alpha\n", encoding="utf-8")
    curated = Path(paths["curated_dir"])
    curated.mkdir(parents=True, exist_ok=True)
    (curated / "alpha.md").write_text("# Alpha\n\nkrop", encoding="utf-8")

    from core.services.prompt_contract import build_visible_stable_prefix
    prefix = build_visible_stable_prefix(name="default")
    text = prefix if isinstance(prefix, str) else str(prefix)
    # Rendered compactly (audit #2, 2026-07-22): 'title · slug', no curated/*.md link.
    assert "- Alpha · alpha" in text           # compact index one-liner er med
    assert "curated/alpha.md" not in text      # verbose link-syntaks droppet


def test_index_is_noop_before_migration(isolated_runtime):
    # FØR migration: ingen topic-filer i curated/ → migration-guarden returnerer
    # no-op (index'et vises IKKE), så identitets-kernen (MEMORY.md) ikke røres.
    idx = topic_index_path_for(name="default")
    idx.parent.mkdir(parents=True, exist_ok=True)
    idx.write_text("- [Alpha](curated/alpha.md) — om alpha\n", encoding="utf-8")
    # curated_dir har INGEN topic-filer → guard = no-op.

    from core.services.prompt_contract import _curated_memory_index_section
    assert _curated_memory_index_section(name="default") == ""
