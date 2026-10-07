"""Goal reporter — fører systemets egne målinger tilbage til målet der bad om dem.

Baggrund (28/9-2026): to prio-100-mål stod urørt siden maj og juli — begge på
`progress_pct = 0`, med `updated_at` identisk med `created_at`. Ikke fordi
målingerne manglede: tick-kvalitet, heed-rate og decision-adherence regnes
allerede, flere steder i kodebasen. Men ingen af dem blev ført tilbage til det
mål der bad om dem.

Et mål der altid står på 0% ser neutralt ud og siger ingenting. Et mål der står
på 45% siger præcis hvad der halter. Rapportøren er den ledning.

Den læser de tre tal, skriver dem som én goal-update, og sætter `progress_pct`
efter målets EGNE kriterier. Er ét kriterium ikke opfyldt, er det det svageste
led der bestemmer — ikke gennemsnittet. Målet er ikke i mål før begge er det.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Målets egne kriterier, ordret fra beskrivelsen:
#   "Tick-kvalitet skal op over 75. R2 heed-rate over 80%."
TICK_TARGET = 75.0
HEED_TARGET = 80.0

# Målet findes på titel-fragment frem for et hardcodet id, så en genskabelse af
# målet ikke gør rapportøren tavs uden at nogen opdager det.
GOAL_TITLE_FRAGMENT = "Bevis pålidelighed"


def _criterion_fulfilment(measured: float | None, target: float) -> float | None:
    """Hvor stor en del af kriteriet er opfyldt — kappet ved 1.0.

    None betyder "ingen måling", ikke "opfyldt". Kalderen skal kunne skelne
    mellem *målt og god* og *ikke målt* — ellers ville et tavst instrument
    ligne en fuldført opgave.
    """
    if measured is None:
        return None
    try:
        return min(1.0, max(0.0, float(measured) / float(target)))
    except (TypeError, ValueError):  # ikke et tal — behandles som «ingen måling»
        return None


def _find_goal(*, title_fragment: str) -> dict[str, Any] | None:
    """Slå det aktive mål op hvis titel indeholder fragmentet."""
    from core.runtime.db_goals import list_goals

    for g in list_goals(status="active", limit=100):
        if title_fragment.lower() in str(g.get("title") or "").lower():
            return g
    return None


def collect_metrics(*, days: int = 7) -> dict[str, Any]:
    """Læs de tre tal. Fejler aldrig hårdt — et manglende tal bliver None.

    Adherence hører ikke til dette måls kriterier, men måles med her fordi det
    mål der bar det (trust-målet) blev lukket 28/9. Tallet skal ikke forsvinde
    sammen med målet.
    """
    tick_score: float | None = None
    adherence: float | None = None
    heed_rate: float | None = None

    try:
        from core.services.agent_self_evaluation import (
            decision_adherence_summary,
            tick_quality_summary,
        )

        tick_score = (tick_quality_summary(days=days) or {}).get("avg_score")
        adherence = (decision_adherence_summary() or {}).get("score")
    except Exception as exc:  # pragma: no cover — defensiv, kilden er ekstern
        logger.warning("goal_reporter: selv-evaluering kunne ikke læses: %s", exc)

    try:
        from core.services.verification_gate_telemetry import get_telemetry_summary

        heed_rate = (get_telemetry_summary(hours=days * 24) or {}).get("heed_rate")
    except Exception as exc:  # pragma: no cover — defensiv
        logger.warning("goal_reporter: telemetri kunne ikke læses: %s", exc)

    return {
        "tick_score": tick_score,
        "heed_rate": heed_rate,
        "adherence": adherence,
        "window_days": days,
    }


def compute_progress(*, tick_score: float | None, heed_rate: float | None) -> dict[str, Any]:
    """progress_pct + de enkelte kriterier. Svageste led bestemmer.

    `heed_rate` kommer som 0..1 fra telemetrien og ganges op til procent.
    """
    parts: list[dict[str, Any]] = [
        {
            "name": "tick-kvalitet",
            "measured": None if tick_score is None else round(float(tick_score), 1),
            "target": TICK_TARGET,
            "unit": "/100",
        },
        {
            "name": "heed-rate",
            "measured": None if heed_rate is None else round(float(heed_rate) * 100, 1),
            "target": HEED_TARGET,
            "unit": "%",
        },
    ]

    fulfilments: list[float] = []
    for p in parts:
        f = _criterion_fulfilment(p["measured"], p["target"])
        p["fulfilment"] = f
        if f is not None:
            fulfilments.append(f)

    progress = round(100 * min(fulfilments)) if fulfilments else None
    measured_parts = [p for p in parts if p["fulfilment"] is not None]
    weakest = (
        min(measured_parts, key=lambda p: p["fulfilment"])["name"]
        if measured_parts
        else None
    )
    return {"progress_pct": progress, "parts": parts, "weakest": weakest}


def _format_note(metrics: dict[str, Any], progress: dict[str, Any]) -> str:
    """Én kort note til update-loggen — tallene, ikke fortællingen om dem."""
    days = metrics.get("window_days", 7)
    lines = [f"Ugentlig måling (vindue {days} d):"]
    for p in progress["parts"]:
        if p["measured"] is None:
            lines.append(f"- {p['name']}: ingen måling (mål ≥{p['target']:g}{p['unit']})")
            continue
        ok = "✓" if p["measured"] >= p["target"] else "✗"
        lines.append(
            f"- {p['name']}: {p['measured']:g}{p['unit']} "
            f"(mål ≥{p['target']:g}{p['unit']}) {ok}"
        )
    adh = metrics.get("adherence")
    if adh is not None:
        lines.append(f"- decision-adherence: {adh:g}% (følger ikke målets kriterier)")
    if progress["progress_pct"] is not None and progress.get("weakest"):
        lines.append(
            f"→ {progress['progress_pct']}% — sat af det svageste led: {progress['weakest']}"
        )
    return "\n".join(lines)


def report_goal_metrics(
    *,
    days: int = 7,
    dry_run: bool = False,
    goal_title_fragment: str = GOAL_TITLE_FRAGMENT,
) -> dict[str, Any]:
    """Mål, skriv til målet, returnér hvad der skete. Aldrig stille."""
    metrics = collect_metrics(days=days)
    progress = compute_progress(
        tick_score=metrics["tick_score"], heed_rate=metrics["heed_rate"]
    )
    note = _format_note(metrics, progress)

    goal = _find_goal(title_fragment=goal_title_fragment)
    if goal is None:
        return {
            "status": "error",
            "error": f"intet aktivt mål matcher '{goal_title_fragment}'",
            "metrics": metrics,
            "progress": progress,
            "note": note,
        }

    current = int(goal.get("progress_pct") or 0)
    new = progress["progress_pct"]
    delta = None if new is None else new - current

    if dry_run:
        return {
            "status": "ok",
            "dry_run": True,
            "goal_id": goal["goal_id"],
            "from_progress": current,
            "to_progress": new,
            "note": note,
            "metrics": metrics,
        }

    from core.runtime.db_goals import append_goal_update

    updated = append_goal_update(
        goal_id=goal["goal_id"],
        note=note,
        progress_delta=delta,
        source="goal_reporter",
    )
    return {
        "status": "ok",
        "goal_id": goal["goal_id"],
        "from_progress": current,
        "to_progress": new,
        "delta": delta,
        "note": note,
        "metrics": metrics,
        "progress_pct_after": (updated or {}).get("progress_pct"),
    }
