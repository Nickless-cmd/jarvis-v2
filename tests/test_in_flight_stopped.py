"""Et stop skal efterlade et spor — men ikke rejse sig selv.

Bjørn 16/11-2026: «de burde ikk dø, men endten lande i din inbox eller i en kø …
eller risikere vi jo noget kunne gå tabt».

Målt samme dag: `settle_terminal` skrev brugerens stop som `cancelled`, men den
eneste læser — `interrupted_for_session` — kræver `interrupted`. Posten fandtes
altså, med checkpoint og hele sin historie, uden en eneste læser. Sporet var der;
indgangsbetingelsen kunne per konstruktion ikke opfyldes.

To ting skal være sande samtidig, og de trækker i hver sin retning:

1. Næste tur skal KUNNE se at der ligger et halvt stykke arbejde.
2. Stoppet må ikke genoptages af sig selv — det var fejlen 17/9, hvor brugerens
   eget stop startede igen.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import in_flight_runs as ifr


@pytest.fixture(autouse=True)
def _isoleret_lager(tmp_path, monkeypatch):
    lager: dict = {}
    monkeypatch.setattr(ifr, "_load", lambda: lager)
    monkeypatch.setattr(ifr, "_save", lambda d: lager.update(d))
    return lager


def _post(lager, rid, sid, *, status="cancelled", reason="user-cancelled",
          kind="visible", alder_timer=0.0, settled_forskud_timer=0.0):
    nu = datetime.now(UTC)
    started = (nu - timedelta(hours=alder_timer)).isoformat()
    settled = (nu - timedelta(hours=alder_timer) + timedelta(seconds=settled_forskud_timer)).isoformat()
    lager[rid] = {
        "run_id": rid, "session_id": sid, "status": status, "kind": kind,
        "exit_reason": reason, "started_at": started, "settled_at": settled,
        "excerpt": "halvfærdigt arbejde", "last_tool": "bash",
    }


def test_stop_efterlader_et_spor(_isoleret_lager):
    """Kernen i sagen: et brugerstop skal kunne findes af næste tur."""
    _post(_isoleret_lager, "r1", "s1", alder_timer=0.5)
    assert (ifr.stopped_for_session("s1") or {}).get("run_id") == "r1"


def test_senere_afsluttet_tur_fjerner_sporet(_isoleret_lager):
    """Er samtalen kommet videre, må varselet ikke hænge ved.

    Uden den regel ville blokken blive gentaget hver tur i 24 timer — og et
    varsel der altid står der, er ikke et varsel.
    """
    _post(_isoleret_lager, "stop", "s1", alder_timer=2.0)
    _post(_isoleret_lager, "senere", "s1", status="completed",
          reason="completed", alder_timer=1.0)
    assert ifr.stopped_for_session("s1") is None


def test_steer_stop_er_ikke_et_brugerstop(_isoleret_lager):
    """`user-steer-stop` er en ny besked der styrer turen — den ER fortsættelsen.

    Et «du stoppede mig»-varsel oven på brugerens egen nye besked ville være støj
    der fik mig til at spørge om noget han lige havde svaret på.
    """
    _post(_isoleret_lager, "r1", "s1", reason="user-steer-stop")
    assert ifr.stopped_for_session("s1") is None


def test_andet_sessions_stop_er_ikke_min(_isoleret_lager):
    _post(_isoleret_lager, "r1", "s2")
    assert ifr.stopped_for_session("s1") is None


def test_autonomt_stop_er_ikke_min(_isoleret_lager):
    """En vækning der blev stoppet er ikke en opgave jeg skal spørge om."""
    _post(_isoleret_lager, "r1", "s1", kind="autonomous")
    assert ifr.stopped_for_session("s1") is None


def test_for_gammelt_stop_forsvinder(_isoleret_lager):
    """Samme vindue som genoptagelse: 24 timer, ikke evigt."""
    _post(_isoleret_lager, "r1", "s1", alder_timer=ifr.GENOPTAGELSES_VINDUE_TIMER + 1)
    assert ifr.stopped_for_session("s1") is None


def test_stop_er_stadig_ikke_genoptagelig(_isoleret_lager):
    """Den eksisterende garanti skal stå uændret.

    `interrupted_for_session` må ALDRIG begynde at returnere et `cancelled`-run:
    den driver auto-genoptagelsen, og så ville brugerens stop starte sig selv —
    præcis fejlen fra 17/9.
    """
    _post(_isoleret_lager, "r1", "s1")
    assert ifr.interrupted_for_session("s1") is None
    assert ifr.stopped_for_session("s1") is not None


def test_sektionen_beder_om_at_spoerge(_isoleret_lager):
    """Blokken skal bære politikken: spørg, genoptag ikke."""
    _post(_isoleret_lager, "r1", "s1")
    tekst = ifr.stopped_prompt_section("s1") or ""
    assert "STOPPEDE" in tekst
    assert "halvfærdigt arbejde" in tekst
    assert "spørg" in tekst.lower()
    assert "AUTO-RESUME" not in tekst


def test_ingen_post_giver_ingen_sektion(_isoleret_lager):
    assert ifr.stopped_prompt_section("s1") is None


def test_sektionen_lander_i_den_byggede_prompt(_isoleret_lager, monkeypatch):
    """Ende-til-ende: blokken skal stå i den FAKTISKE prompt — ikke bare kunne bygges.

    En sektion der kan formateres men aldrig når modellen, er den teater-fejl
    Bjørn jager: mekanismen ser ud som om den virker, fordi den skriver noget.
    `_awareness_add` har to gates (sektions-switch og kontekst-komponist), og en
    af dem kunne tavst kaste blokken væk. Den her test ser det.

    Vindues-opslaget patches: assembly'en prob'er ellers model-kataloger over
    nettet, og en test skal ikke røre netværket for at bevise en prompt-sektion.
    """
    _post(_isoleret_lager, "r1", "s1")
    monkeypatch.setattr(
        "core.services.model_context.model_context_window",
        lambda *_a, **_k: 200_000,
        raising=False,
    )
    from core.services.prompt_contract import (
        _build_visible_chat_prompt_assembly_impl as build,
    )

    asm = build(
        provider="deepseek",
        model="deepseek-v4-flash",
        user_message="hvad var det vi lavede?",
        session_id="s1",
    )
    assert "STOPPEDE" in asm.text
    assert "halvfærdigt arbejde" in asm.text
    assert "genoptag det IKKE" in asm.text
