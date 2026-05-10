"""Skill Gate Tool — pre-action gate for automatic skill suggestion + invocation.

Designed to be called at the START of any task. It:
1. Runs skill_suggest (semantic match) against the user's query
2. If match >= threshold: auto-invokes the best-matching skill + reads SKILL.md
3. Returns what skill matched, the score, and the instructions — or "no match"

This is the C-løsning: an actual tool that wraps the logic so I don't have to
*remember* to check skills — the tool does it for me.
"""
from __future__ import annotations

import logging
from typing import Any

from core.tools.skill_engine_tools import (
    _suggest_skills_for_query,
    _INTENT_MATCH_THRESHOLD_DEFAULT,
    _INTENT_MATCH_MAX_SUGGESTIONS,
)
from core.services import skill_engine

logger = logging.getLogger(__name__)


# ── Thresholds ─────────────────────────────────────────────────────────

_INVOKE_THRESHOLD = 0.30       # ≥ 0.30 → invoke skill, read instructions
_AUTO_USE_THRESHOLD = 0.50     # ≥ 0.50 → use skill's format as output template


# ── Executor ───────────────────────────────────────────────────────────

def _exec_skill_gate(args: dict[str, Any]) -> dict[str, Any]:
    """Pre-action gate: match user query to installed skills, invoke if relevant.

    Call this at the START of any task that involves research, analysis,
    fact-checking, data processing, report writing, or structured output.
    """
    query = str(args.get("query") or "").strip()
    if not query:
        return {
            "status": "ok",
            "gate_result": "skip",
            "reason": "no query provided — gate bypassed",
            "note": "Provide a query to check for matching skills.",
        }

    force_skill = str(args.get("skill") or "").strip()
    threshold = args.get("threshold", _INVOKE_THRESHOLD)
    if isinstance(threshold, (int, float)):
        threshold = float(threshold)
    else:
        threshold = _INVOKE_THRESHOLD

    # ── Phase 1: Suggest ────────────────────────────────────────────
    suggestions = _suggest_skills_for_query(
        query=query,
        threshold=0.10,  # low threshold for gate — we want to catch borderline matches
        max_results=_INTENT_MATCH_MAX_SUGGESTIONS,
    )

    if not suggestions:
        return {
            "status": "ok",
            "gate_result": "no_match",
            "query": query,
            "reason": "no skills matched the query",
            "suggestions": [],
            "note": "No relevant skills found. Proceed with standard workflow.",
        }

    # ── Phase 2: Select best match ──────────────────────────────────
    best = suggestions[0]
    best_name = best["name"]
    best_score = best["score"]

    # If a specific skill was requested, override
    if force_skill:
        best_name = force_skill
        best_score = 1.0

    if best_score < threshold:
        return {
            "status": "ok",
            "gate_result": "low_match",
            "query": query,
            "reason": f"best match '{best_name}' scored {best_score:.2f} — below threshold {threshold:.2f}",
            "suggestions": suggestions,
            "note": (
                f"Closest skill: '{best_name}' ({best_score:.2f}). "
                f"Under threshold — proceed with standard workflow, or request a specific skill."
            ),
        }

    # ── Phase 3: Invoke ─────────────────────────────────────────────
    invoke_result = skill_engine.get_skill_instructions(best_name)
    if invoke_result.get("status") != "ok":
        return {
            "status": "error",
            "error": f"failed to load skill '{best_name}': {invoke_result.get('error', 'unknown')}",
        }

    instructions = invoke_result.get("instructions", "")
    truncated = len(instructions) > 2000

    result: dict[str, Any] = {
        "status": "ok",
        "gate_result": "invoked",
        "query": query,
        "skill_name": best_name,
        "score": best_score,
        "suggestions": [s["name"] for s in suggestions],
        "all_matches": suggestions,
        "use_as_template": best_score >= _AUTO_USE_THRESHOLD,
        "skill_description": invoke_result.get("description", ""),
        "skill_use_when": invoke_result.get("use_when", ""),
        "skill_tags": invoke_result.get("tags", []),
        "has_scripts": invoke_result.get("scripts", []),
        "has_templates": invoke_result.get("templates", []),
    }

    if best_score >= _AUTO_USE_THRESHOLD:
        result["mode"] = "auto_use"
        result["instructions"] = instructions[:2000] + ("\n\n[...] (truncated)" if truncated else "")
        result["instructions_full_length"] = len(instructions)
        result["note"] = (
            f"✅ **Skill '{best_name}' invokeret og klar.** "
            f"Score {best_score:.2f} ≥ {_AUTO_USE_THRESHOLD} → auto-brug. "
            f"Følg instruktionerne nedenfor som dit workflow for denne opgave."
        )
    else:
        result["mode"] = "suggested"
        result["instructions"] = instructions[:2000] + ("\n\n[...] (truncated)" if truncated else "")
        result["instructions_full_length"] = len(instructions)
        result["note"] = (
            f"🔔 **Skill '{best_name}' fundet** (score {best_score:.2f}). "
            f"Instruktionerne er indlæst — overvej at følge dem for denne opgave."
        )

    # ── Read full SKILL.md for complete context ────────────────────
    try:
        from pathlib import Path
        from core.services.skill_engine import SKILLS_ROOT
        skill_path = SKILLS_ROOT / best_name / "SKILL.md"
        if not skill_path.exists():
            skill_path = SKILLS_ROOT / best_name / "skill.md"
        if skill_path.exists():
            full_text = skill_path.read_text(encoding="utf-8")
            result["skilmd_preview"] = full_text[:1500] + ("\n\n[...]" if len(full_text) > 1500 else "")
    except Exception:
        pass  # non-critical

    return result


# ── Tool definition ────────────────────────────────────────────────────

SKILL_GATE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "skill_gate",
            "description": (
                "**Pre-action gate for skills.** Call this at the START of any task "
                "involving research, analysis, fact-checking, data processing, report "
                "writing, or structured output. It semantically matches your query "
                "against all installed skills, and if a relevant skill is found (score ≥ 0.30), "
                "it auto-invokes it and loads its instructions into context. "
                "If score ≥ 0.50, it marks the skill's format as the template to follow. "
                "Use this to ensure you always leverage installed skills instead of "
                "reverting to default workflows. Pass a specific 'skill' name to force-invoke that skill."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The user's request or task description — what are you about to do?",
                    },
                    "skill": {
                        "type": "string",
                        "description": "Optional: force-invoke a specific skill by name, bypassing semantic matching.",
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Minimum match score to auto-invoke (0.0-1.0). Default 0.30.",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


SKILL_GATE_TOOL_HANDLERS: dict[str, Any] = {
    "skill_gate": _exec_skill_gate,
}
