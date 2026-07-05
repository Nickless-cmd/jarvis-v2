"""Soul digest — §24.4 reducér-ved-kilden for Jarvis' stadig-mørke sjæle-/tids-signaler.

Disse daemons PRODUCERER data (længsel, identitets-drift, aktiv sansning,
følelses-reparation, associativ genkaldelse, bruger-model, narrativ,
kausal-inferens, signal-decay) men når hverken Jarvis' bevidsthed ELLER
Centralen — helt mørke. Dette digest giver dem en central-nerve.

Kører i jarvis-runtime (hvor daemon-tilstanden bor). Rå privat tekst
(længsels-tekst, drift-noter, model-indhold, ...) forlader ALDRIG denne
proces — KUN bool liveness + int count pr. signal. Proxy'es som én samlet
flade til /central/soul (§24.4 PRIVATE_NO_EGRESS-ånd, reducér-ved-kilden).
"""
from __future__ import annotations

from typing import Callable

# (signal-navn, modul-sti, funktionsnavn). Hver producent er VERIFICERET at
# eksistere og returnere en dict. En manglende/kastende producent isoleres til
# {liveness:False, count:0} (self-safe pr. signal).
_SOUL: list[tuple[str, str, str]] = [
    ("longing", "core.services.longing_signal_daemon", "build_longing_signal_daemon_surface"),
    ("identity_drift", "core.services.identity_drift_daemon", "build_identity_drift_surface"),
    ("active_sensing", "core.services.active_sensing_daemon", "build_active_sensing_surface"),
    ("emotion_repair", "core.services.emotion_repair_bridge_daemon", "build_emotion_repair_bridge_surface"),
    ("associative_recall", "core.services.associative_recall", "build_associative_recall_surface"),
    ("user_model", "core.services.user_model_daemon", "build_user_model_surface"),
    ("narrative_summary", "core.services.narrative_summary_daemon", "build_narrative_summary_surface"),
    ("causal_inference", "core.services.causal_graph", "build_causal_graph_surface"),
    ("signal_decay", "core.services.signal_decay_daemon", "build_signal_decay_surface"),
]


def _first_count(surface: dict) -> int:
    """Find en repræsentativ magnitude UDEN at afsløre indhold: længden af den
    første liste-værdi, ellers den første ikke-negative int-værdi, ellers 0."""
    if not isinstance(surface, dict):
        return 0
    for v in surface.values():
        if isinstance(v, (list, tuple)):
            return len(v)
    for v in surface.values():
        if isinstance(v, bool):
            continue
        if isinstance(v, int) and v >= 0:
            return v
    return 0


def _reduce(surface) -> dict:
    """KUN liveness+count. Ingen tekst. Self-safe."""
    if not isinstance(surface, dict) or not surface:
        return {"liveness": False, "count": 0}
    active = surface.get("active")
    liveness = bool(active) if active is not None else True
    return {"liveness": liveness, "count": _first_count(surface)}


def build_soul_digest() -> dict:
    """Samlet reduceret sjæle-/tids-digest. Kaster ALDRIG.

    Kun liveness+count pr. signal (§24.4 reducér-ved-kilden). Rå indhold
    forlader ALDRIG runtime. Self-safe pr. signal (import/kald i try/except
    → ``{liveness:False,count:0}``).
    """
    import importlib
    signals: dict[str, dict] = {}
    for name, mod, fn in _SOUL:
        try:
            m = importlib.import_module(mod)
            builder: Callable = getattr(m, fn)
            signals[name] = _reduce(builder())
        except Exception:
            signals[name] = {"liveness": False, "count": 0}
    live_count = sum(1 for s in signals.values() if s.get("liveness"))
    return {
        "signals": signals,
        "live_count": live_count,
        "total": len(signals),
    }
