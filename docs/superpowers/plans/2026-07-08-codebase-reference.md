# Docs SP4 — Codebase Reference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate per-package codebase reference pages (signatures + docstrings + source links) + a docstring-coverage audit, documenting every file/function feasibly.

**Architecture:** One static AST generator (`scripts/api_docs_gen.py`, stdlib only) writes dozens-to-~100 markdown pages under `docs/reference/api/` (flat mega-dirs paginated alphabetically), an index, and a coverage report listing the undocumented public functions. No source edits; code↔doc is bidirectional by convention.

**Tech Stack:** Python 3.11 stdlib (`ast`), pytest.

**Execution note:** Task 1 (generator + tests) → fresh **haiku** subagent. Tasks 2–3 (run it, wire README/CONTRIBUTING, commit) → **Claude inline**.

---

## Task 1: `scripts/api_docs_gen.py` + tests

**Files:**
- Create: `scripts/api_docs_gen.py`
- Test: `tests/test_api_docs_gen.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_api_docs_gen.py
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "api_docs_gen", Path(__file__).resolve().parents[1] / "scripts" / "api_docs_gen.py")
g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g)


def test_module_entry_function_signature_and_summary():
    src = 'def foo(a, b=1, *args, **kw):\n    """Does a thing.\n\n    More."""\n    pass\n'
    e = g.module_entry(src, "core/x.py")
    m = [x for x in e["members"] if x["name"] == "foo"][0]
    assert m["kind"] == "function"
    assert m["signature"] == "(a, b=…, *args, **kw)"
    assert m["doc_summary"] == "Does a thing."


def test_module_entry_no_docstring_empty_summary():
    e = g.module_entry("def bar():\n    return 1\n", "core/x.py")
    assert [x for x in e["members"] if x["name"] == "bar"][0]["doc_summary"] == ""


def test_module_entry_class_and_methods():
    src = 'class C:\n    """A class."""\n    def m(self, x):\n        """Method."""\n        pass\n'
    e = g.module_entry(src, "core/x.py")
    names = {x["name"]: x for x in e["members"]}
    assert names["C"]["kind"] == "class"
    assert "C.m" in names and names["C.m"]["kind"] == "method" and names["C.m"]["signature"] == "(self, x)"


def test_module_entry_bad_syntax_safe():
    e = g.module_entry("def (:\n", "core/x.py")
    assert e["members"] == [] and e.get("error")


def test_package_of():
    assert g.package_of("core/services/foo.py") == "core.services"
    assert g.package_of("scripts/jarvis.py") == "scripts"


def test_page_id_single_vs_chunked():
    small = ["a", "b", "c"]
    assert g.page_id("core.runtime", "b", small, chunk=40) == "core.runtime"
    big = [f"m{i:03d}" for i in range(90)]
    pid = g.page_id("core.services", "m000", big, chunk=40)
    assert pid.startswith("core.services.") and pid != "core.services"


def test_coverage_counts_and_public_undocumented():
    entries = [
        {"module": "core/x.py", "members": [
            {"kind": "function", "name": "pub", "doc_summary": "", "lineno": 1, "signature": "()"},
            {"kind": "function", "name": "_priv", "doc_summary": "", "lineno": 2, "signature": "()"},
            {"kind": "function", "name": "documented", "doc_summary": "Yep.", "lineno": 3, "signature": "()"},
        ]},
    ]
    cov = g.coverage(entries)
    pkg = cov["packages"]["core"]
    assert pkg["functions"] == 3 and pkg["documented"] == 1
    names = {u["name"] for u in cov["undocumented_public"]}
    assert "pub" in names and "_priv" not in names and "documented" not in names


def test_render_contains_names_and_srclink():
    entries = [{"module": "core/x.py", "docstring_summary": "Mod.", "members": [
        {"kind": "function", "name": "foo", "signature": "(a)", "doc_summary": "Hi.", "lineno": 7}]}]
    md = g.render_package_md("core", entries)
    assert "foo" in md and "(a)" in md and "#L7" in md and "core/x.py" in md
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_api_docs_gen.py -q`
Expected: FAIL — module not defined.

- [ ] **Step 3: Write the implementation**

```python
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
            return f"{pkg}.{grp[0][0].lower()}-{grp[-1][0].lower()}"
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


def render_index_md(pages: list, cov: dict) -> str:
    pct = 100 * cov["total_documented"] // max(1, cov["total_functions"])
    lines = ["# Codebase API reference", "",
             f"Generated per-package reference for `core/`+`apps/`+`scripts/`. "
             f"{cov['total_functions']} functions/methods, {pct}% with docstrings. "
             f"Undocumented public functions: see [`DOCSTRING_COVERAGE.md`](../DOCSTRING_COVERAGE.md).", "",
             "**Convention (code ↔ doc):** a module `<pkg>/<mod>.py` is documented on the page for its "
             "package (`docs/reference/api/<dotted pkg>[.chunk].md`), section `## \\`<pkg>/<mod>.py\\``. "
             "Each entry links back to the source at `file#Lline`.", "", "## Pages", ""]
    for p in sorted(pages):
        lines.append(f"- [`{p}`]({p}.md)")
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
    # group modules by package, assign each to a (possibly chunked) page
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
    (API_DIR / "README.md").write_text(render_index_md(list(pages), cov))
    COV_OUT.write_text(render_coverage_md(cov))
    pct = 100 * cov["total_documented"] // max(1, cov["total_functions"])
    print(f"api_docs_gen: {len(pages)} pages, {cov['total_functions']} functions ({pct}% documented), "
          f"{len(cov['undocumented_public'])} undocumented public → {API_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_api_docs_gen.py -q`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/api_docs_gen.py tests/test_api_docs_gen.py
git commit -m "feat(docs): SP4 codebase reference generator (AST → per-package pages + coverage)"
```

---

## Task 2 (Claude inline): run the generator + sanity-check

- [ ] **Step 1: Generate**

Run: `conda run -n ai python scripts/api_docs_gen.py`
Expected: prints page count (dozens-to-~100), function count (~15k), documented %, undocumented count; writes `docs/reference/api/*.md`, `docs/reference/api/README.md`, `docs/reference/DOCSTRING_COVERAGE.md`.

- [ ] **Step 2: Sanity-check**

- No single page is unusably large: `wc -l docs/reference/api/*.md | sort -rn | head` — the biggest should be a chunked `core.services.*` page, not one giant file.
- A couple source links resolve: pick an entry from a page, confirm the `../../../core/…#Lnn` path points at a real file and the line is plausibly that symbol.
- The index lists every generated page; the coverage report's total matches (~15,204 functions, ~42% documented).
- Fix the generator + re-run if a check fails (re-run Task 1 tests first).

- [ ] **Step 3: Commit the generated reference**

```bash
git add docs/reference/api/ docs/reference/DOCSTRING_COVERAGE.md
git commit -m "docs(docs): SP4 generated codebase reference + docstring coverage report"
```

---

## Task 3 (Claude inline): wire README + CONTRIBUTING + push

- [ ] **Step 1: Update `docs/README.md`** — under Reference, add: `reference/api/` (the per-package code reference) and `reference/DOCSTRING_COVERAGE.md` (documentation gaps). Keep the existing links.

- [ ] **Step 2: Update `docs/CONTRIBUTING.md`** — under "Regenerating derived docs", add `python scripts/api_docs_gen.py    # reference/api/ + DOCSTRING_COVERAGE.md`. Add a short "Code ↔ docs" note: a module `<pkg>/<mod>.py` is documented on `docs/reference/api/<dotted pkg>[.chunk].md` (section `## \`<pkg>/<mod>.py\``); the reference is generated — never hand-edit it, add/improve the **docstring in the source** and regenerate.

- [ ] **Step 3: Link-check the two updated docs** — every relative link in README + CONTRIBUTING resolves (extract `](...)`, resolve relative to the doc dir, assert exists).

- [ ] **Step 4: Generator tests + compile**

Run: `conda run -n ai python -m pytest tests/test_api_docs_gen.py -q && conda run -n ai python -m compileall scripts/api_docs_gen.py -q`
Expected: PASS.

- [ ] **Step 5: Commit + push**

```bash
git add docs/README.md docs/CONTRIBUTING.md
git commit -m "docs(docs): SP4 link api reference + coverage; document code↔doc convention"
git push
```
No container deploy (repo-docs + one tested `scripts/` generator). Full runtime suite not required (no runtime code); the generator test + link/anchor sanity is the gate.

- [ ] **Step 6: Report** the coverage numbers (pages, functions, % documented, undocumented count) to Bjørn, and note SP5 (drift-sikring) is the final sub-project — this generator + coverage report + the SP2/SP3 generators are its building blocks.

---

## Self-Review

**Spec coverage:** generator with `iter_py`/`module_entry`/`package_of`/`page_id` pagination/`coverage`/`render_*`/`main` (Task 1) ✓; per-package pages + index + coverage report output (Task 1 `main`, Task 2 run) ✓; pagination of flat mega-dirs (Task 1 `page_id` + `build`, tested) ✓; doc→code `file#Lline` links (`render_package_md`, tested) ✓; code→doc convention documented, no source edits (Task 3 README/CONTRIBUTING) ✓; coverage = documented vs undocumented + public-only mangler list (Task 1 `coverage`, tested) ✓; scope boundary (no docstring gap-fill) — inherent (SP4 only generates + audits) ✓.

**Placeholder scan:** none — generator is complete; Tasks 2–3 are concrete run/wire/verify steps.

**Type consistency:** `module_entry(text, relpath)→{module,docstring_summary,members[{kind,name,signature,doc_summary,lineno}]}`, `package_of(relpath)→str`, `page_id(pkg, name, sorted_names, chunk)→str`, `coverage(entries)→{packages,undocumented_public,total_*}`, `render_package_md(page, entries)`, `render_index_md(pages, cov)`, `render_coverage_md(cov)` — identical across the generator, `build`/`main`, and the tests. Member dict keys consistent throughout.
