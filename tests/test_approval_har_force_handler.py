"""Ethvert værktøj der kan bede om godkendelse SKAL kunne køres bagefter.

Fejlen der gav testen (7/9-2026, målt på Bjørns telefon): `phone_adb_shell`
returnerede `approval_needed`, Bjørn godkendte — og kaldet kom tilbage som
afventende igen. Og igen.

Årsagen er `execute_tool_force`:

    handler = _FORCE_HANDLERS.get(name) or _TOOL_HANDLERS.get(name)

Uden en force-handler falder den tilbage til den NORMALE handler og kalder den
med de OPRINDELIGE argumenter — altså uden `_runtime_trust_all`. Handleren
rammer sin egen approval-gren igen og svarer `approval_needed` på ny.
Godkendelsen kom frem; handlingen skete bare aldrig.

Fejlen er tavs på den værste måde: intet kaster, intet logges som fejl, og
brugeren ser en godkendelses-dialog der bare kommer tilbage. Derfor er den her
en invariant over ALLE værktøjer og ikke en test af ét.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_ROD = Path(__file__).resolve().parents[1] / "core" / "tools"

# Dicts der beder om godkendelse har formen
#     {"status": "approval_needed", "tool_name": "X", ...}
# — feltrækkefølgen varierer, så vi leder efter tool_name i et vindue omkring
# approval_needed frem for at kræve en bestemt rækkefølge.
_APPROVAL = re.compile(r'"status":\s*"approval_needed"')
_TOOLNAME = re.compile(r'"tool_name":\s*"([a-z0-9_]+)"')
_VINDUE = 400


def _vaerktoejer_der_beder_om_godkendelse() -> set[str]:
    fundne: set[str] = set()
    for sti in sorted(_ROD.glob("*.py")):
        tekst = sti.read_text(encoding="utf-8", errors="replace")
        for m in _APPROVAL.finditer(tekst):
            omkring = tekst[max(0, m.start() - _VINDUE): m.end() + _VINDUE]
            for navn in _TOOLNAME.findall(omkring):
                fundne.add(navn)
    return fundne


def test_scanneren_finder_faktisk_noget():
    """Et regex der er holdt op med at matche ville gøre testen nedenfor grøn
    og betydningsløs — den slags tavshed er præcis det vi tester imod."""
    fundne = _vaerktoejer_der_beder_om_godkendelse()
    assert len(fundne) >= 5, "scanneren fandt kun %s — er formen ændret?" % sorted(fundne)
    assert "phone_adb_shell" in fundne


def test_alle_godkendelses_vaerktoejer_har_en_force_handler():
    from core.tools.simple_tools import _FORCE_HANDLERS

    mangler = sorted(_vaerktoejer_der_beder_om_godkendelse() - set(_FORCE_HANDLERS))
    assert not mangler, (
        "Disse værktøjer beder om godkendelse men har ingen force-handler, så "
        "en godkendelse løber i ring i stedet for at udføre handlingen: %s"
        % mangler
    )


@pytest.mark.parametrize("navn", ["phone_adb_shell", "phone_adb_screenshot"])
def test_force_handleren_beder_ikke_om_godkendelse_igen(navn, monkeypatch):
    """Det konkrete symptom: samme svar, anden gang.

    Force-handleren skal sætte `_runtime_trust_all`, ellers rammer den samme
    gren som første gang.
    """
    from core.tools import phone_adb as A
    from core.tools.simple_tools import execute_tool_force

    monkeypatch.setattr(A, "_adresse", lambda args=None: "10.0.0.1:5555")
    monkeypatch.setattr(A, "_koer_adb", lambda argv, **k: {"status": "ok", "stdout": "ok"})
    monkeypatch.setattr(A, "_adb_sti", lambda: "/usr/bin/adb")

    r = execute_tool_force(navn, {"kommando": "getprop ro.product.model"})
    assert r.get("status") != "approval_needed", (
        "%s bad om godkendelse IGEN efter at være blevet godkendt" % navn
    )
