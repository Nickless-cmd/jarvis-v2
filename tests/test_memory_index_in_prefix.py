from __future__ import annotations
from pathlib import Path
from core.identity.workspace_bootstrap import workspace_memory_paths

def test_index_appears_in_stable_prefix(isolated_runtime):
    # Seed an index line for the resolved user.
    idx = Path(workspace_memory_paths(name="default")["curated_memory"])
    idx.parent.mkdir(parents=True, exist_ok=True)
    idx.write_text("- [Alpha](curated/alpha.md) — om alpha\n", encoding="utf-8")

    from core.services.prompt_contract import build_visible_stable_prefix
    prefix = build_visible_stable_prefix(name="default")
    text = prefix if isinstance(prefix, str) else str(prefix)
    assert "curated/alpha.md" in text          # index one-liner er med
    assert "Alpha" in text
