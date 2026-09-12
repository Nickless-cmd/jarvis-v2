"""Ros og ris — og hvad de bliver til."""
from datetime import UTC, datetime, timedelta

import pytest

from core.services import message_feedback as mf


@pytest.fixture(autouse=True)
def rent():
    mf._nulstil_for_tests()


def test_en_stemme_gemmes(isolated_runtime):
    assert mf.sæt_stemme(message_id="m1", vote="up")["vote"] == "up"
    assert [p["vote"] for p in mf.ugennemgåede()] == ["up"]


def test_samme_besked_taeller_ÉN_gang(isolated_runtime):
    # Uden det ville et dobbelttryk give et review en styrke der ikke var der.
    mf.sæt_stemme(message_id="m1", user_id="u", vote="up")
    mf.sæt_stemme(message_id="m1", user_id="u", vote="down")
    poster = mf.ugennemgåede()
    assert len(poster) == 1 and poster[0]["vote"] == "down"


def test_at_FORTRYDE_sletter_frem_for_at_gemme_tomt(isolated_runtime):
    # En stemme man har taget tilbage er ikke data om noget, og maa ikke
    # taelle med som «neutral».
    mf.sæt_stemme(message_id="m1", user_id="u", vote="up")
    mf.sæt_stemme(message_id="m1", user_id="u", vote="")
    assert mf.ugennemgåede() == []


def test_ugyldig_stemme_afvises(isolated_runtime):
    assert mf.sæt_stemme(message_id="m1", vote="måske")["status"] == "error"
    assert mf.sæt_stemme(message_id="", vote="up")["status"] == "error"


def test_review_prompten_beder_om_en_DOM_ikke_et_referat():
    # Uden det tredje udfald bliver alt til en lektie, og listen bliver
    # ubrugelig.
    t = mf.byg_review_prompt([
        {"vote": "up", "created_at": "2026-09-01T00:00:00", "uddrag": "godt svar"},
        {"vote": "down", "created_at": "2026-09-02T00:00:00", "uddrag": "forkert"},
    ])
    assert "LEKTIE" in t and "OVERVEJELSE" in t and "STØJ" in t
    assert "1 tommel op, 1 tommel ned" in t
    assert "godt svar" in t and "forkert" in t


def test_tikket_TIER_naar_der_intet_er(isolated_runtime, monkeypatch):
    # En maanedlig paamindelse om nul stemmer laerer én at ignorere den.
    kaldt = []
    import core.services.self_wakeup as sw
    monkeypatch.setattr(sw, "schedule_self_wakeup", lambda **k: kaldt.append(k) or {"status": "ok"})
    ud = mf.tick_feedback_review()
    assert ud["planlagt"] is False and kaldt == []


def test_tikket_planlaegger_en_WAKEUP_naar_der_ER_noget(isolated_runtime, monkeypatch):
    # En prompt-sektion der aldrig laeses er husets hyppigste fejl; en wakeup
    # giver ham en rigtig tur at taenke i.
    kaldt = []
    import core.services.self_wakeup as sw
    monkeypatch.setattr(sw, "schedule_self_wakeup", lambda **k: kaldt.append(k) or {"status": "ok"})
    mf.sæt_stemme(message_id="m1", vote="down")
    ud = mf.tick_feedback_review()
    assert ud == {"planlagt": True, "antal": 1}
    assert len(kaldt) == 1 and "LEKTIE" in kaldt[0]["prompt"]
    # ... og de er nu gennemgaaet.
    assert mf.ugennemgåede() == []


def test_kadencen_holder_en_maaned(isolated_runtime, monkeypatch):
    import core.services.self_wakeup as sw
    monkeypatch.setattr(sw, "schedule_self_wakeup", lambda **k: {"status": "ok"})
    mf.sæt_stemme(message_id="m1", vote="up")
    assert mf.tick_feedback_review()["planlagt"] is True
    mf.sæt_stemme(message_id="m2", vote="up")
    nu = datetime.now(UTC)
    assert mf.tick_feedback_review(nu + timedelta(days=29))["grund"] == "kadence"
    assert mf.tick_feedback_review(nu + timedelta(days=31))["planlagt"] is True


def test_en_AFVIST_wakeup_efterlader_stemmerne_ugennemgaaede(isolated_runtime, monkeypatch):
    # Markerede vi foer, ville maanedens stemmer forsvinde uden at nogen saa dem.
    import core.services.self_wakeup as sw
    monkeypatch.setattr(sw, "schedule_self_wakeup",
                        lambda **k: {"status": "error", "error": "nej"})
    mf.sæt_stemme(message_id="m1", vote="up")
    assert mf.tick_feedback_review()["planlagt"] is False
    assert len(mf.ugennemgåede()) == 1


def test_uret_saettes_OGSAA_naar_der_intet_var(isolated_runtime, monkeypatch):
    # Ellers ville en tom maaned betyde et databaseopslag ved HVERT tick
    # resten af maaneden.
    import core.services.self_wakeup as sw
    monkeypatch.setattr(sw, "schedule_self_wakeup", lambda **k: {"status": "ok"})
    assert mf.tick_feedback_review()["grund"] == "ingen stemmer"
    mf.sæt_stemme(message_id="m1", vote="up")
    assert mf.tick_feedback_review()["grund"] == "kadence"


def test_tikket_er_KOBLET_PAA_kadencen():
    """Mekanismen findes-kalderen-mangler er husets hyppigste fejl.

    Et tick ingen kalder koerer aldrig - og tavshed ligner «ingen stemmer».
    """
    import inspect
    from core.services import cluster_daemon_families as f
    kilde = inspect.getsource(f)
    assert '("feedback_review", _infra_feedback_review_live)' in kilde
    assert "from core.services.message_feedback import tick_feedback_review" in kilde


def test_ruten_er_KOBLET_PAA_servicen():
    import inspect
    from apps.api.jarvis_api.routes import chat
    kilde = inspect.getsource(chat.chat_message_feedback)
    assert "sæt_stemme(" in kilde
    assert "current_user_id()" in kilde   # stemmen hoerer til EN bruger
