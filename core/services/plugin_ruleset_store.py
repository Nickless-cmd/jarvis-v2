"""Persistens for plugin-regelsæt (spec §5.3/§5.4, Fase 6 #2).

plugin_ruleset.is_allowed() tager et regelsæt-dict; denne store holder de
bruger-definerede regelsæt pr. kanal-plugin, så gateways kan slå dem op på inbound
og Settings-UI'en kan redigere dem.

DB-backed (runtime_state_kv) — cross-proces (api↔runtime). Ét dict under én nøgle:
{plugin_id → ruleset}. Regelsæt-felter (alle valgfrie): allowed_channels,
blocked_roles, quiet_hours [start,end], rate_limits {channel: max}.

Bagdørs-/privatlivs-note: regelsæt er hardblock for ALLE inkl. owner (§5.3) — denne
store ændrer ikke på det; den leverer bare data til plugin_ruleset.is_allowed.
"""
from __future__ import annotations

from core.runtime.db import get_runtime_state_value, set_runtime_state_value

_KEY = "plugin_rulesets"

_ALLOWED_FIELDS = ("allowed_channels", "blocked_roles", "quiet_hours", "rate_limits")


def _load_all() -> dict:
    raw = get_runtime_state_value(_KEY, {})
    return raw if isinstance(raw, dict) else {}


def get_ruleset(plugin_id: str) -> dict:
    """Regelsæt for et kanal-plugin ({} hvis intet sat)."""
    pid = str(plugin_id or "").strip()
    if not pid:
        return {}
    rs = _load_all().get(pid)
    return rs if isinstance(rs, dict) else {}


def set_ruleset(plugin_id: str, ruleset: dict) -> dict:
    """Gem/erstat regelsættet for et plugin. Returnér det gemte (rensede) regelsæt.

    Kun kendte felter beholdes (defensiv mod vilkårlig payload fra UI).
    """
    pid = str(plugin_id or "").strip()
    if not pid:
        return {}
    clean = {k: v for k, v in (ruleset or {}).items() if k in _ALLOWED_FIELDS}
    allp = _load_all()
    allp[pid] = clean
    set_runtime_state_value(_KEY, allp)
    return clean


def list_rulesets() -> dict:
    """Alle regelsæt {plugin_id → ruleset} (til Settings-UI)."""
    return _load_all()
