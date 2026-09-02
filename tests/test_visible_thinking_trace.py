"""Varighed af tænkning: målt i SSE-laget, læst ved persistering.

Ræsonneringens TEKST har altid været gemt (chat_messages.reasoning_content),
men lå uden for blok-arrayet — og klienten renderer efter blokke. Derfor
forsvandt tænkningen fra tråden i samme sekund streamen sluttede. Testene
holder fast i de to halvdele: målingen, og at den lander i turen.
"""
from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from core.services import visible_thinking_trace as vtt


@pytest.fixture(autouse=True)
def _clean():
    with vtt._lock:
        vtt._marks.clear()
    yield
    with vtt._lock:
        vtt._marks.clear()


def test_maaler_varighed_og_rydder_posten():
    vtt.mark_start("run-1")
    time.sleep(0.15)
    vtt.mark_end("run-1")

    sec = vtt.take_seconds("run-1")
    assert sec is not None and sec > 0
    # Ryddet: samme run må ikke arve tallet til en senere tur.
    assert vtt.take_seconds("run-1") is None


def test_foerste_start_vinder_sidste_slut_vinder():
    """En tur kan åbne flere tænke-blokke (én pr. runde). Bjørn skal se ÉN
    linje for turen — derfor spænder målingen fra første åbning til sidste
    lukning, ikke pr. runde."""
    vtt.mark_start("run-2")
    first = vtt._marks["run-2"][0]
    time.sleep(0.08)
    vtt.mark_start("run-2")          # ignoreres
    assert vtt._marks["run-2"][0] == first

    vtt.mark_end("run-2")
    early = vtt._marks["run-2"][1]
    time.sleep(0.08)
    vtt.mark_end("run-2")            # sidste vinder
    assert vtt._marks["run-2"][1] > early
    assert vtt.take_seconds("run-2") is not None


def test_for_kort_taenkning_taeller_ikke():
    """«Tænkte i 0 s» er ikke en oplysning. Runder varigheden til nul, siger vi
    at der ikke blev tænkt."""
    vtt.mark_start("run-kort")
    vtt.mark_end("run-kort")
    assert vtt.take_seconds("run-kort") is None


def test_ulukket_blok_maales_frem_til_nu():
    """Afbrudt stream: blokken lukkede aldrig. Han tænkte faktisk i den tid,
    så tallet kastes ikke væk."""
    vtt.mark_start("run-3")
    time.sleep(0.15)
    assert vtt.take_seconds("run-3") is not None


def test_ukendt_run_giver_none():
    assert vtt.take_seconds("findes-ikke") is None
    assert vtt.peek_seconds("findes-ikke") is None


def test_kortet_vokser_ikke_uendeligt():
    for i in range(vtt._MAX_ENTRIES + 50):
        vtt.mark_start(f"run-{i}")
    assert len(vtt._marks) <= vtt._MAX_ENTRIES


def test_taenke_blok_laegges_forrest_i_turen():
    from core.services.visible_runs_outcomes import _with_thinking_block

    vtt.mark_start("run-9")
    time.sleep(0.15)
    vtt.mark_end("run-9")

    run = SimpleNamespace(run_id="run-9")
    blocks = [{"type": "text", "text": "svaret"}]
    out = _with_thinking_block(blocks, run, "jeg overvejede noget")

    assert out[0]["type"] == "thinking"
    assert out[0]["seconds"] > 0
    assert out[0]["text"] == "jeg overvejede noget"
    assert out[1] == {"type": "text", "text": "svaret"}


def test_ingen_taenkning_giver_uaendret_tur():
    """En model der ikke tænker må ikke få en «Tænkte i 0 s»-linje."""
    from core.services.visible_runs_outcomes import _with_thinking_block

    run = SimpleNamespace(run_id="run-uden")
    blocks = [{"type": "text", "text": "svaret"}]
    assert _with_thinking_block(blocks, run, "") == blocks


def test_lang_raesonnering_trunkeres_i_blokken():
    from core.services.visible_runs_outcomes import _with_thinking_block

    vtt.mark_start("run-lang")
    time.sleep(0.15)
    vtt.mark_end("run-lang")
    run = SimpleNamespace(run_id="run-lang")
    out = _with_thinking_block([{"type": "text", "text": "x"}], run, "a" * 9000)
    assert len(out[0]["text"]) == 4000
