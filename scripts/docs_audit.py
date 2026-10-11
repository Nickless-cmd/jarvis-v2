"""SP1 docs auditor — classify docs/*.md against git+runtime truth. Regenerable, static
(mirrors scripts/capability_audit.py). Stdlib only. Writes docs/docs_audit_raw.json.

11/10-2026 — udvidet efter at audit'et meldte «gaps: []» mens 241 levende docs bar
døde stier. Det havde tre blinde pletter, og alle tre er lukket her:

1. **Mønsteret** fangede kun `core|apps|scripts/…`. Stier under `tests/`, `docs/`,
   skill-relative stier og absolutte stier blev slet ikke set.
2. **Opløsningen** kendte kun repo-roden. `../tests/x.py` og `src/App.tsx` (en ægte
   fil, der bare ligger under `apps/mobile/`) stod derfor som døde. Nu prøves
   doc-relative stier, runtime-hjemmet (`~/.jarvis-v2/`) og til sidst et
   suffix-trin mod træets fil-indeks.
3. **Skills** blev ikke scannet — kun `docs/`. `.claude/skills/` er nu et andet rod.

En sti kan nu meldes i tre klasser: `repo` (skal findes i træet), `runtime` (skal
findes i `~/.jarvis-v2/`) og `abs_other` (`/etc`, `/tmp` — uden for træet; vi kan
ikke sige at den er død, kun at vi ikke kan se den herfra, så den tælles ikke).
"""
from __future__ import annotations

import json
import posixpath
import re
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"
SKILLS_ROOT = REPO_ROOT / ".claude" / "skills"

# Runtime-hjemmet. Spejlet fra core/runtime/config.py:4 med vilje — dette script er
# stdlib-only og må ikke importere runtime for at kunne køre som hook.
_RUNTIME_HOME = Path.home() / ".jarvis-v2"

# Fil-endelser der tæller som en kode-sti. Bredere end før (kun py/ts/tsx/md/json).
_FILE_EXT = "py|ts|tsx|js|jsx|mjs|cjs|md|json|sh|yml|yaml|toml|cfg|ini|sql|html|css|txt"

# En sti = mindst ét skråstreg OG en kendt endelse. Det holder rene filnavne i prosa
# ude, men fanger `tests/x.py`, `docs/y.md`, `src/App.tsx` og `../z.py`.
_PATH_RE = re.compile(
    r"(?<![\w:/@.-])(?:~/|\.\./|\./|/)?(?:[\w@.+-]+/)+[\w@.+-]+\.(?:" + _FILE_EXT + r")\b")

# Et link er en kildehenvisning, ikke en påstand om at filen ligger i træet.
_URL_RE = re.compile(r"[a-zA-Z][\w+.-]*://[^\s`)\]>\"'*]+")

_SYMBOL_RE = re.compile(r"`([a-zA-Z_][a-zA-Z0-9_]{3,})`")
_STALE_DAYS = 120
_SUBSYSTEMS = ["core/services", "core/runtime", "core/tools", "core/context",
               "apps/api", "apps/ui", "scripts"]

# Historik-filer beskriver FORTIDEN. En død sti i en changelog er meningen med den,
# præcis som i _archive — så de holdes ude af «lever dokumentet op til nutiden».
_HISTORY_NAMES = {"COMMIT_HISTORY.md"}
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache"}


def find_docs(root: Path | None = None) -> list[Path]:
    """Return all *.md files under root (recursive, sorted), excluding _archive dirs and
    history logs. root=None → DOCS_ROOT (resolved at call time, so tests can monkeypatch)."""
    root = root if root is not None else DOCS_ROOT
    return sorted(p for p in root.rglob("*.md")
                  if "_archive" not in p.parts and p.name not in _HISTORY_NAMES)


def extract_references(text: str) -> dict:
    """Pull code references out of markdown text: repo paths (any prefix, see _PATH_RE) and
    backtick-quoted symbols. URLs are stripped first — a link is a source, not a path claim.
    Returns {"paths": [...], "symbols": [...]} (deduped, sorted)."""
    paths = sorted(set(_PATH_RE.findall(_URL_RE.sub(" ", text))))
    symbols = sorted(set(_SYMBOL_RE.findall(text)))
    return {"paths": paths, "symbols": symbols}



def _ref_kind(p: str, repo_root: Path = REPO_ROOT) -> str:
    """Classify a reference: "runtime" (~/.jarvis-v2/…), "repo" (lives in the tree) or
    "abs_other" (absolute path outside the tree — unverifiable from here, so never dead)."""
    if p.startswith("~/.jarvis-v2/") or p.startswith("/.jarvis-v2/"):
        return "runtime"
    if p.startswith("/"):
        return "repo" if p.startswith(str(repo_root).rstrip("/") + "/") else "abs_other"
    return "repo"


def _tail(p: str) -> str:
    """Strip leading `/`, `./` and `../` — the part we can match on without knowing which
    directory the doc meant. `../tests/x.py` → `tests/x.py`."""
    p = p.lstrip("/")
    while p.startswith("../") or p.startswith("./"):
        p = p[3:] if p.startswith("../") else p[2:]
    return p


def _tree_index(repo_root: Path = REPO_ROOT) -> dict:
    """basename → [repo-relative paths]. `git ls-files` when available (respects .gitignore,
    ignores stale worktrees, fast); a plain walk as fallback so tests can use a tmp dir."""
    rel: list[str] = []
    try:
        out = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                             cwd=repo_root, timeout=30)
        if out.returncode == 0:
            rel = [ln for ln in out.stdout.splitlines() if ln.strip()]
    except Exception:
        rel = []
    if not rel:
        for p in repo_root.rglob("*"):
            if any(s in p.parts for s in _SKIP_DIRS):
                continue
            if p.is_file():
                rel.append(p.relative_to(repo_root).as_posix())
    index: dict = {}
    for f in rel:
        index.setdefault(f.rsplit("/", 1)[-1], []).append(f)
    return index


def _resolves(p: str, doc_rel: str | None, repo_root: Path,
              index: dict, runtime_root: Path) -> bool:
    """Does the reference point at something that exists? Tries, in order: the runtime home,
    the repo root, the doc's OWN directory, and finally a suffix-match against the tree —
    that last one is what makes `src/App.tsx` resolve to `apps/mobile/src/App.tsx`."""
    for pre in ("~/.jarvis-v2/", "/.jarvis-v2/"):
        if p.startswith(pre):
            return (runtime_root / p[len(pre):]).exists()
    root = str(repo_root).rstrip("/")
    if p.startswith(root + "/"):
        p = p[len(root) + 1:]
    elif p.startswith("/"):
        return Path(p).exists()          # absolut uden for træet — se den virkelige fil
    if (repo_root / p).exists():
        return True
    if doc_rel:
        joined = posixpath.normpath(posixpath.join(posixpath.dirname(doc_rel), p))
        if not joined.startswith("..") and (repo_root / joined).exists():
            return True
    tail = _tail(p)
    base = tail.rsplit("/", 1)[-1]
    return any(f == tail or f.endswith("/" + tail) for f in index.get(base, ()))


def liveness(refs: dict, repo_root: Path = REPO_ROOT, doc_rel: str | None = None,
             runtime_root: Path | None = None, index: dict | None = None) -> dict:
    """Check how many of refs["paths"] still resolve. Absolute paths outside the tree are left
    out of the count — we cannot see them from here, and «unseen» is not «gone».
    Returns {"resolved", "total", "ratio", "dead"}; ratio is None when nothing is verifiable."""
    runtime_root = runtime_root if runtime_root is not None else _RUNTIME_HOME
    paths = [p for p in (refs.get("paths") or []) if _ref_kind(p, repo_root) != "abs_other"]
    if not paths:
        return {"resolved": 0, "total": 0, "ratio": None, "dead": []}
    index = index if index is not None else _tree_index(repo_root)
    dead = [p for p in paths if not _resolves(p, doc_rel, repo_root, index, runtime_root)]
    return {"resolved": len(paths) - len(dead), "total": len(paths),
            "ratio": round((len(paths) - len(dead)) / len(paths), 3), "dead": dead}


def dead_paths(refs: dict, repo_root: Path = REPO_ROOT, doc_rel: str | None = None,
               runtime_root: Path | None = None, index: dict | None = None) -> list[str]:
    """The references that point at nothing we can find. Absolute paths outside the tree are
    skipped — «we cannot see it» is not the same as «it is gone»."""
    return liveness(refs, repo_root=repo_root, doc_rel=doc_rel,
                    runtime_root=runtime_root, index=index)["dead"]


def git_last_touch(path: Path, repo_root: Path = REPO_ROOT) -> tuple[int | None, str]:
    """Return (days_since_last_commit, iso_commit_date) for path via `git log -1`.
    Returns (None, "") when the file has no git history or git fails."""
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cI", "--", str(path)],
                             capture_output=True, text=True, cwd=repo_root, timeout=10)
        iso = out.stdout.strip()
        if not iso:
            return None, ""
        dt = datetime.fromisoformat(iso)
        return (datetime.now(dt.tzinfo) - dt).days, iso
    except Exception:
        return None, ""


def title_and_headings(text: str) -> tuple[str, set]:
    """Parse markdown headings from text. Returns (title, headings): title is the first `#` heading
    (lowercased), headings is the set of all lowercased heading texts."""
    title, headings = "", set()
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("#"):
            h = s.lstrip("#").strip().lower()
            if not title:
                title = h
            if h:
                headings.add(h)
    return title, headings


def detect_superseded(docs: list[dict]) -> dict:
    """docs: [{path,title,headings,days}]. Older doc is superseded by a NEWER doc that shares the
    same title or >0.6 heading Jaccard overlap."""
    result: dict = {}
    for a in docs:
        for b in docs:
            if a["path"] == b["path"] or not a["headings"] or not b["headings"]:
                continue
            same_title = bool(a["title"]) and a["title"] == b["title"]
            union = a["headings"] | b["headings"]
            overlap = len(a["headings"] & b["headings"]) / max(1, len(union))
            newer = (b["days"] is not None and a["days"] is not None and b["days"] < a["days"])
            if (same_title or overlap > 0.6) and newer:
                result[a["path"]] = b["path"]
                break
    return result


def feature_shipped(refs: dict, repo_root: Path = REPO_ROOT) -> bool:
    """A superpowers spec/plan 'shipped' if any referenced path exists, or a key symbol is in the tree."""
    if any((repo_root / p).exists() for p in refs.get("paths") or []):
        return True
    for sym in (refs.get("symbols") or [])[:8]:
        try:
            out = subprocess.run(["git", "grep", "-lE", re.escape(sym), "--", "core", "apps", "scripts"],
                                 capture_output=True, text=True, cwd=repo_root, timeout=10)
            if out.stdout.strip():
                return True
        except Exception:
            pass
    return False


def classify_heuristic(*, path: str, refs: dict, live: dict, days: int | None,
                       superseded_by: str | None, is_superpowers: bool,
                       shipped: bool) -> tuple[str, float, str]:
    """Classify a doc from its signals into a category. Returns (category, confidence, basis):
    "droppet" if superseded; superpowers artifacts → "færdig"/"droppet"/"needs_review" by shipped/age;
    otherwise "forældet" (all refs dead + stale), "færdig" (>=90% refs alive + fresh), else "needs_review"."""
    ratio = live.get("ratio")
    old = days is not None and days > _STALE_DAYS
    if superseded_by:
        return "droppet", 0.8, f"superseded by {superseded_by}"
    if is_superpowers:
        if shipped:
            return "færdig", 0.75, "superpowers artifact shipped (refs/symbols present in tree)"
        if old:
            return "droppet", 0.6, "superpowers artifact, no trace in tree + old"
        return "needs_review", 0.0, "superpowers artifact, shipped-status unclear"
    if ratio is not None:
        if ratio == 0.0 and old:
            return "forældet", 0.8, f"all {live['total']} code refs dead + {days}d old"
        if ratio >= 0.9 and not old:
            return "færdig", 0.7, f"{live['resolved']}/{live['total']} refs alive, {days}d old"
    return "needs_review", 0.0, "ambiguous signals — needs read"


_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def _yaml_val(v) -> str:
    s = str(v)
    return f'"{s}"' if (":" in s or "#" in s or s == "") else s


def stamp_frontmatter(text: str, fields: dict) -> str:
    """Idempotent, surgical YAML frontmatter merge: replaces only the given keys, preserves the rest
    verbatim (no lossy parse). Prepends a block when none exists. Stdlib only."""
    new_lines = [f"{k}: {_yaml_val(v)}" for k, v in fields.items()]
    m = _FM_RE.match(text)
    if m:
        keys = set(fields)
        kept = [ln for ln in m.group(1).splitlines()
                if ln.split(":", 1)[0].strip() not in keys]
        block = "\n".join(kept + new_lines)
        return f"---\n{block}\n---\n" + text[m.end():]
    return "---\n" + "\n".join(new_lines) + "\n---\n" + text


def render_manifest_md(entries: list[dict]) -> str:
    """Render the audit entries as a DOCS_MANIFEST markdown document: a generated-header line with
    per-category counts plus a table of path/category/basis/superseded-by, sorted by category then path."""
    by_cat = Counter(e["category"] for e in entries)
    lines = ["# DOCS_MANIFEST", "",
             f"Generated {datetime.now(UTC).date().isoformat()} · {len(entries)} docs · {dict(by_cat)}",
             "", "| Path | Category | Basis | Superseded by |", "|---|---|---|---|"]
    for e in sorted(entries, key=lambda x: (x["category"], x["path"])):
        lines.append(f"| `{e['path']}` | {e['category']} | {e.get('basis','')} | {e.get('superseded_by') or ''} |")
    return "\n".join(lines) + "\n"


def build_gap_list(entries: list[dict]) -> list[dict]:
    """Coarse subsystem coverage: which _SUBSYSTEMS have NO færdig doc referencing them."""
    covered = set()
    for e in entries:
        if e["category"] != "færdig":
            continue
        for sub in _SUBSYSTEMS:
            if any(str(p).startswith(sub) for p in e.get("ref_paths") or []):
                covered.add(sub)
    return [{"subsystem": s, "covered": s in covered} for s in _SUBSYSTEMS]


def audit() -> dict:
    """Run the full docs audit: scan every doc under docs/ AND .claude/skills/, extract
    refs/headings/git-age, detect supersession, classify each, and return {generated, count,
    by_category, gap_list, dead_paths_total, dead_docs, docs:[entry,...]}."""
    index = _tree_index(REPO_ROOT)
    metas = []
    for p in find_docs(DOCS_ROOT) + find_docs(SKILLS_ROOT):
        text = p.read_text(errors="ignore")
        title, headings = title_and_headings(text)
        days, iso = git_last_touch(p)
        refs = extract_references(text)
        metas.append({"path": str(p.relative_to(REPO_ROOT)), "title": title, "headings": headings,
                      "days": days, "iso": iso, "refs": refs,
                      "is_sp": "superpowers" in p.parts})
    superseded = detect_superseded([{"path": m["path"], "title": m["title"],
                                     "headings": m["headings"], "days": m["days"]} for m in metas])
    entries = []
    for m in metas:
        live = liveness(m["refs"], doc_rel=m["path"], index=index)
        shipped = feature_shipped(m["refs"]) if m["is_sp"] else False
        cat, conf, basis = classify_heuristic(
            path=m["path"], refs=m["refs"], live=live, days=m["days"],
            superseded_by=superseded.get(m["path"]), is_superpowers=m["is_sp"], shipped=shipped)
        entries.append({"path": m["path"], "category": cat, "confidence": conf, "basis": basis,
                        "days": m["days"], "liveness": live, "superseded_by": superseded.get(m["path"]),
                        "ref_paths": m["refs"]["paths"], "dead_paths": live["dead"]})
    return {"generated": datetime.now(UTC).isoformat(), "count": len(entries),
            "by_category": dict(Counter(e["category"] for e in entries)),
            "dead_paths_total": sum(len(e["dead_paths"]) for e in entries),
            "dead_docs": sum(1 for e in entries if e["dead_paths"]),
            "gap_list": build_gap_list(entries), "docs": entries}


def main() -> int:
    """CLI entry point: run audit(), write docs/docs_audit_raw.json, print a summary — category
    counts, gap subsystems and the dead-path tally. Returns 0."""
    result = audit()
    out = DOCS_ROOT / "docs_audit_raw.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"docs_audit: {result['count']} docs → {result['by_category']}")
    print(f"gaps: {[g['subsystem'] for g in result['gap_list'] if not g['covered']]}")
    print(f"døde stier: {result['dead_paths_total']} i {result['dead_docs']} dokumenter")
    print(f"written {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
