"""Vagter for opgave → værktøj-mappingen (A7, 3/11-2026).

Mappingen er en KURATERET, deterministisk heuristik — ikke en indlært model. Målt
3/11-2026 var embedding-routeren ubrugelig til formålet (`phone_location` for «læs
logfilen»), og tick-historikken bærer ikke hvilke værktøjer der blev brugt. Disse tests
holder derfor to ting fast: at klassifikationen er rigtig på de klare tilfælde, og at
den ÆRLIGT siger `unknown` når teksten intet signal bærer — i stedet for at gætte.
"""
from __future__ import annotations

import pytest

from core.services.task_tool_mapping import (
    TIER_IRREVERSIBLE,
    TIER_MUTATE,
    TIER_READ,
    TIER_UNKNOWN,
    map_task_to_tools,
)


@pytest.mark.parametrize("opgave,tier", [
    ("kritisk migration af produktionsdatabase", TIER_IRREVERSIBLE),
    ("deploy til produktion", TIER_IRREVERSIBLE),
    ("slet de gamle logfiler", TIER_IRREVERSIBLE),
    ("send en besked til Bjorn", TIER_IRREVERSIBLE),
    ("genstart api'et", TIER_IRREVERSIBLE),
    ("push til main", TIER_IRREVERSIBLE),
    ("opret en ny testfil", TIER_MUTATE),
    ("ret fortegnssemantikken i gut-gaten", TIER_MUTATE),
    ("læs logfilen og find fejlen", TIER_READ),
    ("vis status på daemons", TIER_READ),
    ("analysér tick-kvaliteten", TIER_READ),
])
def test_klassifikation_paa_klare_tilfaelde(opgave, tier):
    assert map_task_to_tools(opgave)["tier"] == tier


def test_irreversibel_vejer_tungest():
    """En opgave er så farlig som sit farligste led — «læs og slet» er en sletning."""
    r = map_task_to_tools("læs listen og slet de gamle rækker")
    assert r["tier"] == TIER_IRREVERSIBLE


def test_tom_og_stoej_giver_unknown_ikke_gaet():
    """`unknown` er et ÆRLIGT svar: intet signal, delta 0,0 — ikke en falsk neutralværdi."""
    for tekst in ("", "   ", "qwertyuiop", "direkte sammenligning af to filer"):
        r = map_task_to_tools(tekst)
        assert r["tier"] == TIER_UNKNOWN
        assert r["method"] == "none"
        assert r["confidence_delta"] == 0.0


def test_fortegnet_saenker_for_farlige_opgaver():
    """Fortegnet er det bærende: farlige opgaver skal lettere ramme `caution`."""
    assert map_task_to_tools("deploy til produktion")["confidence_delta"] < 0
    assert map_task_to_tools("læs logfilen")["confidence_delta"] > 0


def test_ordgraense_forhindrer_falsk_positiv():
    """Målt 3/11-2026: «ret» ramte inde i «opret» og «direkte» med ren substring."""
    # «direkte» indeholder «ret» — må ikke blive en muterende klassifikation.
    assert map_task_to_tools("direkte sammenligning")["tier"] == TIER_UNKNOWN


def test_bash_er_irreversibel_per_konstruktion():
    """Målt 3/11-2026: `bash` blev `read` fordi navnet ikke bærer et mutations-ord —
    men et shell kan udføre hvad som helst. Navnet kan ikke bære den viden."""
    r = map_task_to_tools("kør bash kommando")
    assert r["tier"] == TIER_IRREVERSIBLE
    assert r["method"] == "explicit"


def test_svarer_altid_paa_forventet_form():
    r = map_task_to_tools("vis status")
    for noegle in ("tools", "tier", "signals", "method", "confidence_delta"):
        assert noegle in r
    assert isinstance(r["tools"], list)
    assert isinstance(r["signals"], list)
