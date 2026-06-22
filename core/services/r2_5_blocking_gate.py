"""R2.5 — conditional blocking gate.

R2 (verification_gate) is observational. R2.5 promotes it to advisory-
plus-blocking when telemetry shows the model is actively ignoring
warnings AND we're in a deep-reasoning context where unverified
mutations carry high risk.

This module provides one function:

    should_block_for_verification(reasoning_tier) -> dict | None

It returns a block-instruction dict when ALL of the following hold:

1. Reasoning tier is 'deep' or 'reasoning' (not 'fast')
2. There are >= _MIN_FAILED_VERIFIES failed verifications in the last
   10 minutes, OR >= _MIN_UNVERIFIED unverified mutations
3. The R2 heed_rate over the last 24h is below _HEED_RATE_THRESHOLD
   (i.e. the model has a track record of ignoring warnings)
4. We haven't blocked too recently (don't ping-pong; cooldown)

The gate is INJECTED INTO THE PROMPT as a high-priority awareness
section saying: "Du bliver bedt om at stoppe og verificere. Kør
verify_* før du fortsætter." This relies on the model honoring the
instruction. Without further signal that needs more enforcement,
soft blocking is enough — when telemetry shows even this is ignored,
we can escalate to actual output gating (refuse to stream further
deltas until a verify_* completes), but that's a separate decision.

Returns None when no block is needed.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


_MIN_FAILED_VERIFIES = 1

# Tier-aware unverified-mutation thresholds (2026-05-14, Phase 1 retune).
# Uses unverified_effective (mutations with NO readback of any kind —
# strict verify_* OR light readback like read_file/db_query/process_list).
# Numbers reflect risk-proportional caution: deep work blocks fast,
# fast chat tolerates more before nagging.
_UNVERIFIED_THRESHOLD_BY_TIER: dict[str, int] = {
    "deep": 3,
    "reasoning": 5,
    "fast": 8,
}

_HEED_RATE_THRESHOLD = 0.4
_BLOCK_COOLDOWN_SECONDS = 60


def _live_thresholds() -> tuple[dict[str, int], float]:
    """Settings-backed tærskler (config uden deploy, 2026-06-22); modul-konstanterne
    ovenfor er fallback hvis settings ikke kan læses."""
    try:
        from core.runtime.settings import load_settings
        s = load_settings()
        tiers = {
            "deep": int(s.r2_5_unverified_threshold_deep),
            "reasoning": int(s.r2_5_unverified_threshold_reasoning),
            "fast": int(s.r2_5_unverified_threshold_fast),
        }
        return tiers, float(s.r2_5_heed_rate_threshold)
    except Exception:
        return dict(_UNVERIFIED_THRESHOLD_BY_TIER), _HEED_RATE_THRESHOLD


_last_block_at: datetime | None = None


def _heed_rate_24h() -> float | None:
    try:
        from core.services.verification_gate_telemetry import get_telemetry_summary
        s = get_telemetry_summary(hours=24)
        if s.get("surfaced_total", 0) < 5:
            # Not enough data — give the model the benefit of the doubt
            return None
        return s.get("heed_rate")
    except Exception:
        return None


def should_block_for_verification(*, reasoning_tier: str) -> dict[str, Any] | None:
    """Decide whether to inject a 'stop and look back' block.

    Returns a dict {reason, suggestions, urgency} when blocking is warranted,
    else None. Tier-aware: deep work blocks fast, fast chat tolerates more
    before nagging. Uses unverified_effective (Phase 1) so a readback —
    not just verify_* — counts as resolving the block.
    """
    global _last_block_at
    tier = (reasoning_tier or "").strip().lower()
    if tier not in _UNVERIFIED_THRESHOLD_BY_TIER:
        tier = "fast"

    # Cooldown — don't re-block within a minute of the last block
    now = datetime.now(UTC)
    if _last_block_at is not None and (now - _last_block_at).total_seconds() < _BLOCK_COOLDOWN_SECONDS:
        return None

    try:
        from core.services.verification_gate import evaluate_verification_gate
        gate = evaluate_verification_gate()
    except Exception:
        return None

    failed = int(gate.get("failed_verify_count") or 0)
    # Use unverified_effective if available (post-Phase-1); fall back to
    # unverified_count (back-compat strict) when running against an
    # older verification_gate.
    unverified_effective = int(
        gate.get("unverified_effective", gate.get("unverified_count")) or 0
    )
    _tier_thresholds, _heed_threshold = _live_thresholds()
    threshold = _tier_thresholds[tier]
    if failed < _MIN_FAILED_VERIFIES and unverified_effective < threshold:
        return None

    heed_rate = _heed_rate_24h()
    # Only escalate to block when we have evidence the model ignores warnings.
    # If heed_rate is None (insufficient data) we don't block — soft R2 surfaces.
    if heed_rate is None or heed_rate >= _heed_threshold:
        return None

    suggestions = list(gate.get("suggestions") or [])
    urgency = "high" if failed > 0 else "medium"

    # Mark cooldown
    _last_block_at = now

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("r2_5_gate.blocked", {
            "tier": tier,
            "failed_verify_count": failed,
            "unverified_effective": unverified_effective,
            "threshold": threshold,
            "heed_rate": heed_rate,
            "urgency": urgency,
        })
    except Exception:
        pass

    # NB (2026-06-22): den tidligere observe()-spore her er FJERNET — R2.5 routes nu
    # gennem den konsoliderede graderede proactivity_gate via central().decide (fuld
    # catch+flag+notify+trace). Dobbelt-trace ikke nødvendig.

    # Phase 2.4 finding (2026-05-14): R2.5 itself sits at 17% heed-rate
    # because the previous block message ended with "STOP og kig tilbage"
    # — passive imperative without a concrete next move. Same anti-pattern
    # we fixed in replan-signal and inline verify-hints today: surface
    # the action shape, not just the alert.
    #
    # Build a concrete one-line action prompt from the top unverified
    # tool. The mutation-tool ↔ verify-tool mapping mirrors
    # _suggested_verify in verification_gate.py.
    by_tool = gate.get("by_tool") or {}
    top_tool = next(iter(sorted(by_tool.items(), key=lambda kv: -kv[1])), None)
    action_line = ""
    if top_tool:
        mut_name, mut_count = top_tool
        if mut_name in ("write_file", "edit_file", "publish_file", "stage_edit_file"):
            action_line = (
                f"Næste move: read_file den fil du senest skrev til, "
                "eller verify_file_contains(path='...', expected='...')."
            )
        elif mut_name in ("control_daemon", "restart_overdue_daemons"):
            action_line = (
                "Næste move: verify_service_active(service='...') eller "
                "process_list for at bekræfte at servicen kører."
            )
        elif mut_name == "propose_git_commit":
            action_line = (
                "Næste move: git_log eller bash 'git status' for at bekræfte "
                "commit'en landede."
            )
        elif mut_name == "memory_upsert_section":
            action_line = (
                "Næste move: read_file MEMORY.md eller search_memory for at "
                "bekræfte sektionen blev skrevet i den form du ville."
            )
        elif mut_name == "send_discord_dm":
            action_line = "Næste move: tjek om brugeren har svaret."
        elif mut_name in ("bash", "bash_session_run"):
            action_line = (
                "Næste move: kør en anden bash der inspicerer udfaldet "
                "(systemctl status / ps / ls / git status / curl ...) — "
                "eller read_file det output du forventer ændredes."
            )
        else:
            action_line = (
                "Næste move: read_file / db_query / process_list / git_log "
                "på det du lige ændrede."
            )

    return {
        "reason": (
            f"R2.5 conditional block (tier={tier}, threshold={threshold}): "
            f"{failed} fejlede verifies, {unverified_effective} mutation(er) "
            f"uden ÉT kig tilbage. 24t effective heed_rate="
            f"{int(heed_rate*100)}% under {int(_heed_threshold*100)}%-"
            f"grænsen.\n{action_line}"
        ),
        "suggestions": suggestions,
        "urgency": urgency,
        "tier": tier,
        "threshold": threshold,
        "unverified_effective": unverified_effective,
        "action_line": action_line,
    }


def r2_5_block_section(reasoning_tier: str) -> str | None:
    """Render the block as a high-priority awareness section, or None."""
    block = should_block_for_verification(reasoning_tier=reasoning_tier)
    if not block:
        return None
    lines = ["R2.5 block (verifikation required):", block["reason"]]
    suggestions = block.get("suggestions") or []
    if suggestions:
        lines.append("Verifikations-kandidater:")
        for s in suggestions:
            lines.append(f"  {s}")
    return "\n".join(lines)


def build_r2_5_blocking_gate_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Added during 2026-05-13 coverage push (system_cartographer dark-edge
    closure). Reports module presence so the cartographer registers it as
    observed. Specific state-readers added as the module evolves.
    """
    return {
        "active": True,
        "mode": "r2_5_blocking_gate",
        "summary": "Module loaded; entry points available.",
        "authority": "derived-read-only",
    }


def _emit_r2_5_blocking_gate_event(kind: str, payload: dict[str, object] | None = None) -> None:
    """Emit a scoped event — defensive, never blocks caller.
    Cartographer scans for event_bus.publish() text.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            f"r2_5_blocking_gate.{kind}",
            payload or {},
        )
    except Exception:
        pass

