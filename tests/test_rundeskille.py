"""Rundeskille i agentic-loopet (1/10-2026).

Runderne blev lagt sammen med ``"".join()`` uden separator, så runde N's
sidste sætning og runde N+1's første smeltede sammen. Målt i Bjørns besked
1/10-2026: «...koster én fil.Skillen er læst...» blev gemt som
«...koster én fil.Skillen er læst...» — præcis ÉT lim-sted i 6.714 tegn, og
det lå på rundeskiftet. Det næste skift i samme besked var rent, fordi
modellen dér selv skrev et indledende ``\\n\\n``. Vi må ikke afhænge af det.

Loopet er én lang generator der ikke kan instantieres i en unit-test uden en
hel model-lane. Disse tests læser kilden og hævder kontrakten, så den ikke kan
fjernes uden at nogen opdager det — samme form som ``test_loop_stop_reasons``.
"""
from __future__ import annotations

import inspect

from core.services import visible_runs

_SEPARATOR = '_all_followup_parts.append("\\n\\n")'
_SNAPSHOT = "_round_partial_snapshot = len(_all_followup_parts)"


def _source() -> str:
    return inspect.getsource(visible_runs)


def test_rundeskiftet_faar_en_separator():
    """Uden separatoren smelter to runders tekst sammen til én linje, og
    hverken klienten eller normaliseringen kan redde den: der er ingen ``\\n``
    at bryde på."""
    assert _SEPARATOR in _source()


def test_separatoren_ligger_foer_retry_snapshotet():
    """Rækkefølgen betyder alt. En retry trunkerer ``_all_followup_parts``
    tilbage til ``_round_partial_snapshot``; lægges separatoren EFTER den
    måling, forsvinder den ved første retry og limen vender tilbage."""
    src = _source()
    assert src.index(_SEPARATOR) < src.index(_SNAPSHOT)


def test_separatoren_er_guardet_mod_dobbelt_skift():
    """Modellen skriver nogle gange selv et indledende ``\\n\\n``. Uden
    guarden ville vi lægge et ekstra lag ovenpå — og vi ville ikke længere
    kunne se forskel på «modellen gjorde det» og «vi gjorde det»."""
    src = _source()
    idx = src.index(_SEPARATOR)
    block = src[idx - 400: idx + 200]
    assert '_all_followup_parts and not _all_followup_parts[-1].endswith("\\n")' in block


def test_separatoren_naar_baade_stream_og_persisteret_svar():
    """Live-visningen skal stemme med det der gemmes — ellers ser Bjørn noget
    andet undervejs end det han ser bagefter, og det var netop kløften mellem
    det streamede og det gemte svar der gjorde fejlen svær at se."""
    src = _source()
    idx = src.index(_SEPARATOR)
    block = src[idx: idx + 400]
    assert '"delta": "\\n\\n"' in block
