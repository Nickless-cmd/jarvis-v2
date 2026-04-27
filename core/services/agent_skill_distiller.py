"""Agent skill distillation — turns observed outcomes into principles.

agent_skill_library stores raw observations. This module reads recent
agent runs (their outcomes, errors, success patterns) and distills them
into one-line *principles* — added back into skills.md as 'Workflows',
'Pitfalls', or 'Successful patterns'.

Run as a periodic job (weekly). LLM-led: the model decides if there's
a real pattern worth extracting. Empty result → nothing appended.

This is what makes the skill library actually *learn* over time, not
just accumulate timestamps.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _gather_recent_outcomes(role: str, days: int = 7) -> list[dict[str, Any]]:
    """Pull recent runs/outcomes for this role from agent observations."""
    try:
        from core.runtime.state_store import load_json
        observations = load_json("agent_observations", [])
        if not isinstance(observations, list):
            return []
    except Exception:
        return []
    cutoff = datetime.now(UTC) - timedelta(days=days)
    out: list[dict[str, Any]] = []
    for o in observations[-300:]:
        if not isinstance(o, dict):
            continue
        if o.get("role") != role:
            continue
        ts = str(o.get("recorded_at", ""))
        try:
            if datetime.fromisoformat(ts) < cutoff:
                continue
        except ValueError:
            continue
        out.append(o)
    return out


def _build_distill_prompt(role: str, outcomes: list[dict[str, Any]]) -> str:
    lines = []
    for o in outcomes[:30]:
        kind = o.get("kind", "outcome")
        summary = str(o.get("summary", ""))[:200]
        success = o.get("success")
        lines.append(f"- [{kind}] success={success} :: {summary}")
    body = "\n".join(lines) or "(ingen observationer)"
    return (
        f"Du er Jarvis i refleksion over rollen '{role}'.\n\n"
        f"Her er observationer fra de seneste {len(outcomes)} runs:\n\n"
        f"{body}\n\n"
        "Find op til 3 KONKRETE mønstre — ikke generiske råd. "
        "Format: hver linje starter med en af kategorierne:\n"
        "  WORKFLOW: <one-liner om hvad der virker>\n"
        "  PITFALL: <one-liner om hvad der svigter>\n"
        "  PATTERN: <one-liner om en gentagen succes>\n\n"
        "Skriv kun linjer hvor du faktisk ser et mønster i data. "
        "Ingen mønstre? Skriv 'NONE'. Maks 3 linjer."
    )


def _parse_distillation(text: str) -> list[tuple[str, str]]:
    if not text or "NONE" in text.upper():
        return []
    out: list[tuple[str, str]] = []
    section_map = {
        "WORKFLOW": "Workflows",
        "PITFALL": "Pitfalls",
        "PATTERN": "Successful patterns",
    }
    for raw in text.splitlines():
        line = raw.strip().lstrip("-").strip()
        if not line:
            continue
        for prefix, section in section_map.items():
            if line.upper().startswith(prefix + ":"):
                principle = line.split(":", 1)[1].strip()
                if principle and len(principle) < 280:
                    out.append((section, principle))
                break
        if len(out) >= 3:
            break
    return out


def distill_skills_for_role(role: str, *, days: int = 7) -> dict[str, Any]:
    """Distill recent outcomes for a role into principles. Appends to skills.md."""
    outcomes = _gather_recent_outcomes(role, days=days)
    if len(outcomes) < 3:
        return {"status": "skipped", "reason": "not enough outcomes", "count": len(outcomes)}

    prompt = _build_distill_prompt(role, outcomes)
    try:
        from core.services.daemon_llm import daemon_llm_call
        text = daemon_llm_call(prompt, max_len=400, fallback="", daemon_name=f"skill_distill_{role}")
    except Exception as exc:
        return {"status": "error", "error": f"llm failed: {exc}"}

    principles = _parse_distillation(text or "")
    if not principles:
        return {"status": "ok", "appended": 0, "reason": "no clear pattern"}

    try:
        from core.services.agent_skill_library import append_skill_observation
    except Exception as exc:
        return {"status": "error", "error": f"import failed: {exc}"}

    appended = 0
    for section, principle in principles:
        try:
            res = append_skill_observation(
                role=role, section=section, observation=principle,
                proposer="distiller",
            )
            if res.get("status") == "ok":
                appended += 1
        except Exception as exc:
            logger.warning("distiller: append failed for %s: %s", role, exc)
    return {"status": "ok", "role": role, "appended": appended,
            "considered": len(outcomes)}


def distill_all_known_roles(*, days: int = 7) -> dict[str, Any]:
    try:
        from core.services.agent_skill_library import list_known_roles
        roles = list_known_roles()
    except Exception:
        roles = []
    if not roles:
        return {"status": "skipped", "reason": "no known roles"}
    results = []
    total_appended = 0
    for role in roles:
        try:
            r = distill_skills_for_role(role, days=days)
            results.append(r)
            total_appended += int(r.get("appended", 0) or 0)
        except Exception as exc:
            results.append({"role": role, "status": "error", "error": str(exc)})
    return {"status": "ok", "roles_processed": len(roles),
            "total_appended": total_appended, "details": results}
