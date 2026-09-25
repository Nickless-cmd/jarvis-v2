"""Livsfasen har altid et indhold — og skal sige at den har det.

Målt 25/9-2026: `determine_life_phase()` returnerede en rigtig fase
(«Refleksion — ikke hvad der gik godt/skidt, men hvad der forskubbede sig»),
men stod `active: false` i mind-rapporten. `cognitive_architecture_surface.py:37`
gør `result.get("active", False)`, og nøglen fandtes ikke. Et fravær blev læst
som en påstand.
"""
from __future__ import annotations

from core.services.living_heartbeat_cycle import determine_life_phase


def test_hver_time_paa_doegnet_giver_en_aktiv_fase():
    for time in range(24):
        fase = determine_life_phase(hour=time)
        assert fase["active"] is True, time
        assert fase["phase"], time
        assert fase["description"], time


def test_fasen_skifter_over_doegnet():
    """Ellers ville «altid aktiv» være sandt uden at betyde noget."""
    faser = {determine_life_phase(hour=t)["phase"] for t in range(24)}
    assert len(faser) > 1, faser


def test_fasen_baerer_det_der_bruges_nedstroems():
    """`cadence_producers` slaar op paa `phase`; hjerteslaget paa
    `suggested_actions` og `mood_tendency`."""
    fase = determine_life_phase(hour=14)
    for noegle in ("phase", "suggested_actions", "mood_tendency", "initiative_bias"):
        assert noegle in fase, noegle
