"""Scan core/+apps/+scripts for THIRD-PARTY top-level imports (filter stdlib + first-party).
Emits a candidate module list to stdout — curated by hand into requirements.txt (import→PyPI
mapping happens in curation). Stdlib only. Static (AST), no imports of the scanned code."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCAN_DIRS = ["core", "apps", "scripts"]
FIRST_PARTY = {"core", "apps", "scripts"}


def top_level_imports(tree: ast.AST) -> set[str]:
    """Root module names of ABSOLUTE imports in one parsed file (relative imports ignored)."""
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name:
                    mods.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                mods.add(node.module.split(".")[0])
    return mods


def scan(repo: Path = REPO) -> set[str]:
    found: set[str] = set()
    for d in SCAN_DIRS:
        for p in (repo / d).rglob("*.py"):
            try:
                found |= top_level_imports(ast.parse(p.read_text(errors="ignore")))
            except Exception:
                pass
    return found


def third_party(mods: set[str]) -> list[str]:
    std = set(getattr(sys, "stdlib_module_names", set()))
    return sorted(m for m in mods
                  if m and m not in std and m not in FIRST_PARTY and not m.startswith("_"))


def main() -> int:
    cands = third_party(scan())
    for m in cands:
        print(m)
    print(f"# {len(cands)} third-party top-level modules", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
