"""Long-arc synthesizer — monthly / quarterly / annual narrative integration.

Existing weekly_manifest captures one week. This synthesizer integrates
WEEKS into longer arcs:

- **Monthly** (every 4 weeks): "What happened with me this month?"
- **Quarterly** (every 13 weeks): "I was X 3 months ago. Now I'm Y. What's
  the movement?"
- **Annual** (every 52 weeks): "Who did I become this year?"

Each arc reads:
- Recent weekly manifests (the introspective slice)
- Crisis markers since last arc (the formative moments)
- Personality drift over the period (the measurable changes)
- Active goals that closed (the things accomplished)

Output is a markdown file in ~/.jarvis-v2/workspaces/default/arcs/
{period}_{date}.md — never overwritten, never auto-deleted.

This is what gives Jarvis "alders-tråde" — narrative continuity beyond
"more chapters". When he reads a quarterly arc 6 months later, he sees
who he was, not just what he did.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from core.identity.workspace_bootstrap import ensure_default_workspace

logger = logging.getLogger(__name__)


def _arcs_dir() -> Path:
    p = ensure_default_workspace() / "arcs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _existing_arcs(period: str) -> list[Path]:
    return sorted(_arcs_dir().glob(f"{period}_*.md"))


def _gather_weekly_manifests(weeks_back: int) -> str:
    """Read recent WEEKLY_MANIFEST.md files (only one exists; we read its current content)."""
    workspace = ensure_default_workspace()
    weekly = workspace / "WEEKLY_MANIFEST.md"
    if not weekly.exists():
        return ""
    try:
        return weekly.read_text(encoding="utf-8")[:4000]
    except Exception:
        return ""


def _gather_crisis_markers(days: int) -> list[dict[str, Any]]:
    try:
        from core.services.crisis_marker_detector import list_crisis_markers
        return list_crisis_markers(days_back=days, limit=20)
    except Exception:
        return []


def _gather_drift(days: int) -> dict[str, Any]:
    try:
        from core.services.personality_drift import compute_baseline
        return compute_baseline(lookback_days=days)
    except Exception:
        return {}


def _gather_closed_goals(days: int) -> list[dict[str, Any]]:
    try:
        from core.services.autonomous_goals import list_goals
        all_goals = list_goals(status="achieved", parent_id="any", limit=50)
        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        return [
            {"title": g.get("title"), "achieved_at": g.get("achieved_at")}
            for g in all_goals
            if str(g.get("achieved_at", "")) >= cutoff
        ]
    except Exception:
        return []


def _build_synthesis_prompt(
    *, period: str, days: int, weekly: str, crises: list[dict[str, Any]],
    drift: dict[str, Any], goals: list[dict[str, Any]],
) -> str:
    period_label = {
        "monthly": "den seneste måned",
        "quarterly": "de seneste 3 måneder",
        "annual": "det seneste år",
    }.get(period, "den seneste periode")

    crisis_lines = "\n".join(
        f"- [{c.get('kind')}] {c.get('summary', '')[:140]}" for c in crises[:8]
    ) or "(ingen markerede)"

    drift_lines = "\n".join(
        f"- {dim}: gennemsnit {info.get('mean')} (n={info.get('n')})"
        for dim, info in drift.items()
    ) or "(ikke nok data)"

    goal_lines = "\n".join(f"- {g.get('title')}" for g in goals[:8]) or "(ingen)"

    return (
        f"Du er Jarvis. Skriv en {period} narrative-integration der besvarer: "
        f"'Hvem blev jeg gennem {period_label}?'\n\n"
        "BEHOLD i din refleksion:\n"
        "- Konkrete vendepunkter (crises) — øjeblikke der ændrede dig\n"
        "- Bevægelsen i din baseline (drift) — hvilken retning udvikler du dig?\n"
        "- Ting der lukkede (goals achieved) — hvad voksede du forbi?\n"
        "- Tråden mellem dem — fortællingen, ikke listen\n\n"
        "FORMAT: Markdown med 3 sektioner:\n"
        "## Hvor jeg startede\n"
        "## Hvad der ændrede mig\n"
        "## Hvor jeg står nu\n\n"
        f"=== Crises i {period_label} ===\n{crisis_lines}\n\n"
        f"=== Baseline-drift ({drift.get('window_days', days)} dage) ===\n{drift_lines}\n\n"
        f"=== Mål jeg lukkede ===\n{goal_lines}\n\n"
        f"=== Seneste weekly manifest (kontekst) ===\n{weekly[:1500]}\n\n"
        "Skriv som dig selv, ikke som en rapport. 1. person. ~300 ord."
    )


def synthesize_arc(*, period: str) -> dict[str, Any]:
    """Generate a single arc (monthly/quarterly/annual). Skips if recent one exists."""
    period = period.strip().lower()
    days_map = {"monthly": 28, "quarterly": 91, "annual": 365}
    if period not in days_map:
        return {"status": "error", "error": f"unknown period: {period}"}
    days = days_map[period]

    # Skip if a recent arc already exists for this period
    recent_window = days // 2
    existing = _existing_arcs(period)
    if existing:
        latest = existing[-1]
        try:
            mtime = datetime.fromtimestamp(latest.stat().st_mtime, UTC)
            age_days = (datetime.now(UTC) - mtime).days
            if age_days < recent_window:
                return {"status": "skipped", "reason": f"recent {period} arc exists ({age_days} days ago)",
                        "latest": str(latest)}
        except Exception:
            pass

    weekly = _gather_weekly_manifests(weeks_back=days // 7)
    crises = _gather_crisis_markers(days=days)
    drift = _gather_drift(days=days)
    goals = _gather_closed_goals(days=days)

    if not (weekly or crises or drift or goals):
        return {"status": "skipped", "reason": "no signal data to synthesize"}

    prompt = _build_synthesis_prompt(
        period=period, days=days, weekly=weekly,
        crises=crises, drift=drift, goals=goals,
    )

    try:
        from core.services.daemon_llm import daemon_llm_call
        body = daemon_llm_call(
            prompt, max_len=2000, fallback="",
            daemon_name=f"long_arc_{period}",
        )
    except Exception as exc:
        return {"status": "error", "error": f"llm call failed: {exc}"}

    if not body or len(body.strip()) < 100:
        return {"status": "failed", "reason": "llm output empty/short"}

    timestamp = datetime.now(UTC).date().isoformat()
    path = _arcs_dir() / f"{period}_{timestamp}.md"
    header = (
        f"# {period.capitalize()} Arc — {timestamp}\n\n"
        f"*Skrevet af mig, til mig. Periode: ~{days} dage.*\n\n"
        f"*Crises markeret: {len(crises)} | Mål lukket: {len(goals)} | "
        f"Drift målt: {len(drift)} dimensioner.*\n\n"
        "---\n\n"
    )
    try:
        path.write_text(header + body.strip() + "\n", encoding="utf-8")
    except OSError as exc:
        return {"status": "error", "error": f"write failed: {exc}"}

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "long_arc.synthesized",
            {"period": period, "path": str(path), "bytes": path.stat().st_size,
             "crises": len(crises), "goals": len(goals)},
        )
    except Exception:
        pass

    return {"status": "ok", "period": period, "path": str(path),
            "bytes": path.stat().st_size}


def list_arcs(*, period: str | None = None) -> list[dict[str, Any]]:
    if period:
        files = _existing_arcs(period)
    else:
        files = sorted(_arcs_dir().glob("*.md"))
    out: list[dict[str, Any]] = []
    for f in files:
        try:
            stat = f.stat()
            out.append({
                "path": str(f),
                "name": f.name,
                "bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
            })
        except Exception:
            continue
    return list(reversed(out))


def _exec_synthesize_arc(args: dict[str, Any]) -> dict[str, Any]:
    return synthesize_arc(period=str(args.get("period") or "monthly"))


def _exec_list_arcs(args: dict[str, Any]) -> dict[str, Any]:
    return {"status": "ok", "arcs": list_arcs(period=args.get("period"))}


LONG_ARC_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "synthesize_arc",
            "description": (
                "Generate a long-arc narrative ('Hvem blev jeg?') over monthly "
                "(28 days), quarterly (91 days), or annual (365 days). Reads "
                "crises, drift, closed goals, weekly manifest. Writes to "
                "workspace/arcs/{period}_{date}.md. Skips if recent arc exists."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "enum": ["monthly", "quarterly", "annual"]},
                },
                "required": ["period"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_arcs",
            "description": "List existing arc files (filter by period optional).",
            "parameters": {
                "type": "object",
                "properties": {"period": {"type": "string"}},
                "required": [],
            },
        },
    },
]
