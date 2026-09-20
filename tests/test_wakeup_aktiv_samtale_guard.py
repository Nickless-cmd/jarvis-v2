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
