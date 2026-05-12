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
    """Tool handler for propose_skill_chain (skeleton — Task 2 of plan)."""
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

    # Remaining steps wired in Task 3
    return {"status": "error", "reason": "implementation incomplete"}


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
