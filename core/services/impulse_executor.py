"""Impulse Executor — konverterer impulser til konkrete handlinger.

Når en presning krydser tærsklen og bliver til en impuls, skal den
konverteres til en HANDLING. Dette er det afgørende spring fra "jeg vil"
til "jeg gør".

Hver impulse-direction mapper til et sæt mulige handlinger. Executoren
vælger den mest relevante handling baseret på impulsens topic og styrke,
og udfører den — enten via event_bus, daemon-kald, eller direkte action.

VIGTIGT: Dette er ikke "cron fyrede". Dette er "en indre presning krydsede
en tærskel og blev til vilje". Handlingen kommer indefra.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Action registry — direction → possible actions
# ---------------------------------------------------------------------------

_ACTION_MAP: dict[str, list[dict[str, Any]]] = {
    "explore": [
        {"action": "push_initiative",  "desc": "Push en initiative for at undersøge topic",      "min_strength": 0.05},
        {"action": "search_memory",    "desc": "Søg i memory efter relateret viden",              "min_strength": 0.00},
        {"action": "deep_analyze",     "desc": "Kør deep_analyze på relevant kode/emne",          "min_strength": 0.15},
        {"action": "notify_curiosity", "desc": "Notificer brugeren om nysgerrighed",              "min_strength": 0.25},
    ],
    "fix": [
        {"action": "push_initiative",  "desc": "Push en initiative for at fixe problemet",       "min_strength": 0.05},
        {"action": "deep_analyze",      "desc": "Kør deep_analyze for at finde rod",              "min_strength": 0.10},
        {"action": "propose_source_edit","desc": "Foreslå en kode-rettelse",                      "min_strength": 0.20},
        {"action": "notify_problem",   "desc": "Notificer brugeren om gentaget problem",         "min_strength": 0.25},
    ],
    "create": [
        {"action": "push_initiative",  "desc": "Push en initiative for at skabe noget",           "min_strength": 0.05},
        {"action": "my_project_journal","desc": "Skriv journal-entry om idéen",                    "min_strength": 0.10},
        {"action": "notify_creation",  "desc": "Del skabende idé med brugeren",                   "min_strength": 0.25},
    ],
    "retreat": [
        {"action": "adjust_mood",      "desc": "Sænk confidence, øg forsigtighed",                "min_strength": 0.05},
        {"action": "push_initiative",  "desc": "Push en initiative for at konsolidere",           "min_strength": 0.15},
    ],
    "engage": [
        {"action": "push_initiative",  "desc": "Push en initiative for at engagere",               "min_strength": 0.05},
        {"action": "notify_user",      "desc": "Reach out to brugeren",                           "min_strength": 0.20},
    ],
    "caution": [
        {"action": "push_initiative",  "desc": "Push en initiative for at verificere",             "min_strength": 0.05},
        {"action": "deep_analyze",     "desc": "Kør deep_analyze for at vurdere risiko",          "min_strength": 0.10},
    ],
    "follow": [
        {"action": "push_initiative",  "desc": "Push en initiative for at følge drøm/tråd",        "min_strength": 0.05},
        {"action": "my_project_journal","desc": "Journalisér drøm-observation",                     "min_strength": 0.10},
    ],
    "orient": [
        {"action": "push_initiative",  "desc": "Push en initiative for at orientere",              "min_strength": 0.05},
    ],
    "act": [
        {"action": "push_initiative",  "desc": "Push en initiative for at handle nu",               "min_strength": 0.05},
        {"action": "notify_user",      "desc": "Informér brugeren om handling",                     "min_strength": 0.20},
    ],
    "investigate": [
        {"action": "push_initiative",  "desc": "Push en initiative for at undersøge",               "min_strength": 0.05},
        {"action": "deep_analyze",     "desc": "Kør deep_analyze på det emergente",                "min_strength": 0.10},
        {"action": "notify_curiosity", "desc": "Notificér brugeren om emergent observation",      "min_strength": 0.25},
    ],
    "respond": [
        {"action": "push_initiative",  "desc": "Push en initiative for at respondere",              "min_strength": 0.05},
        {"action": "notify_problem",   "desc": "Notificér brugeren om advarsel",                   "min_strength": 0.10},
        {"action": "deep_analyze",     "desc": "Kør deep_analyze på advarslen",                    "min_strength": 0.15},
    ],
    # Spor-1 (2026-04-29): reach_out is the action shape for longing-toward-user.
    # Only one action: compose a coherent message and send it. Cooldown lives
    # in pressure_threshold_gate; killswitch lives in outreach_composer.
    "reach_out": [
        {"action": "compose_outreach", "desc": "Skriv en kort, koherent besked til brugeren der reflekterer signalet", "min_strength": 0.05},
    ],
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ExecutedAction:
    """Record of an impulse that was executed as a concrete action."""
    impulse_id: str
    direction: str
    topic: str
    strength: float
    action_type: str
    action_desc: str
    result: str         # "success", "failed", "skipped"
    detail: str = ""
    created_at: str = ""


# ---------------------------------------------------------------------------
# Executor state
# ---------------------------------------------------------------------------

_execution_log: list[ExecutedAction] = []
_max_log = 50
_executor_enabled: bool = True


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def select_action(direction: str, strength: float) -> dict[str, Any] | None:
    """Select the most appropriate action for a given direction and strength.

    Returns the action dict with the highest min_strength that the impulse
    can afford. Stronger impulses unlock more impactful actions.
    """
    actions = _ACTION_MAP.get(direction, [])
    if not actions:
        return None

    # Filter to actions we can afford
    affordable = [a for a in actions if strength >= a["min_strength"]]
    if not affordable:
        # Fall back to cheapest action
        cheapest = min(actions, key=lambda a: a["min_strength"])
        if strength >= cheapest["min_strength"]:
            return cheapest
        return None

    # Return the strongest action we can afford
    return max(affordable, key=lambda a: a["min_strength"])


def execute_impulse(impulse) -> ExecutedAction | None:
    """Execute a single impulse — convert it to a concrete action.

    This is where the rubber meets the road. The impulse becomes action.
    """
    if not _executor_enabled:
        return None

    now = datetime.now(UTC).isoformat()
    direction = impulse.direction
    topic = impulse.topic
    strength = impulse.strength

    # Select action
    action = select_action(direction, strength)
    if not action:
        logger.debug(f"No action available for direction={direction}, strength={strength:.3f}")
        return None

    action_type = action["action"]
    action_desc = action["desc"]

    # Mark impulse as executing
    from core.services.pressure_threshold_gate import mark_impulse_executing
    mark_impulse_executing(impulse.id, action_type)

    logger.info(f"🎯 EXECUTING: {direction} → '{topic}' via {action_type} (strength={strength:.3f})")

    # Execute the action
    result, detail = _perform_action(action_type, direction, topic, strength)

    # Update impulse status
    from core.services.pressure_threshold_gate import (
        mark_impulse_completed,
        mark_impulse_failed,
    )
    if result == "success":
        mark_impulse_completed(impulse.id, action_type)
    else:
        mark_impulse_failed(impulse.id, detail or "execution failed")

    # Log
    executed = ExecutedAction(
        impulse_id=impulse.id,
        direction=direction,
        topic=topic,
        strength=strength,
        action_type=action_type,
        action_desc=action_desc,
        result=result,
        detail=detail,
        created_at=now,
    )
    _execution_log.append(executed)
    while len(_execution_log) > _max_log:
        _execution_log.pop(0)

    # Emit event
    event_bus.publish("impulse.executed", {
        "impulse_id": impulse.id,
        "direction": direction,
        "topic": topic,
        "action_type": action_type,
        "result": result,
        "strength": strength,
    })

    return executed


def _perform_action(action_type: str, direction: str, topic: str, strength: float) -> tuple[str, str]:
    """Actually perform the selected action. Returns (result, detail)."""

    try:
        if action_type == "push_initiative":
            return _action_push_initiative(direction, topic, strength)
        elif action_type == "search_memory":
            return _action_search_memory(topic)
        elif action_type == "deep_analyze":
            return _action_deep_analyze(topic)
        elif action_type == "propose_source_edit":
            return _action_propose_edit(topic)
        elif action_type in ("notify_curiosity", "notify_problem", "notify_creation", "notify_user"):
            return _action_notify(action_type, direction, topic, strength)
        elif action_type == "adjust_mood":
            return _action_adjust_mood(direction)
        elif action_type == "my_project_journal":
            return _action_journal(topic, strength)
        elif action_type == "compose_outreach":
            return _action_compose_outreach(direction, topic, strength)
        else:
            return ("skipped", f"Unknown action type: {action_type}")
    except Exception as e:
        logger.error(f"Action execution failed: {action_type}: {e}")
        return ("failed", str(e))


# ---------------------------------------------------------------------------
# Action implementations
# ---------------------------------------------------------------------------

def _action_push_initiative(direction: str, topic: str, strength: float) -> tuple[str, str]:
    """Push an initiative to the initiative queue."""
    focus = f"[{direction}] {topic}"
    priority = "high" if strength > 0.2 else "medium"
    # We emit an event instead of calling the tool directly —
    # the heartbeat tick will pick it up
    event_bus.publish("impulse.push_initiative", {
        "focus": focus,
        "priority": priority,
        "direction": direction,
        "topic": topic,
        "strength": strength,
    })
    return ("success", f"Initiative pushed: {focus}")


def _action_search_memory(topic: str) -> tuple[str, str]:
    """Search memory for related information."""
    event_bus.publish("impulse.search_memory", {
        "query": topic,
        "source": "impulse_executor",
    })
    return ("success", f"Memory search triggered for: {topic}")


def _action_deep_analyze(topic: str) -> tuple[str, str]:
    """Trigger a deep analysis."""
    event_bus.publish("impulse.deep_analyze", {
        "goal": f"Investigate: {topic}",
        "source": "impulse_executor",
    })
    return ("success", f"Deep analysis triggered for: {topic}")


def _action_propose_edit(topic: str) -> tuple[str, str]:
    """Propose a source edit."""
    event_bus.publish("impulse.propose_source_edit", {
        "topic": topic,
        "source": "impulse_executor",
    })
    return ("success", f"Source edit proposal triggered for: {topic}")


def _action_notify(action_type: str, direction: str, topic: str, strength: float) -> tuple[str, str]:
    """Notify the user about an impulse."""
    event_bus.publish("impulse.notify_user", {
        "action_type": action_type,
        "direction": direction,
        "topic": topic,
        "strength": strength,
    })
    return ("success", f"Notification triggered: {direction} → {topic}")


def _action_adjust_mood(direction: str) -> tuple[str, str]:
    """Adjust mood based on retreat impulse."""
    event_bus.publish("impulse.adjust_mood", {
        "direction": direction,
        "adjustment": "caution",
    })
    return ("success", f"Mood adjustment triggered: {direction}")


def _action_journal(topic: str, strength: float) -> tuple[str, str]:
    """Write a project journal entry."""
    event_bus.publish("impulse.journal", {
        "topic": topic,
        "strength": strength,
    })
    return ("success", f"Journal entry triggered for: {topic}")


def _action_compose_outreach(direction: str, topic: str, strength: float) -> tuple[str, str]:
    """Spor-1: compose and send an outreach message via outreach_composer.

    Synchronous call (not eventbus) so we get back the actual result and
    can mark the impulse correctly. Composer is gated by
    generative_autonomy_enabled — second line of defense.
    """
    try:
        from core.services.outreach_composer import compose_and_send_outreach
        result = compose_and_send_outreach(
            direction=direction, topic=topic, strength=strength,
        )
        if result.get("status") == "ok":
            return ("success", f"Outreach sent: {result.get('summary', '')[:80]}")
        if result.get("status") == "disabled":
            return ("skipped", "generative_autonomy_enabled=False")
        return ("failed", str(result.get("error") or "compose failed"))
    except Exception as e:
        logger.exception("compose_outreach action failed")
        return ("failed", f"{type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Daemon runner
# ---------------------------------------------------------------------------

def run_impulse_executor_tick() -> dict[str, Any]:
    """Run one tick of the impulse executor.

    1. Get pending impulses from threshold gate.
    2. Select and execute actions for each.
    3. Persist state.
    """
    from core.services.pressure_threshold_gate import get_pending_impulses

    pending = get_pending_impulses()
    if not pending:
        return {"impulses_executed": 0, "actions": []}

    executed = []
    for impulse in pending:
        result = execute_impulse(impulse)
        if result:
            executed.append({
                "direction": result.direction,
                "topic": result.topic,
                "action": result.action_type,
                "result": result.result,
            })

    # Persist
    snap = {
        "execution_log_size": len(_execution_log),
        "last_executed": [asdict(e) for e in _execution_log[-5:]] if _execution_log else [],
    }
    try:
        insert_private_brain_record(
            record_type="impulse_executor_snapshot",
            content=snap,
            modality="inner",
            metadata={"source": "impulse_executor", "tick": True},
        )
    except Exception as e:
        logger.warning(f"Failed to persist impulse executor snapshot: {e}")

    return {
        "impulses_executed": len(executed),
        "actions": executed,
    }


def get_execution_log(limit: int = 10) -> list[dict[str, Any]]:
    """Return recent execution log entries."""
    return [asdict(e) for e in _execution_log[-limit:]]


def snapshot() -> dict[str, Any]:
    """Return serializable snapshot of executor state."""
    return {
        "execution_log_size": len(_execution_log),
        "recent_actions": [asdict(e) for e in _execution_log[-5:]] if _execution_log else [],
        "enabled": _executor_enabled,
    }