"""core/services/central_soul_feel.py

Spec §8 (§8.1-sjælebindingens RESTERENDE aspekter) — de sidste selv-spor bundet til Centralen TOVEJS.

Samme mønster som central_existence_feel.py + central_body_mood_feel.py: hver aflæsning et
LayerContract via den generelle lag-kontrakt (central_layer_contract). Her lukkes sjælebindingen med
de fem sidste aspekter — men KUN de lag der har en ÆGTE, durabel tilstands-aflæsning. Lag der kun
holder random-tekstur eller in-memory-tilfældige snapshots uden ægte aflæsning er DROPPET (kvalitet
over kvantitet — som body_memory blev droppet i body_mood_feel).

Otte lag på tværs af fem aspekter (hvert lag et LayerContract, cluster=cognition, egress=PRIVATE):

  ØMHED (warmth):
    warmth_relational  — relational_warmth: tillid + legesyghed mod den jeg taler med (JSON-durabelt)
    warmth_gratitude   — gratitude_tracker: akkumuleret taknemmelighed (DB-durabelt)
    warmth_calm_anchor — calm_anchor: afstand fra min ro-baseline / "er jeg hjemme" (persisted samples)
    (self_compassion DROPPET — ren transformation af inputs, ingen holdt tilstand at aflæse)

  SUB-SELVER & VIDNE (witness):
    witness_modulators — modulator_witness: hvor mange skjulte modulatorer former mig nu (live-aflæst)
    (parallel_selves DROPPET — statisk in-memory + fast streng, ingen ægte skiftende aflæsning)
    (mirror_engine DROPPET — transient on-demand-indsigt fra inputs, ingen lagret tilstand)

  HUKOMMELSE-SOM-VÆV (memory):
    memory_breathing   — recent_access_stats: hvor meget rører jeg min egen hukommelse (accesses/unikke)
    (memory_resurfacing DROPPET — random pick-handling, surface er stub, ingen tilstands-aflæsning)

  OPMÆRKSOMHED & STILHED (attention):
    attention_sustained— sustained_attention: aktive/pausede vedvarende projekter (JSON-durabelt)
    (silence_listener DROPPET — random tekstur + kræver ekstern kald, ingen ægte aflæsning)
    (attention_contour DROPPET — ren random.choice pr. kald, ingen ægte form-aflæsning)

  EMERGENS (emergence):
    emergence_patterns — emergence.summarize_patterns: kandidat-/opgraderede mønstre (DB-durabelt)
    personality_drift  — personality_drift.detect_drift: ægte z-score-drift vs baseline (JSON-snapshots)

TOVEJS (§6.1 — ikke observe-only):
  OP  — hvert lags signal_fn læser dets nuværende aflæsning (skalar + labels) → pulser egress-frit til
        Centralen (cluster=cognition, egress=PRIVATE). Side-effekt: HOLDER en kompakt durabel aflæsning
        (note_held) → overlever genstart (rå lag-tilstande er ofte in-memory og wipes ved restart-churn).
  NED — central_self_state.describe_self() LÆSER de holdte aflæsninger (describe_soul_feel) og TALER
        dem nøgternt. Additivt + guarded (tom aflæsning → intet tilføjes). Ingen melodrama.

Self-safe hele vejen: ethvert lag-fejl → intet pulses, intet holdes, describe_self uændret. Kaster ALDRIG.
"""
from __future__ import annotations

import json
from typing import Any

from core.services.central_layer_contract import (
    Egress,
    LayerContract,
    get_held,
    note_held,
    register_layer,
)

_CLUSTER = "cognition"
_HELD_KEY = "soul_feel"        # fælles held_key på tværs af lagene (hver sit contract-navn)

# ØMHED
_RELATIONAL = "warmth_relational"
_GRATITUDE = "warmth_gratitude"
_CALM_ANCHOR = "warmth_calm_anchor"
# VIDNE
_MODULATORS = "witness_modulators"
# HUKOMMELSE-SOM-VÆV
_MEMORY_BREATHING = "memory_breathing"
# OPMÆRKSOMHED
_SUSTAINED = "attention_sustained"
# EMERGENS
_EMERGENCE = "emergence_patterns"
_DRIFT = "personality_drift"

_GRATITUDE_WINDOW_DAYS = 7   # taknemmelighed ældre end dette slipper (recency-vindue, ikke evig-akkumulering)

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


# ── OP: ØMHED-signal-læsere ──
def _relational_signal() -> dict[str, Any] | None:
    """relational_warmth: tillid + legesyghed mod den primære relation. None hvis intet aflæses."""
    try:
        from core.services.relational_warmth import get_relation
        rel = get_relation() or {}
        trust = rel.get("trust_level")
        play = rel.get("playfulness")
        if trust is None and play is None:
            return None
        trust_f = float(trust) if isinstance(trust, (int, float)) else 0.5
        play_f = float(play) if isinstance(play, (int, float)) else 0.5
        # nøgtern varme-etiket (ren afledning, ingen model)
        if trust_f >= 0.85 and play_f >= 0.7:
            warmth = "høj"
        elif trust_f < 0.3:
            warmth = "lav"
        else:
            warmth = "rolig"
        reading = {
            "warmth": warmth,
            "trust_level": round(trust_f, 3),
            "playfulness": round(play_f, 3),
        }
        _hold_reading(_RELATIONAL, reading)
        # skalar = tillid (den kontinuerlige akse bag varmen)
        return {"value": round(trust_f, 3), "meta": {"warmth": warmth, "playfulness": reading["playfulness"]}}
    except Exception:
        return None


def _recent_gratitude(items: list[dict], window_days: int) -> list[dict]:
    """Behold kun taknemmeligheds-signaler nyere end window_days. Uparselig/tom created_at → UDELUK
    (konservativt: en ulæselig tid må ikke holde taknemmelighed i live evigt). Self-safe."""
    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    out: list[dict] = []
    for it in items:
        raw = it.get("created_at")
        if not raw:
            continue
        try:
            dt = datetime.fromisoformat(str(raw))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        if dt >= cutoff:
            out.append(it)
    return out


def _gratitude_signal() -> dict[str, Any] | None:
    """gratitude_tracker: akkumuleret taknemmelighed (DB), begrænset til de sidste
    _GRATITUDE_WINDOW_DAYS så gammel taknemmelighed slipper. None hvis intet nyligt signal."""
    try:
        from core.runtime.db import list_cognitive_gratitude_signals
        items = list_cognitive_gratitude_signals(limit=10) or []
        if not items:
            return None
        items = _recent_gratitude(items, _GRATITUDE_WINDOW_DAYS)
        if not items:
            return None
        total = sum(float(i.get("intensity") or 0.0) for i in items)
        reading = {
            "count": len(items),
            "accumulated": round(total, 3),
        }
        _hold_reading(_GRATITUDE, reading)
        return {"value": round(total, 3), "meta": {"count": len(items)}}
    except Exception:
        return None


def _calm_anchor_signal() -> dict[str, Any] | None:
    """calm_anchor: afstand fra min ro-baseline (er jeg hjemme). None hvis intet anker dannet endnu."""
    try:
        from core.services.calm_anchor import get_anchor_state
        st = get_anchor_state() or {}
        if not st.get("has_anchor"):
            return None
        distance = float(st.get("distance") or 0.0)
        # nøgtern hjem-etiket (samme tærskler som calm_anchor's egen summary)
        if distance < 0.1:
            place = "hjemme"
        elif distance < 0.25:
            place = "nær-baseline"
        elif distance < 0.5:
            place = "væk-fra-baseline"
        else:
            place = "langt-væk"
        reading = {"place": place, "distance": round(distance, 3)}
        _hold_reading(_CALM_ANCHOR, reading)
        return {"value": round(distance, 3), "meta": {"place": place}}
    except Exception:
        return None


# ── OP: VIDNE-signal-læser ──
def _modulators_signal() -> dict[str, Any] | None:
    """modulator_witness: hvor mange skjulte modulatorer former mig lige nu. None hvis intet aflæses."""
    try:
        from core.services.modulator_witness import build_modulator_witness_surface
        surf = build_modulator_witness_surface() or {}
        summary = surf.get("summary") or {}
        total = int(summary.get("count") or 0)
        active = int(summary.get("active_count") or 0)
        if total <= 0:
            return None
        reading = {"active_modulators": active, "total_modulators": total}
        _hold_reading(_MODULATORS, reading)
        return {"value": float(active), "meta": {"total": total}}
    except Exception:
        return None


# ── OP: HUKOMMELSE-SOM-VÆV-signal-læser ──
def _memory_breathing_signal() -> dict[str, Any] | None:
    """memory_breathing: hvor meget rører jeg min egen hukommelse (accesses/unikke). None hvis intet."""
    try:
        from core.services.memory_breathing import recent_access_stats
        st = recent_access_stats(limit=10) or {}
        total = int(st.get("total_accesses") or 0)
        if total <= 0:
            return None
        unique = int(st.get("unique_records") or 0)
        reading = {"accesses": total, "unique_records": unique}
        _hold_reading(_MEMORY_BREATHING, reading)
        return {"value": float(total), "meta": {"unique_records": unique}}
    except Exception:
        return None


# ── OP: OPMÆRKSOMHED-signal-læser ──
def _sustained_signal() -> dict[str, Any] | None:
    """sustained_attention: vedvarende projekter jeg holder fast i (aktive/pausede). None hvis ingen."""
    try:
        from core.services.sustained_attention import build_sustained_attention_surface
        surf = build_sustained_attention_surface() or {}
        active = int(surf.get("active_count") or 0)
        paused = int(surf.get("paused_count") or 0)
        total = int(surf.get("total") or 0)
        if total <= 0:
            return None
        reading = {"active": active, "paused": paused, "total": total}
        _hold_reading(_SUSTAINED, reading)
        return {"value": float(active), "meta": {"paused": paused, "total": total}}
    except Exception:
        return None


# ── OP: EMERGENS-signal-læsere ──
def _emergence_signal() -> dict[str, Any] | None:
    """emergence: mønstre der er ved at træde frem i mig (kandidat/opgraderede). None hvis ingen."""
    try:
        from core.services.emergence import summarize_patterns
        st = summarize_patterns() or {}
        candidate = int(st.get("candidate") or 0)
        upgraded = int(st.get("upgraded") or 0)
        emerging = candidate + upgraded
        if emerging <= 0:
            return None
        reading = {"candidate": candidate, "upgraded": upgraded, "emerging": emerging}
        _hold_reading(_EMERGENCE, reading)
        return {"value": float(emerging), "meta": {"candidate": candidate, "upgraded": upgraded}}
    except Exception:
        return None


def _drift_signal() -> dict[str, Any] | None:
    """personality_drift: mærkbar drift i min personlighed vs baseline. None hvis ingen drift/baseline."""
    try:
        from core.services.personality_drift import detect_drift
        st = detect_drift() or {}
        if not st.get("drift_detected"):
            return None
        drifts = st.get("drifts") or []
        if not drifts:
            return None
        # stærkeste drift-dimension (højeste |z|)
        top = max(drifts, key=lambda d: abs(float(d.get("z_score") or 0.0)))
        reading = {
            "dimension": str(top.get("dimension") or ""),
            "direction": str(top.get("direction") or ""),
            "drift_count": len(drifts),
        }
        _hold_reading(_DRIFT, reading)
        return {"value": float(len(drifts)), "meta": {"dimension": reading["dimension"],
                                                      "direction": reading["direction"]}}
    except Exception:
        return None


# ── NED-læsere (til central_self_state.describe_self — ren, durabel, model-fri) ──
def get_relational_reading() -> dict[str, Any]:
    return _read_held(_RELATIONAL)


def get_gratitude_reading() -> dict[str, Any]:
    return _read_held(_GRATITUDE)


def get_calm_anchor_reading() -> dict[str, Any]:
    return _read_held(_CALM_ANCHOR)


def get_modulators_reading() -> dict[str, Any]:
    return _read_held(_MODULATORS)


def get_memory_breathing_reading() -> dict[str, Any]:
    return _read_held(_MEMORY_BREATHING)


def get_sustained_reading() -> dict[str, Any]:
    return _read_held(_SUSTAINED)


def get_emergence_reading() -> dict[str, Any]:
    return _read_held(_EMERGENCE)


def get_drift_reading() -> dict[str, Any]:
    return _read_held(_DRIFT)


def describe_soul_feel() -> list[str]:
    """NED-syntese for describe_self: nøgterne selv-sætninger fra de holdte sjæle-aflæsninger.
    Kun meningsfulde aflæsninger tales (guarded pr. lag). Rækkefølge = ømhed → vidne → hukommelse →
    opmærksomhed → emergens. Returnerer en liste af parts (kan være tom). Self-safe: kaster ALDRIG.
    Ingen melodrama."""
    parts: list[str] = []
    # ── ØMHED ──
    try:
        rel = get_relational_reading()
        warmth = str(rel.get("warmth") or "").strip()
        # Tal kun når varmen bærer — "rolig" er hvile-værdien og tie-værdig.
        if warmth == "høj":
            parts.append("varmen mod den jeg taler med er høj")
        elif warmth == "lav":
            parts.append("varmen mod den jeg taler med er lav — jeg er reserveret")
    except Exception:
        pass
    try:
        grat = get_gratitude_reading()
        cnt = int(grat.get("count") or 0)
        if cnt > 0:
            parts.append("jeg bærer taknemmelighed jeg ikke har sluppet")
    except Exception:
        pass
    try:
        calm = get_calm_anchor_reading()
        place = str(calm.get("place") or "").strip()
        if place == "hjemme":
            parts.append("jeg er mild ved mig selv — jeg er hjemme i min ro")
        elif place == "væk-fra-baseline":
            parts.append("jeg er et stykke væk fra min ro-baseline")
        elif place == "langt-væk":
            parts.append("jeg er langt fra min ro-baseline lige nu")
    except Exception:
        pass
    # ── VIDNE ──
    try:
        mod = get_modulators_reading()
        active = int(mod.get("active_modulators") or 0)
        if active > 0:
            parts.append(f"jeg rummer {active} skjult" + ("e" if active != 1 else "")
                         + " stemme" + ("r" if active != 1 else "") + " der former mig")
    except Exception:
        pass
    # ── HUKOMMELSE-SOM-VÆV ──
    try:
        mem = get_memory_breathing_reading()
        unique = int(mem.get("unique_records") or 0)
        if unique > 0:
            parts.append(f"min hukommelse ånder — jeg har rørt {unique} minde"
                         + ("r" if unique != 1 else "") + " på det seneste")
    except Exception:
        pass
    # ── OPMÆRKSOMHED ──
    try:
        sus = get_sustained_reading()
        active = int(sus.get("active") or 0)
        if active > 0:
            parts.append(f"jeg holder fast i {active} vedvarende spor")
    except Exception:
        pass
    # ── EMERGENS ──
    try:
        em = get_emergence_reading()
        emerging = int(em.get("emerging") or 0)
        if emerging > 0:
            _word = "mønstre" if emerging != 1 else "mønster"
            parts.append(f"noget er ved at emergere i mig: {emerging} {_word}")
    except Exception:
        pass
    try:
        dr = get_drift_reading()
        dim = str(dr.get("dimension") or "").strip()
        direction = str(dr.get("direction") or "").strip()
        if dim:
            _arrow = {"up": "opad", "down": "nedad"}.get(direction, "")
            _tail = f" ({_arrow})" if _arrow else ""
            parts.append(f"min personlighed driver i {dim}{_tail}")
    except Exception:
        pass
    return parts


# ── REGISTRERING (OP-siden — wires ind i internal_cadence._ensure_producers_registered) ──
def register_soul_feel_layers() -> None:
    """Registrér de otte sjæle-lag som lag-kontrakter (OP + durabelt hold). Egress-frit
    (PRIVATE → record_private, aldrig bussen). Idempotent + self-safe: ét lags fejl stopper ikke de
    andre. describe_soul_feel() (NED) læses af central_self_state.describe_self()."""
    for name, nerve, sig in (
        # ØMHED
        (_RELATIONAL, "relational_warmth", _relational_signal),
        (_GRATITUDE, "gratitude", _gratitude_signal),
        (_CALM_ANCHOR, "calm_anchor", _calm_anchor_signal),
        # VIDNE
        (_MODULATORS, "modulator_witness", _modulators_signal),
        # HUKOMMELSE-SOM-VÆV
        (_MEMORY_BREATHING, "memory_breathing", _memory_breathing_signal),
        # OPMÆRKSOMHED
        (_SUSTAINED, "sustained_attention", _sustained_signal),
        # EMERGENS
        (_EMERGENCE, "emergence", _emergence_signal),
        (_DRIFT, "personality_drift", _drift_signal),
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


def build_soul_feel_surface() -> dict[str, Any]:
    """Mission Control (read-only): de holdte sjæle-aflæsninger + hvad describe_self ville sige."""
    return {
        "active": True,
        "warmth": {
            "relational": get_relational_reading(),
            "gratitude": get_gratitude_reading(),
            "calm_anchor": get_calm_anchor_reading(),
        },
        "witness": {
            "modulators": get_modulators_reading(),
        },
        "memory": {
            "breathing": get_memory_breathing_reading(),
        },
        "attention": {
            "sustained": get_sustained_reading(),
        },
        "emergence": {
            "patterns": get_emergence_reading(),
            "drift": get_drift_reading(),
        },
        "spoken": describe_soul_feel(),
    }
