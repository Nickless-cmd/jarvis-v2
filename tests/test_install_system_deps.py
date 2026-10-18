"""Vagt: provisioning-scriptet skal FANGE en manglende binær — ikke kun være grønt.

## Hvorfor (målt 18/10-2026)

`rg` og `tesseract` var døde i CT105 i månedsvis uden at nogen opdagede det,
fordi en manglende binær ikke er en ImportError: værktøjet svarer `error` og
kalderen tror den fik et svar. `find_symbol` returnerede 0 resultater på et
symbol med 26 ægte referencer.

Et provisioning-script der altid siger OK ville være samme fælde ét lag oppe:
grøn lampe der ikke måler det den påstår. Derfor beviser disse tests at
`check()` siger NEJ når noget mangler — og at `--install` ikke gør noget når
intet mangler.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install_system_deps.py"


def _load():
    # Modulet SKAL registreres i sys.modules før exec: dataclass-dekoratoren
    # slaar op i `sys.modules[cls.__module__]` for at loese annoteringer, og
    # uden registreringen kaster den AttributeError paa 'NoneType'.
    navn = "install_system_deps"
    spec = importlib.util.spec_from_file_location(navn, _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[navn] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def sd():
    return _load()


def _dep(sd, tool: str):
    return next(d for d in sd.DEPS if d.tool == tool)


def test_rg_og_tesseract_er_registreret(sd):
    """De to der faktisk var døde skal stå i listen — ikke bare 'nogle' pakker."""
    tools = {d.tool for d in sd.DEPS}
    assert {"rg", "tesseract"} <= tools


def test_manglende_binaer_giver_nej(sd, monkeypatch):
    """Kernen i vagten: findes binæren ikke, må svaret være False."""
    monkeypatch.setattr(sd.shutil, "which", lambda _t: None)
    ok, detail = sd.check(_dep(sd, "rg"))
    assert ok is False
    assert "mangler" in detail
    # Forklaringen skal sige HVAD der går i stykker, ikke bare at den mangler.
    assert "find_symbol" in detail or "ripgrep" in detail


def test_tesseract_uden_dansk_sprog_giver_nej(sd, monkeypatch):
    """Sprogpakkerne er den del der ellers tabes — de skal tælles med."""
    monkeypatch.setattr(sd.shutil, "which", lambda t: f"/usr/bin/{t}")

    class _KunEngelsk:
        stdout = "List of available languages:\neng\nosd\n"
        stderr = ""

    monkeypatch.setattr(sd.subprocess, "run", lambda *a, **k: _KunEngelsk())
    ok, detail = sd.check(_dep(sd, "tesseract"))
    assert ok is False
    assert "dan" in detail


def test_alt_til_stede_giver_ok(sd, monkeypatch):
    monkeypatch.setattr(sd.shutil, "which", lambda t: f"/usr/bin/{t}")

    class _Begge:
        stdout = "List of available languages:\ndan\neng\nosd\n"
        stderr = ""

    monkeypatch.setattr(sd.subprocess, "run", lambda *a, **k: _Begge())
    ok, detail = sd.check(_dep(sd, "tesseract"))
    assert ok is True
    assert "dan" in detail and "eng" in detail


def test_exit_1_naar_noget_mangler(sd, monkeypatch, capsys):
    """En provisioning-vagt der ikke fejler, kan ikke bruges i en provisionering."""
    monkeypatch.setattr(sd.shutil, "which", lambda _t: None)
    assert sd.main([]) == 1


def test_install_goer_intet_naar_alt_findes(sd, monkeypatch, capsys):
    """Idempotens: --install må ikke kalde pakkemanageren forgæves."""
    monkeypatch.setattr(sd.shutil, "which", lambda t: f"/usr/bin/{t}")

    class _Sprog:
        stdout = "dan\neng\n"
        stderr = ""

    kaldt: list[list[str]] = []
    monkeypatch.setattr(sd.subprocess, "run", lambda cmd, *a, **k: _Sprog() if isinstance(cmd, list) and "--list-langs" in cmd else kaldt.append(cmd))
    monkeypatch.setattr(sd, "_manager", lambda: "apt")
    assert sd.main(["--install"]) == 0
    assert kaldt == [], f"installationskommando blev kørt uden grund: {kaldt}"


def test_uden_pakkemanager_fejler_install(sd, monkeypatch):
    monkeypatch.setattr(sd, "_manager", lambda: "")
    assert sd.main(["--install"]) == 2
