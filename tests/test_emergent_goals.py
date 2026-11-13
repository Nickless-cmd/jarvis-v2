"""Emergent goals — et ønske skal have et indhold, ellers er det en tæller.

Målt 13/11-2026: `generate_emergent_goal_from_experience` uden et emne skrev
den samme tomme sætning hver gang («Udforsk og forstå  bedre» — dobbelt
mellemrum fordi `recent_topic` var tom). Fordi `goal_id` er nyt pr. kald,
erstattede `INSERT OR REPLACE` intet: **108 identiske rækker på under et
døgn**. Et ønske uden indhold er ikke en appetit, det er en tæller der løber.

Testen måler den ægte søm: funktionen kalder `upsert_cognitive_emergent_goal`
fra modulets eget namespace (`from core.runtime.db import …` binder en KOPI),
så patchen skal ramme `core.services.emergent_goals`.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from core.services import emergent_goals


@pytest.fixture
def skrevne():
    """Fanger hvert forsøg på at skrive et ønske."""
    skrevet: list[dict] = []

    def _upsert(**kw):
        skrevet.append(kw)
        return {"goal_id": kw["goal_id"], "desire": kw["desire"]}

    with patch.object(emergent_goals, "upsert_cognitive_emergent_goal", _upsert), \
         patch.object(emergent_goals.event_bus, "publish", lambda *a, **k: None):
        yield skrevet


def test_tomt_emne_og_intet_hul_giver_INGEN_raekke(skrevne):
    """Kernen i rettelsen. Uden denne gren blev den samme sætning skrevet igen."""
    svar = emergent_goals.generate_emergent_goal_from_experience(
        recent_topic="", curiosity_level=0.9, knowledge_gap="",
    )
    assert svar is None
    assert skrevne == [], "et tomt ønske må ikke nå databasen"


def test_kun_mellemrum_taeller_som_tomt(skrevne):
    """`recent_topic` kan vaere en streng der ser ud af noget, men ikke er det."""
    svar = emergent_goals.generate_emergent_goal_from_experience(
        recent_topic="   \n\t ", curiosity_level=0.9,
    )
    assert svar is None
    assert skrevne == []


def test_et_rigtigt_emne_skrives_med_emnet_i_teksten(skrevne):
    svar = emergent_goals.generate_emergent_goal_from_experience(
        recent_topic="feltteori", curiosity_level=0.9,
    )
    assert svar is not None
    assert len(skrevne) == 1
    assert "feltteori" in skrevne[0]["desire"]
    # Det dobbelte mellemrum var symptomet: teksten skal vaere renset.
    assert "  " not in skrevne[0]["desire"]


def test_et_knowledge_gap_baerer_sig_selv_uden_emne(skrevne):
    """Et hul ER et indhold — det må ikke afvises fordi emnet mangler."""
    svar = emergent_goals.generate_emergent_goal_from_experience(
        recent_topic="", curiosity_level=0.9, knowledge_gap="hvorfor glipper cachen",
    )
    assert svar is not None
    assert skrevne[0]["desire"] == "hvorfor glipper cachen"


def test_lav_nysgerrighed_uden_hul_giver_stadig_ingen_raekke(skrevne):
    """Den oprindelige graense skal ikke aendres af rettelsen."""
    svar = emergent_goals.generate_emergent_goal_from_experience(
        recent_topic="feltteori", curiosity_level=0.1,
    )
    assert svar is None
    assert skrevne == []


def test_intensiteten_foelger_nysgerrigheden(skrevne):
    emergent_goals.generate_emergent_goal_from_experience(
        recent_topic="feltteori", curiosity_level=2.5,
    )
    assert skrevne[0]["intensity"] == 1.0, "intensiteten skal klippes til 1.0"
