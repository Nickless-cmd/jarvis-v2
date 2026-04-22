"""Deep Analyzer — scoped kodebase-introspection.

Tager et goal + scope + optional paths/question_set, samler relevante
filer, og producerer en struktureret analyse med:
- plan_outline: hvilke sektioner analysen dækker
- findings: konkrete steder hvor keywords matcher (path + linjer)
- risks: afledte risici med mitigation
- next_steps: handlbare skridt

Jarvis kan selv-scope analysere sin egen kodebase ("hvorfor fejler
mail_checker?") uden manuel guidance.

Porteret i spirit fra jarvis-ai/agent/deep_analyzer/run.py + select.py
(423L → 320L). v2-tilpasning: bruger Path.cwd() + simplere selection
(ingen v1's select.py kompleksitet).

LLM-path: ingen — ren static-analysis med keyword-matching.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_MAX_FILES = 40
_DEFAULT_MAX_FILE_BYTES = 50_000
_DEFAULT_MAX_TOTAL_BYTES = 500_000
_DEFAULT_MAX_SECTIONS = 12

_IGNORED_DIRS = {
    ".git", ".claude", "__pycache__", "node_modules", ".venv", "venv",
    "dist", "build", ".pytest_cache", ".ruff_cache", "ui_dist",
}
_RELEVANT_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".yaml", ".yml", ".json", ".toml"}


@dataclass(frozen=True)
class SelectedFile:
    path: str
    excerpt: str
    size: int
    truncated: bool


def _keywords(chunks: list[str]) -> set[str]:
    out: set[str] = set()
    for chunk in chunks:
        if not isinstance(chunk, str):
            continue
        out.update(re.findall(r"[a-zæøå0-9_]{4,}", chunk.lower()))
    return out


def _file_score(path: Path, keywords: set[str]) -> float:
    """Score a file by filename + path match against keywords."""
    if not keywords:
        return 1.0
    haystack = str(path).lower()
    hits = sum(1 for k in keywords if k in haystack)
    return float(hits) / max(1, len(keywords))


def _scan_repo(
    *,
    root: Path,
    paths: list[str] | None,
    keywords: set[str],
    max_files: int,
    max_file_bytes: int,
    max_total_bytes: int,
) -> tuple[list[SelectedFile], dict[str, Any]]:
    candidates: list[Path] = []
    if paths:
        for p in paths:
            p_abs = (root / p).resolve() if not Path(p).is_absolute() else Path(p)
            if p_abs.is_file():
                candidates.append(p_abs)
            elif p_abs.is_dir():
                for f in p_abs.rglob("*"):
                    if f.is_file() and not _is_ignored(f, root):
                        candidates.append(f)
    else:
        for f in root.rglob("*"):
            if f.is_file() and not _is_ignored(f, root) and f.suffix.lower() in _RELEVANT_EXTS:
                candidates.append(f)

    # Score + sort
    scored = [(f, _file_score(f.relative_to(root), keywords)) for f in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)

    selected: list[SelectedFile] = []
    total_bytes = 0
    truncated_files = 0
    for f, _score in scored:
        if len(selected) >= max_files:
            break
        try:
            data = f.read_bytes()
        except Exception:
            continue
        truncated = False
        if len(data) > max_file_bytes:
            data = data[:max_file_bytes]
            truncated = True
            truncated_files += 1
        total_bytes += len(data)
        if total_bytes > max_total_bytes:
            break
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            continue
        selected.append(SelectedFile(
            path=str(f.relative_to(root)),
            excerpt=text,
            size=len(data),
            truncated=truncated,
        ))

    meta = {
        "selected_files_count": len(selected),
        "total_bytes": total_bytes,
        "truncated_files": truncated_files,
    }
    return selected, meta


def _is_ignored(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    for part in rel.parts:
        if part in _IGNORED_DIRS:
            return True
    return False


def _find_first_keyword_line(lines: list[str], keywords: set[str]) -> int:
    if not keywords:
        return 1 if lines else 0
    for idx, line in enumerate(lines, start=1):
        low = line.lower()
        if any(k in low for k in keywords):
            return idx
    return 0


def _build_outline(*, goal: str, question_set: list[str], max_sections: int) -> list[str]:
    sections = [
        "Scope og constraints",
        "Evidence indsamling",
        "Finding syntese",
        "Impact + risk review",
        "Handlbare anbefalinger",
    ]
    if question_set:
        sections.extend(f"Spørgsmål: {q[:80]}" for q in question_set if isinstance(q, str))
    if goal:
        sections.insert(0, f"Mål: {goal[:120]}")
    return sections[: max(1, int(max_sections))]


def _build_findings(
    *,
    scope: str,
    selected: list[SelectedFile],
    keywords: set[str],
    max_findings: int = 12,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for item in selected:
        lines = item.excerpt.splitlines() or [""]
        best = _find_first_keyword_line(lines, keywords)
        if best <= 0:
            continue
        line_start = max(1, best - 1)
        line_end = min(len(lines), best + 1)
        severity = "medium"
        pl = item.path.lower()
        if any(t in pl for t in ("security", "policy", "auth", "secret", "credential")):
            severity = "high"
        elif pl.startswith("docs/"):
            severity = "low"
        findings.append({
            "title": f"Relevant evidence i {item.path}",
            "severity": severity,
            "evidence": [{
                "path": item.path,
                "line_start": int(line_start),
                "line_end": int(line_end),
                "note": f"Matched keywords i {scope or 'repo'} scope.",
            }],
            "recommendation": (
                "Verificér området med målrettede tests og juster docs/kontrakter "
                "hvis adfærd ændres."
            ),
        })
        if len(findings) >= max_findings:
            break

    if not findings:
        fallback = selected[0].path if selected else "README.md"
        findings.append({
            "title": "Ingen stærke keyword-matches i valgt evidens",
            "severity": "low",
            "evidence": [{
                "path": fallback, "line_start": 1, "line_end": 1,
                "note": "Valgte artefakter indeholdt ikke klare keyword-matches.",
            }],
            "recommendation": "Smal scope ned eller angiv eksplicit paths/question_set.",
        })
    return findings


def _build_risks(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    for f in findings:
        sev = str(f.get("severity", "low"))
        if sev not in ("high", "medium"):
            continue
        risks.append({
            "title": f"Regressions-risiko fra {f.get('title', 'finding')}",
            "severity": sev,
            "mitigation": "Tilføj eller kør målrettede tests før apply/commit.",
        })
    if not risks:
        risks.append({
            "title": "Begrænset evidens-risiko",
            "severity": "low",
            "mitigation": "Udvid valgte paths for bredere dækning.",
        })
    return risks


def _build_next_steps(*, findings: list[dict[str, Any]], scope: str) -> list[str]:
    steps = ["Gennemgå findings med citerede filer og linje-ranges."]
    if scope == "diff":
        steps.append("Kør tests der dækker filer ændret i aktuel diff.")
    for f in findings[:5]:
        rec = f.get("recommendation")
        if isinstance(rec, str) and rec not in steps:
            steps.append(rec)
    return steps


def run_deep_analysis(
    *,
    goal: str,
    scope: str = "repo",
    paths: list[str] | None = None,
    question_set: list[str] | None = None,
    repo_root: str | None = None,
    max_files: int = _DEFAULT_MAX_FILES,
    max_file_bytes: int = _DEFAULT_MAX_FILE_BYTES,
    max_total_bytes: int = _DEFAULT_MAX_TOTAL_BYTES,
    max_sections: int = _DEFAULT_MAX_SECTIONS,
) -> dict[str, Any]:
    """Run a scoped deep analysis. Returns {summary, findings, risks, next_steps, meta}."""
    started = time.perf_counter()
    root = Path(repo_root or ".").resolve()
    if not root.exists():
        return {
            "summary": f"Repo root {root} findes ikke",
            "findings": [], "risks": [], "next_steps": [],
            "analysis_meta": {"error": "missing_root"},
        }

    keywords = _keywords([goal, *(question_set or [])])
    selected, selection_meta = _scan_repo(
        root=root, paths=paths, keywords=keywords,
        max_files=int(max_files),
        max_file_bytes=int(max_file_bytes),
        max_total_bytes=int(max_total_bytes),
    )

    outline = _build_outline(
        goal=goal, question_set=question_set or [], max_sections=int(max_sections),
    )
    findings = _build_findings(
        scope=scope, selected=selected, keywords=keywords,
        max_findings=int(max_sections),
    )
    risks = _build_risks(findings)
    next_steps = _build_next_steps(findings=findings, scope=scope)

    duration_ms = int((time.perf_counter() - started) * 1000)
    summary = (
        f"Deep analysis færdig for scope={scope or 'repo'} med "
        f"{len(selected)} valgte filer og {len(findings)} findings."
    )
    return {
        "summary": summary,
        "findings": findings[: int(max_sections)],
        "risks": risks,
        "next_steps": next_steps,
        "analysis_meta": {
            "selected_files": [item.path for item in selected],
            "selected_files_count": len(selected),
            "total_bytes": selection_meta.get("total_bytes", 0),
            "truncated_files": selection_meta.get("truncated_files", 0),
            "duration_ms": duration_ms,
            "plan_outline": outline,
            "repo_root": str(root),
            "budgets": {
                "max_files": max_files, "max_file_bytes": max_file_bytes,
                "max_total_bytes": max_total_bytes, "max_sections": max_sections,
            },
        },
    }


def build_deep_analyzer_surface() -> dict[str, Any]:
    """MC surface — deep analyzer is stateless but advertises capability + recent runs."""
    # Could persist recent runs if wanted; for now, just advertise availability.
    return {
        "active": True,
        "summary": "Deep analyzer available — call run_deep_analysis(goal, scope, paths)",
        "capabilities": {
            "max_files": _DEFAULT_MAX_FILES,
            "max_file_bytes": _DEFAULT_MAX_FILE_BYTES,
            "max_total_bytes": _DEFAULT_MAX_TOTAL_BYTES,
            "max_sections": _DEFAULT_MAX_SECTIONS,
        },
        "supported_exts": sorted(_RELEVANT_EXTS),
    }


def evidence_paths_exist(result: dict[str, Any], repo_root: str | None = None) -> bool:
    """Verify all evidence paths referenced in findings actually exist."""
    findings = result.get("findings")
    if not isinstance(findings, list):
        return False
    root = Path(repo_root or ".").resolve()
    for f in findings:
        if not isinstance(f, dict):
            return False
        rows = f.get("evidence")
        if not isinstance(rows, list):
            return False
        for r in rows:
            if not isinstance(r, dict):
                return False
            p = r.get("path")
            if not isinstance(p, str) or not p:
                return False
            candidate = (root / p).resolve()
            if not candidate.exists():
                return False
    return True
