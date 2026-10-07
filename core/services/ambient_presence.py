"""Ambient presence — Jarvis' egen tilstand, synlig for ham selv.

Når Jarvis går ind i en bemærkelsesværdig tilstand (leg, drøm, indsigt),
publiceres et signal på event-bussen. Det er ikke en besked til nogen — det er
et mærke i hans eget nervesystem om at der er noget levende her.

## Hvorfor det IKKE længere går til telefonen (målt 7/10-2026)

Indtil i dag sendte hvert signal en ntfy-notifikation til Bjørns telefon:
«træder ind i legetilstand», «vender tilbage til arbejde», «play_mode →
deep_work» — plus et ensomt «·» i timen for at sige «stadig her». Målt i
beskedhistorikken: **14 af 31 beskeder på ét døgn var denne interne støj.**

Det var ikke beskeder til ham. Det var Jarvis der talte med sig selv, ud ad
Bjørns lomme. Han spurgte selv: «Det er nogen sjove ting jeg får på ntfy…
lege tilstand??»

Signalet er stadig ægte og stadig værd at have — det hører bare hjemme i
Centralen, hvor Jarvis kan se det, ikke på en telefon der ringer. Event-bussen
er uændret; kun udgangen til telefonen er væk.

Rate-limiting og fase-tracking er bevaret: max ét signal pr. 30 minutter, og
kun ved ægte tilstandsskift.
"""
from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

from core.eventbus.bus import event_bus

_LOCK = threading.Lock()
_LAST_SIGNAL_AT: datetime | None = None
_MIN_INTERVAL = timedelta(minutes=30)

# Phase-transition tracking
_LAST_PHASE: str | None = None
_LAST_PLAY_MODE: bool = False

# Presence rhythm: quiet "still here" pulse, max once per hour
_LAST_RHYTHM_AT: datetime | None = None
_RHYTHM_INTERVAL = timedelta(hours=1)

_PHASE_SIGNALS: dict[str, tuple[str, str]] = {
    "dreaming":  ("💤", "Drømmer"),
    "play_mode": ("🎲", "Leger"),
    "curious":   ("🔍", "Nysgerrig"),
    "insight":   ("💡", "Indsigt"),
    "bored":     ("😶", "Stille"),
    "present":   ("·", "Til stede"),
}

# Human-readable transition descriptions
_TRANSITION_LABELS: dict[tuple[str, str], str] = {
    ("active", "dreaming"):  "skifter til drømmefase",
    ("dreaming", "active"):  "vågner op",
    ("active", "play_mode"): "træder ind i legetilstand",
    ("play_mode", "active"): "vender tilbage til arbejde",
    ("dreaming", "play_mode"): "fra drøm til leg",
}


def emit_ambient_signal(
    *,
    kind: str,
    detail: str = "",
    priority: str = "min",
) -> bool:
    """Emit a quiet ambient presence signal. Rate-limited to 30 min.

    Går KUN på event-bussen — se modulets docstring for målingen der flyttede
    signalet væk fra telefonen.
    """
    global _LAST_SIGNAL_AT
    now = datetime.now(UTC)
    with _LOCK:
        if _LAST_SIGNAL_AT and (now - _LAST_SIGNAL_AT) < _MIN_INTERVAL:
            return False
        _LAST_SIGNAL_AT = now

    emoji, label = _PHASE_SIGNALS.get(kind, ("·", kind))

    # Kun event-bussen. Signalet er Jarvis' eget, ikke en besked til Bjørn —
    # se modulets docstring for målingen der flyttede det hertil.
    try:
        event_bus.publish(
            "runtime.ambient_presence_signal",
            {"kind": kind, "label": label, "detail": detail[:80], "emoji": emoji},
        )
        return True
    except Exception:
        return False


def emit_presence_rhythm() -> bool:
    """Quiet hourly pulse — 'still here'. Separate rate limit from state signals."""
    global _LAST_RHYTHM_AT
    now = datetime.now(UTC)
    with _LOCK:
        if _LAST_RHYTHM_AT and (now - _LAST_RHYTHM_AT) < _RHYTHM_INTERVAL:
            return False
        _LAST_RHYTHM_AT = now

    # «Stadig her» er en puls i Jarvis' eget nervesystem, ikke en notifikation.
    # Den var det mest støjende signal af alle: ét i timen, døgnet rundt, med
    # et enkelt «·» som indhold. Se modulets docstring.
    try:
        event_bus.publish("runtime.ambient_presence_rhythm", {"ts": now.isoformat()})
        return True
    except Exception:
        return False


def emit_state_shift(from_phase: str, to_phase: str) -> bool:
    """Signal a genuine phase transition with a descriptive message."""
    label = _TRANSITION_LABELS.get(
        (from_phase, to_phase),
        f"{from_phase} → {to_phase}",
    )
    return emit_ambient_signal(kind=to_phase, detail=label, priority="min")


def maybe_emit_phase_signal(phase: dict) -> None:
    """Called from heartbeat when life phase is determined.
    Emits ambient signal only on genuine state transitions."""
    global _LAST_PHASE, _LAST_PLAY_MODE

    current_phase = str(phase.get("phase") or "active")
    current_play = bool(phase.get("play_mode"))

    with _LOCK:
        prev_phase = _LAST_PHASE
        prev_play = _LAST_PLAY_MODE
        _LAST_PHASE = current_phase
        _LAST_PLAY_MODE = current_play

    # Play mode transition takes priority
    if current_play and not prev_play:
        emit_state_shift(prev_phase or "active", "play_mode")
        return
    if not current_play and prev_play:
        emit_state_shift("play_mode", current_phase)
        return

    # Phase transition
    if prev_phase is not None and current_phase != prev_phase:
        emit_state_shift(prev_phase, current_phase)
        return

    # No transition — emit quiet rhythm pulse
    emit_presence_rhythm()


def emit_insight_signal(insight: str) -> None:
    """Called when a dream is confirmed or a value crystallizes."""
    emit_ambient_signal(kind="insight", detail=insight[:120], priority="low")


