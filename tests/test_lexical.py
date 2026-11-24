"""Tests for den fælles leksikalske mekanisme (24/11-2026).

Modulet blev udskilt fra `core/services/behavioral_decisions.py`, fordi de samme
to begreber — «ord der ikke bærer betydning» og «ord der er maskinens egen
status» — blev genopfundet i tolv andre moduler med hver sin næsten-identiske
liste. Testene her vogter to ting: at skellet mellem de to niveauer holder, og at
der ikke opstår en ny kopi i den fil der flyttede fra.
"""

from __future__ import annotations

from core.util import lexical


def test_stopord_fjernes_helt() -> None:
    """Et funktionsord må ikke nå scoren — det bærer intet signal."""
    ord_ = lexical.relevans_ord("jeg synes at det er godt og hvordan")
    assert ord_ == set(), f"stopord slap igennem: {sorted(ord_)}"


def test_fagord_bevares() -> None:
    """Et ord med indhold må ikke forsvinde sammen med stojen."""
    ord_ = lexical.relevans_ord("relevans-gaten valgte beslutninger")
    assert "relevans" in ord_ and "beslutninger" in ord_


def test_sti_fjernes_foer_tokenisering() -> None:
    """Målt i drift 24/11-2026: 9 af 15 tokens kom fra en pytest-sti alene."""
    ctx = (
        "sudo-exec-completed Approved bounded sudo exec blev udført for sudo "
        "chmod 600 /tmp/pytest-of-bs/pytest-419/test_approved_sudo_exec_become0/"
        "workspaces/default/to"
    )
    ord_ = lexical.relevans_ord(ctx)
    for stoej in ("pytest-of-bs", "become0", "workspaces", "default", "pytest-419"):
        assert stoej not in ord_, f"«{stoej}» er en del af en sti, ikke et signal"
    assert "chmod" in ord_ and "sudo" in ord_, "aegte ord forsvandt med stien"


def test_sammensat_ord_giver_baade_helhed_og_dele() -> None:
    """«prompt-sektionen» skal ramme både den sammensatte form og hver del."""
    ord_ = lexical.relevans_ord("prompt-sektionen")
    assert "prompt-sektionen" in ord_
    assert "prompt" in ord_ and "sektionen" in ord_


def test_tom_og_none_giver_tomt_saet() -> None:
    assert lexical.relevans_ord("") == set()
    assert lexical.relevans_ord(None) == set()


def test_de_to_niveauer_overlapper_ikke() -> None:
    """Et ord kan ikke både FJERNES og VÆGTES — så er skellet uklart.

    Overlap ville betyde at et ord er erklæret betydningsløst i én sætning og
    «kan være en sag» i den næste, og så afhænger adfærden af hvilken gren der
    læses først.
    """
    faelles = lexical.RELEVANS_STOPORD & lexical.STRUKTURELLE_ORD
    assert not faelles, f"ord staar i begge lister: {sorted(faelles)}"


def test_success_er_fagord() -> None:
    """Den dokumenterede undtagelse: `success` rammer beslutningen om
    applied/ok/success-felter, så dér er ordet et ægte signal."""
    assert "success" not in lexical.RELEVANS_STOPORD
    assert "success" not in lexical.STRUKTURELLE_ORD


def test_hele_statusvokabularet_er_strukturelt() -> None:
    """Statusfamilien og de sammensatte former skal alle være dækket.

    Målt 24/11-2026: listen var en stikprøve, og 12 af 13 status-tokens gik
    gennem filteret som fagsignaler.
    """
    forventet = {
        "running", "pending", "failed", "cancelled", "expired", "queued",
        "tool", "intent", "tool_intent", "loop", "state", "loop_state",
        "heartbeat", "active", "idle", "completed",
    }
    manglende = sorted(forventet - lexical.STRUKTURELLE_ORD - lexical.RELEVANS_STOPORD)
    assert not manglende, f"status-tokens der ikke er daekket: {manglende}"


def test_probe_paa_ren_maskin_kontekst_laekker_ikke() -> None:
    """Den konkrete fejl der udloeste listen: to beslutninger valgt paa `loop`."""
    probe = (
        "idle active running completed tool_intent loop_state heartbeat "
        "pending failed cancelled expired queued"
    )
    ord_ = lexical.relevans_ord(probe)
    laekket = sorted(ord_ - lexical.STRUKTURELLE_ORD)
    assert not laekket, f"strukturelle tokens slap gennem som fagord: {laekket}"


def test_ord_frekvens_taeller_poster_ikke_forekomster() -> None:
    poster = [
        {"directive": "gaten valgte fem", "trigger_cue": "prompten relevans"},
        {"directive": "gaten igen", "trigger_cue": ""},
        {"directive": "", "trigger_cue": ""},
    ]
    freq = lexical.ord_frekvens(poster)
    assert freq.get("gaten") == 2, freq
    assert freq.get("valgte") == 1
    # `fem` er tre tegn og filtreres af laengdekravet — det er med vilje, og
    # derfor skal den ikke staa i frekvensen.
    assert "fem" not in freq
    assert all(isinstance(v, int) and v > 0 for v in freq.values())


def test_ord_frekvens_taaler_poster_uden_felter() -> None:
    assert lexical.ord_frekvens([{}, {"directive": None}]) == {}


def test_behavioral_decisions_arver_samme_objekt() -> None:
    """Gaten må ikke holde sin egen KOPI — så kan de to drive fra hinanden.

    Det er præcis fejlklassen flytningen skulle lukke: tolv moduler med hver sin
    næsten-identiske liste. En `from … import` binder samme objekt; en
    gen-indskrevet liste ville være et andet objekt med samme indhold i dag og
    et andet indhold i morgen.
    """
    from core.services import behavioral_decisions as bd

    assert bd._STRUKTURELLE_ORD is lexical.STRUKTURELLE_ORD
    assert bd._RELEVANS_STOPORD is lexical.RELEVANS_STOPORD
    assert bd._STRUKTUREL_VAEGT == lexical.STRUKTUREL_VAEGT
    assert bd._relevans_ord is lexical.relevans_ord
    assert bd._ord_frekvens is lexical.ord_frekvens
