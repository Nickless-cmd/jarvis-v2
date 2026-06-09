"""Skill Gate Tool — pre-action gate for automatic skill suggestion + invocation.

Designed to be called at the START of any task. It:
1. Runs skill_suggest (semantic match) against the user's query
2. If match >= INVOKE_THRESHOLD: auto-invokes the best-matching skill + reads SKILL.md
3. Returns what skill matched, the score, and the instructions — or "no match"

This is the C-løsning: an actual tool that wraps the logic so I don't have to
*remember* to check skills — the tool does it for me.

THRESHOLDS — these are tuned by hand for the HF MiniLM-L6-v2 embedding
model used by skill_suggest. That model scores Danish/English blended
queries lower than an intuitive 0.5-0.8 range. After per-skill
multi-candidate max aggregation, legit matches land above 0.30 while
the observed noise floor tops out around 0.32. If you swap the embedding
model or matcher, retune.

  - INVOKE_THRESHOLD (0.30): below this, no skill is loaded.
  - AUTO_USE_THRESHOLD (0.45): above this, the skill's format is treated
    as the template for the response. Strong match.
  - Initial suggest threshold (0.20): one notch lower than INVOKE so the
    gate sees borderline matches and can report them as `low_match`.

Killable via runtime setting `skill_gate_enabled=False` in runtime.json.
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

# Tuned 2026-05-10 after rolling out per-skill multi-candidate max-aggregation
# in skill_engine_tools._suggest_skills_for_query. With the new matcher, all
# correct matches (DA + EN) score 0.36-0.60 while the noise floor maxes at
# 0.32, giving a clean separation at 0.30.
_INVOKE_THRESHOLD = 0.30       # ≥ 0.30 → invoke skill, read instructions
_AUTO_USE_THRESHOLD = 0.45     # ≥ 0.45 → use skill's format as output template


# ── Chain-candidate helpers (Lag #4 — added 2026-05-10) ───────────────


def _build_chain_candidates(suggestions: list[dict]) -> list[dict]:
    """Return top-3 (max) skills within 0.10 of top score.

    Empty list when:
    - No suggestions
    - Only 1 suggestion exists
    - Top score below 0.30 (weak match — chain doesn't help)
    - Only top-1 was within the 0.10 window
    """
    if not suggestions or len(suggestions) < 2:
        return []
    top_score = float(suggestions[0].get("score") or 0.0)
    if top_score < 0.30:
        return []
    candidates = [
        {"name": s["name"], "score": s["score"]}
        for s in suggestions[:3]
        if float(s.get("score") or 0.0) >= top_score - 0.10
    ]
    if len(candidates) < 2:
        return []
    return candidates


def _build_chain_hint(candidates: list[dict]) -> str:
    """Render human-readable chain suggestion from candidates."""
    if not candidates:
        return ""
    names = [c["name"] for c in candidates]
    plan_repr = ", ".join(f"'{n}'" for n in names)
    n = len(candidates)
    return (
        f"{n} skills matched closely (within 0.10 of top score). "
        f"Consider skill_chain(plan=[{plan_repr}]) "
        "if the task requires multiple steps."
    )


# ── Executor ───────────────────────────────────────────────────────────

def _exec_skill_gate(args: dict[str, Any]) -> dict[str, Any]:
    """Pre-action gate: match user query to installed skills, invoke if relevant.

    Call this at the START of any task that involves research, analysis,
    fact-checking, data processing, report writing, or structured output.
    """
    # Kill-switch: runtime setting `skill_gate_enabled=False` short-circuits
    # the gate to a cheap stub. Avoids embedding call + auto-invoke when
    # the gate is misbehaving or HF latency is biting. The tool stays in
    # the schema so the model can still call it; it just returns a no-op.
    try:
        from core.runtime.settings import load_settings
        if not load_settings().skill_gate_enabled:
            return {
                "status": "ok",
                "gate_result": "disabled",
                "note": "skill_gate is disabled in runtime settings — proceed with standard workflow.",
                "chain_candidates": [],
                "chain_hint": "",
            }
    except Exception:
        # Settings unavailable (very unlikely) — fail open and run gate.
        pass

    query = str(args.get("query") or "").strip()
    if not query:
        return {
            "status": "ok",
            "gate_result": "skip",
            "reason": "no query provided — gate bypassed",
            "note": "Provide a query to check for matching skills.",
            "chain_candidates": [],
            "chain_hint": "",
        }

    force_skill = str(args.get("skill") or "").strip()
    threshold = args.get("threshold", _INVOKE_THRESHOLD)
    if isinstance(threshold, (int, float)):
        threshold = float(threshold)
    else:
        threshold = _INVOKE_THRESHOLD

    # ── Context tag pre-filter (C2 — Skills meta-tags) ──────────────
    raw_context = args.get("context")
    context_tags: list[str] | None = None
    if raw_context:
        if isinstance(raw_context, str):
            context_tags = [t.strip() for t in raw_context.split(",") if t.strip()]
        elif isinstance(raw_context, list):
            context_tags = [str(t).strip() for t in raw_context if str(t).strip()]

    # ── Phase 1: Suggest ────────────────────────────────────────────
    # One notch below INVOKE_THRESHOLD so the gate can report `low_match`
    # and `suggestions` for borderline queries. Below this nothing useful
    # is happening and we'd rather skip the embedding cost.
    suggestions = _suggest_skills_for_query(
        query=query,
        threshold=0.20,
        max_results=_INTENT_MATCH_MAX_SUGGESTIONS,
        context_tags=context_tags,
    )

    # Lag #4: compute chain candidates from suggestions (always, all return paths)
    chain_candidates = _build_chain_candidates(suggestions)
    chain_hint = _build_chain_hint(chain_candidates)

    if not suggestions:
        return {
            "status": "ok",
            "gate_result": "no_match",
            "query": query,
            "reason": "no skills matched the query",
            "suggestions": [],
            "note": "No relevant skills found. Proceed with standard workflow.",
            "chain_candidates": chain_candidates,
            "chain_hint": chain_hint,
            "context_tags": context_tags,
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
            "chain_candidates": chain_candidates,
            "chain_hint": chain_hint,
            "context_tags": context_tags,
        }

    # ── Phase 3: Invoke ─────────────────────────────────────────────
    # Track usage (C4 — auto-learning)
    context_str = ",".join(context_tags) if context_tags else ""
    skill_engine.record_skill_usage(
        best_name,
        source="skill_gate",
        success=True,
        query=query,
        context_tags=context_str,
        score=best_score,
    )
    invoke_result = skill_engine.get_skill_instructions(best_name)
    if invoke_result.get("status") != "ok":
        return {
            "status": "error",
            "error": f"failed to load skill '{best_name}': {invoke_result.get('error', 'unknown')}",
            "chain_candidates": chain_candidates,
            "chain_hint": chain_hint,
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
        "context_tags": context_tags,
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

    # Lag #4: inject chain fields into invoked-result path
    result["chain_candidates"] = chain_candidates
    result["chain_hint"] = chain_hint
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
                "against all installed skills, and if a relevant skill is found "
                "(score ≥ 0.30), it auto-invokes it and loads its instructions into context. "
                "If score ≥ 0.45, it marks the skill's format as the template to follow. "
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
                    "context": {
                        "type": "string",
                        "description": (
                            "Optional context/domain filter: comma-separated tag names, "
                            "e.g. 'coding,research'. Only skills whose tags match "
                            "(case-insensitive) are considered. Narrower pool = "
                            "fewer false positives. Use when the task falls within "
                            "a known domain."
                        ),
                    },
                    "threshold": {
                        "type": "number",
                        "description": (
                            "Minimum match score to auto-invoke (0.0-1.0). "
                            "Default 0.30 after multi-candidate aggregation. "
                            "Raise for stricter matching."
                        ),
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
