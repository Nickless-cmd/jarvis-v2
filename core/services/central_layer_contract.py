"""core/services/central_layer_contract.py

PUNKT #6 (spec §11): den GENERELLE tovejs lag-kontrakt. Retter bespoke-fejlen (self-review 3. jul):
hver binding var ~85% identisk boilerplate (_kv_get-par, off/shadow/on-flag, record_private-wrapper,
register_*_producer, build_*_surface) + ~15% ægte lag-specifik logik. Kontrakten samler de 85% ét
sted, så at forbinde lag #201 = én deklaration + de 3 valgfri lag-funktioner.

Et lag deklarerer HVAD; Centralen gør HVORDAN generisk:
  OP     — signal_fn() → sink (egress-klasse VALGT AF KONTRAKTEN, ikke laget → kan ikke lække).
  BESTEM — salience_fn() + decide() (off/shadow/on) → genbrug holdt selv når ikke bevæget.
  NED    — consume_fn() → laget læser Centralens holdte/syntetiserede tilstand.
  TRACE/GOVERNANCE — skalar-filtrering + flag + MC-surface + cadence-registrering: generisk.

Bygger OVENPÅ eksisterende primitiver (ingen kerne rørt): internal_cadence.ProducerSpec (OP-driver),
central_private_observe.record_private (egress-fri sink), central_core.central().observe (egress-OK).
Fanger de 3 arketyper uden tab: world_model (kun OP), central_self_state (OP+NED),
central_inner_salience (OP+BESTEM+NED). Migration er Boy-Scout (konvertér ved berøring). Kaster ALDRIG.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

_HELD_KEY = "central_layer_held"      # durabelt: {name: {held_key: {key,value,ts}}}
_MODE_PREFIX = "layer_mode:"           # per-lag flag: off|shadow|on (runtime-state kv)


class Egress(Enum):
    PRIVATE = "private"          # → record_private (trace+serie, ALDRIG _emit). Fail-safe default.
    OPERATIONAL = "operational"  # → central().observe (egress-OK, skalar-strippet af membranen)


class DecideMode(Enum):
    OFF = "off"
    SHADOW = "shadow"
    ON = "on"


@dataclass(slots=True)
class LayerContract:
    name: str
    cluster: str
    nerve: str
    signal_fn: Callable[[], dict[str, Any] | None]     # → {"value": float, "meta": {skalarer}} | None
    egress: Egress = Egress.PRIVATE                     # tvivl → privat (fail-safe, jf. broen §24.4)
    salience_fn: Callable[[Any], str] | None = None     # rå tilstand → stabil salience-nøgle (valgfri)
    consume_fn: Callable[[], Any] | None = None         # NED: Centralens holdte tilstand (valgfri)
    cooldown_minutes: float = 5.0
    visible_grace_minutes: float = 0.0
    priority: int = 20
    depends_on: list[str] = field(default_factory=list)
    ttl_seconds: float = 6 * 3600.0                     # decide: genbrug kun hvis holdt inden for TTL


_CONTRACTS: dict[str, LayerContract] = {}


# ── KV (ét sted — erstatter de kopierede _kv_get/_kv_set-par) ──
def _kv_get(key: str, default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return v if v is not None else default
    except Exception:
        return default


def _kv_set(key: str, value: Any) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(key, value)
    except Exception:
        pass


def _scalars(meta: dict[str, Any] | None) -> dict[str, Any]:
    """Privatlags-membran ÉT sted (§24.4): kun tal/bool/str krydser — aldrig lister/nested/blobs."""
    return {k: v for k, v in (meta or {}).items() if isinstance(v, (int, float, bool, str))}


def _mode(name: str) -> DecideMode:
    m = str(_kv_get(_MODE_PREFIX + name, "off") or "off").strip().lower()
    return DecideMode(m) if m in ("off", "shadow", "on") else DecideMode.OFF


# ── SINK (ét sted vælger egress-klasse → et privat lag kan ALDRIG ramme observe ved uheld) ──
def _sink(c: LayerContract, value: float, meta: dict[str, Any], reason: str = "") -> None:
    m = _scalars(meta)
    try:
        if c.egress is Egress.PRIVATE:
            from core.services.central_private_observe import record_private
            record_private(c.cluster, c.nerve, value=float(value), meta=m, reason=reason)
        else:
            from core.services.central_core import central
            central().observe({"cluster": c.cluster, "nerve": c.nerve, "kind": "observe",
                               "value": float(value), **m})
    except Exception:
        pass


# ── OP + NED tick (generisk producer-krop) ──
def _run_contract_tick(c: LayerContract) -> dict[str, object]:
    observed = False
    try:
        sig = c.signal_fn() or None
        if isinstance(sig, dict):
            _sink(c, float(sig.get("value") or 0.0), sig.get("meta") or {})
            observed = True
    except Exception:
        pass
    if c.consume_fn is not None:
        try:
            held = c.consume_fn()
            _sink(c, 1.0, {"consumed": held is not None}, reason="consume")
        except Exception:
            pass
    return {"status": "ran" if observed else "noop", "observed": observed}


# ── BESTEM (generisk salience-gate — fanger inner_salience 1:1) ──
def _held_get(name: str, held_key: str) -> dict[str, Any]:
    st = _kv_get(_HELD_KEY, {})
    if not isinstance(st, dict):
        return {}
    h = (st.get(name) or {}).get(held_key)
    return h if isinstance(h, dict) else {}


def note_held(name: str, held_key: str, *, key: str, value: str) -> None:
    """Fodr det friske selv TILBAGE i Centralen (NED-holdet) efter en ægte genudledning. Self-safe."""
    try:
        v = str(value or "").strip()
        if not v:
            return
        st = _kv_get(_HELD_KEY, {})
        if not isinstance(st, dict):
            st = {}
        st.setdefault(name, {})[held_key] = {"key": str(key), "value": v[:400], "ts": time.time()}
        _kv_set(_HELD_KEY, st)
    except Exception:
        pass


def get_held(name: str, held_key: str = "default") -> Any:
    """NED-læser for forbrugere (prompt/voice). Ren KV-read (ingen syntese på læse-tid → hot-path-sikker)."""
    return _held_get(name, held_key).get("value")


def decide(name: str, *, key: str, held_key: str = "default") -> dict[str, Any]:
    """Centralen BESTEMMER: genudled via LLM, eller genbrug holdt selv? off/shadow/on. Self-safe.
    reuse=True KUN i 'on' når selvet ikke er bevæget (samme nøgle + inden TTL) og der er et holdt selv."""
    try:
        c = _CONTRACTS.get(name)
        ttl = c.ttl_seconds if c else 6 * 3600.0
        mode = _mode(name)
        held = _held_get(name, held_key)
        fresh = bool(held and held.get("key") == key and held.get("value")
                     and (time.time() - float(held.get("ts") or 0.0)) < ttl)
        if mode is not DecideMode.OFF:
            _sink(c, 1.0 if fresh else 0.0, {"kind": "salience", "would_reuse": fresh,
                                             "mode": mode.value, "held_key": held_key}) if c else None
        if mode is DecideMode.ON and fresh:
            return {"reuse": True, "held": held.get("value"), "would_reuse": True, "mode": mode.value}
        return {"reuse": False, "held": None, "would_reuse": fresh, "mode": mode.value}
    except Exception:
        return {"reuse": False, "held": None, "would_reuse": False, "mode": "off"}


# ── REGISTRERING ──
def register_layer(c: LayerContract) -> None:
    """Deklarativ binding: registrér laget på cadence-motoren via en genereret run_fn. Idempotent, self-safe."""
    try:
        _CONTRACTS[c.name] = c
        from core.services.internal_cadence import ProducerSpec, register_producer
        register_producer(ProducerSpec(
            name=c.name,
            cooldown_minutes=c.cooldown_minutes,
            visible_grace_minutes=c.visible_grace_minutes,
            run_fn=(lambda _c=c: (lambda **_kw: _run_contract_tick(_c)))(),
            priority=c.priority,
            depends_on=list(c.depends_on),
        ))
    except Exception:
        pass


def build_layer_surface(name: str) -> dict[str, Any]:
    """Generisk MC-projektion (read-only): mode + holdt selv pr. held_key."""
    c = _CONTRACTS.get(name)
    st = _kv_get(_HELD_KEY, {})
    held = st.get(name, {}) if isinstance(st, dict) else {}
    return {"active": bool(c) and _mode(name) is not DecideMode.OFF,
            "mode": _mode(name).value, "registered": bool(c),
            "held": {k: (v or {}).get("value") for k, v in held.items()} if isinstance(held, dict) else {}}
