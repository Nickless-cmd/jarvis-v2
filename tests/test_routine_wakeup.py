"""Rutningen: en session-rutine skal kunne vække mig hvor Bjørn er.

Bjørn 19/10-2026: «når en rutine oprettes skal man vælge om den skal udføre i
baggrunden og rapportere til inbox eller om rutines udføres af dig hvor
brugeren sidst var aktiv og self med cool Down så de ikk kan forurene en
kørende sessionen».

Tre led skal holde, og de testes hver for sig fordi de fejler hver sin vej:

1. **Dispatch-tilladelsen** — kildetypen `recurring` må starte et run.
2. **Modenheden** — men KUN for opgaver der er bundet til en samtale. En
   baggrunds-opgave rapporterer til indbakken og venter; den må ikke trænge
   ind i en samtale den ikke hører til.
3. **Cool-down** — har jeg selv svaret for nylig, er samtalen ikke ledig.

Plus ejer-beviset, som er det der ellers gør hele kæden virkningsløs: målt
19/10-2026 stod ALLE 16 recurring-poster som `huset`, fordi
`verificeret_jarvis_run` kræver at run-id'et er det KØRENDE run — og posten
skrives først ved lukning, hvor det ikke længere er.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


# ── 1. Dispatch-tilladelsen ────────────────────────────────────────────────

def test_recurring_ma_starte_et_run():
    """Kildetypen skal stå i sættet — ellers når posten aldrig til modenheden."""
    from core.services.inbox_state import KAN_DISPATCHES_KILDETYPER, kan_dispatch

    assert "recurring" in KAN_DISPATCHES_KILDETYPER
    assert kan_dispatch("recurring") is True


def test_recurring_er_stadig_ikke_gatende():
    """Dispatch-tilladelse må IKKE give magten til at nægte en mutation.

    Det er hele kontrakten: «kun det du selv har lovet kan blokere». En
    baggrunds-rutines rapport må informere, aldrig lamme.
    """
    from core.services.inbox_state import IKKE_GATENDE_KILDETYPER

    assert "recurring" in IKKE_GATENDE_KILDETYPER


def test_kilde_ejer_kan_loefte_en_session_rutine():
    """Ejer-beviset er den vej der gør posten løftbar uden at give den magt.

    `_kilde_ejer_kan_loefte` accepterer netop fordi `recurring` er
    ikke-gatende: etiketten flyttes, `kraever_handling` forbliver False.
    """
    from core.services.inbox_state import _kilde_ejer_kan_loefte

    assert _kilde_ejer_kan_loefte("recurring", "jarvis") is True
    # En gatende type må ikke kunne løftes ad samme vej.
    assert _kilde_ejer_kan_loefte("job", "jarvis") is False


# ── 2. Opgave-id udtrukket fra postens kilde_id ────────────────────────────

@pytest.mark.parametrize(
    "kilde_id,forventet",
    [
        ("recurring-rec-6456e88d03-autonomous-cd6aadfc166e4cec8b4a3cd869819412",
         "rec-6456e88d03"),
        ("recurring-rec-276ee9620d-visible-abc123", "rec-276ee9620d"),
        ("recurring-rec-1a3ff3a1ad-run_40cf6f1ac738", "rec-1a3ff3a1ad"),
        ("", ""),
        ("noget-andet", ""),
        ("recurring-ukendt-format", ""),
    ],
)
def test_task_id_fra_kilde(kilde_id, forventet):
    """Ukendt form → tom streng. Kalleren vækker ikke på en post vi ikke forstår."""
    from core.services.inbox_idle_waker import _task_id_fra_kilde

    assert _task_id_fra_kilde(kilde_id) == forventet


# ── 3. Modenheden: session vs. baggrund ────────────────────────────────────

def _post(kilde_id: str, kildetype: str = "recurring") -> dict:
    return {
        "kildetype": kildetype,
        "kilde_id": kilde_id,
        "kraever_handling": 0,
        "verificeret_ejer": "jarvis",
    }


def test_session_rutine_er_moden(monkeypatch):
    monkeypatch.setattr(
        "core.services.recurring_tasks.er_session_rutine", lambda _t: True,
    )
    from core.services.inbox_idle_waker import _er_moden

    assert _er_moden(_post("recurring-rec-abc123-autonomous-x"), vaekninger={}) is True


def test_baggrunds_rutine_er_ikke_moden(monkeypatch):
    """Den vigtigste negation: en baggrunds-opgave må IKKE vække nogen.

    Uden dette led ville alle 13 levende opgaver — inkl. den 4×daglige
    runtime-inspektion — begynde at starte runs midt i en samtale.
    """
    monkeypatch.setattr(
        "core.services.recurring_tasks.er_session_rutine", lambda _t: False,
    )
    from core.services.inbox_idle_waker import _er_moden

    assert _er_moden(_post("recurring-rec-abc123-autonomous-x"), vaekninger={}) is False


def test_ukendt_opgave_er_ikke_moden(monkeypatch):
    """Kan opgaven ikke redegøres for, vækker vi ikke. Fail-closed."""
    from core.services.inbox_idle_waker import _er_moden

    assert _er_moden(_post("noget-ukendt"), vaekninger={}) is False


# ── 4. Cool-down efter MIN egen besked ─────────────────────────────────────

def _beskeder(*, rolle: str, alder_s: float) -> list[dict]:
    tid = (datetime.now(UTC) - timedelta(seconds=alder_s)).isoformat()
    return [{"role": rolle, "created_at": tid, "content": "x"}]


def test_jeg_har_lige_svaret_blokerer(monkeypatch):
    monkeypatch.setattr(
        "core.services.chat_sessions.recent_chat_session_messages",
        lambda _s, limit=8: _beskeder(rolle="assistant", alder_s=60),
    )
    from core.services.wakeup_dispatcher import _jarvis_skrev_for_nylig

    assert _jarvis_skrev_for_nylig("s1") is True


def test_gammelt_svar_blokerer_ikke(monkeypatch):
    monkeypatch.setattr(
        "core.services.chat_sessions.recent_chat_session_messages",
        lambda _s, limit=8: _beskeder(rolle="assistant", alder_s=600),
    )
    from core.services.wakeup_dispatcher import _jarvis_skrev_for_nylig

    assert _jarvis_skrev_for_nylig("s1") is False


def test_brugerens_egen_besked_taeller_ikke_som_min(monkeypatch):
    """De to karantæner må ikke blande roller — de har forskellige vinduer."""
    monkeypatch.setattr(
        "core.services.chat_sessions.recent_chat_session_messages",
        lambda _s, limit=8: _beskeder(rolle="user", alder_s=60),
    )
    from core.services.wakeup_dispatcher import _jarvis_skrev_for_nylig

    assert _jarvis_skrev_for_nylig("s1") is False


def test_manglende_historik_blokerer_ikke(monkeypatch):
    """Self-safe: en læsefejl må ikke tie et run ihjel for evigt."""
    def _braek(*_a, **_k):
        raise RuntimeError("db nede")

    monkeypatch.setattr(
        "core.services.chat_sessions.recent_chat_session_messages", _braek,
    )
    from core.services.wakeup_dispatcher import _jarvis_skrev_for_nylig

    assert _jarvis_skrev_for_nylig("s1") is False


def test_min_karantaene_er_kortere_end_hans():
    """5 min mod 10 — de to vinduer er bevidst forskellige."""
    from core.services.wakeup_dispatcher import (
        _BRUGER_KARANTAENE_S,
        _JARVIS_KARANTAENE_S,
    )

    assert _JARVIS_KARANTAENE_S == 300.0
    assert _JARVIS_KARANTAENE_S < _BRUGER_KARANTAENE_S


def test_guarden_navngiver_min_karantaene(monkeypatch):
    """Skip-årsagen skal skelne de to vinduer — ellers kan loggen ikke svare."""
    monkeypatch.setattr(
        "core.services.wakeup_dispatcher._bruger_skrev_for_nylig", lambda _s: False,
    )
    monkeypatch.setattr(
        "core.services.wakeup_dispatcher._jarvis_skrev_for_nylig", lambda _s: True,
    )
    from core.services.wakeup_dispatcher import _active_turn_blocks

    assert _active_turn_blocks("s1") == "jarvis_skrev_for_nylig"


# ── 5. Hele kæden: fra registrering til kandidat ───────────────────────────

@pytest.fixture
def inbox_db(monkeypatch, tmp_path):
    import sqlite3
    from contextlib import contextmanager

    from core.runtime import db_inbox

    sti = tmp_path / "rutning.db"

    @contextmanager
    def _connect():
        k = sqlite3.connect(sti)
        k.row_factory = sqlite3.Row
        try:
            yield k
            k.commit()
        finally:
            k.close()

    monkeypatch.setattr(db_inbox, "connect", _connect)
    monkeypatch.setattr(db_inbox, "_skema_klar", False)
    return sti


def _registrer(monkeypatch, *, kilde_ejer: str, kilde_id: str) -> dict:
    """Skriv en recurring-post gennem den ÆGTE vej — ikke en håndlavet række.

    Det er hele pointen: `verificeret_ejer` afgøres af `registrer_kilde`, og
    den afgørelse er præcis det der ellers gør kæden virkningsløs.
    """
    from core.services import inbox_state

    monkeypatch.setattr(
        inbox_state, "_autentificeret_bruger_matcher", lambda _b: True,
    )
    return inbox_state.registrer_kilde(
        bruger_id="bjorn",
        kildetype="recurring",
        kilde_id=kilde_id,
        oprettende_run_id="autonomous-abc",
        paastaaet_ejer="huset",
        beskrivelse="Rutine-resultat",
        session_id="chat-1",
        kilde_ejer=kilde_ejer,
    )


def test_session_rutine_bliver_en_kandidat(inbox_db, monkeypatch):
    """En session-rutine skal ende som `jarvis` OG kunne vække.

    Uden ejer-beviset stod posten som `huset`, og `kandidater()` sprang den
    over — målt på alle 16 faktiske recurring-poster 19/10-2026.
    """
    monkeypatch.setattr(
        "core.services.recurring_tasks.er_session_rutine", lambda _t: True,
    )
    _registrer(monkeypatch, kilde_ejer="jarvis",
               kilde_id="recurring-rec-abc123-autonomous-abc")

    from core.services.inbox_idle_waker import kandidater

    fundet = kandidater("bjorn")
    assert len(fundet) == 1, fundet
    assert fundet[0]["verificeret_ejer"] == "jarvis"
    # Stadig ikke-gatende: den må informere, aldrig lamme.
    assert not fundet[0]["kraever_handling"]


def test_baggrunds_rutine_bliver_ikke_en_kandidat(inbox_db, monkeypatch):
    """En baggrunds-rutine er `huset` og må ikke vække nogen."""
    monkeypatch.setattr(
        "core.services.recurring_tasks.er_session_rutine", lambda _t: False,
    )
    _registrer(monkeypatch, kilde_ejer="",
               kilde_id="recurring-rec-abc123-autonomous-abc")

    from core.services.inbox_idle_waker import kandidater

    assert kandidater("bjorn") == []


def test_ejer_beviset_naegtes_for_en_gatende_type(inbox_db, monkeypatch):
    """Grænsen der gør ejer-beviset sikkert: en gatende type kan IKKE løftes.

    Uden den kunne `kilde_ejer="jarvis"` på en `job`-post både mærke OG låse,
    og «huset kan informere, men ikke kræve» var omgået ad en ny vej.
    """
    from core.services import inbox_state

    monkeypatch.setattr(
        inbox_state, "_autentificeret_bruger_matcher", lambda _b: True,
    )
    r = inbox_state.registrer_kilde(
        bruger_id="bjorn",
        kildetype="job",
        kilde_id="job-1",
        oprettende_run_id="autonomous-abc",
        paastaaet_ejer="huset",
        kilde_ejer="jarvis",
    )
    assert r["post"]["verificeret_ejer"] != "jarvis"

