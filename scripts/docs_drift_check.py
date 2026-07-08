# scripts/docs_drift_check.py
"""SP5 docs-drift checker — catch when docs/ diverges from git+runtime truth.

Hybrid: HARD checks gate a commit (broken markdown links; generated docs not regenerated
after their source changed); SOFT checks are advisory (bare code-path mentions that don't
resolve; requirements imports missing from requirements.txt). Stdlib only, self-safe per
family. `--check` = gate (hard families; staleness scoped to staged files) → exit 1 on hard
drift; default = full report → docs/drift_report.json."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"
REPORT_OUT = DOCS / "drift_report.json"

_PATH_RE = re.compile(r"(?:core|apps|scripts)/[\w./-]+\.(?:py|ts|tsx|md|json)")
_MDLINK_RE = re.compile(r"\]\(([^)]+)\)")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
# Historical-record trees (docs/README freshness policy): "not current truth" — their
# docs cite aspirational/example paths by design, so they are excluded from drift checking.
_SKIP_DOC_PARTS = {"_archive", "superpowers", "design-history"}


def find_docs(root: Path = DOCS) -> list[Path]:
    return sorted(p for p in root.rglob("*.md") if not (_SKIP_DOC_PARTS & set(p.parts)))


def _norm(text: str) -> str:
    """Neutralize volatile 'Generated <date>' stamps so regeneration diffs are content-only."""
    return _DATE_RE.sub("DATE", text)


# ---- HARD: broken markdown links ----
def broken_links(docs_root: Path = DOCS) -> list[dict]:
    out: list[dict] = []
    for doc in find_docs(docs_root):
        text = doc.read_text(errors="ignore")
        rel_doc = str(doc.relative_to(docs_root.parent)) if docs_root.parent in doc.parents else doc.name
        for href in _MDLINK_RE.findall(text):
            href = href.split("#")[0].strip()
            if not href or href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = (doc.parent / href)
            if not target.exists():
                out.append({"doc": rel_doc, "kind": "link", "target": href})
    return out


# ---- HARD: stale generated docs (in-memory regenerate + compare) ----
def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _expected_api_docs() -> dict[str, str]:
    g = _load_script("api_docs_gen")
    pages, cov = g.build()
    out = {str((g.API_DIR / f"{pid}.md").relative_to(REPO)): g.render_package_md(pid, es)
           for pid, es in pages.items()}
    out[str((g.API_DIR / "README.md").relative_to(REPO))] = g.render_index_md(pages, cov)
    out[str(g.COV_OUT.relative_to(REPO))] = g.render_coverage_md(cov)
    return out


def _expected_api_reference() -> dict[str, str]:
    g = _load_script("api_reference_gen")
    rows, source = g.collect_routes()
    return {str(g.OUT.relative_to(REPO)): g.render_md(rows, source)}


def _expected_capabilities() -> dict[str, str]:
    g = _load_script("capabilities_gen")
    rows = g.collect()
    return {str(g.OUT.relative_to(REPO)): g.render_md(rows)}


_GENERATORS = [
    {"name": "api_docs_gen", "source_dirs": ["core", "apps", "scripts"], "expected": _expected_api_docs},
    {"name": "api_reference_gen", "source_dirs": ["apps/api"], "expected": _expected_api_reference},
    {"name": "capabilities_gen", "source_dirs": ["core/tools", "core/services"], "expected": _expected_capabilities},
]


def _staged_under(source_dirs: list[str], staged: list[str]) -> bool:
    return any(sp == sd or sp.startswith(sd + "/") for sd in source_dirs for sp in staged)


def stale_generated(only_dirs: list[str] | None = None, repo: Path = REPO) -> list[dict]:
    out: list[dict] = []
    for gen in _GENERATORS:
        if only_dirs is not None and not _staged_under(gen["source_dirs"], only_dirs):
            continue
        try:
            expected = gen["expected"]()
        except Exception as exc:  # a broken checker must not wedge the repo → soft
            out.append({"generator": gen["name"], "kind": "checker_error", "error": str(exc)[:200]})
            continue
        for relpath, content in expected.items():
            f = repo / relpath
            actual = f.read_text(errors="ignore") if f.exists() else ""
            if _norm(actual) != _norm(content):
                out.append({"generator": gen["name"], "kind": "stale", "path": relpath})
    return out


# ---- SOFT: bare code-path mentions in prose that don't resolve ----
def prose_drift(docs_root: Path = DOCS, repo: Path = REPO) -> list[dict]:
    out: list[dict] = []
    skip = repo / "docs" / "reference" / "api"
    for doc in find_docs(docs_root):
        if skip in doc.parents:
            continue
        text = doc.read_text(errors="ignore")
        rel_doc = str(doc.relative_to(repo))
        for m in sorted(set(_PATH_RE.findall(text))):
            if not (repo / m).exists():
                out.append({"doc": rel_doc, "kind": "prose_path", "target": m})
    return out


# ---- SOFT: requirements drift ----
def requirements_drift(repo: Path = REPO) -> list[dict]:
    try:
        g = _load_script("requirements_gen")
        third = set(g.third_party(g.scan(repo)))
    except Exception as exc:
        return [{"kind": "checker_error", "checker": "requirements", "error": str(exc)[:200]}]
    req = repo / "requirements.txt"
    have: set[str] = set()
    if req.exists():
        for line in req.read_text(errors="ignore").splitlines():
            line = line.split("#")[0].strip()
            if line and not line.startswith("-"):
                have.add(re.split(r"[<>=~!\[ ]", line)[0].strip().lower())
    return [{"kind": "requirement_missing", "module": m}
            for m in sorted(third) if m.lower() not in have]


# ---- assembly ----
def staged_paths(repo: Path = REPO) -> list[str]:
    try:
        r = subprocess.run(["git", "-C", str(repo), "diff", "--cached", "--name-only"],
                           capture_output=True, text=True, timeout=15)
        return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
    except Exception:
        return []


def hard_drift(staged: list[str] | None = None, repo: Path = REPO) -> list[dict]:
    gen = stale_generated(only_dirs=staged, repo=repo)
    return broken_links() + [x for x in gen if x.get("kind") == "stale"]


def run_check(repo: Path = REPO, staged: list[str] | None = None) -> dict:
    links = broken_links()
    gen = stale_generated(only_dirs=staged, repo=repo)
    hard = links + [x for x in gen if x.get("kind") == "stale"]
    soft = ([x for x in gen if x.get("kind") == "checker_error"]
            + prose_drift(repo=repo) + requirements_drift(repo))
    return {"generated_at": datetime.now(UTC).isoformat(),
            "hard": hard, "soft": soft,
            "counts": {"hard": len(hard), "soft": len(soft)}}


def main() -> int:
    ap = argparse.ArgumentParser(description="docs-drift checker")
    ap.add_argument("--check", action="store_true",
                    help="gate mode: hard families only, staleness scoped to staged files; exit 1 on hard drift")
    args = ap.parse_args()
    if args.check:
        hard = hard_drift(staged=staged_paths())
        if hard:
            print(f"docs-drift: {len(hard)} HARD drift item(s) — regenerate or fix links:")
            for h in hard[:50]:
                print("  -", json.dumps(h, ensure_ascii=False))
            print("Fix: run the relevant generator "
                  "(scripts/api_docs_gen.py / api_reference_gen.py / capabilities_gen.py) "
                  "or repair the broken link, then re-stage.")
            return 1
        print("docs-drift: clean (hard=0)")
        return 0
    rep = run_check()
    REPORT_OUT.write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n")
    print(f"docs-drift report → {REPORT_OUT.relative_to(REPO)}: "
          f"hard={rep['counts']['hard']}, soft={rep['counts']['soft']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
