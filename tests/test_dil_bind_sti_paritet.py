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
