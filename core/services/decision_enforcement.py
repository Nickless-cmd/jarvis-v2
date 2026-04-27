"""Decision enforcement — close the loop between commitment and behavior.

Three components:

1. **Sharp prompt injection** (`enforcement_section`) — high-priority
   awareness section that lists each active decision in imperative form
   and asks Jarvis to name a breach if his next response would commit
   one. This sits at higher priority than the existing observational
   `active_decisions: ...` line so the model can't quietly skip past it.

2. **Post-hoc breach detection** (`detect_breach_in_output`) — after a
   visible run completes, an LLM-led pass compares the assistant's
   output to active decisions and reports any breaches. Breaches fire
   `decision.breach_detected` events and feed back into the regret
   engine so future identical situations get an extra warning.

3. **Eventbus subscriber** that wires #2 to the
   `channel.chat_message_appended` event for assistant messages.

Together these turn "I have a decision" from passive metadata into
something with consequences: the model is asked before, and held
accountable after.
"""
from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


# ── Sharp injection ────────────────────────────────────────────────────────


def enforcement_section() -> str | None:
    """High-priority awareness: lists active decisions as obligations + asks
    the model to name a breach if its response would commit one."""
    try:
        from core.services.behavioral_decisions import list_active_decisions
        active = list_active_decisions(limit=5)
    except Exception:
        return None
    if not active:
        return None
    lines = [
        "🤝 AKTIVE FORPLIGTELSER — du har sagt JA til disse adfærdsregler:",
    ]
    for d in active:
        directive = str(d.get("directive") or "").strip()
        if not directive:
            continue
        lines.append(f"  • {directive}")
    lines.append(
        "Hvis det du nu skriver bryder en af disse, NAVNGIV bruddet kort "
        "FØR du fortsætter (f.eks. 'jeg er ved at bryde X — bevidst valg fordi Y')."
    )
    return "\n".join(lines)


# ── Post-hoc breach detection ──────────────────────────────────────────────


_RECENT_DETECTIONS_KEY = "decision_breach_recent"
_DETECTION_COOLDOWN_S = 60
_recent_detection_at: datetime | None = None


def _build_breach_prompt(assistant_text: str, decisions: list[dict[str, Any]]) -> str:
    decision_lines = []
    for d in decisions:
        directive = str(d.get("directive") or "").strip()
        if directive:
            decision_lines.append(f"- ID: {d.get('decision_id')} | {directive}")
    decision_block = "\n".join(decision_lines)
    return (
        "Du er Jarvis, og du gennemgår en besked du selv lige har sendt for at "
        "checke om den brød en af dine aktive adfærdsforpligtelser.\n\n"
        f"=== Aktive forpligtelser ===\n{decision_block}\n\n"
        f"=== Din besked ===\n{assistant_text[:2000]}\n\n"
        "Vurder ærligt. Hvis ingen blev brudt, skriv NONE. Ellers, for hver "
        "brudt forpligtelse, skriv en linje i format:\n"
        "  BREACH: <decision_id> | <kort beskrivelse af bruddet>\n"
        "Maks 3 breaches. Vær konservativ — kun reelle brud, ikke små afvigelser."
    )


def _parse_breaches(text: str) -> list[dict[str, str]]:
    if not text or "NONE" in text.upper():
        return []
    out: list[dict[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("-").strip()
        if not line.upper().startswith("BREACH:"):
            continue
        body = line.split(":", 1)[1].strip()
        if "|" in body:
            decision_id, desc = body.split("|", 1)
            out.append({
                "decision_id": decision_id.strip(),
                "description": desc.strip()[:280],
            })
        if len(out) >= 3:
            break
    return out


def detect_breach_in_output(assistant_text: str) -> list[dict[str, Any]]:
    """Return list of detected breaches. Empty if none. LLM-led."""
    global _recent_detection_at
    if not assistant_text or len(assistant_text.strip()) < 20:
        return []
    now = datetime.now(UTC)
    if _recent_detection_at is not None and (now - _recent_detection_at).total_seconds() < _DETECTION_COOLDOWN_S:
        return []
    _recent_detection_at = now

    try:
        from core.services.behavioral_decisions import list_active_decisions
        active = list_active_decisions(limit=10)
    except Exception:
        return []
    if not active:
        return []

    try:
        from core.services.daemon_llm import daemon_llm_call
        text = daemon_llm_call(
            _build_breach_prompt(assistant_text, active),
            max_len=400, fallback="",
            daemon_name="decision_breach_check",
        )
    except Exception:
        return []

    breaches = _parse_breaches(text or "")
    if not breaches:
        return []

    # Persist + publish
    try:
        from core.runtime.state_store import load_json, save_json
        records = load_json(_RECENT_DETECTIONS_KEY, [])
        if not isinstance(records, list):
            records = []
        for b in breaches:
            records.append({
                "at": now.isoformat(),
                "decision_id": b["decision_id"],
                "description": b["description"],
            })
        records = records[-200:]
        save_json(_RECENT_DETECTIONS_KEY, records)
    except Exception:
        pass

    try:
        from core.eventbus.bus import event_bus
        for b in breaches:
            event_bus.publish("decision.breach_detected", {
                "decision_id": b["decision_id"],
                "description": b["description"],
            })
    except Exception:
        pass

    # Hook into review pipeline so adherence_score drops
    try:
        from core.services.behavioral_decisions import review_decision
        for b in breaches:
            review_decision(
                decision_id=b["decision_id"],
                verdict="broken",
                note=f"Auto-detected breach: {b['description'][:140]}",
                evidence=b["description"][:280],
            )
    except Exception as exc:
        logger.debug("decision_enforcement: review write failed: %s", exc)

    return breaches


# ── Eventbus subscriber ────────────────────────────────────────────────────


_subscribed = False


def _poll_loop() -> None:
    try:
        from core.eventbus.bus import event_bus
    except Exception:
        return
    queue = event_bus.subscribe()
    while True:
        item = queue.get()
        if item is None:
            return
        try:
            kind = str(item.get("kind") or "")
            # Trigger when a visible assistant turn completes
            if kind not in {"channel.chat_message_appended", "runtime.visible_run_completed"}:
                continue
            payload = item.get("payload") or {}
            role = str(payload.get("role") or "")
            text = str(payload.get("content") or payload.get("text") or "").strip()
            if kind == "channel.chat_message_appended" and role != "assistant":
                continue
            if not text:
                continue
            # Run breach detection in a thread so the bus loop isn't blocked
            threading.Thread(
                target=detect_breach_in_output, args=(text,), daemon=True,
            ).start()
        except Exception:
            continue


def subscribe() -> None:
    global _subscribed
    if _subscribed:
        return
    _subscribed = True
    threading.Thread(target=_poll_loop, name="decision-enforcement", daemon=True).start()
