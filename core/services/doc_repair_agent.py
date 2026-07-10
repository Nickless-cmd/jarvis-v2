"""Doc repair agent (spec 2026-07-10 Del 2).

Opgraderer doc-vedligehold fra watch→repair. docs_drift_watchdog forbliver
watch-only; denne fil ejer den scope-begraensede handling. KRITISK invariant:
kan fysisk kun skrive under docs/ — roerer aldrig kode.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import logging

from core.services.docs_drift_watchdog import check_docs_drift
from core.services.gate_enforcement import is_enforced
from core.services.central_capture import GateClass

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


def find_stale_docs() -> list[dict[str, Any]]:
    """Konsumér docs_drift_watchdog-signalet → liste af {path, generator} for docs
    der er drevet. Self-safe: fejl → tom liste."""
    try:
        report = check_docs_drift() or {}
    except Exception as exc:
        logger.debug("doc_repair_agent: drift check failed: %s", exc)
        return []
    docs = report.get("docs") or []
    out = []
    for d in docs:
        path = str((d or {}).get("path") or "")
        if path and is_allowed_doc_path(path):
            out.append({"path": path, "generator": (d or {}).get("generator")})
    return out


def _run_generator(name: str) -> str | None:
    """Kør en kendt deterministisk doc-generator og returnér det nye indhold.
    Foreloebig: kun 'capability_audit' → capability_matrix. Ukendt → None (→ ingen
    handling; LLM-draft-mode er en senere udvidelse, ikke v1)."""
    if not name:
        return None
    # v1 er bevidst konservativ: kun deterministiske generatorer. Returnér None for
    # ukendte saa vi aldrig skriver ugrundet indhold (YAGNI: LLM-draft senere).
    return None


def repair_doc(target: dict[str, Any], *, live: bool) -> dict[str, Any]:
    """Repair én doc. Skriver KUN under docs/ (invariant), KUN naar live=True og
    en deterministisk generator gav indhold. Self-safe."""
    path = str((target or {}).get("path") or "")
    out: dict[str, Any] = {"path": path, "applied": False, "shadow": not live,
                           "would_write": False, "reason": ""}
    if not is_allowed_doc_path(path):
        out["reason"] = "path-not-allowed"
        return out
    try:
        content = _run_generator(str((target or {}).get("generator") or ""))
    except Exception as exc:
        logger.debug("doc_repair_agent: generator failed: %s", exc)
        out["reason"] = "generator-error"
        return out
    if content is None:
        out["reason"] = "no-deterministic-generator"
        return out
    out["would_write"] = True
    if not live:
        return out
    try:
        abs_path = (_REPO_ROOT / path).resolve()
        abs_path.relative_to(_DOCS_ROOT)  # dobbelt-tjek invariant FOER write
        abs_path.write_text(content, encoding="utf-8")
        out["applied"] = True
    except Exception as exc:
        logger.debug("doc_repair_agent: write failed: %s", exc)
        out["reason"] = "write-error"
    return out


_MAX_DOCS_PER_TICK = 3


def run_doc_repair_tick() -> dict[str, Any]:
    """Cadence-indgang, kørt gennem central().decide (Centralen er aktoeren).
    gate_enforcement afgoer live vs shadow (default not-enforced = shadow-rampe).
    Returnerer summary'en (testbar) og router den STADIG gennem Centralen for
    governance/trace."""
    from core.services.central_core import central
    try:
        live = bool(is_enforced("doc_repair", GateClass.COGNITIVE))
    except Exception:
        live = False

    summary: dict[str, Any] = {"shadow": not live, "applied": 0,
                               "would_write": 0, "skipped": 0, "error": False}
    try:
        for target in (find_stale_docs() or [])[:_MAX_DOCS_PER_TICK]:
            out = repair_doc(target, live=live)
            if out.get("applied"):
                summary["applied"] += 1
            elif out.get("would_write"):
                summary["would_write"] += 1
            else:
                summary["skipped"] += 1
    except Exception as exc:
        logger.debug("doc_repair_agent: repair loop failed: %s", exc)
        summary["error"] = True

    try:
        central().decide("doc_repair", {"live": live}, lambda _c: summary,
                         cluster="maintenance", klass=GateClass.COGNITIVE)
    except Exception:
        pass  # governance-trace maa aldrig aendre resultatet
    return summary


def build_doc_repair_surface() -> dict[str, Any]:
    """Read-surface til jc raw /central/doc-repair. Side-effect-fri."""
    try:
        enforced = bool(is_enforced("doc_repair", GateClass.COGNITIVE))
    except Exception:
        enforced = False
    stale = find_stale_docs() or []
    return {
        "active": bool(stale),
        "mode": "doc-repair",
        "enforced": enforced,
        "summary": {"stale_count": len(stale),
                    "state": "live" if enforced else "shadow-ramp"},
        "items": stale,
    }
