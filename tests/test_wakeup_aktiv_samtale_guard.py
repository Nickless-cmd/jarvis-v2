"""En autonom kørsel må ikke starte i en samtale brugeren er i gang med.

Bjørn 20/9-2026: «hvis han selv er i gang må en autonom session ikke kunne
starte og køre i baggrunden i samme session — det er kun agenter der skal
kunne det».

Den gamle vagt spurgte den GLOBALE aktiv-plads og holdt kun op i 120 sekunder
efter sidste livstegn. To huller: pladsen rummer ét run ad gangen, og et run
der venter på et godkendelses-kort kan stå stille i minutter uden at være
færdigt. Og mellem to af hans beskeder kører der ingenting — dér smuttede en
autonom ind mens han læste svaret.

Nu spørges run-loggen pr. samtale, og der er en karantæne efter hans sidste
besked. Hans valg: «til turen er færdig + en karantæne».
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import wakeup_dispatcher as wd


@pytest.fixture(autouse=True)
def _ingen_global_aktiv(monkeypatch):
    """Den gamle vej siger altid «fri», så testene måler de NYE regler."""
    import core.services.visible_runs as vr
    monkeypatch.setattr(vr, "_get_active_visible_run_state", lambda: {})


def _beskeder(monkeypatch, *, alder_s: float | None):
    """Sessionens seneste beskeder — med en brugerbesked af den alder."""
    rk = []
    if alder_s is not None:
        t = datetime.now(UTC) - timedelta(seconds=alder_s)
        rk = [{"role": "user", "content": "hej", "created_at": t.isoformat()}]
    import core.services.chat_sessions as cs
    monkeypatch.setattr(cs, "recent_chat_session_messages", lambda sid, **k: list(rk))


def _levende(monkeypatch, run_id):
    from core.services import run_event_log as rel
    monkeypatch.setattr(rel, "active_run_for_session", lambda sid: run_id)


def test_et_levende_run_i_samtalen_blokerer(monkeypatch):
    """Uanset hvor længe det har stået stille — et kort kan vente i minutter."""
    _levende(monkeypatch, "visible-koerer")
    _beskeder(monkeypatch, alder_s=None)
    assert wd._active_turn_blocks("chat-1") == "session_har_levende_run"


def test_hans_seneste_besked_holder_karantaene(monkeypatch):
    """Mellem to beskeder kører der ingenting — og dér smuttede den ind før."""
    _levende(monkeypatch, None)
    _beskeder(monkeypatch, alder_s=60)
    assert wd._active_turn_blocks("chat-1") == "bruger_skrev_for_nylig"


def test_efter_karantaenen_er_samtalen_fri(monkeypatch):
    _levende(monkeypatch, None)
    _beskeder(monkeypatch, alder_s=wd._BRUGER_KARANTAENE_S + 30)
    assert wd._active_turn_blocks("chat-1") == ""


def test_karantaenen_er_ti_minutter(monkeypatch):
    """Hans eget valg 20/9-2026. Pinnet, så den ikke skrider i det stille."""
    assert wd._BRUGER_KARANTAENE_S == 600.0


def test_vinduet_er_BUNDET_og_ikke_en_fuld_historik(monkeypatch):
    """Vagten må ikke blive en ny fuld historik-læsning — se verify_history_reads."""
    set_limit = {}
    import core.services.chat_sessions as cs
    monkeypatch.setattr(cs, "recent_chat_session_messages",
                        lambda sid, **k: set_limit.update(k) or [])
    _levende(monkeypatch, None)
    wd._active_turn_blocks("chat-1")
    assert set_limit.get("limit") == wd._KARANTAENE_VINDUE


def test_en_ulaeselig_runlog_blokerer_ikke_et_wakeup(monkeypatch):
    """Self-safe: et wakeup må aldrig forsvinde fordi loggen ikke kunne læses."""
    from core.services import run_event_log as rel

    def _braekker(_sid):
        raise RuntimeError("væk")
    monkeypatch.setattr(rel, "active_run_for_session", _braekker)
    _beskeder(monkeypatch, alder_s=None)
    assert wd._active_turn_blocks("chat-1") == ""


def test_uden_session_falder_den_tilbage_paa_den_gamle_vej(monkeypatch):
    """Et wakeup uden samtale kan ikke måles pr. samtale — så gælder det gamle."""
    _levende(monkeypatch, "visible-x")
    _beskeder(monkeypatch, alder_s=10)
    assert wd._active_turn_blocks("") == ""


# ── Indbakke-vækkeren spørger KUN om et levende run (Bjørn 12/11-2026) ─────────
#
# Målt: wake-eee651a4e1 fyrede 18:15:26 i en samtale hvor intet kørte (sidste run
# `completed` 18:11:51), og blev holdt tilbage i 7 minutter fordi hans seneste
# besked var 4 min gammel (karantæne 10 min) og Jarvis' 3,5 min (karantæne 5 min).
# 17 tilbageholdelser samme dag, 2 vækninger der faktisk startede. Loggen kaldte
# det «aktiv». Bjørn: «karantænen mener sessionen er aktiv selv om den er
# inaktiv» — og valgte at «aktiv» for en vækning kun er et levende run.
def _assistent_besked(monkeypatch, *, alder_s: float):
    t = datetime.now(UTC) - timedelta(seconds=alder_s)
    rk = [{"role": "assistant", "content": "svar", "created_at": t.isoformat()}]
    import core.services.chat_sessions as cs
    monkeypatch.setattr(cs, "recent_chat_session_messages", lambda sid, **k: list(rk))


@pytest.mark.parametrize("levende, bruger_alder_s, jarvis_alder_s, uden_karantaene, med_karantaene", [
    # intet kører, hans besked er 1 min gammel: karantænen holder, vækkeren slipper
    (None, 60, None, "", "bruger_skrev_for_nylig"),
    # intet kører, Jarvis svarede for 1 min siden
    (None, None, 60, "", "jarvis_skrev_for_nylig"),
    # et levende run blokerer UANSET (et godkendelses-kort kan stå i minutter)
    ("visible-koerer", None, None, "session_har_levende_run", "session_har_levende_run"),
    ("visible-koerer", 60, None, "session_har_levende_run", "session_har_levende_run"),
    # helt stille: begge slipper
    (None, None, None, "", ""),
])
def test_karantaenen_kan_slaas_fra_men_et_levende_run_blokerer_altid(
        monkeypatch, levende, bruger_alder_s, jarvis_alder_s, uden_karantaene, med_karantaene):
    _levende(monkeypatch, levende)
    if jarvis_alder_s is not None:
        _assistent_besked(monkeypatch, alder_s=jarvis_alder_s)
    else:
        _beskeder(monkeypatch, alder_s=bruger_alder_s)

    assert wd._active_turn_blocks("chat-1", karantaene=False) == uden_karantaene
    # standarden er UÆNDRET for rutiner, sideopgaver og kvitteringer
    assert wd._active_turn_blocks("chat-1") == med_karantaene


def test_indbakke_vaekkeren_regner_en_samtale_uden_levende_run_for_inaktiv(monkeypatch):
    """Den ÆGTE `_session_er_aktiv` — ikke en stub — med hans besked 1 min gammel."""
    from core.services import inbox_idle_waker as w

    _levende(monkeypatch, None)
    _beskeder(monkeypatch, alder_s=60)
    monkeypatch.setattr("core.services.visible_runs.turn_is_open", lambda sid: False)

    assert w._session_er_aktiv("chat-1") is False


def test_indbakke_vaekkeren_regner_en_samtale_med_levende_run_for_aktiv(monkeypatch):
    from core.services import inbox_idle_waker as w

    _levende(monkeypatch, "visible-koerer")
    _beskeder(monkeypatch, alder_s=None)

    assert w._session_er_aktiv("chat-1") is True
