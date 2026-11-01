"""Loft pr. emne pr. doegn i glemselskurven — emnet er KILDEN, ikke teksten.

MAALT 31/10-2026 (og gentaget 1/11): tekst-lighed kan ikke skelne emner i denne
korpus. difflib paa alle 124.750 par af samme kind: median 0,280, p95 0,583.
Emne-parene laa paa median 0,376, og kun 5,1 % over 0,60 — mod 4,0 % af ALLE
par. En 0,60-taerskel ville fange naesten lige saa meget fremmed som emne.

Aarsagen er at de gentagne poster ikke er omformuleringer: de er samme EMNE
gennem skiftende kanaler. Teksten er reelt forskellig hver gang.

MAALT PAA DE 103 POSTER OM EMMET (siden 31/10): **77 kom fra EN generator**
(`inner-voice-daemon`), 7 fra `thought-stream-daemon`, 7 fra `initiative-queue`,
resten spredt. Loekken er altsaa ikke syv kanaler — den er eet daemon der
gentager sig med skiftende `focus`. Derfor virker et KILDE-loft.

Kilden ligger i `source_signals` i formatet `generator:kontekst`, og baerer en
sag naar den findes (`initiative-queue:init-e954bcf831`). Den er derfor den
n taermeste emne-noegle naar intet emne-felt findes.
"""
from __future__ import annotations

import pytest

import core.services.forgetting_curve as F
from core.runtime import state_store

KILDE = "inner-voice-daemon:cadence-scheduler"


@pytest.fixture(autouse=True)
def _tom_tilstand():
    state_store.save_json("forgetting_curve", {})
    yield
    state_store.save_json("forgetting_curve", {})


def _reg() -> dict:
    return state_store.load_json("forgetting_curve", {}) or {}


def test_tre_poster_samme_emne_forskellig_ordlyd_giver_en_post(monkeypatch):
    """KRAVET: 3 poster, samme emne, forskellig ordlyd -> kun 1 post.

    Loftet saettes til 1 her, saa testen maaler MEKANISMEN (at kilden er
    noeglen og at overskud forstaerker i stedet for at skrive nyt). At
    produktionens loft er 8 maales separat nedenfor.
    """
    monkeypatch.setattr(F, "_EMNE_LOFT", 1)
    tekster = [
        "Koerslen blev afbrudt midt i et vaerktoejskald",
        "Den afbrudte koersel haenger stadig som en aaben loop",
        "Brugeren stoppede mig under eksekveringen",
    ]
    for i, tekst in enumerate(tekster):
        F.register_memory(memory_key=f"k{i}", content_preview=tekst, source=KILDE)

    reg = _reg()
    assert len(reg) == 1, f"forventede 1 post, fik {len(reg)}: {list(reg)}"
    post = next(iter(reg.values()))
    assert post["reinforcement_count"] == 2, "de to overskydende skal forstaerke, ikke forsvinde"
    assert post["source"] == KILDE


def test_forskellige_emner_kollapser_ikke(monkeypatch):
    """Det er HELE grunden til at kurven advarer mod dedup: to emner er to.

    Samme ordlyd er ikke nok til at smelte dem sammen — kilden afgoer.
    """
    monkeypatch.setattr(F, "_EMNE_LOFT", 1)
    F.register_memory(memory_key="a", content_preview="kolonner og vaerdier",
                      source="thought-stream-daemon:heartbeat")
    F.register_memory(memory_key="b", content_preview="cpu 4% og 47 grader",
                      source="somatic-daemon:heartbeat")
    F.register_memory(memory_key="c", content_preview="frav aer af kontakt",
                      source="absence-daemon")

    reg = _reg()
    assert len(reg) == 3, f"tre kilder skal give tre poster, fik {len(reg)}"
    assert {p["source"] for p in reg.values()} == {
        "thought-stream-daemon:heartbeat",
        "somatic-daemon:heartbeat",
        "absence-daemon",
    }


def test_loftet_er_otte_i_produktion():
    """Default N=8, maalt: simulering paa de 500 levende poster beholdt 31 %
    som aegte arbejdssaet, mens inner-voice-daemonens 64 poster/dag klippes."""
    assert F._EMNE_LOFT == 8
    for i in range(12):
        F.register_memory(memory_key=f"m{i}", content_preview=f"tanke nummer {i}", source=KILDE)
    reg = _reg()
    assert len(reg) == 8, f"loftet skal give 8 poster, fik {len(reg)}"


def test_poster_aedre_end_24_timer_taeller_ikke_i_loftet(monkeypatch):
    """Vinduet er et DOEGN, ikke evigt: en post fra i gaar spaererr ikke i dag.

    Loftet saettes til 1 — ellers kan testen ikke se forskel. MAALT: med
    default N=8 passede testen OGSAA da 24-timers-grenen var fjernet, fordi
    én gammel post aldrig fylder et loft paa otte. Vagten var groen uden at
    maale noget.
    """
    monkeypatch.setattr(F, "_EMNE_LOFT", 1)
    state_store.save_json("forgetting_curve", {
        "gammel": {
            "decay_score": 0.0,
            "reinforcement_count": 0,
            "content_preview": "gammel tanke",
            "summary": "gammel tanke",
            "source": KILDE,
            "registered_at": "2026-10-29T10:00:00Z",
            "last_referenced_at": "2026-10-29T10:00:00Z",
        },
    })
    F.register_memory(memory_key="ny", content_preview="ny tanke", source=KILDE)
    reg = _reg()
    assert len(reg) == 2, "en post fra i forg aars skal ikke spise dagens plads"
    assert "ny" in reg


def test_uden_kilde_registreres_som_foer():
    """Bagudkompatibelt: kaldes register_memory uden source, oprettes posten."""
    F.register_memory(memory_key="x", content_preview="noget helt andet")
    reg = _reg()
    assert len(reg) == 1
    assert reg["x"]["source"] == ""
