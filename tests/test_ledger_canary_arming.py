"""Den NAESTE nye session baerer observationsvinduet — Fase 11.

MAALT 10/9-2026: kanariefuglen sad paa to sessioner der havde vaeret DOEDE i
20 timer (sidste haendelse 9/9 kl. 16:32), mens dagens trafik loeb i en tredje
session med 729 beskeder som slet ikke var i ledgeren. Et observationsvindue
der ikke foelger trafikken, er et lukket vindue.

Bjoerns valg: indrullér den naeste NYE session i stedet for den igangvaerende.
`advance_storage_mode` er ENVEJS med vilje, og en ren start giver et vindue
der loeber paa aegte trafik fra foerste besked — uden en irreversibel aendring
paa en samtale der er i gang.
"""
from __future__ import annotations


def test_armering_gaelder_KUN_én_session(isolated_runtime, monkeypatch):
    import core.services.ledger_canary as lc

    kaldt: list[str] = []
    monkeypatch.setattr(lc, "enable_shadow",
                        lambda sid: kaldt.append(sid) or {"ok": True})

    assert lc.is_armed() is False
    assert lc.arm_next_session(note="proeve")["ok"] is True
    assert lc.is_armed() is True

    lc.maybe_enroll_new_session("chat-foerste")
    lc.maybe_enroll_new_session("chat-anden")

    assert kaldt == ["chat-foerste"], (
        "armeringen ramte mere end én session — vinduet skal have ÉN baerer")
    assert lc.is_armed() is False, "armeringen blev ikke ryddet"


def test_uarmet_roerer_ingenting(isolated_runtime, monkeypatch):
    import core.services.ledger_canary as lc

    kaldt: list[str] = []
    monkeypatch.setattr(lc, "enable_shadow", lambda sid: kaldt.append(sid))
    assert lc.maybe_enroll_new_session("chat-x") is None
    assert kaldt == []


def test_en_fejlende_kanariefugl_vaelter_ikke_sessionen(isolated_runtime, monkeypatch):
    """En kanariefugl maa aldrig kunne braekke oprettelsen af en samtale.
    Gaar noget galt, forbliver sessionen `legacy` — praecis som foer."""
    import core.services.ledger_canary as lc

    def _sprael(sid):
        raise RuntimeError("ledgeren er nede")

    monkeypatch.setattr(lc, "enable_shadow", _sprael)
    lc.arm_next_session()
    assert lc.maybe_enroll_new_session("chat-y") is None   # ingen undtagelse
    assert lc.is_armed() is False, (
        "en fejlet indrullering efterlod armeringen — naeste session ville "
        "proeve igen i det uendelige")


def test_oprettelsen_af_en_session_kalder_kanariefuglen(isolated_runtime, monkeypatch):
    """Koblingen, ikke bare muligheden. Uden denne test kunne armeringen
    findes og aldrig blive kaldt — dagens hyppigste fejl."""
    import core.services.chat_sessions as cs

    set_sid: list[str] = []
    monkeypatch.setattr("core.services.ledger_canary.maybe_enroll_new_session",
                        lambda sid: set_sid.append(sid))
    ny = cs.create_chat_session(title="proeve")
    assert set_sid == [str(ny.get("session_id") or ny.get("id") or "")], (
        "oprettelsen af en session kalder ikke kanariefuglen")


def test_en_TOM_session_kan_indrulleres(isolated_runtime):
    """Fejlen fra foerste deploy. `enable_shadow` var bygget til at efterfylde
    en EKSISTERENDE session og afviste en helt ny med «sessionen har ingen
    beskeder». Armeringen fyrer ved OPRETTELSEN — altsaa praecis dér hvor der
    er nul beskeder — saa mekanismen koerte og gjorde ingenting.

    Nul historik er den RENESTE sag: der er ingen tidligere beskeder som
    ledgeren kan komme til at mangle.
    """
    import core.services.chat_sessions as cs
    from core.runtime.db_session_ledger import storage_mode
    from core.services.ledger_canary import arm_next_session

    arm_next_session()
    ny = cs.create_chat_session(title="frisk")
    sid = str(ny.get("session_id") or ny.get("id") or "")
    assert storage_mode(sid) == "shadow", (
        f"en frisk session blev ikke indrulleret (mode={storage_mode(sid)!r}) "
        "— kanariefuglen koerte og gjorde ingenting")
