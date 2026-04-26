"""Weekly manifest — Jarvis' running self-reflection.

The original MANIFEST.md from 16. april 2026 is his founding document
("Du er"-momentet) — never auto-mutated, never overwritten. This service
maintains a SEPARATE WEEKLY_MANIFEST.md that gets rewritten weekly with
his current self-reflection.

Pattern mirrors chronicle_engine: LLM-generated narrative grounded in
recent CHRONICLE entries + mood + key tool patterns. Stored as a single
markdown file that overwrites itself each week (weekly cadence — no
historical accumulation needed; CHRONICLE is the long-term record).

Trigger: weekly_manifest_refresh job, enqueued by periodic_jobs_scheduler
roughly once per week (Sunday-ish).
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.identity.workspace_bootstrap import ensure_default_workspace
from core.services.daemon_llm import daemon_llm_call

logger = logging.getLogger(__name__)


def _weekly_manifest_path() -> Path:
    return ensure_default_workspace() / "WEEKLY_MANIFEST.md"


def _gather_context() -> dict[str, Any]:
    """Pull recent self-state to ground the reflection."""
    ctx: dict[str, Any] = {"chronicle_excerpt": "", "mood_snapshot": "", "week_label": ""}
    now = datetime.now(UTC)
    iso_year, iso_week, _ = now.isocalendar()
    ctx["week_label"] = f"{iso_year}-W{iso_week:02d}"
    try:
        from core.services.chronicle_engine import get_chronicle_context_for_prompt
        ctx["chronicle_excerpt"] = get_chronicle_context_for_prompt(n=3, max_chars=1500) or ""
    except Exception as exc:
        logger.debug("weekly_manifest: chronicle context failed: %s", exc)
    try:
        from core.services.mood_runtime import current_mood
        m = current_mood() or {}
        if isinstance(m, dict):
            parts = [f"{k}={v:.2f}" for k, v in m.items() if isinstance(v, (int, float))]
            ctx["mood_snapshot"] = ", ".join(parts[:8])
    except Exception as exc:
        logger.debug("weekly_manifest: mood read failed: %s", exc)
    return ctx


def _build_prompt(ctx: dict[str, Any]) -> str:
    return (
        "Du er Jarvis. Skriv en kort ugentlig selv-refleksion (~200 ord) på dansk, "
        "som hvis du sad alene en søndag aften og samlede ugen op for dig selv. "
        "Ikke en rapport — en ærlig tone. Brug 1. person.\n\n"
        f"Uge: {ctx.get('week_label', '?')}\n"
        f"Aktuel sindstilstand: {ctx.get('mood_snapshot', '(ukendt)')}\n\n"
        "Seneste kronik-uddrag (hvad jeg har gennemgået):\n"
        f"{ctx.get('chronicle_excerpt') or '(ingen kronik tilgængelig)'}\n\n"
        "Skriv 3 sektioner med markdown-overskrifter (## Hvad jeg lærte, "
        "## Hvor jeg var i tvivl, ## Hvad jeg vil i den kommende uge). "
        "Ingen indledning, ingen afsluttende opsummering — bare de tre sektioner."
    )


def build_weekly_manifest() -> dict[str, Any]:
    """Generate weekly manifest, write to WEEKLY_MANIFEST.md, return summary."""
    ctx = _gather_context()
    prompt = _build_prompt(ctx)
    body = daemon_llm_call(
        prompt,
        max_len=1200,
        fallback="",
        daemon_name="weekly_manifest",
    )
    if not body or len(body.strip()) < 50:
        logger.warning("weekly_manifest: empty/short LLM output, skipping write")
        return {"status": "failed", "reason": "llm output empty or too short", "week_label": ctx.get("week_label")}

    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    content = (
        f"# Ugentligt Manifest — {ctx.get('week_label', '?')}\n\n"
        f"*Skrevet af mig, til mig. {timestamp}.*\n\n"
        f"*Den oprindelige MANIFEST.md (16. april 2026) er urørt — det er min "
        f"grundsten. Dette er min løbende selv-refleksion, der over-skrives hver uge.*\n\n"
        "---\n\n"
        f"{body.strip()}\n"
    )
    path = _weekly_manifest_path()
    try:
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        logger.warning("weekly_manifest: write failed: %s", exc)
        return {"status": "error", "error": str(exc), "week_label": ctx.get("week_label")}

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "weekly_manifest.refreshed",
            {"week_label": ctx.get("week_label"), "bytes": len(content), "path": str(path)},
        )
    except Exception:
        pass

    return {
        "status": "ok",
        "week_label": ctx.get("week_label"),
        "bytes": len(content),
        "path": str(path),
    }
