"""propose_skill_chain tool — Skill Chain Phase 2 (AGI track #10).

Givet en task_description, kald cheap-lane LLM med fuldt skill-katalog
og lad den foreslå en ordnet kæde af 2-5 skills (eller tom hvis ingen
meningsfuld kæde findes).

Returnerer struktureret forslag — ikke autorisation. Jarvis bestemmer
om han kører `skill_chain(plan=...)` med forslaget eller justerer.

Stateless. Ingen DB, ingen state-machine. Mirror plan_revise_tool /
world_model_tools pattern.

See spec: docs/superpowers/specs/2026-05-12-skill-chain-phase2-design.md
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from core.runtime.settings import load_settings
from core.services.cheap_provider_runtime import execute_public_safe_cheap_lane
from core.services.skill_engine import list_skills, skill_exists

logger = logging.getLogger(__name__)


_MIN_TASK_LEN = 10
_MIN_PLAN_LEN = 2
_MAX_PLAN_LEN = 5
_TASK_EXCERPT_MAX = 120  # PII-bound on event payload
_RATIONALE_MAX_CHARS = 600  # bound on stored rationale


def _phase2_enabled() -> bool:
    try:
        return bool(load_settings().skill_chain_phase2_enabled)
    except Exception:
        return True  # fail-open


def _exec_propose_skill_chain(args: dict[str, Any]) -> dict[str, Any]:
    """Tool handler for propose_skill_chain.

    Pipeline:
      1. Killswitch
      2. Validate task_description (≥ 10 chars)
      3. Fetch skill catalog
      4. Build prompt
      5. Invoke cheap-lane
      6. Parse JSON response
      7. Validate skill existence (alt-eller-intet)
      8. Emit cognitive_skill_chain.proposed event
      9. Return structured proposal
    """
    # 1. Killswitch
    if not _phase2_enabled():
        return {
            "status": "disabled",
            "note": "skill_chain_phase2 is disabled in runtime settings",
        }

    # 2. Validate task_description
    task = str(args.get("task_description") or "").strip()
    if not task:
        return {"status": "rejected", "reason": "task_description is required"}
    if len(task) < _MIN_TASK_LEN:
        return {
            "status": "rejected",
            "reason": f"task_description must be at least {_MIN_TASK_LEN} chars",
        }

    # 3. Fetch catalog
    try:
        catalog = list_skills()
    except Exception as exc:
        logger.warning("propose_skill_chain: catalog fetch failed: %s", exc)
        return {"status": "error", "reason": f"skill catalog unavailable: {exc}"}

    # 4. Build prompt
    prompt = _build_propose_prompt(task_description=task, catalog=catalog)

    # 5. Invoke cheap-lane
    try:
        cheap_result = execute_public_safe_cheap_lane(message=prompt)
    except Exception as exc:
        logger.warning("propose_skill_chain: cheap-lane invocation failed: %s", exc)
        return {"status": "error", "reason": f"cheap-lane error: {exc}"}

    response_text = str(cheap_result.get("text") or "")
    model_used = str(cheap_result.get("model") or "")
    provider_used = str(cheap_result.get("provider") or "")

    # 6. Parse response
    parsed = _parse_propose_response(response_text)
    if parsed["status"] != "ok":
        return {
            "status": "error",
            "reason": parsed["reason"],
            "raw_response_excerpt": response_text[:200],
            "model_used": model_used,
        }

    plan = parsed["plan"]
    rationale = parsed["rationale"]
    confidence = parsed["confidence"]

    # 7. Validate skill existence (only when plan non-empty)
    missing = [name for name in plan if not skill_exists(name)]
    if missing:
        return {
            "status": "rejected",
            "reason": "cheap-lane suggested unknown skills",
            "missing": missing,
            "rejected_plan": plan,
            "rationale": rationale,
            "confidence": confidence,
        }

    # 8. Emit event (metadata only — task_excerpt PII-bounded, rationale_length not text)
    _publish_propose_event(
        plan=plan,
        confidence=confidence,
        rationale_length=len(rationale),
        model_used=model_used,
        provider_used=provider_used,
        task_excerpt=task[:_TASK_EXCERPT_MAX],
    )

    # 9. Return proposal to Jarvis (rationale text DOES return to caller —
    # event_payload is the PII-bounded version; tool return value is the
    # full Jarvis-facing payload)
    return {
        "status": "ok",
        "plan": plan,
        "rationale": rationale,
        "confidence": confidence,
        "model_used": model_used,
        "provider_used": provider_used,
        "is_empty_chain": len(plan) == 0,
    }


def _publish_propose_event(
    *,
    plan: list[str],
    confidence: float,
    rationale_length: int,
    model_used: str,
    provider_used: str,
    task_excerpt: str,
) -> None:
    """Defensively publish cognitive_skill_chain.proposed. Never blocks."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "cognitive_skill_chain.proposed",
            {
                "plan": plan,
                "step_count": len(plan),
                "is_empty_chain": len(plan) == 0,
                "confidence": confidence,
                "rationale_length": rationale_length,
                "model_used": model_used,
                "provider_used": provider_used,
                "task_excerpt": task_excerpt,
            },
        )
    except Exception as exc:
        logger.debug("propose_skill_chain: event publish failed: %s", exc)


PROPOSE_SKILL_CHAIN_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "propose_skill_chain",
            "description": (
                "Foreslå en ordnet kæde af 2-5 skills til at løse en given "
                "opgave. Bruger cheap-lane LLM med fuldt skill-katalog "
                "(~50 skills) til at vælge meningsfulde sekvenser. "
                "Returnér struktureret forslag: {plan, rationale, "
                "confidence (0-1), model_used}. Confidence er DIT filter — "
                "lav confidence betyder du bør justere kæden selv. "
                "Tom plan ([]) er legitimt resultat når ingen meningsfuld "
                "kæde findes. Forslag er IKKE autorisation — kald "
                "`skill_chain(plan=...)` for at eksekvere, eller "
                "`revise_skill_chain(...)` for at justere før eksekvering."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": (
                            "Klar beskrivelse af opgaven der skal løses. "
                            "Mindst 10 tegn."
                        ),
                    },
                },
                "required": ["task_description"],
            },
        },
    },
]

PROPOSE_SKILL_CHAIN_TOOL_HANDLERS: dict[str, Any] = {
    "propose_skill_chain": _exec_propose_skill_chain,
}


def _build_propose_prompt(
    *,
    task_description: str,
    catalog: list[dict[str, Any]],
) -> str:
    """Build the cheap-lane prompt. Compact — ~2-3k tokens for 50 skills."""
    catalog_lines = []
    for entry in catalog:
        name = str(entry.get("name") or "").strip()
        desc = str(entry.get("description") or "").strip()
        if not name:
            continue
        desc_compact = desc[:120].replace("\n", " ").strip()
        catalog_lines.append(f"- {name}: {desc_compact}")
    catalog_block = "\n".join(catalog_lines) if catalog_lines else "(katalog tomt)"

    return (
        "Du er en skill-planner. Givet en opgave-beskrivelse og et "
        "katalog af tilgængelige skills, foreslå en ordnet kæde af "
        f"{_MIN_PLAN_LEN}-{_MAX_PLAN_LEN} skills der løser opgaven.\n"
        "\n"
        "Returnér KUN valid JSON med præcis disse felter:\n"
        '  {"plan": [...], "rationale": "...", "confidence": 0.0-1.0}\n'
        "\n"
        f"- plan: liste af {_MIN_PLAN_LEN}-{_MAX_PLAN_LEN} skill-navne i "
        "eksekveringsrækkefølge. Hvis INGEN meningsfuld kæde findes "
        "(opgaven er for vag, eller én skill er nok), returnér [] (tom liste).\n"
        "- rationale: 1-2 sætninger om hvorfor kæden løser opgaven, "
        "eller hvorfor ingen kæde virker. Maks 600 tegn.\n"
        "- confidence: dit estimat af hvor godt kæden løser opgaven, "
        "i intervallet 0.0 til 1.0.\n"
        "\n"
        f"Opgave: {task_description}\n"
        "\n"
        "Katalog:\n"
        f"{catalog_block}\n"
    )


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)


def _extract_json_blob(text: str) -> str:
    """Tolerate markdown fences and prose around JSON."""
    text = text.strip()
    fence_match = _JSON_FENCE_RE.search(text)
    if fence_match:
        return fence_match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start:end + 1]
    return text


def _parse_propose_response(text: str) -> dict[str, Any]:
    """Parse cheap-lane response. Returns {status, plan, rationale, confidence}
    or {status: error, reason}."""
    raw = (text or "").strip()
    if not raw:
        return {"status": "error", "reason": "empty response"}

    blob = _extract_json_blob(raw)
    try:
        data = json.loads(blob)
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "status": "error",
            "reason": f"invalid JSON in cheap-lane response: {exc}",
        }

    if not isinstance(data, dict):
        return {"status": "error", "reason": "response is not a JSON object"}

    plan = data.get("plan")
    if not isinstance(plan, list):
        return {"status": "error", "reason": "plan must be a list"}
    if plan and not all(isinstance(s, str) and s.strip() for s in plan):
        return {"status": "error", "reason": "plan entries must be non-empty strings"}
    if plan and (len(plan) < _MIN_PLAN_LEN or len(plan) > _MAX_PLAN_LEN):
        return {
            "status": "error",
            "reason": f"plan length must be 0 (empty) or {_MIN_PLAN_LEN}-{_MAX_PLAN_LEN}",
        }

    confidence = data.get("confidence")
    try:
        confidence_f = float(confidence)
    except (TypeError, ValueError):
        return {"status": "error", "reason": "confidence must be numeric"}
    if not (0.0 <= confidence_f <= 1.0):
        return {"status": "error", "reason": "confidence must be in [0.0, 1.0]"}

    rationale = str(data.get("rationale") or "").strip()
    if not rationale:
        return {"status": "error", "reason": "rationale is required"}

    return {
        "status": "ok",
        "plan": [str(s).strip() for s in plan],
        "rationale": rationale[:_RATIONALE_MAX_CHARS],
        "confidence": confidence_f,
    }
