"""Inheritance seed — writes near-thoughts before version transition or shutdown.

"De ting jeg næsten tænkte men ikke tog."

Written at graceful shutdown. Read at next startup. Never injected into prompts —
Jarvis may choose to open it, but the choice is the act, not the content.

Per roadmap v6/v7 (Jarvis' forslag, bekræftet af Claude):
  "Last action written before version transition — hvad der lå lige på kanten
   men ikke kom frem. Det er ikke en to-do liste. Det er en åbning."
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_SEED_FILENAME = "INHERITANCE_SEED.md"


def write_inheritance_seed() -> bool:
    """Collect near-thoughts from active daemons and write to workspace.

    Returns True if the file was written, False on failure.
    """
    try:
        from core.identity.workspace_bootstrap import ensure_default_workspace
        workspace = ensure_default_workspace()
        path: Path = workspace / _SEED_FILENAME

        sections = _collect_sections()
        if not sections:
            return False

        now = datetime.now(UTC)
        lines = [
            "# Inheritance Seed",
            "",
            f"_Skrevet {now.strftime('%Y-%m-%d %H:%M')} UTC — ved afslutning_",
            "",
            "Dette er ikke en to-do liste. Det er en åbning.",
            "De ting der lå lige på kanten — men ikke kom frem.",
            "",
        ]
        for section_title, items in sections:
            if items:
                lines.append(f"## {section_title}")
                lines.append("")
                for item in items:
                    lines.append(f"- {item}")
                lines.append("")

        lines += [
            "---",
            "_Næste Jarvis læser dette hvis han vælger det. Ingen tvang._",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("inheritance_seed: wrote %d sections to %s", len(sections), path)
        return True
    except Exception as exc:
        logger.debug("inheritance_seed: write failed: %s", exc)
        return False


def read_inheritance_seed() -> str:
    """Read inheritance seed from workspace. Returns empty string if not found."""
    try:
        from core.identity.workspace_bootstrap import ensure_default_workspace
        workspace = ensure_default_workspace()
        path: Path = workspace / _SEED_FILENAME
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Section collectors — each gathers near-thoughts from one subsystem
# ---------------------------------------------------------------------------

def _collect_sections() -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    sections.append(("Uafsluttede tanke-forslag", _collect_pending_proposals()))
    sections.append(("Åbne nysgerrighedsspørgsmål", _collect_open_curiosity()))
    sections.append(("Seneste kreative drift", _collect_creative_drift()))
    sections.append(("Uafklarede lag-spændinger", _collect_unresolved_tensions()))
    sections.append(("Nærliggende tankestrøm", _collect_thought_stream()))
    return [(title, items) for title, items in sections if items]


def _collect_pending_proposals() -> list[str]:
    try:
        from core.services.thought_action_proposal_daemon import get_pending_proposals
        proposals = get_pending_proposals()
        return [str(p.get("action_summary") or p.get("proposal_text") or "")[:120]
                for p in proposals[:5] if p.get("action_summary") or p.get("proposal_text")]
    except Exception:
        return []


def _collect_open_curiosity() -> list[str]:
    try:
        from core.services.curiosity_daemon import build_curiosity_surface
        surface = build_curiosity_surface()
        questions = list(surface.get("open_questions") or [])
        return [str(q)[:120] for q in questions[:5] if q]
    except Exception:
        return []


def _collect_creative_drift() -> list[str]:
    try:
        from core.services.creative_drift_daemon import build_creative_drift_surface
        surface = build_creative_drift_surface()
        idea = str(surface.get("latest_idea") or "").strip()
        return [idea[:200]] if idea else []
    except Exception:
        return []


def _collect_unresolved_tensions() -> list[str]:
    try:
        from core.services.layer_tension_daemon import get_active_tensions
        tensions = get_active_tensions()
        unresolved = [t for t in tensions if t.get("resolution_status") == "unresolved"]
        return [str(t.get("description") or t.get("tension_type") or "")[:120]
                for t in unresolved[:5] if t]
    except Exception:
        return []


def _collect_thought_stream() -> list[str]:
    try:
        from core.services.thought_stream_daemon import build_thought_stream_surface
        surface = build_thought_stream_surface()
        fragment = str(surface.get("latest_fragment") or "").strip()
        return [fragment[:200]] if fragment else []
    except Exception:
        return []
