"""Droemmen maa ikke kasseres paa tre backticks.

25/9-2026, maalt paa CT105: `run_dream_bias_distillation` svarede
`json_parse_failed` — ikke fordi der manglede indhold, men fordi modellen
svarer med ```-indhegnet JSON og `dream_bias_engine` brugte raa `json.loads`.

Forlaegget, ordret fra produktionen:

    ```
    {
      "dream_text": "Jeg foeler uro og skam, men siger det hoejt til Bjoern",
      "attention_bias": { ...

Droemmen var der hver cyklus. `dream_bias_active` har aldrig haft en raekke
siden tabellen kom 10/5-2026.
"""
from __future__ import annotations

from core.services.llm_json import udtraek_json


def test_forlaegget_fra_produktionen_parses():
    """DEN konkrete streng der blev kasseret."""
    raw = ('```\n{\n  "dream_text": "Jeg foeler uro og skam, men siger det '
           'hoejt til Bjoern",\n  "attention_bias": {"unfinished_business": 0.4}\n}\n```')
    ud = udtraek_json(raw)
    assert ud is not None, "droemmen blev kasseret igen"
    assert ud["dream_text"].startswith("Jeg foeler uro")
    assert ud["attention_bias"] == {"unfinished_business": 0.4}


def test_med_sprogmaerke_paa_hegnet():
    assert udtraek_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_uden_hegn():
    assert udtraek_json('{"a": 1}') == {"a": 1}


def test_indledning_og_efterskrift():
    """En model der forklarer sig foer og efter skal stadig kunne forstaas."""
    assert udtraek_json('Her er mit svar:\n{"a": 1}\nSig til hvis du vil have mere.') == {"a": 1}


def test_indlejrede_klammer_taelles_med():
    """Regulaere udtryk fejler her; klammematchningen skal tage HELE objektet."""
    ud = udtraek_json('```\n{"ydre": {"indre": {"dyb": 3}}, "efter": 1}\n```')
    assert ud == {"ydre": {"indre": {"dyb": 3}}, "efter": 1}


def test_kun_det_FOERSTE_objekt():
    assert udtraek_json('{"a": 1}\n{"b": 2}') == {"a": 1}


def test_uparsbart_giver_None_uden_at_kaste():
    """Et svar vi ikke kan bruge er ikke en fejl der skal vaelte den der spurgte."""
    for d in ("", "   ", None, "ingen klammer her", "{ikke gyldig json", "[1, 2, 3]"):
        assert udtraek_json(d) is None, repr(d)


def test_en_liste_er_ikke_et_objekt():
    """Kalderne laeser felter; en liste ville give AttributeError et andet sted."""
    assert udtraek_json('```\n[1, 2]\n```') is None


def test_generatorens_navn_gaar_samme_vej():
    """`dream_hypothesis_generator._extract_dream_json` gjorde det rigtigt hele
    tiden. Den beholder sit navn, men maa ikke faa sin egen kopi igen."""
    from core.services.dream_hypothesis_generator import _extract_dream_json
    assert _extract_dream_json('```\n{"a": 1}\n```') == {"a": 1}
