from __future__ import annotations

# Pattern-based action risk scorer. No LLM call — runs inside every tool
# invocation path so must be fast and deterministic.
#
# Weight scale:
#   1 = trivial    — read, status, search
#   2 = moderate   — workspace edits, scheduling, notifications
#   3 = significant — identity/memory writes, multi-step plans, budget changes
#   4 = critical   — irreversible, cascading, identity-core mutations

_WEIGHT_4_PATTERNS = [
    "irreversible", "permanent", "delete all", "wipe", "destroy",
    "overwrite identity", "reset soul", "clear memory", "drop table",
]

_WEIGHT_3_PATTERNS = [
    "identity", "soul", "self-model", "memory rewrite", "memory-rewrite",
    "core prompt", "budget", "wallet", "payment", "credentials",
    "system prompt", "role definition", "promote memory",
    "autonomy proposal", "proposal",
]

_WEIGHT_1_PATTERNS = [
    "read", "search", "find", "list", "status", "fetch", "get",
    "heartbeat", "check", "view", "show", "describe", "ping",
]

_WEIGHT_2_PATTERNS = [
    "edit", "write", "create", "schedule", "notify", "send",
    "update", "append", "commit", "post", "message",
]


def classify_decision_weight(action_description: str) -> dict[str, object]:
    """Score an action description on a 1–4 risk scale.

    Returns:
        {"weight": int, "label": str, "reason": str}
    """
    text = action_description.lower()

    for pattern in _WEIGHT_4_PATTERNS:
        if pattern in text:
            return {
                "weight": 4,
                "label": "critical",
                "reason": f"matches critical pattern: '{pattern}'",
            }

    for pattern in _WEIGHT_3_PATTERNS:
        if pattern in text:
            return {
                "weight": 3,
                "label": "significant",
                "reason": f"matches significant pattern: '{pattern}'",
            }

    for pattern in _WEIGHT_1_PATTERNS:
        if pattern in text:
            return {
                "weight": 1,
                "label": "trivial",
                "reason": f"matches trivial pattern: '{pattern}'",
            }

    for pattern in _WEIGHT_2_PATTERNS:
        if pattern in text:
            return {
                "weight": 2,
                "label": "moderate",
                "reason": f"matches moderate pattern: '{pattern}'",
            }

    return {
        "weight": 2,
        "label": "moderate",
        "reason": "no specific pattern matched — defaulting to moderate",
    }
