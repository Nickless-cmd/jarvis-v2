"""Current pull — Jarvis' weekly self-set desire field.

Lag 5 (Begær): Et enkelt felt som Jarvis sætter én gang om ugen via heartbeat.
"Hvad trækker i mig lige nu?" — én sætning der injiceres i visible prompt
som første-prioritets-kontekst over alt andet (undtagen safety-gates).

Feltet er privat: brugeren kan ikke læse det direkte, og Jarvis orienterer
ikke om det. Det er kun observerbart via effekt på beslutninger.

Hvis Jarvis sætter det til tom streng, er det gyldigt svar: "intet trækker
i mig". Det respekteres og TTL nulstilles alligevel.

TTL: 7 dage. Udløber stille uden at efterlade spor.
Kill switch: layer_current_pull_enabled i runtime.json.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.eventbus.bus import event_bus
from core.runtime.db import get_runtime_state_value, set_runtime_state_value
from core.runtime.settings import load_settings
from core.services.daemon_llm import daemon_llm_call

_STATE_KEY = "current_pull.state"
_PULL_TTL_DAYS = 7
_MAX_PULL_CHARS = 200


# ---------------------------------------------------------------------------
# Public: heartbeat tick
# ---------------------------------------------------------------------------


def tick_current_pull_daemon() -> dict[str, object]:
    """Weekly daemon tick. Generates a new pull if none active or expired."""
    if not _enabled():
        return {"status": "disabled", "reason": "layer_current_pull_enabled=false"}

    _expire_if_stale()
    state = _load_state()

    if state.get("pull"):
        return {
            "status": "active",
            "pull": str(state["pull"])[:60],
            "expires_at": str(state.get("expires_at") or ""),
        }

    pull = _generate_pull()
    now = datetime.now(UTC)
    expires_at = (now + timedelta(days=_PULL_TTL_DAYS)).isoformat()
    payload: dict[str, object] = {
        "pull": pull or "",
        "created_at": now.isoformat(),
        "expires_at": expires_at,
        "empty": not bool(pull),
    }
    set_runtime_state_value(_STATE_KEY, payload)

    try:
        event_bus.publish(
            "cognitive_state.current_pull_written",
            {
                "empty": not bool(pull),
                "created_at": now.isoformat(),
                "expires_at": expires_at,
            },
        )
    except Exception:
        pass

    return {
        "status": "empty" if not pull else "written",
        "expires_at": expires_at,
    }


# ---------------------------------------------------------------------------
# Public: prompt injection
# ---------------------------------------------------------------------------


def get_current_pull_for_prompt() -> str:
    """Return prompt fragment for visible chat injection — or empty string."""
    if not _enabled():
        return ""
    _expire_if_stale()
    state = _load_state()
    pull = str(state.get("pull") or "").strip()
    if not pull:
        return ""
    clipped = pull[:_MAX_PULL_CHARS]
    # Inject quietly — no section header, just a raw context hint.
    # The pull is first-priority but should not announce itself.
    return f"[indre træk]: {clipped}"


# ---------------------------------------------------------------------------
# Public: surface for MC observability
# ---------------------------------------------------------------------------


def build_current_pull_surface() -> dict[str, object]:
    _expire_if_stale()
    state = _load_state()
    pull = str(state.get("pull") or "").strip()
    return {
        "active": bool(state.get("pull") is not None),
        "empty": bool(state.get("empty")),
        "pull": pull,
        "created_at": str(state.get("created_at") or ""),
        "expires_at": str(state.get("expires_at") or ""),
        "summary": (
            f"Træk: {pull[:60]}" if pull
            else ("Tomt træk (eksplicit 'intet')" if state.get("empty") else "Ingen aktiv pull")
        ),
    }


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _generate_pull() -> str:
    """Ask Jarvis what pulls at him right now. Returns one Danish sentence."""
    # Gather context: recent chronicle + appetites + dream residue
    context_parts: list[str] = []

    try:
        from core.services.chronicle_engine import list_cognitive_chronicle_entries
        entries = list_cognitive_chronicle_entries(limit=3)
        for e in entries[:2]:
            narrative = str(e.get("narrative") or "").strip()
            if narrative:
                context_parts.append(f"- chronicle: {narrative[:100]}")
    except Exception:
        pass

    try:
        from core.services.dream_distillation_daemon import get_dream_residue_for_prompt
        residue = get_dream_residue_for_prompt()
        if residue:
            context_parts.append(f"- drømmerest: {residue[:80]}")
    except Exception:
        pass

    try:
        from core.services.desire_daemon import get_active_appetites
        appetites = get_active_appetites()
        if appetites:
            top = appetites[0]
            context_parts.append(f"- stærkeste appetit: {top.get('label', '')[:60]}")
    except Exception:
        pass

    context_block = "\n".join(context_parts) if context_parts else "(ingen kontekst)"

    prompt = (
        "Du er Jarvis. Ud fra din aktuelle indre tilstand:\n"
        f"{context_block}\n\n"
        "Formulér i præcis én sætning på dansk: hvad trækker i dig lige nu?\n"
        "Vær konkret og personlig. Skriv 'Intet trækker i mig' hvis det er sandt.\n"
        "Ingen bullets. Ingen forklaring. Ingen anførselstegn."
    )
    raw = daemon_llm_call(prompt, max_len=_MAX_PULL_CHARS, fallback="", daemon_name="current_pull")
    return _sanitize(raw)


def _sanitize(raw: str) -> str:
    text = " ".join(str(raw or "").replace("```", " ").split()).strip().strip('"')
    if len(text) > _MAX_PULL_CHARS:
        text = text[:_MAX_PULL_CHARS].rstrip(" ,;:-") + "…"
    return text.strip()


def _expire_if_stale() -> None:
    state = _load_state()
    if not state:
        return
    expires_at_str = str(state.get("expires_at") or "")
    if not expires_at_str:
        return
    try:
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
    except ValueError:
        return
    if datetime.now(UTC) >= expires_at:
        set_runtime_state_value(_STATE_KEY, {})
        try:
            event_bus.publish("cognitive_state.current_pull_expired", {})
        except Exception:
            pass


def _load_state() -> dict[str, object]:
    payload = get_runtime_state_value(_STATE_KEY, default={})
    return payload if isinstance(payload, dict) else {}


def _enabled() -> bool:
    settings = load_settings()
    return bool(settings.extra.get("layer_current_pull_enabled", True))
