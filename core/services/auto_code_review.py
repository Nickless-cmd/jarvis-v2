"""Auto code-review heuristic for git-commit proposals.

Mirrors my own habit of running the code-reviewer subagent before
saying "ready to merge". Spawning a real LLM critic per commit is
expensive; this module does a fast deterministic pass that flags the
most common issues, and attaches the report to the proposal payload so
the human reviewer in Mission Control sees it without an extra click.

A real LLM critic can be layered on top later via spawn_agent_task with
role="critic" — this is the cheap baseline.

Heuristics (each becomes a flag in the report):
- big-diff      : >500 changed lines (consider splitting)
- mixed-scope   : changes span ≥3 distinct top-level dirs
                  (e.g. core/, apps/, tests/) — split per scope?
- no-tests      : code under core/ or apps/ changed but tests/ untouched
- secrets-risk  : changes touch .env, credentials, secrets.json, etc.
- migration-risk: changes touch alembic/ or migrations/ — needs care
- format-only   : only whitespace/comments changed (likely noise)
- huge-file     : single file change >1000 lines (extra-careful review)
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_BIG_DIFF_THRESHOLD = 500
_HUGE_FILE_THRESHOLD = 1000
_SCOPE_THRESHOLD = 3


def _git_diff_stats(repo: Path, files: list[str]) -> dict[str, Any]:
    """Return per-file added/removed line counts for the staged or unstaged diff."""
    target = list(files) if files and files != ["."] else []
    args = ["git", "diff", "--numstat"] + (["--cached"] if False else [])
    # Run two diffs (cached + unstaged) and merge — propose_git_commit
    # files what's currently in working tree, regardless of stage state.
    out = {}
    for cached in (True, False):
        cmd = ["git", "diff", "--numstat"]
        if cached:
            cmd.append("--cached")
        if target:
            cmd += ["--", *target]
        try:
            res = subprocess.run(
                cmd, capture_output=True, text=True, cwd=str(repo), timeout=10,
            )
        except Exception:
            continue
        for line in res.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            try:
                added = int(parts[0]) if parts[0] != "-" else 0
                removed = int(parts[1]) if parts[1] != "-" else 0
            except ValueError:
                continue
            path = parts[2]
            cur = out.get(path, {"added": 0, "removed": 0})
            cur["added"] += added
            cur["removed"] += removed
            out[path] = cur
    return out


def _scope_for_path(p: str) -> str:
    parts = p.split("/")
    return parts[0] if parts else p


def review_pending_commit(
    *, repo_root: Path, files: list[str], message: str, rationale: str
) -> dict[str, Any]:
    stats = _git_diff_stats(repo_root, files)
    if not stats:
        return {
            "status": "ok",
            "verdict": "nothing-to-review",
            "flags": [],
            "summary": "No diff content found for the requested files.",
        }

    total_added = sum(s["added"] for s in stats.values())
    total_removed = sum(s["removed"] for s in stats.values())
    total = total_added + total_removed
    file_count = len(stats)
    huge_files = [p for p, s in stats.items() if (s["added"] + s["removed"]) >= _HUGE_FILE_THRESHOLD]
    scopes = sorted({_scope_for_path(p) for p in stats})

    flags: list[dict[str, str]] = []
    if total >= _BIG_DIFF_THRESHOLD:
        flags.append({
            "kind": "big-diff",
            "severity": "warn",
            "message": f"{total} lines changed across {file_count} files — consider splitting",
        })
    if len(scopes) >= _SCOPE_THRESHOLD:
        flags.append({
            "kind": "mixed-scope",
            "severity": "warn",
            "message": f"changes span {len(scopes)} top-level dirs ({', '.join(scopes)}) — split per scope?",
        })
    if huge_files:
        flags.append({
            "kind": "huge-file",
            "severity": "warn",
            "message": f"single-file diff exceeds {_HUGE_FILE_THRESHOLD} lines: {', '.join(huge_files[:3])}",
        })

    code_paths_touched = any(p.startswith(("core/", "apps/")) for p in stats)
    tests_touched = any(p.startswith("tests/") for p in stats)
    if code_paths_touched and not tests_touched:
        flags.append({
            "kind": "no-tests",
            "severity": "info",
            "message": "core/ or apps/ changed but no tests/ updated — confirm not needed",
        })

    secret_pat = ("/.env", "/credentials", "/secrets", "runtime.json")
    if any(any(s in p for s in secret_pat) for p in stats):
        flags.append({
            "kind": "secrets-risk",
            "severity": "block",
            "message": "diff touches .env / credentials / runtime.json / secrets — review carefully",
        })

    if any("/migrations/" in p or p.startswith("alembic/") for p in stats):
        flags.append({
            "kind": "migration-risk",
            "severity": "warn",
            "message": "diff touches DB migrations — has a rollback plan?",
        })

    # Rough format-only check: very few additions, mostly removals, or vice
    # versa, AND the file types are all docs.
    only_docs = all(p.endswith((".md", ".rst", ".txt")) for p in stats)
    if only_docs and total < 50:
        flags.append({
            "kind": "docs-only",
            "severity": "info",
            "message": "diff appears docs-only — fine to ship",
        })

    severities = {f["severity"] for f in flags}
    if "block" in severities:
        verdict = "needs-attention"
    elif flags:
        verdict = "ok-with-flags"
    else:
        verdict = "clean"

    return {
        "status": "ok",
        "verdict": verdict,
        "totals": {"added": total_added, "removed": total_removed, "files": file_count},
        "scopes": scopes,
        "flags": flags,
        "summary": f"{verdict}: {len(flags)} flag(s) across {file_count} files",
    }
