"""Central governance flag-register (Backend A1).

Governeret læse/skrive-kanal for Centralens governance-flags. I dag kan disse
flags KUN flippes ved at håndredigere runtime.json — der findes ingen API.
Dette modul er det rene logik-lag: et flag-register + ``list_flags()`` (læs
nuværende værdier) + ``set_flag(key, value, confirm)`` (skriv, med confirm-krav
på FARLIGE flags). En senere task wirer en HTTP-route ovenpå.

Self-safe: læsning kaster ALDRIG (falder tilbage til default); skrivning fanger
og returnerer en status-dict. ``list_flags`` og ``set_flag`` kaster aldrig.

Design:
- ``_FLAGS``: key → spec {label, kind, dangerous, kv_key, options, writer}
- ``_kv_get`` / ``_kv_set`` wrapper runtime-state (self-safe). Tests
  monkeypatcher disse.
- Plain runtime-state-flags skriver via ``_kv_set(kv_key, value)``.
- Injection-flags skriver via ``set_injection_live`` (lazy, self-safe).
- Healer-flags skriver via ``set_healer_flag`` (lazy, self-safe).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Self-safe runtime-state kv-helpers (matcher central_self_state.py-mønster).
# Tests monkeypatcher _kv_get / _kv_set.
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Writers (lazy + self-safe). Returnerer intet — kald pakkes i try i set_flag,
# men holdes også selv-sikre her så et brækket setter-modul ikke vælter os.
# ---------------------------------------------------------------------------

def _write_kv(kv_key: str) -> Callable[[Any], None]:
    """Plain runtime-state-writer der går gennem _kv_set (monkeypatch-bart)."""
    def _w(value: Any) -> None:
        _kv_set(kv_key, value)
    return _w


def _write_injection(inj_key: str) -> Callable[[Any], None]:
    def _w(value: Any) -> None:
        try:
            from core.services.central_injection_registry import set_injection_live
            set_injection_live(inj_key, bool(value))
        except Exception:
            pass
    return _w


def _write_healer(healer_name: str) -> Callable[[Any], None]:
    def _w(value: Any) -> None:
        try:
            from core.services.error_healers import set_healer_flag
            set_healer_flag(healer_name, bool(value))
        except Exception:
            pass
    return _w


# ---------------------------------------------------------------------------
# Flag-register.
#   kind:      "bool" | "enum"
#   kv_key:    runtime-state-nøgle til LÆSNING via _kv_get (None for injection —
#              de læses via injection_live)
#   inj_key:   injection-registry-nøgle (kun injection-flags)
#   options:   gyldige enum-værdier (kun enum)
#   dangerous: kræver confirm=True før skrivning
#   writer:    Callable[[value], None]
# ---------------------------------------------------------------------------

_FLAGS: Dict[str, Dict[str, Any]] = {
    # --- injection (NOT dangerous) — læses via injection_live ---
    "injection:rule_conclusions": {
        "label": "Injection: rule conclusions",
        "kind": "bool",
        "dangerous": False,
        "kv_key": None,
        "inj_key": "rule_conclusions",
        "writer": _write_injection("rule_conclusions"),
    },
    "injection:cognitive_state": {
        "label": "Injection: cognitive state",
        "kind": "bool",
        "dangerous": False,
        "kv_key": None,
        "inj_key": "cognitive_state",
        "writer": _write_injection("cognitive_state"),
    },
    # --- plain runtime-state ---
    "lag4_live": {
        "label": "Lag-4 adaptation live",
        "kind": "bool",
        "dangerous": True,
        "kv_key": "central_lag4_live_enabled",
        "default": False,
        "writer": _write_kv("central_lag4_live_enabled"),
    },
    "gut_consumer_mode": {
        "label": "Gut consumer mode",
        "kind": "enum",
        "dangerous": True,
        "kv_key": "central_gut_consumer_mode",
        "default": "off",
        "options": ["off", "shadow", "on"],
        "writer": _write_kv("central_gut_consumer_mode"),
    },
    "agenda_authoritative": {
        "label": "Agenda authoritative",
        "kind": "bool",
        "dangerous": True,
        "kv_key": "central_agenda_authoritative_enabled",
        "default": False,
        "writer": _write_kv("central_agenda_authoritative_enabled"),
    },
    "self_prompt": {
        "label": "Central self-prompt",
        "kind": "bool",
        "dangerous": False,
        "kv_key": "central_self_prompt_enabled",
        "default": False,
        "writer": _write_kv("central_self_prompt_enabled"),
    },
    "generative_autonomy": {
        "label": "Generative autonomy",
        "kind": "bool",
        "dangerous": True,
        "kv_key": "generative_autonomy_enabled",
        "default": False,
        "writer": _write_kv("generative_autonomy_enabled"),
    },
    # --- healer-flags (skrives via set_healer_flag, læses via runtime-state) ---
    "healer_enabled": {
        "label": "Error healer enabled",
        "kind": "bool",
        "dangerous": True,
        "kv_key": "error_healer.enabled",
        "default": False,
        "writer": _write_healer("enabled"),
    },
    "healer_daemon_restart_live": {
        "label": "Healer: daemon restart live",
        "kind": "bool",
        "dangerous": True,
        "kv_key": "error_healer.daemon_restart_live",
        "default": False,
        "writer": _write_healer("daemon_restart_live"),
    },
    "healer_syslog_restart_live": {
        "label": "Healer: syslog restart live",
        "kind": "bool",
        "dangerous": True,
        "kv_key": "error_healer.syslog_restart_live",
        "default": False,
        "writer": _write_healer("syslog_restart_live"),
    },
}


def _read_value(key: str, spec: Dict[str, Any]) -> Any:
    """Self-safe læsning af nuværende værdi for ét flag."""
    try:
        inj_key = spec.get("inj_key")
        if inj_key is not None:
            try:
                from core.services.central_injection_registry import injection_live
                return bool(injection_live(inj_key))
            except Exception:
                return False
        kv_key = spec.get("kv_key")
        default = spec.get("default", False)
        if kv_key is None:
            return default
        return _kv_get(kv_key, default)
    except Exception:
        return spec.get("default", False)


def list_flags() -> List[Dict[str, Any]]:
    """Returnér alle flags med nuværende værdi + danger-flag. Kaster aldrig."""
    out: List[Dict[str, Any]] = []
    try:
        for key, spec in _FLAGS.items():
            try:
                out.append({
                    "key": key,
                    "label": spec.get("label", key),
                    "kind": spec.get("kind", "bool"),
                    "dangerous": bool(spec.get("dangerous", False)),
                    "value": _read_value(key, spec),
                    "options": spec.get("options"),
                })
            except Exception:
                # Et enkelt brækket flag må ikke vælte hele listen.
                out.append({
                    "key": key,
                    "label": spec.get("label", key),
                    "kind": spec.get("kind", "bool"),
                    "dangerous": bool(spec.get("dangerous", False)),
                    "value": spec.get("default", False),
                    "options": spec.get("options"),
                })
    except Exception:
        pass
    return out


def _coerce_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "1", "on", "yes"):
            return True
        if low in ("false", "0", "off", "no"):
            return False
    if isinstance(value, (int,)) and value in (0, 1):
        return bool(value)
    return None


def set_flag(key: str, value: Any, confirm: bool = False) -> Dict[str, Any]:
    """Skriv ét flag governeret. Kaster aldrig — returnerer status-dict.

    - ukendt key            → {ok:False, error:"ukendt flag: <key>"}
    - enum m. dårlig værdi   → {ok:False, error:...}
    - bool m. ucoercbar     → {ok:False, error:...}
    - dangerous & ikke confirm → {ok:False, needs_confirm:True}
    - ellers                → writer + {ok:True, key, value}
    """
    try:
        spec = _FLAGS.get(key)
        if spec is None:
            return {"ok": False, "error": f"ukendt flag: {key}"}

        kind = spec.get("kind", "bool")

        # Validér værdi FØR confirm-gate (så en dårlig værdi ikke maskeres).
        if kind == "enum":
            options = spec.get("options") or []
            if value not in options:
                return {
                    "ok": False,
                    "error": f"ugyldig værdi for {key}: {value!r} (gyldige: {options})",
                }
            coerced: Any = value
        else:
            coerced = _coerce_bool(value)
            if coerced is None:
                return {
                    "ok": False,
                    "error": f"ugyldig bool-værdi for {key}: {value!r}",
                }

        # Danger-gate.
        if spec.get("dangerous", False) and not confirm:
            return {
                "ok": False,
                "needs_confirm": True,
                "key": key,
                "value": coerced,
                "error": f"flag {key} er farligt — kræver confirm=True",
            }

        # Skriv (self-safe).
        try:
            writer = spec.get("writer")
            if writer is None:
                return {"ok": False, "error": f"ingen writer for flag: {key}"}
            writer(coerced)
        except Exception as exc:  # pragma: no cover — writer er selv self-safe
            return {"ok": False, "error": f"skrivning fejlede: {exc}"}

        return {"ok": True, "key": key, "value": coerced}
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": f"uventet fejl: {exc}"}


# ---------------------------------------------------------------------------
# Audit-hook for governerede mutationer (eventbus + Central-observe).
# Kaldes af HTTP-routes EFTER en vellykket skrivning (governance/healers/…).
# Self-safe: kaster ALDRIG — audit må aldrig vælte en ellers vellykket write.
# ---------------------------------------------------------------------------

def record_mutation(area: str, key: str, value: Any) -> None:
    """Registrér en governeret mutation som eventbus-event + Central-nerve.

    ``area`` = domænet (fx "governance", "healing"); ``key`` = flag-navn;
    ``value`` = ny værdi. Self-safe.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "central.mutation",
            {"area": area, "key": key, "value": value},
        )
    except Exception:
        pass
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": area,
            "nerve": f"mutation/{key}",
            "kind": "mutation",
            "area": area,
            "key": key,
            "value": value,
        })
    except Exception:
        pass
