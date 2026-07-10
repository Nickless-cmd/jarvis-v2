"""Doc repair agent (spec 2026-07-10 Del 2).

Opgraderer doc-vedligehold fra watch→repair. docs_drift_watchdog forbliver
watch-only; denne fil ejer den scope-begraensede handling. KRITISK invariant:
kan fysisk kun skrive under docs/ — roerer aldrig kode.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import logging

logger = logging.getLogger(__name__)

# Repo-rod: denne fil ligger i <repo>/core/services/doc_repair_agent.py
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOCS_ROOT = (_REPO_ROOT / "docs").resolve()


def is_allowed_doc_path(rel_or_abs: str) -> bool:
    """True KUN hvis stien oploeser til noget UNDER <repo>/docs/. Afviser traversal,
    absolutte stier uden for docs/, og alt kode. Dette er sikkerheds-invariantet."""
    raw = str(rel_or_abs or "").strip()
    if not raw:
        return False
    try:
        p = Path(raw)
        resolved = (p if p.is_absolute() else (_REPO_ROOT / p)).resolve()
    except Exception:
        return False
    try:
        resolved.relative_to(_DOCS_ROOT)
        return True
    except ValueError:
        return False
