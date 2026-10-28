"""En autonom koersel maa ikke lande i en samtale der lever.

MAALT 28/10-2026: to opgaver med mode=inspect landede i `chat-c05e28bb...` —
Bjorns igangvaerende samtale — fordi `_session_for_task` var det eneste led i
vae kke-kaeden der ikke spurgte om nogen talte i den.

Testene her værner om TRE ting, fordi den nemme rettelse er den forkerte:

1. En optaget samtale afvises (den ægte fejl).
2. En rolig samtale afvises IKKE — en regel der afviser alt er virkningsløs.
3. Der findes ingen `kind`-vaerdi der kan bruges som filter: `chat_sessions`
   har kun 'chat' og 'code', og begge er samtaler Bjorn sidder i.
"""
from __future__ import annotations

import pytest

from core.services import autonomous_side_task_dispatcher as d


@pytest.fixture()
def uden_resolvere(monkeypatch):
    """Isolér `_session_for_task` fra DB: giv den en fast app-samtale."""
    monkeypatch.setattr(d, "_target_session", lambda: "chat-levende")
    monkeypatch.setattr(
        "core.identity.owner_resolver.resolve_owner_target_session",
        lambda: "chat-levende",
    )
    monkeypatch.setattr(
        "core.identity.owner_resolver.session_is_external_channel",
        lambda sid: False,
    )
    return "chat-levende"


def test_en_optaget_samtale_afvises(uden_resolvere, monkeypatch):
    """Kernen: kører der en fersk tur, starter vi IKKE et konkurrerende run."""
    from core.services import wakeup_dispatcher as w

    monkeypatch.setattr(w, "_active_turn_blocks", lambda sid: "fersk visible-tur")
    monkeypatch.setattr(w, "_bruger_skrev_for_nylig", lambda sid: False)
    monkeypatch.setattr(w, "_jarvis_skrev_for_nylig", lambda sid: False)

    assert d._session_for_task({"session_id": uden_resolvere}) == ""


def test_en_samtale_hvor_bjoern_lige_skrev_afvises(uden_resolvere, monkeypatch):
    """Han skrev for 30 sekunder siden — opgaven venter, den forsvinder ikke."""
    from core.services import wakeup_dispatcher as w

    monkeypatch.setattr(w, "_active_turn_blocks", lambda sid: "")
    monkeypatch.setattr(w, "_bruger_skrev_for_nylig", lambda sid: True)
    monkeypatch.setattr(w, "_jarvis_skrev_for_nylig", lambda sid: False)

    assert d._session_for_task({"session_id": uden_resolvere}) == ""


def test_en_samtale_hvor_jeg_lige_svarede_afvises(uden_resolvere, monkeypatch):
    """Symmetrien: jeg har netop svaret, han er ved at laese — ikke forstyrr."""
    from core.services import wakeup_dispatcher as w

    monkeypatch.setattr(w, "_active_turn_blocks", lambda sid: "")
    monkeypatch.setattr(w, "_bruger_skrev_for_nylig", lambda sid: False)
    monkeypatch.setattr(w, "_jarvis_skrev_for_nylig", lambda sid: True)

    assert d._session_for_task({"session_id": uden_resolvere}) == ""


def test_en_rolig_samtale_afvises_ikke(uden_resolvere, monkeypatch):
    """Modproeven: en regel der afviser alt er vaerre end fejlen.

    Uden denne test ville et `return ""` paa første linje bestaa alle tre
    test ovenfor — og slukke for al autonom dispatch uden at nogen opdagede det.
    """
    from core.services import wakeup_dispatcher as w

    monkeypatch.setattr(w, "_active_turn_blocks", lambda sid: "")
    monkeypatch.setattr(w, "_bruger_skrev_for_nylig", lambda sid: False)
    monkeypatch.setattr(w, "_jarvis_skrev_for_nylig", lambda sid: False)

    assert d._session_for_task({"session_id": uden_resolvere}) == uden_resolvere


def test_der_findes_ingen_kind_der_kan_bruges_som_filter():
    """Dokumenterer HVORFOR opgavens kind-forslag ikke blev bygget.

    Maalt i `chat_sessions`: kun 'chat' og 'code'. Titlerne i kind='code' er
    Bjorns egne samtaler («yo», «godmorgen j..»), saa et forbud mod kind='chat'
    ville efterlade nul gyldige maal — og et forbud mod begge ville slukke
    dispatchen helt. Testen laaser maalingen, saa forslaget ikke genopstaar
    uden at nogen ser at praemissen ikke findes i data.
    """
    import sqlite3
    from pathlib import Path

    db = Path.home() / ".jarvis-v2" / "state" / "jarvis.db"
    if not db.exists():
        pytest.skip("ingen levende DB i dette miljoe")

    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
        raekker = conn.execute(
            "SELECT DISTINCT kind FROM chat_sessions"
        ).fetchall()
    kinds = {str(r[0]) for r in raekker}

    # Der findes ingen 'autonomous'/'work'/'agent'-kind at falde tilbage paa.
    assert kinds <= {"chat", "code"}, (
        f"der er kommet en ny session-kind ({kinds - {'chat', 'code'}}) — "
        "saa skal kind-forbuddet overvejes igen, for nu findes der et gyldigt maal"
    )
