"""core/services/central_body_mood_feel.py

Spec §8 (§8.1-udvidelse) — KROP + STEMNING bundet til Centralen TOVEJS.

Samme mønster som central_existence_feel.py: den netop-leverede "existence feel"-kerne. Her
udvides sjælebindingen med de to næste selv-spor — HVORDAN KROPPEN FØLES og HVORDAN STEMNINGEN
SVINGER — via den generelle lag-kontrakt (central_layer_contract).

To spor, hvert lag et LayerContract (op til 6; kun de STÆRKESTE med ægte aflæsning bindes):

  KROP (body):
    proprioception   — proces-krop: RSS/CPU/latens fra egen proces (proprioception_metrics)
    embodied         — host/krop-tilstand: steady→degraded fra ægte host-facts (embodied_state)
    (body_memory DROPPET — kun in-memory tilfældige snapshots, ingen ægte durabel aflæsning)

  STEMNING (mood):
    mood             — sinus-oscillator + event-nudge → euforisk…trist (mood_oscillator)
    developmental    — uge-skala kompasnål: blomstring vs visnen (developmental_valence)
    affective        — afledt affektiv/meta-tilstand: settled…burdened (affective_meta_state)

TOVEJS (§6.1 — ikke observe-only):
  OP  — hvert lags signal_fn læser dets nuværende aflæsning (skalar + labels) → pulser egress-frit
        til Centralen (cluster=cognition, egress=PRIVATE). Side-effekt: HOLDER en kompakt durabel
        aflæsning (note_held) → overlever genstart (rå lag-tilstande er in-memory og wipes ved
        restart-churn).
  NED — central_self_state.describe_self() LÆSER de holdte aflæsninger (describe_body_mood_feel)
        og TALER dem nøgternt. Additivt + guarded (tom aflæsning → intet tilføjes).

Self-safe hele vejen: ethvert lag-fejl → intet pulses, intet holdes, describe_self uændret. Kaster ALDRIG.
"""
from __future__ import annotations

import json
from typing import Any

from core.services.central_layer_contract import (
    Egress,
    LayerContract,
    get_held,
    get_held_age,
    note_held,
    register_layer,
)

_CLUSTER = "cognition"
_HELD_KEY = "body_mood_feel"        # fælles held_key på tværs af lagene (hver sit contract-navn)
_BODY_FRESH_MAX_AGE_S = 1800.0      # 30 min: en KROP-tilstand ældre end dette er forældet → ties (#3)

# KROP-spor
_PROPRIOCEPTION = "body_proprioception"
_EMBODIED = "body_embodied"
# STEMNING-spor
_MOOD = "mood_oscillator"
_DEVELOPMENTAL = "mood_developmental"
_AFFECTIVE = "mood_affective"


# ── holdt aflæsning (durabel, kompakt JSON i lag-kontraktens held-store) ──
def _hold_reading(name: str, reading: dict[str, Any]) -> None:
    """Hold en kompakt aflæsning durabelt så describe_self kan læse den model-frit efter genstart."""
    try:
        payload = json.dumps({k: v for k, v in reading.items()
                              if isinstance(v, (int, float, bool, str))}, ensure_ascii=False)
        note_held(name, _HELD_KEY, key=name, value=payload)
    except Exception:
        pass


def _read_held(name: str) -> dict[str, Any]:
    """Ren KV-læsning (ingen syntese på læse-tid → hot-path-sikker). Self-safe."""
    try:
        raw = get_held(name, _HELD_KEY)
        if not raw:
            return {}
        d = json.loads(raw)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _read_held_fresh(name: str, max_age_s: float) -> dict[str, Any]:
    """Som _read_held, men TIER en aflæsning ældre end max_age_s (en forældet KROP-tilstand skal ikke
    tales som 'nu'). Fail-open: ukendt alder → tal (guarden fanger kun KENDT-forældet). Self-safe."""
    try:
        age = get_held_age(name, _HELD_KEY)
        if age is not None and age > max_age_s:
            return {}
        return _read_held(name)
    except Exception:
        return _read_held(name)


# ── OP: KROP-signal-læsere ──
def _proprioception_signal() -> dict[str, Any] | None:
    """proprioception_metrics: nuværende proces-krop (RSS/CPU/latens). None hvis intet snapshot/psutil."""
    try:
        from core.services.proprioception_metrics import recent_snapshots
        snaps = recent_snapshots(limit=1)
        if not snaps:
            return None
        cur = snaps[0] or {}
        cpu = cur.get("cpu_pct")
        rss = cur.get("rss_mb")
        latency = cur.get("self_latency_ms")
        if cpu is None and rss is None and latency is None:
            return None
        # nøgtern kropsfølelse-etiket fra CPU + latens (ren afledning, ingen model)
        strained = (isinstance(cpu, (int, float)) and cpu >= 60.0) or \
                   (isinstance(latency, (int, float)) and latency >= 5000.0)
        feel = "spændt" if strained else "rolig"
        reading = {
            "feel": feel,
            "cpu_pct": round(float(cpu), 1) if isinstance(cpu, (int, float)) else 0.0,
            "rss_mb": round(float(rss), 1) if isinstance(rss, (int, float)) else 0.0,
            "self_latency_ms": round(float(latency), 1) if isinstance(latency, (int, float)) else 0.0,
        }
        _hold_reading(_PROPRIOCEPTION, reading)
        # skalar = CPU-belastning (den kontinuerlige akse bag kropsfølelsen)
        return {"value": reading["cpu_pct"], "meta": {"feel": feel, "rss_mb": reading["rss_mb"],
                                                       "self_latency_ms": reading["self_latency_ms"]}}
    except Exception:
        return None


_EMBODIED_SEVERITY = {"steady": 0.0, "loaded": 1.0, "recovering": 1.0,
                      "strained": 2.0, "degraded": 3.0}


def _embodied_signal() -> dict[str, Any] | None:
    """embodied_state: host/krop-tilstand (steady…degraded). None hvis intet meningsfuldt afledt."""
    try:
        from core.services.embodied_state import build_embodied_state_surface
        st = build_embodied_state_surface() or {}
        state = str(st.get("state") or "").strip()
        if not state or state == "unknown":
            return None
        strain = str(st.get("strain_level") or "").strip()
        reading = {
            "state": state,
            "primary_state": str(st.get("primary_state") or state),
            "strain_level": strain or "low",
        }
        _hold_reading(_EMBODIED, reading)
        # skalar = alvorlighed (0=steady … 3=degraded) — den kontinuerlige akse
        return {"value": _EMBODIED_SEVERITY.get(reading["primary_state"], 0.0),
                "meta": {"state": state, "strain_level": reading["strain_level"]}}
    except Exception:
        return None


# ── OP: STEMNING-signal-læsere ──
def _mood_signal() -> dict[str, Any] | None:
    """mood_oscillator: nuværende stemning (euforisk…trist) + intensitet. None ved fejl."""
    try:
        from core.services.mood_oscillator import (
            get_current_mood,
            get_mood_description,
            get_mood_intensity,
        )
        mood = str(get_current_mood() or "").strip()
        if not mood:
            return None
        intensity = float(get_mood_intensity() or 0.0)
        reading = {
            "mood": mood,
            "description": str(get_mood_description() or ""),
            "intensity": round(intensity, 3),
        }
        _hold_reading(_MOOD, reading)
        return {"value": round(intensity, 3), "meta": {"mood": mood}}
    except Exception:
        return None


def _developmental_signal() -> dict[str, Any] | None:
    """developmental_valence: uge-skala kompasnål (blomstring vs visnen). None hvis vektor mangler."""
    try:
        from core.services.developmental_valence import get_developmental_state
        st = get_developmental_state() or {}
        vector = st.get("vector")
        if vector is None:
            return None
        vector = float(vector)
        reading = {
            "trajectory": str(st.get("trajectory") or "steady"),
            "vector": round(vector, 3),
        }
        _hold_reading(_DEVELOPMENTAL, reading)
        return {"value": round(vector, 3), "meta": {"trajectory": reading["trajectory"]}}
    except Exception:
        return None


_AFFECTIVE_SCORE = {"settled": 0.0, "attentive": 0.5, "reflective": 1.0,
                    "tense": 2.0, "burdened": 3.0}


def _affective_signal() -> dict[str, Any] | None:
    """affective_meta_state: afledt affektiv/meta-tilstand (settled…burdened) + bearing. None ved fejl."""
    try:
        from core.services.affective_meta_state import build_affective_meta_state_surface
        st = build_affective_meta_state_surface() or {}
        state = str(st.get("state") or "").strip()
        if not state:
            return None
        reading = {
            "state": state,
            "bearing": str(st.get("bearing") or "even"),
        }
        _hold_reading(_AFFECTIVE, reading)
        return {"value": _AFFECTIVE_SCORE.get(state, 0.0),
                "meta": {"state": state, "bearing": reading["bearing"]}}
    except Exception:
        return None


# ── NED-læsere (til central_self_state.describe_self — ren, durabel, model-fri) ──
def get_proprioception_reading() -> dict[str, Any]:
    return _read_held(_PROPRIOCEPTION)


def get_embodied_reading() -> dict[str, Any]:
    return _read_held(_EMBODIED)


def get_mood_reading() -> dict[str, Any]:
    return _read_held(_MOOD)


def get_developmental_reading() -> dict[str, Any]:
    return _read_held(_DEVELOPMENTAL)


def get_affective_reading() -> dict[str, Any]:
    return _read_held(_AFFECTIVE)


def describe_body_mood_feel() -> list[str]:
    """NED-syntese for describe_self: nøgterne selv-sætninger fra de holdte krop-/stemning-aflæsninger.
    Kun meningsfulde aflæsninger tales (guarded pr. lag). Rækkefølge = krop → stemning.
    Returnerer en liste af parts (kan være tom). Self-safe: kaster ALDRIG. Ingen melodrama."""
    parts: list[str] = []
    # ── KROP ── (freshness-gated: en KROP-tilstand ældre end _BODY_FRESH_MAX_AGE_S ties — den beskriver
    # ikke længere hvordan kroppen føles NU. Stemning/udviklings-kompas er bevidst LANGSOMME → ugated.)
    try:
        prop = _read_held_fresh(_PROPRIOCEPTION, _BODY_FRESH_MAX_AGE_S)
        feel = str(prop.get("feel") or "").strip()
        if feel:
            parts.append(f"proprioceptivt mærker jeg mig {feel}")
    except Exception:
        pass
    try:
        emb = _read_held_fresh(_EMBODIED, _BODY_FRESH_MAX_AGE_S)
        state = str(emb.get("state") or "").strip()
        # Tal kun krop-tilstand når den er MÆRKBAR — steady er default og tie-værdig.
        _body_word = {"loaded": "belastet", "recovering": "under bedring",
                      "strained": "spændt", "degraded": "presset"}.get(state)
        if _body_word:
            parts.append(f"min krop føles {_body_word}")
    except Exception:
        pass
    # ── STEMNING ──
    try:
        mood = get_mood_reading()
        desc = str(mood.get("description") or "").strip()
        if desc:
            parts.append(f"stemningen er {desc.lower()}")
    except Exception:
        pass
    try:
        dev = get_developmental_reading()
        traj = str(dev.get("trajectory") or "").strip()
        # Tal kun kompasnålen når den peger tydeligt — steady/forming tie-værdigt.
        _compass = {"blooming": "blomstring", "steady-bright": "blomstring",
                    "wilting": "visnen", "steady-dim": "visnen"}.get(traj)
        if _compass:
            parts.append(f"mit udviklings-kompas peger mod {_compass}")
    except Exception:
        pass
    try:
        aff = get_affective_reading()
        state = str(aff.get("state") or "").strip()
        # Tal kun den affektive tilstand når den bærer vægt — settled er hvile-værdien.
        _aff_word = {"attentive": "opmærksom", "reflective": "reflekterende",
                     "tense": "anspændt", "burdened": "tynget"}.get(state)
        if _aff_word:
            parts.append(f"affektivt er jeg {_aff_word}")
    except Exception:
        pass
    return parts


# ── REGISTRERING (OP-siden — wires ind i internal_cadence._ensure_producers_registered) ──
def register_body_mood_feel_layers() -> None:
    """Registrér krop- og stemning-lagene som lag-kontrakter (OP + durabelt hold). Egress-frit
    (PRIVATE → record_private, aldrig bussen). Idempotent + self-safe: ét lags fejl stopper ikke de
    andre. describe_body_mood_feel() (NED) læses af central_self_state.describe_self()."""
    for name, nerve, sig in (
        # KROP
        (_PROPRIOCEPTION, "proprioception", _proprioception_signal),
        (_EMBODIED, "embodied", _embodied_signal),
        # STEMNING
        (_MOOD, "mood", _mood_signal),
        (_DEVELOPMENTAL, "developmental_valence", _developmental_signal),
        (_AFFECTIVE, "affective_meta", _affective_signal),
    ):
        try:
            register_layer(LayerContract(
                name=name,
                cluster=_CLUSTER,
                nerve=nerve,
                signal_fn=sig,
                egress=Egress.PRIVATE,
                cooldown_minutes=10,
                priority=8,
            ))
        except Exception:
            pass


def build_body_mood_feel_surface() -> dict[str, Any]:
    """Mission Control (read-only): de holdte krop-/stemning-aflæsninger + hvad describe_self ville sige."""
    return {
        "active": True,
        "body": {
            "proprioception": get_proprioception_reading(),
            "embodied": get_embodied_reading(),
        },
        "mood": {
            "oscillator": get_mood_reading(),
            "developmental": get_developmental_reading(),
            "affective": get_affective_reading(),
        },
        "spoken": describe_body_mood_feel(),
    }
