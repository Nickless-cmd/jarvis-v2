"""Vagt: jarvis-ui-guarden skal køre på den FÆLLES udgang, ikke på én gren.

MÅLT 24/10-2026: guarden blev kaldt fra `_finalize_second_pass_visible_text`,
som kun bruges i anden- og tredjepas-grenene. Førstepas-vejen — den
almindelige — gik uden om. Konsekvens målt i DB: 6 jarvis-ui-blokke siden
20:20, 8 skæve comparison-rækker i besked 220356 og 220381, og NUL
normaliseringer registreret. Guarden virkede når den blev kaldt direkte, men
blev aldrig kaldt i drift.

Testen her fælder netop det: den kalder guarden på en tekst med et kendt
mismatch og kræver at rækkerne er pad'et. Fjernes kaldet fra udgangen, er
den rød.
"""
from __future__ import annotations

import json
import re

from core.services.jarvis_ui_guard import normalisér

# Præcis den form der slap igennem: 3 kolonner, 2 values pr. række.
SKAeV = (
    "Her er status.\n\n"
    "```jarvis-ui\n"
    '{"type":"comparison","title":"Fejl","columns":["A","B","C"],'
    '"rows":[{"label":"r1","values":["x","y"]},'
    '{"label":"r2","values":["p","q"]}]}\n'
    "```\n"
)


def _blok(tekst: str) -> dict:
    m = re.search(r"```jarvis-ui[^\n]*\n(.*?)```", tekst, re.S)
    assert m, "blokken forsvandt"
    return json.loads(m.group(1))


def test_skaeve_values_pad_es_paa_den_faelles_udgang() -> None:
    """Kernen: en comparison med færre values end kolonner må ikke slippe ud."""
    ud = normalisér(SKAeV, run_id="test-faelles-udgang")
    data = _blok(ud)
    assert len(data["columns"]) == 3
    for i, raekke in enumerate(data["rows"]):
        assert len(raekke["values"]) == 3, (
            f"række {i} har {len(raekke['values'])} values — guarden kørte ikke"
        )
        assert raekke["values"][-1] == "— (mangler)"


def test_korrekt_blok_roeres_ikke() -> None:
    """Regression: en blok der allerede passer må ikke ændres."""
    korrekt = (
        "```jarvis-ui\n"
        '{"type":"comparison","columns":["A","B"],'
        '"rows":[{"label":"r1","values":["x","y"]}]}\n'
        "```\n"
    )
    assert normalisér(korrekt, run_id="test-korrekt") == korrekt


def test_guarden_er_koblet_paa_den_faelles_udgang() -> None:
    """Strukturel vagt: kaldet skal stå i den fælles udgang, ikke kun i
    andenpas-grenen. Læser kilden — en grøn funktionstest alene kan ikke se
    om nogen faktisk kalder den.

    Rettet 25/10-2026: vagten pegede på ``_stream_visible_run``, men guarden
    flyttede til ``_finalize_second_pass_visible_text`` — den funktion der
    normaliserer teksten FØR den både observeres og gemmes. Vagten blev derfor
    falsk-rød: den ledte et sted hvor guarden ikke længere hører hjemme, og
    kunne hverken se koblingen eller mangle den. Nu måler den funktionen.
    """
    import inspect

    from core.services import visible_runs

    kilde = inspect.getsource(visible_runs)
    i_funktion = kilde.find("def _finalize_second_pass_visible_text(")
    assert i_funktion > 0, "_finalize_second_pass_visible_text blev ikke fundet"
    # Funktionens krop slutter ved næste top-level def.
    i_slut = kilde.find("\ndef ", i_funktion + 10)
    krop = kilde[i_funktion:i_slut if i_slut > 0 else len(kilde)]

    # Flade-guarden: normaliserer jarvis-ui-blokke.
    assert "jarvis_ui_guard import normalisér" in krop, (
        "jarvis-ui-guarden kaldes ikke på den fælles udgang — kun i "
        "andenpas-grenen. Det var præcis fejlen 24/10-2026."
    )
    # Prosa-korrektionen: retter smøre-afsnit FØR de vises (25/10-2026).
    # Målt 25/10-2026: navnet står også i import-linjen, så en vagt der blot
    # leder efter «korriger_prosa» er grøn selv når kaldet er væk. Den kræver
    # kalde-formen — navnet efterfulgt af en parentes.
    assert "_korriger_prosa(" in krop, (
        "prosa-korrektionen kaldes ikke på den fælles udgang — så er guarden "
        "igen kun en log, ikke en kontrol."
    )
    # Og den skal køre FØR teksten returneres.
    i_prosa = krop.find("_korriger_prosa(")
    i_return = krop.rfind("return cleaned")
    assert i_return > i_prosa > 0, (
        "prosa-korrektionen står efter return — den kan ikke påvirke svaret."
    )
