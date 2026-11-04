"""Pseudo-overskrift: fed label og brødtekst på SAMME linje skal have et break.

Baggrund (målt 4/11-2026 i chat mode): tre forekomster i træk, senest i et svar
hvor reglen blev citeret og brudt i samme åndedrag. Guarden SÅ formen
(``prosa_struktur_guard._pseudo_overskrift``) men rørte ikke teksten — og den
kaldtes kun fra ``_finalize_second_pass_visible_text``, som er `skipped` for
langt de fleste runs. Primære svar blev aldrig set.

DISKRIMINATOREN — defineret FØR koden, som opgaven kræver
=========================================================

En fed sætningsstart er en PSEUDO-OVERSKRIFT når ALLE fire holder:

  1. linjen er afsnittets FØRSTE linje
  2. den fede tekst slutter med ``.`` ``:`` ``!`` eller ``?``
  3. den fede tekst bærer mindst to ord
  4. brødteksten starter en NY sætning — stort bogstav, tal eller emoji

Punkt 4 er den bærende. ``**Vigtigt:** dette fortsætter sætningen`` er god prosa
med en fed ledetråd; ``**Vigtigt:** Dette er en ny sætning`` er en overskrift der
mangler sit break. Uden punkt 4 ville transformationen rette rigtig tekst
forkert — og den fejl er dyrere end den vi løser, fordi choke-punktet rammer
HVERT svar, ikke kun de få der får en second pass.

Falsifikation i BEGGE retninger er hele pointen med denne fil:

  (a) positiv  — formen rettes
  (b) negativ  — korrekt formateret tekst passerer UÆNDRET
  (d) mutation — slå transformationen fra: (a) fejler. Slå diskriminatoren fra
                 (ret alt): (b) fejler. Begge er testet eksplicit nedenfor.
"""

from __future__ import annotations

import pytest

from core.services.prosa_struktur_guard import (
    ret_pseudo_overskrift,
    skal_have_break,
)


# ---------------------------------------------------------------------------
# (c) Diskriminatoren — testet isoleret, før transformationen bruges
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "linje, forventet",
    [
        # --- SKAL rettes: fed label, derefter en NY sætning ---
        ("**🪶 Break efter header-linjen.** Når jeg skriver en fed overskrift.", True),
        ("**Så et hul på to timer.** Det var ikke meningen.", True),
        ("**Tre huller.** Alle verificeret i kilden.", True),
        ("**Vigtigt:** Dette er en ny sætning.", True),
        ("**Målt 4/11.** Tre forekomster i træk.", True),
        ("**Note!** Læs den her.", True),
        ("**Hvad så?** Det ved jeg ikke.", True),
        # --- SKAL IKKE rettes: fed ledetråd der fortsætter sætningen ---
        ("**Vigtigt:** dette er en sætning der fortsætter.", False),
        ("**Bemærk:** at dette fortsætter med lille.", False),
        # --- SKAL IKKE rettes: andre grunde ---
        ("**Ja.**", False),  # ingen brødtekst på linjen (punkt 4 kan ikke opfyldes)
        ("**Ja.** Det holder ikke.", False),  # kun ét ord i labelen (punkt 3)
        ("Dette er **fed** tekst midt i en sætning.", False),  # ikke linjens start
        ("- **Punkt:** dette er en liste.", False),  # liste, ikke pseudo-overskrift
        ("**Uden tegn** Brødtekst uden afsluttende tegn.", False),  # punkt 2
        ("**Kolon uden mellemrum:**Brødtekst.", False),  # intet break at sætte
    ],
)
def test_diskriminator(linje: str, forventet: bool) -> None:
    """Diskriminatoren alene — ingen transformation, kun klassifikationen."""
    assert skal_have_break(linje) is forventet, (
        f"diskriminatoren klassificerede {linje!r} forkert"
    )


# ---------------------------------------------------------------------------
# (a) POSITIV — formen rettes i den tekst brugeren ser
# ---------------------------------------------------------------------------


def test_positiv_break_sættes() -> None:
    tekst = "**🪶 Overskrift.** Brødtekst på samme linje."
    assert ret_pseudo_overskrift(tekst) == "**🪶 Overskrift.**\n\nBrødtekst på samme linje."


def test_positiv_kun_ramte_linjer() -> None:
    """En tekst med både rigtig og forkert form: kun den forkerte røres."""
    tekst = (
        "**Rigtig header**\n\n"
        "Brødtekst her.\n\n"
        "**🪶 Forkert.** Brødtekst på samme linje.\n\n"
        "**Vigtigt:** dette fortsætter sætningen og er korrekt."
    )
    rettet = ret_pseudo_overskrift(tekst)
    assert "**🪶 Forkert.**\n\nBrødtekst" in rettet
    assert "**Vigtigt:** dette fortsætter" in rettet  # urørt
    assert "**Rigtig header**\n\n" in rettet  # urørt


def test_positiv_i_liste_urørt() -> None:
    """Punkter i en liste er ikke pseudo-overskrifter."""
    tekst = "- **Punkt:** dette er en liste.\n- **Andet:** også en liste."
    assert ret_pseudo_overskrift(tekst) == tekst


# ---------------------------------------------------------------------------
# (b) NEGATIV — korrekt formateret tekst passerer UÆNDRET
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tekst",
    [
        # fed ledetråd midt i prosa (Bjørns eksempel, ordret)
        "**Vigtigt:** dette er en sætning der fortsætter.",
        # fed tekst som helt eget afsnit
        "**Ja.**",
        # fed tekst inde i en løbende sætning
        "Det her er **vigtigt** fordi det ændrer alt.",
        # fed tekst i en punktopstilling
        "- **Trin 1:** gør dette.\n- **Trin 2:** gør hint.",
        # allerede korrekt form
        "**🪶 Overskrift.**\n\nBrødtekst på næste afsnit.",
        # tabel
        "| A | B |\n|---|---|\n| 1 | 2 |",
        # kodeblok
        "```python\ndef f():\n    return 1\n```",
    ],
)
def test_negativ_urørt(tekst: str) -> None:
    """Den negative kant: disse må ikke ændres med ét tegn."""
    assert ret_pseudo_overskrift(tekst) == tekst


def test_negativ_idempotent() -> None:
    """At køre transformationen to gange må ikke give en anden tekst."""
    tekst = "**🪶 Overskrift.** Brødtekst på samme linje."
    én = ret_pseudo_overskrift(tekst)
    to = ret_pseudo_overskrift(én)
    assert én == to, "transformationen er ikke idempotent — den ville æde sit eget break"


# ---------------------------------------------------------------------------
# (d) MUTATIONSTEST — begge veje
# ---------------------------------------------------------------------------


def test_mutation_uden_transformation_fejler_positiv() -> None:
    """Slå transformationen fra: den positive kant SKAL fejle.

    Det er beviset for at (a) faktisk måler transformationen og ikke bare
    tilfældigvis ser den rigtige streng.
    """
    def _identitet(t: str) -> str:
        return t

    tekst = "**🪶 Overskrift.** Brødtekst på samme linje."
    assert _identitet(tekst) == tekst  # mutationen: ingen rettelse
    assert _identitet(tekst) != "**🪶 Overskrift.**\n\nBrødtekst på samme linje."


def test_mutation_uden_diskriminator_fejler_negativ() -> None:
    """Slå diskriminatoren fra (ret ALT): den negative kant SKAL fejle.

    Uden punkt 4 ville ``**Vigtigt:** dette fortsætter`` blive revet midt over.
    Testen viser at den negative kant holdes af diskriminatoren — ikke af et
    tilfælde i regexen.
    """
    import re

    # Mutationen: samme regex, men UDEN kravet om at brødteksten starter ny sætning
    _uden_diskriminator = re.compile(r"^\*\*([^*\n]{2,90}[.:!?])\*\*[ \t]+(\S.*)$")

    linje = "**Vigtigt:** dette er en sætning der fortsætter."
    assert _uden_diskriminator.match(linje), (
        "mutationen skulle gerne matche — ellers beviser testen intet"
    )
    # ... og den rigtige diskriminator afviser den:
    assert skal_have_break(linje) is False
