"""At udskifte `bus.event_bus` i en test lækker ud af testen.

MÅLT 26/9-2026. `tests/test_central_growth_observe.py::test_tick_returns_ok`
gjorde `monkeypatch.setattr(bus, "event_bus", _Bus())`. Den tick den kalder
importerer `core.services.sensory_archive` — og hvis det sker mens attrappen
står i modulet, binder `sensory_archive` attrappen med sit
`from core.eventbus.bus import event_bus` FOR ALTID. `monkeypatch` gendanner
`bus.event_bus`, men aldrig kopien inde i det modul der nåede at importere den.

Følgen: `test_sensory_perception_creates_emotional_memory_anchor` publicerede
ind i attrappen, `event_bus.recent()` gav 0 i stedet for 1, og der blev aldrig
skabt et anker. Testen var rød i den fulde suite og grøn alene — i ugevis, og
den overlevede to sessioner som «kendt flake».

Rettelsen er at lappe METODEN på det ægte objekt
(`monkeypatch.setattr(bus.event_bus, "recent_by_family", ...)`). Så ser enhver
der holder bussen — før eller efter — lappen, og `monkeypatch` ruller den
tilbage.

Denne vagt er en BASELINE, som `verify_silent_except`: de filer der gjorde det
i forvejen står på listen, så de er synlig gæld frem for usynlig. Nye må ikke
komme til, og retter man en, skal den ud af listen — ellers rådner listen.
"""
from __future__ import annotations

import ast
import pathlib

#: Filer der udskifter singletonen. Hver er en tidsbombe af samme slags: den
#: udløses den dag et modul importeres FØRSTE gang inde i netop dét vindue.
#: Ret én, og fjern den herfra.
GRUNDLINJE = {
    "tests/test_bus.py",
    "tests/test_central_coverage.py",
    "tests/test_central_coverage_action.py",
    "tests/test_central_hypothesis_sampler.py",
    "tests/test_db_session_ledger.py",
    "tests/test_eventbus_central_bridge.py",
    "tests/test_existential_wonder_daemon.py",
    "tests/test_forced_tool_choice_probe.py",
    "tests/test_notification_bridge.py",
    "tests/test_openrouter_image_tools.py",
    "tests/test_r2_5_blocking_gate.py",
    "tests/test_session_inbox.py",
}


def _filer_der_udskifter() -> set[str]:
    fundne: set[str] = set()
    for p in sorted(pathlib.Path("tests").rglob("*.py")):
        try:
            traeet = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:  # en fil vi ikke kan parse er ikke vagtens aerinde
            continue
        for n in ast.walk(traeet):
            if not isinstance(n, ast.Call):
                continue
            if (getattr(n.func, "attr", "") or getattr(n.func, "id", "")) != "setattr":
                continue
            if len(n.args) < 2:
                continue
            maal = n.args[1]
            if isinstance(maal, ast.Constant) and maal.value == "event_bus":
                fundne.add(str(p))
    return fundne


def test_ingen_NYE_filer_udskifter_singletonen():
    nye = sorted(_filer_der_udskifter() - GRUNDLINJE)
    assert not nye, (
        f"{nye} udskifter `bus.event_bus`. Et modul der importeres foerste gang "
        "i det vindue binder attrappen for altid. Lap METODEN paa det aegte "
        "objekt i stedet: "
        "`monkeypatch.setattr(bus.event_bus, '<metode>', ..., raising=False)`"
    )


def test_grundlinjen_raadner_ikke():
    """Retter nogen en fil, skal den ud af listen — ellers vokser gælden i det skjulte."""
    forsvundne = sorted(GRUNDLINJE - _filer_der_udskifter())
    assert not forsvundne, (
        f"{forsvundne} udskifter ikke laengere singletonen — fjern dem fra "
        "GRUNDLINJE, saa listen bliver ved at vaere sand"
    )


def test_den_der_faktisk_bed_er_rettet():
    """`test_central_growth_observe.py` forurenede en anden fil. Den er ude."""
    assert "tests/test_central_growth_observe.py" not in _filer_der_udskifter()
    assert "tests/test_central_growth_observe.py" not in GRUNDLINJE
