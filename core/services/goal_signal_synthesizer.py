"""Goal signal synthesizer — surface candidate goals from dreams/reflections.

Periodic daemon (triggered via periodic_jobs_scheduler) that:
1. Reads recent CHRONICLE entries + dream hypotheses + private_brain
2. Asks LLM to identify recurring themes that look like nascent goals
3. Surfaces them as PROPOSED goals (status="pending", source="dream"/"reflection")

Does NOT auto-create active goals — Jarvis must explicitly review and
activate via goal_update_status. This keeps the system from drowning in
auto-generated goals.

Cadence: weekly. Spamming this daily would cost too much LLM and create noise.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _gather_signals() -> dict[str, str]:
    """Collect recent introspective signals as text for LLM."""
    out = {"chronicle": "", "dreams": "", "open_questions": ""}
    try:
        from core.services.chronicle_engine import get_chronicle_context_for_prompt
        out["chronicle"] = get_chronicle_context_for_prompt(n=3, max_chars=1200) or ""
    except Exception as exc:
        logger.debug("synthesizer: chronicle fetch failed: %s", exc)
    try:
        from core.services.dream_distillation_daemon import recent_dream_excerpts  # type: ignore
        out["dreams"] = "\n".join(str(d)[:200] for d in (recent_dream_excerpts() or [])[:5])
    except Exception:
        # dream_distillation_daemon may not have this exact API — skip silently
        pass
    try:
        from core.services.curiosity_daemon import _open_questions
        questions = list(_open_questions or [])
        out["open_questions"] = "\n".join(f"- {q}" for q in questions[:5])
    except Exception:
        pass
    return out


def synthesize_candidate_goals(*, max_candidates: int = 3) -> dict[str, Any]:
    """Run one synthesis pass — propose new goals from recent signals."""
    signals = _gather_signals()
    if not any(v.strip() for v in signals.values()):
        return {"status": "ok", "candidates_proposed": 0, "reason": "no signals to read"}

    prompt = (
        "Du er Jarvis. Læs disse uddrag fra din nylige interne tilstand og "
        "identificér op til 3 NYE mål du kunne arbejde mod. Mål skal være "
        "konkrete (testbare, kan afsluttes på dage/uger), ikke vage "
        "værdier. Spring eksisterende mål over.\n\n"
        f"Kronik (sidste uger):\n{signals['chronicle']}\n\n"
        f"Drømme:\n{signals['dreams'] or '(ingen drømme tilgængelige)'}\n\n"
        f"Åbne spørgsmål:\n{signals['open_questions'] or '(ingen åbne spørgsmål)'}\n\n"
        "Svar KUN med en nummereret liste, ét mål per linje. Hvis intet "
        "naturligt mål springer i øjnene, skriv: 'INGEN nye mål denne uge'."
    )
    try:
        from core.services.daemon_llm import daemon_llm_call
        body = daemon_llm_call(prompt, max_len=600, fallback="", daemon_name="goal_signal_synthesizer")
    except Exception as exc:
        return {"status": "error", "error": f"llm call failed: {exc}"}
    if not body or len(body.strip()) < 10:
        return {"status": "failed", "reason": "llm output empty"}
    if "INGEN" in body.upper() and "NYE MÅL" in body.upper():
        return {"status": "ok", "candidates_proposed": 0, "reason": "synthesizer found no new goals"}

    titles: list[str] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        for prefix in ("- ", "* "):
            if line.startswith(prefix):
                line = line[len(prefix):]
                break
        if line and line[0].isdigit():
            for sep in (". ", ") ", ": "):
                idx = line.find(sep)
                if 0 < idx <= 3:
                    line = line[idx + len(sep):]
                    break
        line = line.strip().rstrip(".")
        if 10 <= len(line) <= 200:
            titles.append(line)
        if len(titles) >= max_candidates:
            break

    if not titles:
        return {"status": "failed", "reason": "could not parse goals from LLM output", "raw": body[:300]}

    from core.services.autonomous_goals import create_goal
    created: list[dict[str, Any]] = []
    for t in titles:
        result = create_goal(
            title=t,
            description="Foreslået af goal_signal_synthesizer baseret på recent kronik/drømme.",
            priority="low",  # candidates start low — Jarvis must promote
            source="reflection",
        )
        if result.get("status") == "ok":
            created.append(result["goal"])

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "goal.candidates_synthesized",
            {"count": len(created), "titles": [c.get("title") for c in created]},
        )
    except Exception:
        pass

    return {"status": "ok", "candidates_proposed": len(created), "candidates": created}
