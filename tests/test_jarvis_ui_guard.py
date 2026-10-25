"""Vagt: ``jarvis-ui``-blokke skal have korrekt form og gyldig JSON.

Målt 24/10-2026 (Bjørn): tre svar i træk fejlede i chatview. Årsagen var min
tekst, ikke rendereren — og de to fejl kræver hver sin kontrol:

1. ``],"}"`` i stedet for ``]}`` (besked 220068). Syntaksfejl; JSON'en kan
   repareres, men beskeden havde OGSÅ 2 values til 3 kolonner, så den blev
   degraderet til ærlig tekst i stedet for en flade der dropper en række.
2. Gyldig JSON skrevet på SAMME LINJE som fence-markøren (besked 220247).
   Her siger enhver datavalidering «OK» — men i CommonMark bliver hele
   resten af linjen en del af info-stringen, så rendereren ikke ser sproget
   ``jarvis-ui`` og falder tilbage til rå kode. Formen skal normaliseres
   FØR dataene valideres; ellers ser vagten ikke fejlen.
"""

from __future__ import annotations

import json
import re

from core.services.jarvis_ui_guard import normalisér

# Den faktiske tekst fra besked 220068 — syntaksfejl OG skæv values-længde.
FRA_220068 = (
    '{"type":"comparison","title":"Tre veje til svaret","columns":'
    '["Kilde","Hvad den giver","Hvor sikker"],"rows":[{"label":"Egne data",'
    '"values":["hvad der faktisk adskiller mine gode svar fra mine dårlige",'
    '"høj — jeg har 100+ svar og du har udpeget det rigtige"],"},'
    '{"label":"Offentlige prompts","values":["konkrete formuleringer fra andre '
    'systemer","middel — de er reverse-engineerede, ikke officielle"]},'
    '{"label":"Model-sammenligning","values":["hvad der er fælles for modeller '
    'der føles som samtale","lav — jeg kan ikke skelne model fra prompt"]}]}'
)

# Den faktiske tekst fra besked 220247 — gyldig JSON, men inline på markøren.
FRA_220247_INLINE = (
    '{"type":"comparison","title":"Etikette eller påstand",'
    '"columns":["Etikette-overskrift","Påstands-overskrift"],"rows":['
    '{"label":"Eksempel","values":["«Vejret»","«Vejret — alt regnen kommer om '
    'natten»"]},{"label":"Hvad den lover","values":["et emne du skal finde '
    'pointen i","pointen, allerede i overskriften"]}]}'
)


def _blok(text: str) -> str:
    """Træk den normaliserede jarvis-ui-blok ud (uden fence-markører)."""
    start = text.find("```jarvis-ui\n")
    assert start >= 0, f"ingen normaliseret blok i: {text[:200]}"
    start += len("```jarvis-ui\n")
    slut = text.find("\n```", start)
    assert slut >= 0, "blokken er ikke lukket"
    return text[start:slut]


def test_inline_json_paa_markoerlinjen_normaliseres() -> None:
    """Fælden fra 220247: gyldig JSON, men formen gør at sproget ikke genkendes."""
    tekst = f"Før.\n\n```jarvis-ui {FRA_220247_INLINE} ```\n\nEfter."
    ny = normalisér(tekst)
    assert ny != tekst, "inline-formen skulle være ændret"
    indhold = _blok(ny)
    data = json.loads(indhold)
    assert data["type"] == "comparison"
    assert len(data["rows"]) == 2
    # Markøren skal stå alene på sin linje, JSON'en på den næste.
    assert "```jarvis-ui\n{" in ny


def test_korrekt_form_beroeres_ikke() -> None:
    """En blok der allerede er korrekt må ikke ændres — en vagt der rører
    gyldige svar er værre end den fejl den skulle fange."""
    tekst = f"Før.\n\n```jarvis-ui\n{FRA_220247_INLINE}\n```\n\nEfter."
    assert normalisér(tekst) == tekst


def test_skaev_values_paddes_frem_for_at_blive_raa_json() -> None:
    """220068 havde to fejl. Syntaksen rettes — og dataene kan også rettes.

    Målt 24/10-2026 (Bjørn: "]!!!!"): den gamle adfærd var at degradere til
    ```` ```text ```` med rå JSON, så læseren så `]` uden at vide hvad det var.
    En comparison med 2 values til 3 kolonner er entydigt rettbar: den
    manglende celle bliver «—», ikke usynlig. Tabellen bevares.
    """
    tekst = f"Før.\n\n```jarvis-ui\n{FRA_220068}\n```\n\nEfter."
    ny = normalisér(tekst)
    assert "```jarvis-ui" in ny, "en rettelig flade må ikke degraderes"
    assert "```text" not in ny, "rå JSON må aldrig havne i chatten"
    assert "Tre veje til svaret" in ny
    blok = re.search(r"```jarvis-ui\s*\n(.*?)```", ny, re.S)
    assert blok is not None
    data = json.loads(blok.group(1))
    assert len(data["columns"]) == 3
    for raekke in data["rows"]:
        assert len(raekke["values"]) == 3, "hver række skal have præcis én værdi pr. kolonne"


def test_uoprettelig_blok_fjernes_uden_at_vise_json() -> None:
    """Kan blokken ikke parses, skal den forsvinde — ikke blive en JSON-mur."""
    tekst = 'Før.\n\n```jarvis-ui\n{"type":"comparison","columns":["a"\n```\n\nEfter.'
    ny = normalisér(tekst)
    assert "```jarvis-ui" not in ny
    assert "```text" not in ny, "rå JSON i en kodeblok er præcis den mur vi fjerner"
    assert '"columns"' not in ny
    assert "kunne ikke vises" in ny
    assert ny.startswith("Før.") and ny.rstrip().endswith("Efter.")


def test_ingen_flader_giver_uændret_tekst() -> None:
    tekst = "Bare prosa.\n\nMed to afsnit."
    assert normalisér(tekst) == tekst


def test_fail_open_paa_tom_tekst() -> None:
    assert normalisér("") == ""


def test_manglende_celle_siger_at_den_mangler() -> None:
    """En pad'et celle må ikke se ud som indhold.

    Målt 24/10-2026 (Bjørn: «Du gjorde det igen!»): fjerde gang på én aften
    skrev jeg en comparison med 3 kolonner og 2 values. Vagten paddede med en
    stille ``—``, så tabellen SÅ komplet ud mens tredje kolonne var tom hele
    vejen ned — den tavse version af samme fejl. Markøren skal sige hvad den
    er, ellers kan fejlen hverken ses eller rettes.
    """
    tekst = (
        'Før.\n\n```jarvis-ui\n'
        '{"type":"comparison","title":"T","columns":["A","B","C"],'
        '"rows":[{"label":"x","values":["1","2"]}]}\n```\n\nEfter.'
    )
    ny = normalisér(tekst)
    blok = re.search(r"```jarvis-ui\n(.*?)\n```", ny, re.S)
    assert blok is not None
    values = json.loads(blok.group(1))["rows"][0]["values"]
    assert len(values) == 3
    assert values[2] == "— (mangler)", "en manglende celle skal navngive sig selv"
    assert values[2] != "—", "en stille bindestreg ser ud som om der stod noget"


# ── Skema-vagten (25/10-2026) ───────────────────────────────────────────────
# Målt: guarden validerede KUN comparison-længder. Rendereren kræver felter
# for alle seks typer og returnerer `null` når de mangler — blokken forsvandt
# sporløst, mens guarden sagde «OK». Disse tests låser hver sådan fejl.

from core.services.jarvis_ui_guard import _DEGRADERET, _diagnosticér  # noqa: E402


def _niveau(spec: dict) -> str:
    return _diagnosticér(spec)[0]


def test_stats_uden_value_ville_forsvinde_stille() -> None:
    """Rendereren filtrerer items uden `value` væk og viser intet."""
    tekst = (
        '```jarvis-ui\n'
        '{"type":"stats","title":"Tal","items":[{"label":"a","value":"1"},'
        '{"label":"b"}]}\n```'
    )
    ny = normalisér(tekst)
    assert _DEGRADERET not in ny, "ét brugbart item er nok til at fladen vises"
    assert '"b"' in ny


def test_stats_helt_uden_brugbare_items_degraderes() -> None:
    tekst = (
        '```jarvis-ui\n'
        '{"type":"stats","title":"Tal","items":[{"label":"a"}]}\n```'
    )
    assert _DEGRADERET in normalisér(tekst)


def test_choices_uden_prompt_degraderes() -> None:
    """Uden `prompt` kan knappen ikke sende noget — rendereren dropper den."""
    tekst = (
        '```jarvis-ui\n'
        '{"type":"choices","title":"Vælg","options":[{"label":"A"}]}\n```'
    )
    assert _DEGRADERET in normalisér(tekst)


def test_location_uden_adresse_og_koordinater_degraderes() -> None:
    tekst = '```jarvis-ui\n{"type":"location","title":"Her"}\n```'
    assert _DEGRADERET in normalisér(tekst)


def test_location_med_adresse_bevares() -> None:
    tekst = '```jarvis-ui\n{"type":"location","address":"Svendborg"}\n```'
    assert _DEGRADERET not in normalisér(tekst)


def test_callout_uden_indhold_degraderes() -> None:
    tekst = '```jarvis-ui\n{"type":"callout","tone":"info"}\n```'
    assert _DEGRADERET in normalisér(tekst)


def test_timeline_uden_title_degraderes() -> None:
    tekst = (
        '```jarvis-ui\n'
        '{"type":"timeline","title":"T","items":[{"time":"09:00"}]}\n```'
    )
    assert _DEGRADERET in normalisér(tekst)


def test_comparison_med_en_kolonne_degraderes() -> None:
    tekst = (
        '```jarvis-ui\n'
        '{"type":"comparison","title":"T","columns":["A"],'
        '"rows":[{"label":"x","values":["1"]}]}\n```'
    )
    assert _DEGRADERET in normalisér(tekst)


def test_ukendt_type_degraderes() -> None:
    tekst = '```jarvis-ui\n{"type":"diagram","title":"T"}\n```'
    assert _DEGRADERET in normalisér(tekst)


def test_delvist_tab_bevarer_blokken_men_siger_det() -> None:
    """Et dårligt item af tre må ikke koste hele fladen — men tabet skal ses."""
    spec = {
        "type": "stats",
        "title": "Tal",
        "items": [{"label": "a", "value": "1"}, {"label": "b"}, {"label": "c", "value": "3"}],
    }
    niveau, fejl = _diagnosticér(spec)
    assert niveau == "delvis", "to gode items er stadig en læsbar flade"
    assert any("item 1" in f for f in fejl), "tabet skal navngives præcist"


def test_korrekt_blok_af_hver_type_beroeres_ikke() -> None:
    """Den negative kontrol: en gyldig flade må aldrig degraderes."""
    specifikationer = [
        {"type": "callout", "title": "T", "body": "B"},
        {"type": "stats", "title": "T", "items": [{"label": "a", "value": "1"}]},
        {"type": "timeline", "title": "T", "items": [{"title": "a", "status": "done"}]},
        {
            "type": "comparison", "title": "T", "columns": ["A", "B"],
            "rows": [{"label": "x", "values": ["1", "2"]}],
        },
        {"type": "choices", "title": "T", "options": [{"label": "a", "prompt": "p"}]},
        {"type": "location", "title": "T", "address": "Svendborg"},
    ]
    for spec in specifikationer:
        tekst = "```jarvis-ui\n" + json.dumps(spec, ensure_ascii=False) + "\n```"
        ny = normalisér(tekst)
        assert _DEGRADERET not in ny, f"{spec['type']} blev fejlagtigt degraderet"
        assert _niveau(spec) == "ok", f"{spec['type']} blev fejlagtigt markeret"
