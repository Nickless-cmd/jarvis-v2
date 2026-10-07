"""Placeringen af budget-valgte sektioner: præfiks eller hale.

Tre sektioner blev flyttet ud af det cachede præfiks 30/9-2026 — tool-kataloget,
`support_signals` og `self_report` — hver gang fordi de ændrede sig tur for tur
og derfor kostede hele værktøjsarrayet OG hele samtalen. Modulet gør den
beslutning til data; disse tests holder den fast.
"""
from __future__ import annotations

import pytest

from core.services.prompt_sections.section_placement import (
    HALE_SEKTIONER,
    PRAEFIKS_SEKTIONER,
    placer_sektioner,
)


def _placer(valgt: dict[str, str | None]):
    parts: list[str] = []
    hale: list[str] = []
    kilder: list[str] = []
    placer_sektioner(
        selected=valgt,
        labels={n: f"label-{n}" for n in valgt},
        parts=parts, dyn_tail=hale, derived_inputs=kilder,
    )
    return parts, hale, kilder


def test_de_to_lister_overlapper_ikke():
    """En sektion kan ikke baade vaere cachet og ikke-cachet."""
    assert not (set(HALE_SEKTIONER) & set(PRAEFIKS_SEKTIONER))


@pytest.mark.parametrize("navn", ["support_signals", "self_report"])
def test_de_volatile_ligger_i_halen(navn):
    """Begge bygges pr. tur — den ene af et kaploeb mod en deadline, den anden
    med brugerbeskeden som parameter. De maa ikke tilbage i praefikset."""
    assert navn in HALE_SEKTIONER
    assert navn not in PRAEFIKS_SEKTIONER
    parts, hale, _ = _placer({navn: "INDHOLD"})
    assert hale == ["INDHOLD"], hale
    assert parts == [], parts


def test_praefiks_sektioner_havner_i_praefikset():
    """Kontrollen: uden den kunne testen ovenfor bestaa fordi ALT gaar i halen."""
    parts, hale, _ = _placer({"capability_truth": "CAP"})
    assert parts == ["CAP"] and hale == []


def test_tomme_sektioner_fylder_ingenting():
    """`None` og tom streng skal udelades begge steder — ellers staar der en
    tom sektion og optager en plads i budgettet."""
    parts, hale, kilder = _placer(
        {"capability_truth": None, "support_signals": "", "self_report": None})
    assert parts == [] and hale == [] and kilder == []


def test_halen_mærkes_saa_sporet_viser_hvor_den_laa():
    """`derived_inputs` er sporet i telemetrien; uden «(tail)» kan man ikke se
    paa den om en sektion blev flyttet."""
    _, _, kilder = _placer({"capability_truth": "C", "support_signals": "S"})
    assert kilder == ["label-capability_truth", "label-support_signals (tail)"]


def test_raekkefoelgen_i_praefikset_er_listens():
    """Raekkefoelgen ER cache-graensen: bytter to sektioner plads, flytter
    afvigelsespunktet og alt efter det betales igen."""
    parts, _, _ = _placer({n: n.upper() for n in PRAEFIKS_SEKTIONER})
    assert parts == [n.upper() for n in PRAEFIKS_SEKTIONER]
