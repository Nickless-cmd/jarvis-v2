"""Paritet mellem server-guardens bind-sti og klientens ``gyldigBindSti``.

DIL lag 1 (commit 723d9dde7) tilføjede ``_sti_dele`` i ``core/services/jarvis_ui_guard.py``
med docstringen «Python-spejl af ``gyldigBindSti`` i desk-klienten». Der findes dermed TRE
kopier af samme grammatik: ``apps/jarvis-desk/src/lib/udtryk.ts``, ``apps/mobile/src/lib/udtryk.ts``
og Python-spejlen.

Uden denne vagt er en divergens TAVS: ændrer nogen TS-siden, vil serveren opløse stier
klienten afviser — eller afvise stier klienten accepterer — uden at nogen test fanger det.

Kilderne til sandheden er:
  * ``apps/jarvis-desk/src/lib/udtryk.ts:68`` — ``gyldigBindSti`` (NAVN_RE, RESERVERET)
  * ``apps/jarvis-desk/src/lib/udtryk.test.ts:153-162`` — de cases klienten selv kræver
"""

from __future__ import annotations

import pytest

from core.services.jarvis_ui_guard import _sti_dele


# Præcis de cases som ``apps/jarvis-desk/src/lib/udtryk.test.ts:153-162`` dækker.
# Ændres klient-testen, skal denne tabel følge med — det er hele pointen.
KLIENTENS_CASES: tuple[tuple[str, bool], ...] = (
    ("pris", True),
    ("pris_a", True),
    ("_pris", True),
    ("objekt.a", True),
    ("liste[0]", True),
    ("liste[0].navn", True),
    ("", False),
)


@pytest.mark.parametrize(("sti", "gyldig"), KLIENTENS_CASES)
def test_klientens_egne_cases(sti: str, gyldig: bool) -> None:
    assert (_sti_dele(sti) is not None) is gyldig


# Kanttilfælde som TS-implementationen afviser strukturelt. De er ikke i klient-testen,
# men følger af dens regler: hvert navnesegment skal matche ``[a-zA-Z_][a-zA-Z0-9_]*``,
# indeks skal være ikke-negative heltal, og ``state`` må ikke være første segment.
KANT_CASES: tuple[tuple[str, bool], ...] = (
    (".pris", False),      # punktum før første navn
    ("pris.", False),      # punktum uden efterfølgende navn
    ("a..b", False),       # dobbelt punktum
    ("[0]", False),        # indeks uden navn foran (TS: ``if (forste) return false``)
    ("a[", False),         # uafsluttet indeks
    ("a[]", False),        # tomt indeks
    ("liste[-1]", False),  # negativt indeks
    ("state", False),      # RESERVERET første segment
    ("state.x", False),    # RESERVERET første segment
    ("a[b]", False),       # ikke-numerisk indeks
)


@pytest.mark.parametrize(("sti", "gyldig"), KANT_CASES)
def test_kanttilfaelde(sti: str, gyldig: bool) -> None:
    assert (_sti_dele(sti) is not None) is gyldig


def test_state_er_kun_reserveret_som_foerste_segment() -> None:
    """``RESERVERET = new Set(['state'])`` gælder kun første segment."""
    assert _sti_dele("a.state") is not None
    assert _sti_dele("state") is None


def test_indeks_er_heltal() -> None:
    assert _sti_dele("liste[12]") == ["liste", 12]
    assert _sti_dele("a[0].b[1]") == ["a", 0, "b", 1]


# TS bruger ``/^\d+$/``, som KUN matcher ASCII 0-9. Pythons ``str.isdigit()`` accepterer
# unicode-cifre, og ``int("²")`` kaster ``ValueError`` — målt 20/11-2026, hvor det gav en
# uindpakket exception i guarden. Disse cases holder spejlen ærlig.
UNICODE_CASES: tuple[str, ...] = (
    "a[\u00b2]",   # superscript two — isdigit() True, int() kaster
    "a[\u0663]",   # arabic-indic three
    "a[\uff11\uff12]",  # fullwidth one-two
)


@pytest.mark.parametrize("sti", UNICODE_CASES)
def test_unicode_cifre_afvises_som_i_ts(sti: str) -> None:
    assert _sti_dele(sti) is None


@pytest.mark.parametrize("sti", UNICODE_CASES)
def test_unicode_cifre_kaster_ikke(sti: str) -> None:
    """Guarden må aldrig kaste på en sti en model kan skrive."""
    _sti_dele(sti)  # kaster den, fejler testen


# --- DIL lag 2: kontrolstrukturer ------------------------------------------------------------
#
# Samme tabel køres mod Python-guarden (``udfold_kontrol``) OG mod klientens ``udfoldKontrol``
# i ``apps/jarvis-desk/src/lib/udtryk.ts`` via ``node --experimental-strip-types``. De to
# ``udtryk.ts``-kopier skal være byte-identiske.

import json
import pathlib
import shutil
import subprocess

from core.services.jarvis_ui_guard import (
    KONTROL_MAX_LISTE,
    _KontrolFejl,
    _bind_indhold,
    udfold_kontrol,
)

_ROD = pathlib.Path(__file__).resolve().parent.parent
_DESK_UDTRYK = _ROD / "apps/jarvis-desk/src/lib/udtryk.ts"
_MOBIL_UDTRYK = _ROD / "apps/mobile/src/lib/udtryk.ts"

KONTROL_CASES: tuple[tuple[str, dict, str], ...] = (
    ("{#each xs som x}[{x}]{/each}", {"xs": [1, 2, 3]}, "[1][2][3]"),
    ("{#each xs som x}{x};{/each}", {"xs": ["a", "b"]}, "a;b;"),
    ("{#each xs som x}{x} {/each}", {"xs": [2.5, 4.0]}, "2,5 4 "),
    ("{#each xs som x}{x}{/each}", {"xs": []}, ""),
    ("{#if a > 1}stor{:else}lille{/if}", {"a": 5}, "stor"),
    ("{#if a > 1}stor{:else}lille{/if}", {"a": 0}, "lille"),
    ("{#if a}ja{/if}", {"a": ""}, ""),
    ("{#if a && !b}ja{:else}nej{/if}", {"a": True, "b": False}, "ja"),
    ("{#if n == 'x'}ja{:else}nej{/if}", {"n": "x"}, "ja"),
    ("{#if a == 1}ja{:else}nej{/if}", {"a": True}, "nej"),  # === : bool er ikke tal
    ("{#if (a + 1) * 2 == 6}ja{:else}nej{/if}", {"a": 2}, "ja"),
    ("{#each xs som x}{#if x > 1}{x}!{:else}{x}.{/if}{/each}", {"xs": [1, 2]}, "1.2!"),
    ("{#each xs som x}{#each ys som y}{x}{y}{/each}{/each}", {"xs": [1, 2], "ys": ["a"]}, "1a2a"),
    ("ingen struktur {a}", {"a": 1}, "ingen struktur {a}"),
)

# Fejlcases: serveren kaster, klienten lader teksten stå uændret.
KONTROL_FEJL: tuple[tuple[str, dict], ...] = (
    ("{#each nope som x}{x}{/each}", {}),
    ("{#each a som x}{x}{/each}", {"a": 3}),
    ("{#each a som x}{x}{/each}", {"a": [[1]]}),
    ("{#each a som x}{x}", {"a": [1]}),
    ("{#if a}x{:else}y{:else}z{/if}", {"a": 1}),
    ("{#if nope}x{/if}", {}),
    ("{#each a som x}{#each a som y}{#each a som z}{#each a som w}.{/each}{/each}{/each}{/each}", {"a": [1]}),
)


@pytest.mark.parametrize(("tekst", "scope", "forventet"), KONTROL_CASES)
def test_kontrol_python(tekst: str, scope: dict, forventet: str) -> None:
    assert udfold_kontrol(tekst, scope) == forventet


@pytest.mark.parametrize(("tekst", "scope"), KONTROL_FEJL)
def test_kontrol_fejl_er_haarde_paa_serveren(tekst: str, scope: dict) -> None:
    with pytest.raises(_KontrolFejl):
        udfold_kontrol(tekst, scope)


def test_listeloft() -> None:
    with pytest.raises(_KontrolFejl):
        udfold_kontrol("{#each a som x}{x}{/each}", {"a": list(range(KONTROL_MAX_LISTE + 1))})


def _node_koer(cases: list) -> list:
    script = (
        "import {udfoldKontrol} from " + json.dumps(_DESK_UDTRYK.as_uri()) + ";\n"
        "const c = JSON.parse(process.argv.at(-1));\n"
        "console.log(JSON.stringify(c.map(([t, s]) => udfoldKontrol(t, s))));\n"
    )
    ud = subprocess.run(
        ["node", "--experimental-strip-types", "--no-warnings", "--input-type=module", "-e", script, json.dumps(cases)],
        capture_output=True, text=True, timeout=60,
    )
    assert ud.returncode == 0, ud.stderr
    return json.loads(ud.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="node mangler")
def test_kontrol_paritet_med_klientens_udfoldKontrol() -> None:
    cases = [[t, s] for t, s, _ in KONTROL_CASES] + [[t, s] for t, s in KONTROL_FEJL]
    klient = _node_koer(cases)
    for (t, s, forventet), svar in zip(KONTROL_CASES, klient):
        assert svar["tekst"] == forventet, (t, svar)
        assert svar["advarsler"] == [], (t, svar)
    for (t, s), svar in zip(KONTROL_FEJL, klient[len(KONTROL_CASES):]):
        assert svar["tekst"] == t, ("klienten degraderer til kildeteksten", t, svar)
        assert svar["advarsler"], (t, svar)


def test_udtryk_kopierne_er_byte_identiske() -> None:
    assert _DESK_UDTRYK.read_bytes() == _MOBIL_UDTRYK.read_bytes()


def test_bind_indhold_udfolder_data_og_fjerner_det() -> None:
    tekst = json.dumps({
        "type": "callout",
        "text": "{#each xs som x}{x},{/each}",
        "data": {"xs": [1, 2]},
    })
    ud, fejl = _bind_indhold(tekst, tool_results={}, run_id="r")
    assert fejl == []
    assert json.loads(ud) == {"type": "callout", "text": "1,2,"}


def test_bind_indhold_hard_fejl_med_nodepath_property_grund() -> None:
    tekst = json.dumps({"type": "callout", "text": "{#each nope som x}{x}{/each}"})
    ud, fejl = _bind_indhold(tekst, tool_results={}, run_id="r")
    assert ud == tekst
    assert len(fejl) == 1
    assert "nodePath=$" in fejl[0] and "property=text" in fejl[0] and "grund=" in fejl[0]


def test_lag1_og_lag2_samarbejder_listen_kan_komme_fra_et_tool_resultat() -> None:
    tekst = json.dumps({
        "text": "{#each xs som x}{x};{/each}",
        "data": {"xs": ["{ref:t1.a}", "{ref:t1.b}"]},
    })
    ud, fejl = _bind_indhold(tekst, tool_results={"t1": {"a": 1, "b": 2}}, run_id="r")
    assert fejl == []
    assert json.loads(ud)["text"] == "1;2;"
