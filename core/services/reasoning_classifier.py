"""Reasoning classifier — router that picks fast / reasoning / deep tier.

R1 of the reasoning-layer rollout. Does NOT replace the existing
classifiers (clarification, delegation, good_enough_gate, self_monitor) —
they have different temporal scopes and complementary signals. This
module composes their *pre-action* signals plus a small complexity
heuristic into one verdict the model (and runtime) can consult before
deciding how hard to think.

Tiers:
  - **fast**: direct answer / single-shot tool call, no over-thinking.
  - **reasoning**: ReAct-style multi-step with a verify-step (R2 will
    add the loop; for now this just *signals* that the model should
    slow down).
  - **deep**: spawn a council / sub-agent (R3 will wire this; for now
    it just signals the recommendation).

Trigger logic (additive points, highest tier wins):
  - clarification verdict ask_first → +30 reasoning
  - clarification verdict mildly_ambiguous → +15 reasoning
  - delegation verdict delegate → +25 reasoning, +15 deep if planner role
  - explicit risk markers (delete, migration, drop table, force-push,
    rm -rf, secrets, prod) → +40 deep
  - long message (>400 chars) → +15 reasoning
  - multi-step markers (numbered list, "først ... så ... derefter") → +20 reasoning
  - novel domain markers ("ny", "fra bunden", "design", "arkitektur") → +20 reasoning

Below threshold 25 → fast. 25-60 → reasoning. >60 → deep.

The verdict is *advisory*. The model still decides; the runtime can
also read it (R2 will use it to gate the verify-step).
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


_RISK_PATTERNS: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"\b(rm\s+-rf|drop\s+table|force[- ]push|--no-verify)\b", re.I), 50, "destructive command marker"),
    (re.compile(r"\b(delete|slet|fjern|drop|destroy|purge|wipe)\b.{0,30}\b(database|table|prod|production|alle|all)\b", re.I), 40, "destructive scope marker"),
    (re.compile(r"\b(migration|migrer|schema change|skema-ændring|breaking change)\b", re.I), 35, "migration / breaking change"),
    (re.compile(r"\b(secret|credential|api[- ]key|password|token)\b", re.I), 30, "secrets-handling"),
    (re.compile(r"\b(prod|production|live system|kritisk system)\b", re.I), 25, "production system"),
]

_NOVELTY_PATTERNS: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"\b(fra bunden|from scratch|greenfield|nyt design|brand new)\b", re.I), 25, "from-scratch work"),
    (re.compile(r"\b(arkitektur|architecture|design pattern|systemdesign)\b", re.I), 20, "architecture work"),
    (re.compile(r"\b(refaktor|refactor|rewrite|omskriv)\b", re.I), 15, "refactor"),
    (re.compile(r"\b(plan|roadmap|strategi|strategy|approach)\b", re.I), 12, "planning work"),
]

_MULTISTEP_PATTERNS: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"\b(først|so|derefter|bagefter|til sidst|first|then|after that|finally)\b.*\b(først|so|derefter|bagefter|til sidst|first|then|after that|finally)\b", re.I), 20, "ordered multi-step"),
    (re.compile(r"^\s*\d+[.)]\s", re.M), 15, "numbered list"),
    (re.compile(r"\bfase \d+|\bphase \d+|\btrin \d+|\bstep \d+", re.I), 18, "explicit phase/step"),
    (re.compile(r"\bog så\b.*\bog så\b", re.I), 12, "chained 'og så'"),
]


def _score_patterns(text: str, patterns: list[tuple[re.Pattern[str], int, str]]) -> tuple[int, list[str]]:
    score = 0
    hits: list[str] = []
    for pat, weight, label in patterns:
        if pat.search(text):
            score += weight
            hits.append(label)
    return score, hits


def classify_reasoning_tier(message: str, *, task_hint: str | None = None) -> dict[str, Any]:
    """Pick reasoning tier for a user message (or task description).

    Returns:
        {
            status: "ok",
            tier: "fast" | "reasoning" | "deep",
            score: int (0-100),
            signals: list[str],  # human-readable reasons
            recommendation: str,  # short prose for the model
            sub_scores: {clarification, delegation, risk, novelty, multistep},
        }
    """
    text = (message or "").strip()
    if task_hint:
        text = f"{text}\n{task_hint}".strip()
    if not text:
        return {
            "status": "ok",
            "tier": "fast",
            "score": 0,
            "signals": [],
            "recommendation": "Tomt input — fast path.",
            "sub_scores": {},
        }

    signals: list[str] = []
    reasoning_pts = 0
    deep_pts = 0

    # 1. Clarification (lazy import — module is cheap but isolation matters)
    clar_score = 0
    try:
        from core.services.clarification_classifier import score_message as _clar
        clar_result = _clar(text)
        verdict = str(clar_result.get("verdict", ""))
        clar_score = int(clar_result.get("score") or 0)
        if verdict == "ask_first":
            reasoning_pts += 30
            signals.append(f"ambiguity ask_first ({clar_score}/100)")
        elif verdict == "mildly_ambiguous":
            reasoning_pts += 15
            signals.append(f"ambiguity mildly ({clar_score}/100)")
    except Exception as e:
        logger.debug("clarification import failed: %s", e)

    # 2. Delegation
    deleg_score = 0
    deleg_role: str | None = None
    try:
        from core.services.delegation_advisor import advise as _advise
        deleg_result = _advise(text)
        deleg_score = int(deleg_result.get("score") or 0)
        deleg_role = deleg_result.get("role_suggestion")
        if deleg_result.get("verdict") == "delegate":
            reasoning_pts += 25
            signals.append(f"delegation suggested → {deleg_role}")
            if deleg_role in ("planner", "researcher"):
                deep_pts += 15
                signals.append(f"deep work role ({deleg_role})")
    except Exception as e:
        logger.debug("delegation import failed: %s", e)

    # 3. Risk markers (push toward deep)
    risk_pts, risk_hits = _score_patterns(text, _RISK_PATTERNS)
    if risk_pts > 0:
        deep_pts += risk_pts
        signals.extend(risk_hits)

    # 4. Novelty / architecture work (reasoning)
    novelty_pts, novelty_hits = _score_patterns(text, _NOVELTY_PATTERNS)
    if novelty_pts > 0:
        reasoning_pts += novelty_pts
        signals.extend(novelty_hits)

    # 5. Multi-step markers
    multi_pts, multi_hits = _score_patterns(text, _MULTISTEP_PATTERNS)
    if multi_pts > 0:
        reasoning_pts += multi_pts
        signals.extend(multi_hits)

    # 6. Length signal — long messages need reasoning
    if len(text) > 400:
        reasoning_pts += 15
        signals.append(f"long input ({len(text)} chars)")
    if text.count("\n") >= 8:
        reasoning_pts += 10
        signals.append(f"multi-line input ({text.count(chr(10))+1} lines)")

    # Composite scoring — deep wins outright if it has any momentum
    total = reasoning_pts + deep_pts
    if deep_pts >= 40:
        tier = "deep"
        recommendation = (
            "Højrisiko / novel domæne. Spawn et council (researcher + critic + "
            "planner) eller bed brugeren bekræfte før destruktive skridt."
        )
    elif deep_pts >= 20 and total >= 60:
        tier = "deep"
        recommendation = (
            "Sammensat opgave med risikomarkører. Brug deep reasoning — verify "
            "før hver action og dobbelt-check filer/funktioner findes."
        )
    elif total >= 25:
        tier = "reasoning"
        recommendation = (
            "Multi-step opgave. Tænk eksplicit i ReAct-stil: observe → think → "
            "verify → act. Brug verify_* tools før du rapporterer noget som "
            "gjort."
        )
    else:
        tier = "fast"
        recommendation = "Direkte svar / enkelt tool-call. Ingen over-tænkning."

    score = max(0, min(100, total))

    return {
        "status": "ok",
        "tier": tier,
        "score": score,
        "signals": signals,
        "recommendation": recommendation,
        "sub_scores": {
            "clarification": clar_score,
            "delegation": deleg_score,
            "delegation_role": deleg_role,
            "risk": risk_pts,
            "novelty": novelty_pts,
            "multistep": multi_pts,
            "reasoning_pts": reasoning_pts,
            "deep_pts": deep_pts,
        },
    }


def reasoning_tier_section(message: str) -> str | None:
    """Format tier verdict as a prompt-awareness section. None for fast tier
    (no point adding noise when no extra reasoning is needed)."""
    result = classify_reasoning_tier(message)
    tier = str(result.get("tier"))
    if tier == "fast":
        return None
    score = result.get("score", 0)
    signals = result.get("signals") or []
    sig_text = "; ".join(signals[:4]) if signals else "ingen specifik markør"
    return (
        f"🧠 Anbefalet reasoning-tier: **{tier}** (score {score}/100). "
        f"Signaler: {sig_text}.\n"
        f"{result.get('recommendation', '')}"
    )


def _exec_reasoning_classify(args: dict[str, Any]) -> dict[str, Any]:
    return classify_reasoning_tier(
        str(args.get("message") or ""),
        task_hint=args.get("task_hint"),
    )


REASONING_CLASSIFIER_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "reasoning_classify",
            "description": (
                "Pick the reasoning tier (fast / reasoning / deep) for a "
                "message or task. Composes ambiguity, delegation, risk, "
                "novelty and multi-step signals into one verdict with a "
                "trace. Advisory — you still decide how to act, but the "
                "verdict tells you whether to slow down, plan explicitly, "
                "or spawn a council."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "task_hint": {
                        "type": "string",
                        "description": "Optional extra context (e.g. your own goal phrased as a task).",
                    },
                },
                "required": ["message"],
            },
        },
    },
]
