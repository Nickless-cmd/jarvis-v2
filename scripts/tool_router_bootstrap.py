"""One-shot bootstrap: generate tool tags via cheap LLM and warm embedding cache.

Run before first deploy. Idempotent — safe to re-run after adding new tools.

Usage:
    conda activate ai
    python scripts/tool_router_bootstrap.py
    python scripts/tool_router_bootstrap.py --skip-tags
    python scripts/tool_router_bootstrap.py --skip-embed
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-tags", action="store_true")
    ap.add_argument("--skip-embed", action="store_true")
    args = ap.parse_args()

    if not args.skip_tags:
        from core.services.tool_tagger import bootstrap_tags
        print("Generating tool tags via cheap LLM...")
        try:
            tags = bootstrap_tags()
            print(f"  → {len(tags)} tools tagged")
        except Exception as exc:
            print(f"  → tagging failed: {exc}")
            print("  (continuing — tags are optional, embeddings handle most matching)")

    if not args.skip_embed:
        from core.services.tool_embeddings import warmup_all
        print("Warming embedding cache (this calls Ollama once per tool)...")
        n = warmup_all()
        print(f"  → {n} tools embedded")

    print("Bootstrap complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
