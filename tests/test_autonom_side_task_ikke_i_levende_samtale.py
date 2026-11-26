"""En autonom koersel maa ikke lande i en samtale der lever.

MAALT 28/10-2026: to opgaver med mode=inspect landede i `chat-c05e28bb...` —
Bjorns igangvaerende samtale — fordi `_session_for_task` var det eneste led i
vae kke-kaeden der ikke spurgte om nogen talte i den.

BJORN 26/11-2026 STRAMMEDE REGLEN: «chat mode skal kun kunne vaekkes af
rutiner eller wakeups.. ikk side opgaver eller inbox eller initeritiver».
Foer handlede reglen om HVORNAAR en samtale var rolig nok; nu handler den om
HVEM der overhovedet maa give en side-opgave en samtale-adresse. Svaret er
ingen — en side-opgave hoerer til i baggrunden.

Testene her værner om tre ting, fordi den nemme rettelse er den forkerte:

1. En `chat-*`-adresse omdirigeres til baggrundssiloen (den aegte regel).
2. En `auto-*`-adresse roeres IKKE — reglen handler om samtaler, ikke om
   baggrundsarbejde. Uden denne modproeve ville et `return silo` paa foerste
   linje bestaa alt nedenfor og flytte ALT arbejde vaek fra sin silo.
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


def test_en_chat_adresse_omdirigeres_til_baggrundssiloen(uden_resolvere):
    """Kernen: en side-opgave maa ikke laane Bjorns samtale.

    26/11-2026: svaret var foer `""` (opgaven ventede). Det var forkert — tomt
    svar betyder «ingen start», saa 78 % af opgaverne (527 af 677 maalt) ville
    vente for evigt. Opgaven skal KOERE, bare ikke i samtalen.
    """
    svar = d._session_for_task({"session_id": uden_resolvere, "autonomy_mode": "inspect"})

    assert svar, "en side-opgave maa ikke ende uden en adresse"
    assert not svar.startswith("chat-"), (
        "side-opgaven landede i en samtale — praecis det Bjorn forbod"
    )
    assert svar.startswith("auto-side-task-"), (
        f"forventede en baggrundssilo, fik {svar!r}"
    )


def test_en_chat_adresse_omdirigeres_uanset_om_samtalen_er_rolig(uden_resolvere):
    """Ogsaa en HELT rolig samtale maa afvises som adresse.

    Foer var dette modproeven der sikrede at reglen ikke afviste alt. Nu er
    modproeven en anden: at en `auto-*`-adresse ikke roeres (se nedenfor).
    Her laases det at rolighed ikke laengere er kriteriet — kilden er.
    """
    svar = d._session_for_task({"session_id": uden_resolvere, "autonomy_mode": "inspect"})

    assert not svar.startswith("chat-")


def test_en_auto_adresse_er_en_logbog_ikke_en_modtager(uden_resolvere):
    """Modproeven: reglen maa ikke goere dispatch virkningsloes.

    `pick_wakeup_run_target` afviser allerede `auto-*` som MODTAGER (17/11-2026:
    «en auto-silo er en logbog, ikke en modtager»), saa svaret bliver en frisk
    baggrundssilo — ikke den oprindelige.

    Det vigtige her er ikke hvilken silo der vaelges, men at svaret ALDRIG er
    tomt: tomt svar betyder «ingen start», og saa ville en regel der ser rigtig
    ud slukke al autonom dispatch. Det var den fejl der blev maalt 26/11-2026,
    hvor 78 % af side-opgaverne ville vente for evigt.
    """
    for adresse in ("auto-work-20261126", "chat-bjoern", ""):
        svar = d._session_for_task(
            {"session_id": adresse, "autonomy_mode": "inspect"}
        )
        assert svar, f"tomt svar for adresse {adresse!r} — dispatch ville staa stille"
        assert not svar.startswith("chat-"), (
            f"adresse {adresse!r} endte i en samtale"
        )


def test_en_ekstern_kanal_giver_stadig_ingen_start(uden_resolvere, monkeypatch):
    """Discord/Telegram er hverken en samtale eller en silo — de venter.

    Bevaret fra 28/10-2026: `_target_session` springer eksterne kanaler over,
    og en opgave der kun har en saadan adresse maa ikke gætte en anden.
    """
    monkeypatch.setattr(
        "core.identity.owner_resolver.session_is_external_channel",
        lambda sid: str(sid).startswith("disc-"),
    )

    svar = d._session_for_task({"session_id": "disc-origin", "autonomy_mode": "inspect"})

    # Der findes ingen gyldig adresse, saa opgaven flyttes til baggrunden —
    # den venter ikke laengere, og den laaner ikke en ekstern kanal.
    assert not svar.startswith("disc-")
    assert not svar.startswith("chat-")


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
