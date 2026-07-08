"""Generate docs/reference/API_REFERENCE.md from the FastAPI app (ground truth).
Primary: import the app and read app.routes. Fallback: AST-walk routes/*.py decorators.
Regenerable — can't re-stale. Stdlib + FastAPI."""
from __future__ import annotations

import ast
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:  # allow `python scripts/api_reference_gen.py` standalone
    sys.path.insert(0, str(REPO))
ROUTES_DIR = REPO / "apps" / "api" / "jarvis_api" / "routes"
OUT = REPO / "docs" / "reference" / "API_REFERENCE.md"


def routes_from_app(app) -> list[dict]:
    """Read real mounted routes from a FastAPI app. Pure over the app object."""
    from fastapi.routing import APIRoute
    rows = []
    for r in getattr(app, "routes", []):
        if not isinstance(r, APIRoute):
            continue
        methods = sorted(m for m in (r.methods or set()) if m not in ("HEAD", "OPTIONS"))
        model = getattr(getattr(r, "response_model", None), "__name__", "") or ""
        mod = getattr(getattr(r, "endpoint", None), "__module__", "") or ""
        for m in methods:
            rows.append({"method": m, "path": r.path, "name": r.name or "",
                         "model": model, "module": mod.split(".")[-1]})
    return rows


_DEC_RE = re.compile(r'@(?:router|app)\.(get|post|put|patch|delete)\(\s*["\']([^"\']+)["\']')


def routes_from_ast(routes_dir: Path = ROUTES_DIR) -> list[dict]:
    """Fallback: scan route files for @router.<method>("path") decorators (no import)."""
    rows = []
    for p in sorted(Path(routes_dir).rglob("*.py")):
        try:
            for m, path in _DEC_RE.findall(p.read_text(errors="ignore")):
                rows.append({"method": m.upper(), "path": path, "name": "",
                             "model": "", "module": p.stem})
        except Exception:
            pass
    return rows


def collect_routes() -> tuple[list[dict], str]:
    """Try the live app first; fall back to AST. Returns (rows, source)."""
    try:
        from apps.api.jarvis_api.app import app  # type: ignore
        rows = routes_from_app(app)
        if rows:
            return rows, "app.routes (live)"
    except Exception:
        pass
    return routes_from_ast(), "AST fallback"


def render_md(rows: list[dict], source: str = "") -> str:
    rows = sorted(rows, key=lambda r: (r["path"], r["method"]))
    lines = ["# API_REFERENCE", "",
             f"> Generated {datetime.now(UTC).date().isoformat()} from {source or 'code'} — "
             f"{len(rows)} routes. Regenerate: `python scripts/api_reference_gen.py`. DO NOT hand-edit.",
             "", "| Method | Path | Response model | Source |", "|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['method']} | `{r['path']}` | {r.get('model','')} | {r.get('module','')} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    rows, source = collect_routes()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render_md(rows, source))
    print(f"api_reference_gen: {len(rows)} routes from {source} → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
