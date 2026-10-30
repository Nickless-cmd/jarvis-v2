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


# ── Force-stien må ikke springe læs-før-skriv over ────────────────────────
# Målt 29/10-2026: `_force_write_file` og `_force_edit_file` kaldte
# `check_file(..., blocked_only=True)`, og den gren returnerer GRØNT før
# læs-før-skriv-linjen i `gate_execution._decide`. Synlige og autonome kørsler
# går gennem force-stien (`simple_tool_executor`, force=True) — så vagten
# blokerede kun den vej ingen brugte. Den var teater i den ene vej der tæller.
#
# Filens egen docstring sagde det hele tiden: «Force betyder spring
# GODKENDELSEN over — ikke spring sikkerheden over.»


@pytest.mark.parametrize("vaerktoej", ["write_file", "edit_file"])
def test_force_stien_blokerer_ulaest_kodefil(vaerktoej, tmp_path):
    """Ulæst .py gennem force-stien skal blokeres — ikke skrives."""
    from core.tools.simple_tools import execute_tool_force

    maal = tmp_path / "ulaest.py"
    maal.write_text("x = 1\n", encoding="utf-8")

    args = {"path": str(maal), "_runtime_session_id": "force-probe-ulaest"}
    if vaerktoej == "write_file":
        args["content"] = "x = 999\n"
    else:
        args.update(old_text="x = 1", new_text="x = 999")

    r = execute_tool_force(vaerktoej, args)

    assert r.get("status") == "guard_blocked", (
        "%s skrev en ulæst kodefil gennem force-stien — vagten blev sprunget over: %r"
        % (vaerktoej, r)
    )
    # Det afgørende bevis: filen er UÆNDRET. En blokering der alligevel skriver
    # er værre end ingen vagt, fordi den ser ud som om den virker.
    assert maal.read_text(encoding="utf-8") == "x = 1\n"


def test_force_stien_slipper_laest_kodefil(tmp_path):
    """Den anden side: har jeg læst filen i sessionen, skal redigeringen gå igennem.

    Uden denne pinner testen kun blokeringen, og en vagt der blokerer ALT
    ville også være grøn.
    """
    from core.tools.simple_tools import execute_tool_force

    sid = "force-probe-laest"
    maal = tmp_path / "laest.py"
    maal.write_text("x = 1\n", encoding="utf-8")

    assert execute_tool_force(
        "read_file", {"path": str(maal), "_runtime_session_id": sid}
    ).get("status") == "ok"

    r = execute_tool_force("edit_file", {
        "path": str(maal), "old_text": "x = 1", "new_text": "x = 2",
        "_runtime_session_id": sid,
    })
    assert r.get("status") == "ok", r
    assert maal.read_text(encoding="utf-8") == "x = 2\n"


def test_force_stien_slipper_ny_fil_og_markdown(tmp_path):
    """Nye filer har intet at clobbe, og .md er bevidst uden for vagten."""
    from core.tools.simple_tools import execute_tool_force

    sid = "force-probe-ny"
    ny = tmp_path / "helt_ny.py"
    note = tmp_path / "note.md"
    note.write_text("# gammel\n", encoding="utf-8")

    assert execute_tool_force(
        "write_file", {"path": str(ny), "content": "y = 3\n", "_runtime_session_id": sid}
    ).get("status") == "ok"
    assert execute_tool_force(
        "write_file", {"path": str(note), "content": "# ny\n", "_runtime_session_id": sid}
    ).get("status") == "ok"
    assert note.read_text(encoding="utf-8") == "# ny\n"

