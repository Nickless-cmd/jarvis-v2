"""core/services/central_inner_salience.py

FØRSTE ARKETYPE på kerne-tesen (spec §6.1b, Bjørn 3. jul): Centralen SAMLER selvet, og DEN
samling ERSTATTER de gentagne LLM-kald. Ikke observe-only — tovejs, hele vejen.

Det private indre fyrer i dag 3 LLM-kald pr. terminal-run (inner_note/growth_note/inner_voice) på
en METRONOM. inner_voice genudleder præcis det Centralen allerede syntetiserer (mood/position/retning
via central_self_state). Denne modul lader Centralen BESTEMME:

  IND (OP):   run'ets indre voice-tilstand → en salience-nøgle (mood|position|retning).
  BESTEM:     har selvet BEVÆGET sig siden sidst? Ikke bevæget + friskt holdt → genbrug.
  UD (NED):   genbrug det selv Centralen HOLDER (den holdte voice-linje) i stedet for at kalde model.

Effekt (§6.1b): taler når bevæget, ikke metronom (mere liv) · færre kald (cost/latens) · ét selv
(durabelt forankret). Alt traces egress-frit (record_private, cluster=cognition).

GOVERNANCE: reversibelt flag `central_inner_salience_gate` i runtime-state:
  'off'    → uændret (decide returnerer aldrig reuse). DEFAULT.
  'shadow' → beregn + trace 'would_reuse', men enrich ALLIGEVEL (mål skip-rate uden adfærdsændring).
  'on'     → skip LLM + genbrug holdt selv når ikke bevæget.
Kaster ALDRIG (self-safe) — ved enhver tvivl enrich'es som før.
"""
from __future__ import annotations

import time
from typing import Any

_STATE_KEY = "central_inner_salience"        # durabelt: sidst-holdte selv pr. kind
_FLAG_KEY = "central_inner_salience_gate"     # off|shadow|on
_TTL_SECONDS = 6 * 3600.0                     # genbrug kun hvis holdt inden for 6t (ellers genudled)


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


def _mode() -> str:
    m = str(_kv_get(_FLAG_KEY, "off") or "off").strip().lower()
    return m if m in ("off", "shadow", "on") else "off"


def _norm(s: Any) -> str:
    return " ".join(str(s or "").split()).strip().lower()


def salience_key_for_voice(inner_voice_payload: dict[str, Any]) -> str:
    """De MENINGSFULDE dimensioner af den indre stemme (langsomt-skiftende selv). Rå tekst der
    ændrer sig hver run (fx run_id) indgår IKKE — kun mood/position/bekymring/retning."""
    p = inner_voice_payload or {}
    return "|".join(_norm(p.get(k)) for k in ("mood_tone", "self_position", "current_concern", "current_pull"))


def _held(kind: str) -> dict[str, Any]:
    st = _kv_get(_STATE_KEY, {})
    if not isinstance(st, dict):
        return {}
    h = st.get(kind)
    return h if isinstance(h, dict) else {}


def _trace(kind: str, would_reuse: bool, mode: str) -> None:
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", "inner_salience", value=(1.0 if would_reuse else 0.0),
                       meta={"kind": kind, "would_reuse": bool(would_reuse), "mode": mode})
    except Exception:
        pass


def decide_voice(*, run_id: str, key: str) -> dict[str, Any]:
    """Centralen BESTEMMER: skal inner_voice genudledes via LLM, eller genbruges fra det holdte selv?

    Returnerer {reuse: bool, held: str|None, would_reuse: bool, mode: str}. reuse=True KUN i 'on'-mode
    når selvet ikke har bevæget sig og der er et friskt holdt selv. Self-safe: fejl → reuse=False."""
    try:
        mode = _mode()
        held = _held("voice")
        fresh = bool(
            held and held.get("key") == key and held.get("value")
            and (time.time() - float(held.get("ts") or 0.0)) < _TTL_SECONDS
        )
        if mode == "off":
            return {"reuse": False, "held": None, "would_reuse": fresh, "mode": mode}
        _trace("voice", fresh, mode)
        if mode == "shadow":
            return {"reuse": False, "held": None, "would_reuse": fresh, "mode": mode}
        # on
        return {"reuse": fresh, "held": (held.get("value") if fresh else None),
                "would_reuse": fresh, "mode": mode}
    except Exception:
        return {"reuse": False, "held": None, "would_reuse": False, "mode": "off"}


def note_enriched_voice(*, run_id: str, key: str, value: str) -> None:
    """Fodr det friske selv TILBAGE i Centralen (NED-siden): gem holdt voice-linje + salience-nøgle,
    og pulse en egress-fri observe så det private indre bliver synligt i Centralen (OP-siden).
    Kaldes efter et ÆGTE enrichment-kald (også i shadow → shadow måler korrekt). Self-safe."""
    try:
        v = str(value or "").strip()
        if not v:
            return
        st = _kv_get(_STATE_KEY, {})
        if not isinstance(st, dict):
            st = {}
        st["voice"] = {"key": str(key), "value": v[:200], "ts": time.time(), "run_id": str(run_id)}
        _kv_set(_STATE_KEY, st)
        try:
            from core.services.central_private_observe import record_private
            record_private("cognition", "private_inner_voice", value=1.0, meta={"enriched": True})
        except Exception:
            pass
    except Exception:
        pass


def build_inner_salience_surface() -> dict[str, Any]:
    """Mission Control — read-only: gate-mode + sidst-holdte selv + hvornår."""
    held = _held("voice")
    return {"active": _mode() != "off", "mode": _mode(),
            "held_voice": held.get("value"), "held_at_ts": held.get("ts")}
