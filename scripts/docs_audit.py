"""SP1 docs auditor — classify docs/*.md against git+runtime truth. Regenerable, static
(mirrors scripts/capability_audit.py). Stdlib only. Writes docs/docs_audit_raw.json."""
from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"

_PATH_RE = re.compile(r"(?:core|apps|scripts)/[\w./-]+\.(?:py|ts|tsx|md|json)")
_SYMBOL_RE = re.compile(r"`([a-zA-Z_][a-zA-Z0-9_]{3,})`")
_STALE_DAYS = 120
_SUBSYSTEMS = ["core/services", "core/runtime", "core/tools", "core/context",
               "apps/api", "apps/ui", "scripts"]


def find_docs(root: Path = DOCS_ROOT) -> list[Path]:
    return sorted(p for p in root.rglob("*.md") if "_archive" not in p.parts)


def extract_references(text: str) -> dict:
    paths = sorted(set(_PATH_RE.findall(text)))
    symbols = sorted(set(_SYMBOL_RE.findall(text)))
    return {"paths": paths, "symbols": symbols}


def liveness(refs: dict, repo_root: Path = REPO_ROOT) -> dict:
    paths = refs.get("paths") or []
    if not paths:
        return {"resolved": 0, "total": 0, "ratio": None}
    resolved = sum(1 for p in paths if (repo_root / p).exists())
    return {"resolved": resolved, "total": len(paths), "ratio": round(resolved / len(paths), 3)}


def git_last_touch(path: Path, repo_root: Path = REPO_ROOT) -> tuple[int | None, str]:
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
    metas = []
    for p in find_docs():
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
        live = liveness(m["refs"])
        shipped = feature_shipped(m["refs"]) if m["is_sp"] else False
        cat, conf, basis = classify_heuristic(
            path=m["path"], refs=m["refs"], live=live, days=m["days"],
            superseded_by=superseded.get(m["path"]), is_superpowers=m["is_sp"], shipped=shipped)
        entries.append({"path": m["path"], "category": cat, "confidence": conf, "basis": basis,
                        "days": m["days"], "liveness": live, "superseded_by": superseded.get(m["path"]),
                        "ref_paths": m["refs"]["paths"]})
    return {"generated": datetime.now(UTC).isoformat(), "count": len(entries),
            "by_category": dict(Counter(e["category"] for e in entries)),
            "gap_list": build_gap_list(entries), "docs": entries}


def main() -> int:
    result = audit()
    out = DOCS_ROOT / "docs_audit_raw.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"docs_audit: {result['count']} docs → {result['by_category']}")
    print(f"gaps: {[g['subsystem'] for g in result['gap_list'] if not g['covered']]}")
    print(f"written {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
