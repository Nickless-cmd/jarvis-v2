"""Hvert felt i RuntimeSettings skal både indlæses og kunne ses/ændres.

Målt 19/9-2026: to_dict() manglede 102 felter (update_setting validerer mod
den, så fx R2.5's tærskler kunne ikke ændres), 17 felter blev aldrig indlæst
fra runtime.json (fx kill-switchen decision_signals_enabled), og bool-felter
blev læst med bool(), så teksten "false" betød True.
"""
from __future__ import annotations

import json
from dataclasses import fields

import pytest


def _anden_vaerdi(std):
    if isinstance(std, bool):
        return not std
    if isinstance(std, int):
        return std + 7
    if isinstance(std, float):
        return round(std + 0.37, 4)
    if isinstance(std, str):
        return (std or "x") + "-testværdi"
    return None


def _skriv(data: dict) -> None:
    from core.runtime.config import SETTINGS_FILE
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data), encoding="utf-8")


def test_to_dict_har_hvert_felt(isolated_runtime):
    from core.runtime.settings import RuntimeSettings
    d = RuntimeSettings().to_dict()
    mangler = [f.name for f in fields(RuntimeSettings) if f.name != "extra" and f.name not in d]
    assert mangler == []


def test_hvert_felt_indlaeses_fra_runtime_json(isolated_runtime):
    from core.runtime.settings import RuntimeSettings, load_settings
    std = RuntimeSettings()
    ønsket = {}
    for f in fields(RuntimeSettings):
        if f.name == "extra":
            continue
        v = _anden_vaerdi(getattr(std, f.name))
        if v is not None:
            ønsket[f.name] = v
    _skriv(ønsket)
    s = load_settings()
    forkerte = {n: (getattr(s, n), v) for n, v in ønsket.items() if getattr(s, n) != v}
    assert forkerte == {}, f"felter der ikke indlæses: {sorted(forkerte)}"


@pytest.mark.parametrize("tekst,forventet", [
    ("false", False), ("False", False), ("0", False), ("nej", False), ("", False),
    ("true", True), ("True", True), ("1", True), ("ja", True), ("on", True),
])
def test_bool_som_tekst_betyder_det_der_staar(isolated_runtime, tekst, forventet):
    from core.runtime.settings import load_settings
    _skriv({"decision_signals_enabled": tekst, "selvmodel_enabled": tekst})
    s = load_settings()
    assert s.decision_signals_enabled is forventet
    assert s.selvmodel_enabled is forventet


def test_update_setting_kan_aendre_r2_5_taerskler(isolated_runtime):
    from core.tools.simple_tools_native import _exec_update_setting
    from core.runtime.settings import load_settings
    _skriv({})
    r = _exec_update_setting({"key": "r2_5_activity_ceiling", "value": 4})
    assert r.get("new") == 4, r
    assert load_settings().r2_5_activity_ceiling == 4
