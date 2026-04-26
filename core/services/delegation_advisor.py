"""Delegation advisor — inline vs which subagent role.

Builds Jarvis' delegation instinct. Given a task description, returns
"do it inline" or "delegate to role X" with a one-line reason. Uses a
small set of pattern→role rules drawn from how Claude Code's harness
makes the same call:

- "find / explore / search across" → researcher (protect main context)
- "plan / design / architecture for" → planner (separate thinking lane)
- "review / critique / audit" → critic
- "synthesize / summarize / merge" → synthesizer
- "execute / run / apply" + multi-step → executor
- "watch / monitor / wait for" → watcher (long-lived, persistent)
- short / single-action / interactive → inline

Verdict is advisory; the model decides what to do with it. Score (0-100)
is confidence that delegation is the right call.
"""
from __future__ import annotations

import re
from typing import Any

# Pattern → (role, weight, reason fragment)
_PATTERNS: list[tuple[re.Pattern[str], str, int, str]] = [
    (re.compile(r"\b(find|search|locate|explore|map|catalog|spor|leder)\b.*\b(across|all|every|whole|entire|everywhere|alle|hver|tværs|kodebasen|hele|repoet|projektet)\b", re.I), "researcher", 35, "broad search across many files"),
    (re.compile(r"\b(audit|inventory|survey|catalog|kortlæg|undersøg)\b", re.I), "researcher", 25, "discovery/inventory work"),
    (re.compile(r"\b(plan|design|architecture|blueprint|approach|planlæg|design|skitse)\b", re.I), "planner", 30, "needs planning before action"),
    (re.compile(r"\b(strategy|roadmap|sequencing)\b", re.I), "planner", 25, "strategic sequencing"),
    (re.compile(r"\b(review|critique|critic|audit|second opinion|sanity[- ]check|gennemgå|kritiser)\b", re.I), "critic", 35, "needs independent perspective"),
    (re.compile(r"\b(synthesize|merge|consolidate|combine|unify|opsummer|saml|sammensæt)\b", re.I), "synthesizer", 30, "combining multiple inputs"),
    (re.compile(r"\b(execute|carry out|apply|run|perform).+\b(steps|sequence|plan)\b", re.I), "executor", 25, "multi-step execution"),
    (re.compile(r"\b(watch|monitor|wait for|alert when|notify when|hold øje|overvåg)\b", re.I), "watcher", 35, "long-lived observation"),
    (re.compile(r"\b(verify|test|check|confirm)\b.{0,40}\b(everywhere|across|all)\b", re.I), "researcher", 25, "verification at scale"),
]

# Anti-patterns: things that suggest staying inline
_INLINE_PATTERNS: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"^\s*\S{1,40}\s*$"), 30, "very short input — likely interactive"),
    (re.compile(r"\b(read|show|cat|print|tell me|hvad er|vis mig)\b", re.I), 25, "single-shot read"),
    (re.compile(r"\?$"), 15, "direct question to you"),
    (re.compile(r"\b(hej|hi|hello|tak|thanks|godmorgen)\b", re.I), 30, "conversational opener"),
]


def advise(task: str) -> dict[str, Any]:
    text = (task or "").strip()
    if not text:
        return {
            "status": "ok",
            "verdict": "inline",
            "score": 0,
            "reason": "empty task",
            "role_suggestion": None,
        }

    role_scores: dict[str, int] = {}
    role_reasons: dict[str, list[str]] = {}
    for pat, role, weight, frag in _PATTERNS:
        if pat.search(text):
            role_scores[role] = role_scores.get(role, 0) + weight
            role_reasons.setdefault(role, []).append(frag)

    inline_score = 0
    inline_reasons: list[str] = []
    for pat, weight, frag in _INLINE_PATTERNS:
        if pat.search(text):
            inline_score += weight
            inline_reasons.append(frag)

    # Long input is itself a delegation signal — model has more to think
    # about, easier to lose context.
    if len(text) > 400:
        role_scores["planner"] = role_scores.get("planner", 0) + 10
        role_reasons.setdefault("planner", []).append("long task description")
    if text.count("\n") >= 4:
        role_scores["planner"] = role_scores.get("planner", 0) + 10
        role_reasons.setdefault("planner", []).append("multi-line spec")

    if not role_scores:
        return {
            "status": "ok",
            "verdict": "inline",
            "score": min(100, inline_score) if inline_score else 0,
            "reason": "; ".join(inline_reasons) or "no delegation signal — handle inline",
            "role_suggestion": None,
        }

    best_role, best_role_score = max(role_scores.items(), key=lambda kv: kv[1])
    delegate_score = max(0, best_role_score - inline_score)

    if delegate_score < 20:
        return {
            "status": "ok",
            "verdict": "inline",
            "score": min(100, max(20, inline_score - delegate_score + 20)),
            "reason": f"weak delegation signal ({best_role} {best_role_score} vs inline {inline_score})",
            "role_suggestion": best_role,
        }

    return {
        "status": "ok",
        "verdict": "delegate",
        "role_suggestion": best_role,
        "score": min(100, delegate_score + 30),
        "reason": "; ".join(role_reasons.get(best_role, [])),
        "alt_roles": sorted(
            ({"role": r, "score": s} for r, s in role_scores.items() if r != best_role),
            key=lambda x: x["score"], reverse=True,
        )[:2],
    }


def _exec_delegation_advisor(args: dict[str, Any]) -> dict[str, Any]:
    return advise(str(args.get("task") or ""))


DELEGATION_ADVISOR_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "delegation_advisor",
            "description": (
                "Get a recommendation: do this inline, or spawn a subagent "
                "(and which role)? Useful before tackling a long or open-ended "
                "task. Returns {verdict: inline|delegate, role_suggestion, "
                "reason, score}. Advisory — you still decide."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Task description (the user request or your own goal)."},
                },
                "required": ["task"],
            },
        },
    },
]
