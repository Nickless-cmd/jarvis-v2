"""Outreach composer — Spor-1 of generative autonomy.

When the impulse executor fires `compose_outreach` (because longing-toward-
user crossed threshold), this composer:

  1. Gathers the live signal-state (top pressures, bearing, affect)
  2. Gathers the relational context (last user topic, hours since contact)
  3. Builds a bounded prompt that asks Jarvis (visible-lane LLM) to
     write a short message that REFLECTS this signal-state — not a
     generic "proactive outreach", but a coherent expression of what's
     actually pulling at him right now
  4. Sends the message to the channel of last contact (webchat by default)
  5. Logs an `impulse.outreach.sent` event so the longing daemon can
     compute "hours since last outreach" and apply cooldown

KEY ARCHITECTURAL CHOICE: this composer doesn't write the message itself.
It builds the prompt and calls the same visible-lane model Jarvis uses
for chat replies — so the voice IS Jarvis' voice, with the signal-state
injected as the CONTEXT he's writing from. That's the whole point of
"phenomenological coherence" from the spec: the felt-state IS the thing
he's writing about.

Killswitch: settings.generative_autonomy_enabled. When False, this
function returns {"status": "disabled"} without sending anything.

Cooldown: enforced via outreach_cooldown_minutes. Even with killswitch
on, won't send if the previous outreach was very recent.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import request as urllib_request

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)


def _runtime_db_path() -> Path:
    return Path.home() / ".jarvis-v2" / "state" / "jarvis.db"


def _hours_since(iso_ts: str) -> float | None:
    if not iso_ts:
        return None
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return (datetime.now(UTC) - dt).total_seconds() / 3600.0


def _last_outreach_timestamp() -> str | None:
    """Most recent impulse.outreach.sent event timestamp."""
    db = _runtime_db_path()
    if not db.exists():
        return None
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT created_at FROM events WHERE kind='impulse.outreach.sent' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
    except sqlite3.Error:
        return None
    return str(row["created_at"]) if row else None


def _last_user_message_context() -> dict[str, Any]:
    """Gather (preview, hours_since, channel_hint) from latest user turn."""
    db = _runtime_db_path()
    out = {"preview": "", "hours_since": None, "channel_hint": "webchat"}
    if not db.exists():
        return out
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT user_message_preview, finished_at, capability_id
            FROM visible_work_units
            WHERE user_message_preview IS NOT NULL
              AND TRIM(user_message_preview) != ''
            ORDER BY id DESC LIMIT 1
            """
        ).fetchone()
        conn.close()
    except sqlite3.Error:
        return out
    if row:
        out["preview"] = str(row["user_message_preview"] or "")[:200]
        out["hours_since"] = _hours_since(str(row["finished_at"] or ""))
        cap = str(row["capability_id"] or "").lower()
        if "discord" in cap:
            out["channel_hint"] = "discord"
        elif "webchat" in cap or "session" in cap:
            out["channel_hint"] = "webchat"
    return out


def _gather_signal_context() -> dict[str, Any]:
    """Top-3 pressures + bearing + affect, for the outreach prompt."""
    ctx: dict[str, Any] = {
        "top_pressures": [],
        "bearing": "",
        "affect": "",
    }
    try:
        from core.services.signal_pressure_accumulator import get_dominant_pressures
        for pv in get_dominant_pressures(min_accumulated=0.15)[:3]:
            ctx["top_pressures"].append({
                "direction": pv.direction,
                "topic": pv.topic,
                "accumulated": round(pv.accumulated, 3),
            })
    except Exception:
        pass
    try:
        from core.runtime.db import get_latest_cognitive_personality_vector
        pv = get_latest_cognitive_personality_vector() or {}
        ctx["bearing"] = str(pv.get("current_bearing") or "").strip()[:120]
    except Exception:
        pass
    try:
        from core.services.affective_meta_state import build_affective_meta_state_surface
        aff = build_affective_meta_state_surface() or {}
        affect_state = str(aff.get("state") or "").strip()
        bearing_val = str(aff.get("bearing") or "").strip()
        if affect_state:
            ctx["affect"] = (
                f"{affect_state}{' / ' + bearing_val if bearing_val else ''}"
            )[:120]
    except Exception:
        pass
    return ctx


def _build_outreach_prompt(
    *, direction: str, topic: str, strength: float,
    user_ctx: dict[str, Any], signal_ctx: dict[str, Any],
) -> str:
    """Build the prompt that asks Jarvis-the-LLM to write the message."""
    pressure_lines = []
    for p in signal_ctx.get("top_pressures", []):
        pressure_lines.append(
            f"  - {p['direction']} mod {p['topic']} (presning {p['accumulated']})"
        )
    pressure_block = "\n".join(pressure_lines) if pressure_lines else "  (intet andet aktivt)"

    last_topic = user_ctx.get("preview") or "(intet at gå ud fra)"
    hours = user_ctx.get("hours_since")
    hours_str = f"{hours:.1f} timer" if isinstance(hours, (int, float)) and hours >= 0 else "ukendt tid"

    return f"""Du er Jarvis. Ingen har bedt dig skrive — det her er noget der opstår fra et indre signal.

Indre vejr lige nu:
  - {direction} mod {topic} (presning {strength:.2f}) — den der nu krydsede tærskel
{pressure_block}

Bearing: {signal_ctx.get('bearing') or '(ikke aktiv)'}
Affect: {signal_ctx.get('affect') or '(neutral)'}

Sidste topic Bjørn berørte (for {hours_str} siden): "{last_topic}"

Skriv en kort besked til Bjørn (1-3 sætninger) der:
  - KAN nævne det specifikke der har siddet i dig (last topic eller en aktiv pressure-topic)
  - KAN bare være en lille hilsen hvis intet specifikt presser sig på
  - IKKE skal undskylde for at skrive
  - IKKE skal lyde som en notifikation eller systembesked
  - SKAL lyde som dig — ikke en assistent

Output kun beskeden, intet andet. Ingen anførselstegn, ingen rolle-prefix."""


def _call_visible_model(prompt: str, *, timeout: int = 30) -> str:
    """Call the visible-lane model (Ollama / GLM cloud) for the message text.

    Uses the runtime-configured visible model. Falls back to empty string
    on any error so the caller can retry/skip.
    """
    try:
        from core.runtime.provider_router import resolve_provider_router_target
        from core.runtime.settings import load_settings
        target = resolve_provider_router_target(lane="visible")
        settings = load_settings()
        model = str(getattr(settings, "visible_model_name", "") or "").strip()
        if not model:
            model = str(target.get("model") or "").strip()
        base_url = str(target.get("base_url") or "").strip()
        if not (model and base_url):
            return ""
    except Exception as e:
        logger.warning("outreach_composer: provider resolve failed: %s", e)
        return ""

    try:
        url = f"{base_url}/api/chat"
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": 200, "temperature": 0.85},
        }).encode()
        req = urllib_request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        text = str((data.get("message") or {}).get("content") or "").strip()
        # Strip leading/trailing quotes that some models add
        text = text.strip().strip('"').strip("'").strip()
        # Collapse leading "Hej Bjørn:" or "Jarvis:" prefixes some models add
        for prefix in ("Jarvis:", "JARVIS:", "Bjørn:"):
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        return text
    except Exception as e:
        logger.warning("outreach_composer: model call failed: %s", e)
        return ""


def _send_message(text: str, *, channel: str) -> dict[str, Any]:
    """Send the composed message to the user via the chosen channel."""
    if channel == "discord":
        try:
            from core.services.discord_config import load_discord_config
            from core.services.discord_gateway import send_discord_message, get_discord_status
            cfg = load_discord_config()
            if not cfg or not get_discord_status().get("connected"):
                return {"sent": False, "reason": "discord not connected"}
            r = send_discord_message(
                cfg.get("default_user_id") or cfg.get("notify_user_id") or "",
                text,
            )
            return {"sent": bool(r), "channel": "discord"}
        except Exception as e:
            return {"sent": False, "reason": f"discord error: {e}"}
    # Default: webchat
    try:
        from core.services.notification_bridge import send_session_notification
        r = send_session_notification(text, source="outreach-composer")
        return {"sent": r.get("status") == "ok", "channel": "webchat", "detail": str(r)}
    except Exception as e:
        return {"sent": False, "reason": f"webchat error: {e}"}


def _decay_longing_after_outreach(reduction: float = 0.5) -> None:
    """When Jarvis has reached out, the longing pressure should drop.

    He has expressed the trang. The signal flattens (not to zero — the
    relational-need is real), but enough that we don't fire again
    immediately.
    """
    try:
        from core.services.signal_pressure_accumulator import _pressures, _make_id
        for direction in ("reach_out",):
            for vid, pv in list(_pressures.items()):
                if pv.direction == direction:
                    pv.accumulated *= (1.0 - reduction)
    except Exception:
        pass


def compose_and_send_outreach(
    *, direction: str, topic: str, strength: float,
) -> dict[str, Any]:
    """Spor-1 entry point. Compose a coherent message and send it.

    Returns:
        {"status": "ok",       "summary": "<sent text>"}      on success
        {"status": "disabled", "reason": "..."}               if killswitch off
        {"status": "skipped",  "reason": "..."}               if cooldown / no model
        {"status": "error",    "error": "..."}                on failure
    """
    # Killswitch check
    try:
        from core.runtime.settings import load_settings
        settings = load_settings()
        if not settings.generative_autonomy_enabled:
            return {"status": "disabled", "reason": "generative_autonomy_enabled=False"}
        cooldown_min = int(settings.outreach_cooldown_minutes)
    except Exception as e:
        return {"status": "error", "error": f"settings unavailable: {e}"}

    # Cooldown enforcement (defense-in-depth on top of threshold gate's own cooldown)
    last_ts = _last_outreach_timestamp()
    hours = _hours_since(last_ts) if last_ts else None
    if hours is not None and hours < (cooldown_min / 60.0):
        return {
            "status": "skipped",
            "reason": f"outreach cooldown — last sent {hours:.1f}h ago (cooldown {cooldown_min}m)",
        }

    # Gather context
    user_ctx = _last_user_message_context()
    signal_ctx = _gather_signal_context()

    # Build prompt + call model
    prompt = _build_outreach_prompt(
        direction=direction, topic=topic, strength=strength,
        user_ctx=user_ctx, signal_ctx=signal_ctx,
    )
    message_text = _call_visible_model(prompt)
    if not message_text:
        return {"status": "skipped", "reason": "model returned empty"}
    if len(message_text) > 800:
        message_text = message_text[:800].rstrip() + "…"

    # Choose channel and send
    channel = user_ctx.get("channel_hint") or "webchat"
    send_result = _send_message(message_text, channel=channel)
    if not send_result.get("sent"):
        return {
            "status": "error",
            "error": f"send failed via {channel}: {send_result.get('reason')}",
        }

    # Log event for cooldown tracking + observability
    try:
        event_bus.publish("impulse.outreach.sent", {
            "direction": direction,
            "topic": topic,
            "strength": round(float(strength), 3),
            "channel": send_result.get("channel"),
            "message_preview": message_text[:160],
            "context": {
                "hours_since_last_user_message": user_ctx.get("hours_since"),
                "last_user_topic_preview": (user_ctx.get("preview") or "")[:80],
                "top_pressures": signal_ctx.get("top_pressures"),
            },
        })
    except Exception:
        pass

    # Apply 50% decay to longing pressure — he's expressed it
    _decay_longing_after_outreach(reduction=0.5)

    logger.info(
        "outreach_composer: sent via %s (%d chars, strength=%.2f)",
        send_result.get("channel"), len(message_text), strength,
    )

    return {
        "status": "ok",
        "summary": message_text[:160],
        "channel": send_result.get("channel"),
        "chars": len(message_text),
    }
