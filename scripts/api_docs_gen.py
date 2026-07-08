# scripts/api_docs_gen.py
"""Generate per-package codebase reference under docs/reference/api/ from AST (static, stdlib only).
Each page lists a package's modules with class/function signatures, docstring summaries, and source
links (file#Lline). Flat mega-directories (e.g. core/services) are paginated alphabetically so no
page is unusable. Also emits a docstring-coverage report. Regenerable — cannot drift."""
from __future__ import annotations

import ast
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCAN_DIRS = ["core", "apps", "scripts"]
API_DIR = REPO / "docs" / "reference" / "api"
COV_OUT = REPO / "docs" / "reference" / "DOCSTRING_COVERAGE.md"
CHUNK = 40
_SKIP = {"__pycache__", "tests", "node_modules"}


def iter_py(root: Path = REPO):
    for d in SCAN_DIRS:
        for p in sorted((root / d).rglob("*.py")):
            if any(part in _SKIP or (part.startswith(".") and part not in (".",)) for part in p.parts):
                continue
            yield p


def _sig(node) -> str:
    a = node.args
    args = list(getattr(a, "posonlyargs", [])) + list(a.args)
    ndef, n = len(a.defaults), len(args)
    parts = []
    for i, arg in enumerate(args):
        parts.append(arg.arg + ("=…" if i - (n - ndef) >= 0 else ""))
    if a.vararg:
        parts.append("*" + a.vararg.arg)
    elif a.kwonlyargs:
        parts.append("*")
    for i, arg in enumerate(a.kwonlyargs):
        parts.append(arg.arg + ("=…" if a.kw_defaults[i] is not None else ""))
    if a.kwarg:
        parts.append("**" + a.kwarg.arg)
    return "(" + ", ".join(parts) + ")"


def _summary(node) -> str:
    d = ast.get_docstring(node)
    return d.strip().splitlines()[0].strip() if d else ""


def module_entry(text: str, relpath: str) -> dict:
    try:
        tree = ast.parse(text)
    except Exception:
        return {"module": relpath, "docstring_summary": "", "members": [], "error": True}
    members = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            members.append({"kind": "function", "name": node.name, "signature": _sig(node),
                            "doc_summary": _summary(node), "lineno": node.lineno})
        elif isinstance(node, ast.ClassDef):
            members.append({"kind": "class", "name": node.name, "signature": "",
                            "doc_summary": _summary(node), "lineno": node.lineno})
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    members.append({"kind": "method", "name": f"{node.name}.{sub.name}",
                                    "signature": _sig(sub), "doc_summary": _summary(sub),
                                    "lineno": sub.lineno})
    return {"module": relpath, "docstring_summary": _summary(tree), "members": members}


def package_of(relpath: str) -> str:
    parts = relpath.split("/")
    return ".".join(parts[:-1]) if len(parts) > 1 else parts[0][:-3] if parts[0].endswith(".py") else parts[0]


def page_id(pkg: str, module_name: str, sorted_names: list, chunk: int = CHUNK) -> str:
    if len(sorted_names) <= chunk:
        return pkg
    for i in range(0, len(sorted_names), chunk):
        grp = sorted_names[i:i + chunk]
        if module_name in grp:
            # numeric ordinal — collision-free (letter ranges collapse when one
            # letter dominates a flat dir, e.g. core/services' 100+ central_* modules)
            return f"{pkg}.{i // chunk + 1:02d}"
    return pkg


def _is_public(name: str) -> bool:
    return not any(part.startswith("_") for part in name.split("."))


def coverage(entries: list) -> dict:
    packages: dict = {}
    undoc: list = []
    for e in entries:
        pkg = package_of(e["module"])
        pc = packages.setdefault(pkg, {"functions": 0, "documented": 0})
        for m in e["members"]:
            if m["kind"] == "class":
                continue
            pc["functions"] += 1
            if m["doc_summary"]:
                pc["documented"] += 1
            elif _is_public(m["name"]):
                undoc.append({"module": e["module"], "name": m["name"], "lineno": m["lineno"]})
    return {"packages": packages, "undocumented_public": undoc,
            "total_functions": sum(p["functions"] for p in packages.values()),
            "total_documented": sum(p["documented"] for p in packages.values())}


def render_package_md(page: str, entries: list) -> str:
    lines = [f"# `{page}` — reference", "",
             f"> Generated {datetime.now(UTC).date().isoformat()} from source (AST). "
             f"Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.", ""]
    for e in sorted(entries, key=lambda x: x["module"]):
        rel = "../../../" + e["module"]
        lines.append(f"## `{e['module']}`")
        if e.get("docstring_summary"):
            lines.append(f"_{e['docstring_summary']}_")
        lines.append("")
        if not e["members"]:
            lines.append("_(no top-level classes or functions)_\n")
            continue
        lines.append("| Kind | Name | Signature | Summary | Source |")
        lines.append("|---|---|---|---|---|")
        for m in e["members"]:
            lines.append(f"| {m['kind']} | `{m['name']}` | `{m['signature']}` | "
                         f"{m['doc_summary'] or '—'} | [src]({rel}#L{m['lineno']}) |")
        lines.append("")
    return "\n".join(lines) + "\n"


def render_index_md(pages, cov: dict) -> str:
    # pages: dict page_id -> entries (preferred, lets us show the module range for
    # numeric-chunked pages); a bare list of ids is still accepted.
    as_dict = pages if isinstance(pages, dict) else {p: [] for p in pages}
    pct = 100 * cov["total_documented"] // max(1, cov["total_functions"])
    lines = ["# Codebase API reference", "",
             f"Generated per-package reference for `core/`+`apps/`+`scripts/`. "
             f"{cov['total_functions']} functions/methods, {pct}% with docstrings. "
             f"Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).", "",
             "**Convention (code ↔ doc):** a module `<pkg>/<mod>.py` is documented on the page for its "
             "package (`docs/reference/api/<dotted pkg>[.chunk].md`), section `## \\`<pkg>/<mod>.py\\``. "
             "Each entry links back to the source at `file#Lline`.", "", "## Pages", ""]
    for p in sorted(as_dict):
        es = as_dict[p]
        rng = ""
        if es and p != package_of(es[0]["module"]):
            mods = sorted(Path(e["module"]).stem for e in es)
            rng = f" — `{mods[0]}` … `{mods[-1]}`"
        lines.append(f"- [`{p}`]({p}.md){rng}")
    return "\n".join(lines) + "\n"


def render_coverage_md(cov: dict) -> str:
    pct = 100 * cov["total_documented"] // max(1, cov["total_functions"])
    lines = ["# Docstring coverage", "",
             f"Generated {datetime.now(UTC).date().isoformat()}. "
             f"{cov['total_documented']}/{cov['total_functions']} functions/methods documented ({pct}%). "
             f"The list below is the **mangler** for functions — public (non-`_`) undocumented functions, "
             f"the target of a future docstring gap-fill.", "",
             "## Coverage by package", "", "| Package | Documented | Functions | % |", "|---|---|---|---|"]
    for pkg in sorted(cov["packages"]):
        p = cov["packages"][pkg]
        ppct = 100 * p["documented"] // max(1, p["functions"])
        lines.append(f"| `{pkg}` | {p['documented']} | {p['functions']} | {ppct}% |")
    lines += ["", f"## Undocumented public functions ({len(cov['undocumented_public'])})", ""]
    for u in sorted(cov["undocumented_public"], key=lambda x: (x["module"], x["name"]))[:5000]:
        lines.append(f"- `{u['module']}` :: `{u['name']}` (L{u['lineno']})")
    return "\n".join(lines) + "\n"


def build() -> tuple:
    entries = [module_entry(p.read_text(errors="ignore"), str(p.relative_to(REPO))) for p in iter_py()]
    from collections import defaultdict
    by_pkg = defaultdict(list)
    for e in entries:
        by_pkg[package_of(e["module"])].append(e)
    pages = defaultdict(list)
    for pkg, es in by_pkg.items():
        names = sorted(Path(e["module"]).stem for e in es)
        for e in es:
            pid = page_id(pkg, Path(e["module"]).stem, names)
            pages[pid].append(e)
    return pages, coverage(entries)


def main() -> int:
    pages, cov = build()
    API_DIR.mkdir(parents=True, exist_ok=True)
    for pid, es in pages.items():
        (API_DIR / f"{pid}.md").write_text(render_package_md(pid, es))
    (API_DIR / "README.md").write_text(render_index_md(pages, cov))
    COV_OUT.write_text(render_coverage_md(cov))
    pct = 100 * cov["total_documented"] // max(1, cov["total_functions"])
    print(f"api_docs_gen: {len(pages)} pages, {cov['total_functions']} functions ({pct}% documented), "
          f"{len(cov['undocumented_public'])} undocumented public → {API_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
