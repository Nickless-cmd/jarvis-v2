"""Role-model resolver — pick best-fit (provider, model) for a role + task.

Bridges the role-based council_models.json config and the task-aware
reasoning_classifier (R1). For each agent spawn:

1. Classify the goal text → tier (fast | reasoning | deep)
2. Look up role_models[role].tiers[tier] → (provider, model)
3. If no tier match, fall back to role_models[role].{provider, model}
4. If no role match, return ("", "") — caller falls to cheap_lane defaults

New council_models.json schema (backwards compatible):

  {
    "role_models": [
      {
        "role": "devils_advocate",
        "provider": "ollamafreeapi",     // legacy default
        "model": "mistral:latest",        // legacy default
        "tiers": {
          "fast":      {"provider": "ollamafreeapi", "model": "llama3.2:3b"},
          "reasoning": {"provider": "ollamafreeapi", "model": "mistral:latest"},
          "deep":      {"provider": "cloudflare",    "model": "@cf/meta/..."}
        }
      }
    ]
  }

Old configs without "tiers" still work — we just use the flat
provider/model regardless of tier. New configs get the upgrade.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _classify_goal_tier(goal: str) -> str:
    """Classify goal text → fast | reasoning | deep using R1 classifier."""
    if not goal or not goal.strip():
        return "fast"
    try:
        from core.services.reasoning_classifier import classify_reasoning_tier
        result = classify_reasoning_tier(goal)
        tier = str(result.get("tier") or "fast")
        if tier in ("fast", "reasoning", "deep"):
            return tier
    except Exception as exc:
        logger.debug("role_model_resolver: tier classify failed: %s", exc)
    return "fast"


def resolve_role_model(*, role: str, goal: str = "") -> dict[str, Any]:
    """Pick (provider, model) for this role and goal complexity.

    Returns:
        {
            "provider": str (may be empty if no config found),
            "model": str (may be empty if no config found),
            "tier": "fast" | "reasoning" | "deep",
            "source": "tier-match" | "role-default" | "no-config",
        }
    """
    tier = _classify_goal_tier(goal)
    try:
        from core.services.agent_runtime import _load_council_model_config
        role_models = _load_council_model_config() or []
    except Exception as exc:
        logger.debug("role_model_resolver: load config failed: %s", exc)
        role_models = []

    role_match = next(
        (m for m in role_models if str(m.get("role") or "") == str(role or "")),
        None,
    )
    if role_match is None:
        return {"provider": "", "model": "", "tier": tier, "source": "no-config"}

    tiers = role_match.get("tiers") or {}
    if isinstance(tiers, dict):
        tier_entry = tiers.get(tier) or {}
        if isinstance(tier_entry, dict):
            tp = str(tier_entry.get("provider") or "").strip()
            tm = str(tier_entry.get("model") or "").strip()
            if tp and tm:
                return {"provider": tp, "model": tm, "tier": tier, "source": "tier-match"}

    # Fallback: legacy flat config
    fp = str(role_match.get("provider") or "").strip()
    fm = str(role_match.get("model") or "").strip()
    return {"provider": fp, "model": fm, "tier": tier, "source": "role-default"}
