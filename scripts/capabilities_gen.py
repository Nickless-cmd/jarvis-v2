"""Generate docs/reference/CAPABILITIES.md from the live tool registry. Regenerable.
Reuses permission_classifier._MUTATING_TOOLS for the mutating flag. Stdlib only."""
from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:  # allow `python scripts/capabilities_gen.py` standalone
    sys.path.insert(0, str(REPO))
OUT = REPO / "docs" / "reference" / "CAPABILITIES.md"


def tools_from_registry(handlers: dict, mutating: set) -> list[dict]:
    """Pure: map the name→handler registry to rows with kind + mutating flag."""
    rows = []
    for name in sorted(k for k in handlers if k):
        kind = "operator" if str(name).startswith("operator_") else "native"
        rows.append({"name": name, "kind": kind, "mutating": name in mutating})
    return rows


def render_md(rows: list[dict]) -> str:
    n_mut = sum(1 for r in rows if r["mutating"])
    lines = ["# CAPABILITIES", "",
             f"> Generated {datetime.now(UTC).date().isoformat()} — {len(rows)} tools "
             f"({n_mut} mutating). Regenerate: `python scripts/capabilities_gen.py`. DO NOT hand-edit.",
             "", "| Tool | Kind | Mutating |", "|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["kind"], r["name"])):
        lines.append(f"| `{r['name']}` | {r['kind']} | {'yes' if r['mutating'] else 'no'} |")
    return "\n".join(lines) + "\n"


def collect() -> list[dict]:
    from core.tools.simple_tools import _TOOL_HANDLERS
    try:
        from core.services.permission_classifier import _MUTATING_TOOLS as mut
    except Exception:
        mut = set()
    return tools_from_registry(dict(_TOOL_HANDLERS), set(mut))


def main() -> int:
    rows = collect()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render_md(rows))
    print(f"capabilities_gen: {len(rows)} tools → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
