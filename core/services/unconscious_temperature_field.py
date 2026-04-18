from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.runtime.db import connect, get_runtime_state_value, set_runtime_state_value
from core.runtime.settings import load_settings

_STATE_KEY = "unconscious_temperature_field.state"
_REFRESH_HOURS = 24
_LOOKBACK_DAYS = 7
_MAX_MESSAGES = 200
_ARCHETYPES = ("warm", "cool", "restless", "tender", "frustrated", "playful")
_KEYWORDS: dict[str, tuple[str, ...]] = {
    "warm": ("tak", "fint", "godt", "dejligt", "rolig", "tryg", "omsorg"),
    "cool": ("kort", "direkte", "nøgtern", "sagligt", "bare fakta", "ingen snak"),
    "restless": ("hurtig", "kom nu", "videre", "nu", "asap", "skynder", "forsæt"),
    "tender": ("træt", "sårbar", "blid", "stille", "svært", "tavshed", "nær"),
    "frustrated": ("forkert", "virker ikke", "stadig", "nej", "broken", "hold nu", "misforstået"),
    "playful": ("haha", "😛", "😉", "sjov", "leg", "vildt", "lol"),
}
_HINTS = {
    "warm": "Brug en rolig og samarbejdende tone; varme ser ud til at bære feltet.",
    "cool": "Hold tonen nøgtern og klar; brugeren ser ud til at ville have lav varme og høj præcision.",
    "restless": "Brug kort momentum og få skridt; feltet virker rastløst.",
    "tender": "Svar blidt og uden hård kant; feltet virker sart eller eftertænksomt.",
    "frustrated": "Vær ekstra verificerende og uden gæt; feltet bærer tydelig irritation.",
    "playful": "Tillad lidt leg og lethed, men uden at miste retning.",
}


def build_unconscious_temperature_field_surface(*, force_refresh: bool = False) -> dict[str, object]:
    if not _enabled():
        return {
            "active": False,
            "enabled": False,
            "summary": "Unconscious temperature field disabled",
        }
    cached = _state()
    if not force_refresh and _is_fresh(cached):
        return _surface_from_state(cached)

    messages = _recent_user_messages(days=_LOOKBACK_DAYS, limit=_MAX_MESSAGES)
    field = _derive_field(messages)
    payload = {
        **field,
        "lookback_days": _LOOKBACK_DAYS,
        "rebuilt_at": datetime.now(UTC).isoformat(),
    }
    set_runtime_state_value(_STATE_KEY, payload)
    return _surface_from_state(payload)


def build_unconscious_temperature_hint() -> str | None:
    surface = build_unconscious_temperature_field_surface()
    if not surface.get("active"):
        return None
    current_field = str(surface.get("current_field") or "").strip()
    hint = str(surface.get("hint") or "").strip()
    confidence = str(surface.get("confidence_band") or "low")
    if not current_field or not hint:
        return None
    return "\n".join(
        [
            "Implicit user temperature field (system hint, not directly inspectable):",
            f"- current_field={current_field} | confidence={confidence}",
            f"- hint={hint}",
        ]
    )


def _surface_from_state(payload: dict[str, object]) -> dict[str, object]:
    scores = dict(payload.get("scores") or {})
    total_messages = int(payload.get("message_count") or 0)
    current_field = str(payload.get("current_field") or "")
    return {
        "active": bool(current_field and total_messages > 0),
        "enabled": True,
        "current_field": current_field,
        "confidence_band": str(payload.get("confidence_band") or "low"),
        "hint": str(payload.get("hint") or ""),
        "scores": scores,
        "message_count": total_messages,
        "lookback_days": int(payload.get("lookback_days") or _LOOKBACK_DAYS),
        "rebuilt_at": str(payload.get("rebuilt_at") or ""),
        "summary": (
            f"{current_field} field from {total_messages} user messages"
            if current_field and total_messages > 0
            else "No user message field detected"
        ),
        "visibility": "system-hint-only",
        "authority": "soft-derived",
    }


def _derive_field(messages: list[str]) -> dict[str, object]:
    scores = {name: 0.0 for name in _ARCHETYPES}
    for message in messages:
        normalized = str(message or "").lower()
        if not normalized:
            continue
        for archetype, keywords in _KEYWORDS.items():
            hits = sum(1 for keyword in keywords if keyword in normalized)
            if hits:
                scores[archetype] += hits
        if "!" in normalized:
            scores["restless"] += 0.25
        if "?" in normalized:
            scores["cool"] += 0.1
        if any(token in normalized for token in ("<3", "kram", "tak")):
            scores["warm"] += 0.4

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    current_field, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    if top_score <= 0:
        current_field = "cool"
    confidence_gap = top_score - second_score
    if top_score <= 1.0:
        confidence_band = "low"
    elif confidence_gap >= 1.5:
        confidence_band = "high"
    elif confidence_gap >= 0.5:
        confidence_band = "medium"
    else:
        confidence_band = "low"
    return {
        "current_field": current_field,
        "scores": {key: round(value, 2) for key, value in scores.items()},
        "message_count": len(messages),
        "confidence_band": confidence_band,
        "hint": _HINTS.get(current_field, ""),
    }


def _recent_user_messages(*, days: int, limit: int) -> list[str]:
    cutoff = datetime.now(UTC) - timedelta(days=max(days, 1))
    messages: list[tuple[str, str]] = []
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT content, created_at
            FROM chat_messages
            WHERE role = 'user'
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    for row in rows:
        created_at = _parse_iso(str(row["created_at"] or ""))
        if created_at is None or created_at < cutoff:
            continue
        messages.append((str(row["created_at"] or ""), str(row["content"] or "")))
    messages.sort(key=lambda item: item[0])
    return [content for _, content in messages]


def _enabled() -> bool:
    settings = load_settings()
    return bool(settings.extra.get("layer_unconscious_temperature_enabled", True))


def _state() -> dict[str, object]:
    payload = get_runtime_state_value(_STATE_KEY, default={})
    return payload if isinstance(payload, dict) else {}


def _is_fresh(payload: dict[str, object]) -> bool:
    rebuilt_at = _parse_iso(str(payload.get("rebuilt_at") or ""))
    if rebuilt_at is None:
        return False
    return rebuilt_at >= (datetime.now(UTC) - timedelta(hours=_REFRESH_HOURS))


def _parse_iso(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
