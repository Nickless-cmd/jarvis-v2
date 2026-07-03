"""core/services/central_form_judge.py

DEN CENTRALE FORM-ÆNDRINGS-DOMMER (Bjørn 3. jul): "hele hans liv genopbygges på hver prompt...
Centralen holder alt til at vurdere når der skal laves et par LLM-kald — kun når data ændrer FORM,
ikke ved gentagelse." Dette er §6.1b/Bölge 1 gjort general: ÉN dommer som alle LLM-brugende lag —
især daemon_llm-choke-pointet (69 daemons) — spørger FØR de bruger et kald:

    "Har min input ændret FORM siden sidst? Nej → genbrug det holdte. Ja → brug kaldet."

FORM ≠ eksakt tekst. Den eksisterende cache er SHA256(rå prompt) = eksakt-match → misser næsten
altid fordi prompten indeholder volatil kontekst (tid, humør-tal, hændelses-id'er). Form-nøglen
STRIPPER det volatile (tal, timestamps, tider) → to prompts der kun adskiller sig i volatile detaljer
får SAMME form-nøgle → gentagelse fanges. Det er dér gentagelses-spildet sidder.

GOVERNANCE: flag `central_form_judge_mode` (runtime-state kv): off|shadow|on. DEFAULT off.
  off    → uændret (dommeren siger aldrig reuse).
  shadow → beregn + observe would_reuse (mål gentagelses-raten), men brug kaldet ALLIGEVEL.
  on     → genbrug holdt resultat når formen er uændret (inden TTL) → INTET LLM-kald.
Self-safe: enhver tvivl/fejl → reuse=False (kald som før). Måler til central_timeseries cost/form_judge.
"""
from __future__ import annotations

import hashlib
import re
import threading
import time
from typing import Any

_MODE_KEY = "central_form_judge_mode"
_TTL_SECONDS = 900.0          # genbrug kun hvis samme form er set inden for 15 min
_MAX_KEYS_PER_NS = 16          # bounded pr. namespace (daemon)
_lock = threading.Lock()
_held: dict[str, dict[str, dict[str, Any]]] = {}   # namespace → form_key → {value, ts}

# Volatile mønstre der IKKE hører til "formen" (fjernes før form-nøglen dannes):
_ISO_TS = re.compile(r"\d{4}-\d{2}-\d{2}[ tT]\d{2}:\d{2}(:\d{2})?(\.\d+)?(z|[+-]\d{2}:?\d{2})?", re.I)
_CLOCK = re.compile(r"\b\d{1,2}:\d{2}(:\d{2})?\b")
_NUM = re.compile(r"\d+([.,]\d+)?")
_WS = re.compile(r"\s+")


def _kv_get(key: str, default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return v if v is not None else default
    except Exception:
        return default


def _mode() -> str:
    m = str(_kv_get(_MODE_KEY, "off") or "off").strip().lower()
    return m if m in ("off", "shadow", "on") else "off"


def form_key(text: str) -> str:
    """Reducér en prompt til dens FORM: fjern timestamps/tider/tal, normalisér whitespace, hash.
    To prompts der kun adskiller sig i volatile detaljer → samme form-nøgle."""
    t = str(text or "")
    t = _ISO_TS.sub(" ", t)
    t = _CLOCK.sub(" ", t)
    t = _NUM.sub("#", t)          # alle tal → ét symbol (formen bevares, værdien fjernes)
    t = _WS.sub(" ", t).strip().lower()
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def _observe(namespace: str, would_reuse: bool, mode: str) -> None:
    try:
        from core.services import central_timeseries as ts
        ts.record("cost", "form_judge", value=(1.0 if would_reuse else 0.0),
                  meta={"ns": str(namespace)[:40], "would_reuse": bool(would_reuse), "mode": mode})
    except Exception:
        pass


def judge(namespace: str, prompt: str) -> dict[str, Any]:
    """Dom FØR et LLM-kald: skal formen genudledes, eller er den uændret siden sidst?
    Returnerer {reuse: bool, held: str|None, would_reuse: bool, mode: str}. Self-safe."""
    try:
        mode = _mode()
        if mode == "off":
            return {"reuse": False, "held": None, "would_reuse": False, "mode": "off"}
        ns = str(namespace or "daemon")
        fk = form_key(prompt)
        with _lock:
            entry = (_held.get(ns) or {}).get(fk)
        fresh = bool(entry and entry.get("value") is not None
                     and (time.time() - float(entry.get("ts") or 0.0)) < _TTL_SECONDS)
        _observe(ns, fresh, mode)
        if mode == "on" and fresh:
            return {"reuse": True, "held": entry.get("value"), "would_reuse": True, "mode": "on"}
        return {"reuse": False, "held": None, "would_reuse": fresh, "mode": mode}
    except Exception:
        return {"reuse": False, "held": None, "would_reuse": False, "mode": "off"}


def note_result(namespace: str, prompt: str, value: str) -> None:
    """Gem et friskt LLM-resultat under dets form-nøgle, så en uændret form kan genbruges. Bounded,
    self-safe. Kaldes efter ethvert ægte kald (også i shadow → shadow måler korrekt)."""
    try:
        v = str(value or "").strip()
        if not v:
            return
        ns = str(namespace or "daemon")
        fk = form_key(prompt)
        with _lock:
            d = _held.setdefault(ns, {})
            d[fk] = {"value": v, "ts": time.time()}
            if len(d) > _MAX_KEYS_PER_NS:   # smid ældste ud (bounded hukommelse)
                oldest = min(d.items(), key=lambda kv: kv[1].get("ts") or 0.0)[0]
                d.pop(oldest, None)
    except Exception:
        pass


def snapshot() -> dict[str, Any]:
    """Read-only: pr. namespace antal holdte former + mode. Til analyse/Mission Control."""
    try:
        with _lock:
            return {"mode": _mode(),
                    "namespaces": {ns: len(d) for ns, d in sorted(_held.items())}}
    except Exception:
        return {"mode": "off", "namespaces": {}}


def _reset_for_tests() -> None:
    with _lock:
        _held.clear()
