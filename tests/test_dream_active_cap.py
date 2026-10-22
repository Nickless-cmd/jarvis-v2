"""Loft over aktive drømme — ratchet'en må ikke vokse monotont.

Målt 22/10-2026: 28 aktive drømme efter 6 dage, 16 på confidence 0,8, nul
bekræftet. Producenten (`dream_consolidation_daemon`) kalder `adopt_dream` ved
HVER konsolidering, og det eneste forbrug var fade-vejen — som var blokeret af
`presented`-fejlen. Fade alene er ikke nok: den kræver sessioner, og
producenten kan køre hurtigere end der kommer sessioner.
"""
from __future__ import annotations

import pytest

from core.services import dream_carry_over as dco


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(dco, "_ACTIVE_DREAMS", [])
    monkeypatch.setattr(dco, "_DREAM_ARCHIVE", [])
    monkeypatch.setattr(dco, "_LOADED", True)
    monkeypatch.setattr(dco, "_persist_file", lambda: tmp_path / "DREAM_CARRY.json")
    monkeypatch.setattr(dco, "_save", lambda: None)
    yield


def test_antal_aktive_overstiger_aldrig_loftet():
    """Kernen: efter mange adopties må listen ikke vokse ubegrænset."""
    for i in range(dco._MAX_ACTIVE_DREAMS + 10):
        dco.adopt_dream(dream_id=f"d{i}", content=f"Drøm nummer {i}", confidence=0.5)

    assert len(dco._ACTIVE_DREAMS) <= dco._MAX_ACTIVE_DREAMS


def test_de_svageste_arkiveres_foerst():
    """Lav confidence skal vige pladsen — ikke den nyeste."""
    dco.adopt_dream(dream_id="stærk", content="Stærk drøm", confidence=0.95)
    for i in range(dco._MAX_ACTIVE_DREAMS):
        dco.adopt_dream(dream_id=f"svag{i}", content=f"Svag {i}", confidence=0.2)

    ids = {d["dream_id"] for d in dco._ACTIVE_DREAMS}
    assert "stærk" in ids, "den stærkeste må ikke arkiveres for en svagere"


def test_bekraeftet_droem_arkiveres_aldrig_af_loftet():
    """Bekræftede drømme uddybes — loftet må ikke fjerne dem."""
    dco.adopt_dream(dream_id="bekraeftet", content="Vigtig", confidence=0.5)
    dco.confirm_dream("bekraeftet")

    for i in range(dco._MAX_ACTIVE_DREAMS + 5):
        dco.adopt_dream(dream_id=f"ny{i}", content=f"Ny {i}", confidence=0.9)

    ids = {d["dream_id"] for d in dco._ACTIVE_DREAMS}
    assert "bekraeftet" in ids


def test_arkiverede_er_markeret_capped():
    """De der ryger ud skal kunne forklares bagefter — ikke bare forsvinde."""
    for i in range(dco._MAX_ACTIVE_DREAMS + 3):
        dco.adopt_dream(dream_id=f"d{i}", content=f"Drøm {i}", confidence=0.3)

    capped = [d for d in dco._DREAM_ARCHIVE if d.get("status") == "capped"]
    assert capped, "mindst én skal være arkiveret med status 'capped'"
    assert all(d.get("dream_id") for d in capped)
