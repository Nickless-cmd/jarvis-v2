"""core/services/central_convene_judge.py

DEN CENTRALE GRUND-TIL-AT-INDKALDE-DOMMER (spec 2026-07-03 §C akse 4 + indkaldelsen).

Samme ånd som central_form_judge (én dommer, spurgt FØR en dyr operation), men ét
niveau op: i stedet for "har min input ændret FORM?" spørger denne:

    "Er der en REEL grund til at indkalde rådet NU — og hvad handler den grund om?"

Den rigide gate den erstatter (autonomous_council_daemon): fast tærskel (_THRESHOLD=0.25)
+ cadence/cooldown/dagligt-cap + et STATISK _SIGNAL_TO_ROLES-map (existential_wonder →
[filosof, synthesizer], uanset hvad der faktisk bevæger sig). Det gør indkaldelsen
mekanisk og rollerne blinde for konteksten.

Denne dommer læser de FLYDENDE værdier — de eksisterende signal-surfaces PLUS valens
(affektiv meta-tilstand) og agenda (ønsker/desire) — og:
  1. vurderer om noget faktisk BEVÆGER sig (ægte grund, ikke bare baggrundsstøj),
  2. udleder et EMNE-HINT af de mest aktive signaler + valens,
  3. udleder ROLLER DYNAMISK af hvad der bevæger sig (ikke det statiske map).

GOVERNANCE: flag `central_convene_judge_mode` (runtime-state kv): off|shadow|on.
DEFAULT off.
  off    → uændret. Dommeren returnerer sit mode men styrer intet; den gamle
           tærskel-gate afgør indkaldelse (nul adfærdsændring).
  shadow → dommeren beregner + observerer hvad den VILLE beslutte (til
           central_timeseries cognition/convene_judge), men den gamle gate styrer stadig.
  on     → dommeren afgør indkaldelse + roller + emne-hint.

Self-safe: enhver tvivl/fejl → convene=False i shadow-observationen; i on-mode falder
kalderen tilbage på den gamle gate hvis dommeren fejler (kalder-siden fanger None).
Måler til central_timeseries cognition/convene_judge. GUARD KUN HANDLINGER: dommeren
gater KUN om rådet indkaldes — den begrænser ikke hvem der må tænke.
"""
from __future__ import annotations

from typing import Any

_MODE_KEY = "central_convene_judge_mode"

# Minimum "bevægelses"-vægt (sum af aktive signal-bidrag + valens-udsving) før der er
# en reel grund. Bevidst lav — dommeren skal fange ægte bevægelse, ikke kræve en storm.
_MOVEMENT_THRESHOLD = 0.30

# Dynamisk rolle-udledning: hvert flydende signal peger på hvilke perspektiver der er
# relevante NÅR det bevæger sig. Bruges KUN til at oversætte faktisk bevægelse → roller
# (modsat det statiske _SIGNAL_TO_ROLES der altid gav de samme to uanset kontekst).
_SIGNAL_PERSPECTIVES: dict[str, list[str]] = {
    "autonomy_pressure": ["planner", "critic"],
    "open_loop": ["planner", "researcher"],
    "internal_opposition": ["critic", "filosof"],
    "conflict": ["critic", "etiker"],
    "existential_wonder": ["filosof", "synthesizer"],
    "creative_drift": ["filosof", "researcher"],
    "desire": ["planner", "etiker"],
    "valence_negative": ["etiker", "critic"],     # lav valens → afvej/omsorg-vinkler
    "valence_positive": ["planner", "researcher"], # høj valens → udforsk/byg-vinkler
}

_MAX_ROLES = 4


def _kv_get(key: str, default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return v if v is not None else default
    except Exception:
        return default


def current_mode() -> str:
    m = str(_kv_get(_MODE_KEY, "off") or "off").strip().lower()
    return m if m in ("off", "shadow", "on") else "off"


# ---------------------------------------------------------------------------
# Reading the flowing values
# ---------------------------------------------------------------------------

def _movement_from_signal(name: str, surface: dict[str, Any]) -> float:
    """Normalise ONE signal surface to a 0..1 'how much is this moving' reading.

    Reuses the same shapes autonomous_council_daemon reads, so this judge sees the
    same live surfaces the old gate did — just interpreted as movement, not a
    weighted score toward a fixed threshold."""
    s = surface or {}
    try:
        if name == "autonomy_pressure":
            return min(int((s.get("summary") or {}).get("active_count") or 0) / 3.0, 1.0)
        if name == "open_loop":
            return min(int((s.get("summary") or {}).get("open_count") or 0) / 5.0, 1.0)
        if name == "internal_opposition":
            return 1.0 if s.get("active") else 0.0
        if name == "existential_wonder":
            return 1.0 if str(s.get("latest_wonder") or "") else 0.0
        if name == "creative_drift":
            return min(int(s.get("drift_count_today") or 0) / 3.0, 1.0)
        if name == "desire":
            return min(int(s.get("active_count") or 0) / 3.0, 1.0)
        if name == "conflict":
            return 1.0 if str(s.get("last_conflict") or "") else 0.0
    except Exception:
        return 0.0
    return 0.0


def _read_flowing_values(surfaces: dict[str, Any] | None) -> dict[str, Any]:
    """Read the flowing values: signal movement + affective valence + agenda hint.

    surfaces: if the caller already read the signal surfaces, reuse them (no double
    read); otherwise read them here. Valence comes from the affective meta-state
    surface (mood), agenda from active desires. All self-safe."""
    from core.services.signal_surface_router import read_surface

    signal_names = [
        "autonomy_pressure", "open_loop", "internal_opposition",
        "existential_wonder", "creative_drift", "desire", "conflict",
    ]
    src = surfaces if isinstance(surfaces, dict) else {}
    movement: dict[str, float] = {}
    latest_wonder = ""
    for name in signal_names:
        surf = src.get(name)
        if not isinstance(surf, dict):
            try:
                surf = read_surface(name)
            except Exception:
                surf = {}
        movement[name] = _movement_from_signal(name, surf if isinstance(surf, dict) else {})
        if name == "existential_wonder" and isinstance(surf, dict):
            latest_wonder = str(surf.get("latest_wonder") or "").strip()

    # Valence — affective meta-state mood. Coarse but live; drives care/explore roles.
    valence = 0.0
    mood = ""
    try:
        aff = read_surface("affective_meta_state")
        if isinstance(aff, dict):
            mood = str(aff.get("mood") or "").strip().lower()
            valence = _mood_to_valence(mood)
    except Exception:
        pass

    # Agenda — a short hint of what he actively wants right now (from desire surface).
    agenda_hint = ""
    try:
        des = src.get("desire")
        if not isinstance(des, dict):
            des = read_surface("desire")
        if isinstance(des, dict):
            agenda_hint = str(
                des.get("top_desire") or des.get("latest") or des.get("summary") or ""
            ).strip()
    except Exception:
        pass

    return {
        "movement": movement,
        "valence": valence,
        "mood": mood,
        "latest_wonder": latest_wonder,
        "agenda_hint": agenda_hint,
    }


def _mood_to_valence(mood: str) -> float:
    """Map a coarse mood word to a signed valence in [-1, 1]. Unknown → 0."""
    negative = {"distressed", "melancholic", "guarded", "anxious", "sad", "frustrated", "tense"}
    positive = {"content", "euphoric", "curious", "warm", "playful", "steady", "attentive"}
    m = str(mood or "").strip().lower()
    if m in negative:
        return -0.6
    if m in positive:
        return 0.4
    return 0.0


# ---------------------------------------------------------------------------
# The verdict
# ---------------------------------------------------------------------------

def _derive_roles(movement: dict[str, float], valence: float) -> list[str]:
    """Derive council roles DYNAMICALLY from what is actually moving — the core of
    akse 4. A signal only contributes its perspectives when it is genuinely active.
    Valence sign adds a care- or explore-lens. Synthesizer always closes the loop."""
    active = sorted(
        (n for n, v in movement.items() if v > 0.0),
        key=lambda n: movement[n],
        reverse=True,
    )
    roles: list[str] = []
    for name in active:
        for role in _SIGNAL_PERSPECTIVES.get(name, []):
            if role not in roles:
                roles.append(role)

    if valence <= -0.4:
        for role in _SIGNAL_PERSPECTIVES["valence_negative"]:
            if role not in roles:
                roles.append(role)
    elif valence >= 0.4:
        for role in _SIGNAL_PERSPECTIVES["valence_positive"]:
            if role not in roles:
                roles.append(role)

    if "synthesizer" not in roles:
        roles.append("synthesizer")

    # Minimum of three perspectives so a council is meaningful.
    for fallback in ("critic", "planner", "researcher"):
        if len(roles) >= 3:
            break
        if fallback not in roles:
            roles.append(fallback)
    return roles[:_MAX_ROLES]


def _derive_topic_hint(
    movement: dict[str, float],
    latest_wonder: str,
    agenda_hint: str,
    mood: str,
) -> str:
    """Build a short subject hint from what is actually moving — fed to derive_topic.
    Prefers a live existential wonder, then the strongest moving signal, then agenda."""
    if latest_wonder:
        return latest_wonder
    ranked = sorted((n for n, v in movement.items() if v > 0.0),
                    key=lambda n: movement[n], reverse=True)
    parts: list[str] = []
    if ranked:
        parts.append(ranked[0].replace("_", " "))
    if agenda_hint:
        parts.append(agenda_hint)
    if mood:
        parts.append(f"stemning: {mood}")
    return " · ".join(parts).strip()


def _observe(verdict: dict[str, Any], mode: str) -> None:
    try:
        from core.services import central_timeseries as ts
        ts.record(
            "cognition", "convene_judge",
            value=(1.0 if verdict.get("convene") else 0.0),
            meta={
                "mode": mode,
                "convene": bool(verdict.get("convene")),
                "movement": round(float(verdict.get("movement_total") or 0.0), 3),
                "roles": list(verdict.get("roles") or [])[:_MAX_ROLES],
                "reason": str(verdict.get("reason") or "")[:80],
            },
        )
    except Exception:
        pass


def judge_convene(
    *,
    surfaces: dict[str, Any] | None,
    top_signals: list[str],
    score: float,
    score_override: float | None = None,
) -> dict[str, Any]:
    """Decide whether there is a real reason to convene the council now.

    Returns a verdict dict:
      {mode, convene, reason, movement_total, top_signals, roles, topic_hint}
    In off-mode: mode="off", convene False, nothing derived (legacy gate rules).
    In shadow-mode: fully computed + observed, but caller keeps the legacy gate.
    In on-mode: caller acts on convene/roles/topic_hint.

    Self-safe: on any failure returns a benign off-verdict so the caller falls back
    to the legacy threshold path."""
    try:
        mode = current_mode()
        if mode == "off":
            return {"mode": "off", "convene": False, "reason": "flag_off",
                    "movement_total": 0.0, "top_signals": list(top_signals or []),
                    "roles": [], "topic_hint": ""}

        # score_override is a test/inject path — no real surfaces to read. Treat the
        # injected score as movement so tests exercise the judge deterministically.
        if score_override is not None:
            movement_total = float(score_override)
            movement = {"autonomy_pressure": min(movement_total, 1.0),
                        "open_loop": min(movement_total, 1.0)}
            flowing = {"valence": 0.0, "mood": "", "latest_wonder": "", "agenda_hint": ""}
        else:
            flowing = _read_flowing_values(surfaces)
            movement = flowing["movement"]
            movement_total = min(sum(movement.values()), 4.0)

        convene = movement_total >= _MOVEMENT_THRESHOLD
        roles = _derive_roles(movement, float(flowing.get("valence") or 0.0)) if convene else []
        topic_hint = (
            _derive_topic_hint(
                movement,
                str(flowing.get("latest_wonder") or ""),
                str(flowing.get("agenda_hint") or ""),
                str(flowing.get("mood") or ""),
            )
            if convene else ""
        )
        ranked = sorted((n for n, v in movement.items() if v > 0.0),
                        key=lambda n: movement[n], reverse=True)
        verdict = {
            "mode": mode,
            "convene": bool(convene),
            "reason": ("real_movement" if convene else "no_real_movement"),
            "movement_total": round(movement_total, 3),
            "top_signals": ranked[:2] or list(top_signals or []),
            "roles": roles,
            "topic_hint": topic_hint,
        }
        _observe(verdict, mode)
        return verdict
    except Exception:
        return {"mode": "off", "convene": False, "reason": "judge_error",
                "movement_total": 0.0, "top_signals": list(top_signals or []),
                "roles": [], "topic_hint": ""}
