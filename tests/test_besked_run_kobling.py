"""Run-id'et følger med snapshottet ud, så klienten ikke afdublerer på prosa.

## Hullet (målt 6/10-2026)

Bjørn: «Jeg ser 2 runs i tråden med samme svar.»

Dubletten står IKKE i databasen — jeg sammenlignede alle svarpar i vinduet
omkring klagen, og ligheden var 1-12 %. Der er én kopi gemt. Det er desks
bro-kopi af det streamede svar der bliver stående ved siden af serverens kopi,
fordi afdubleringen er et BYTE-match på en prosa serveren selv har skrevet om.

Mobilens egen kommentar navngiver forskellen præcist, målt samme dag: serveren
persisterer alle text-blokke **undtagen den første**, mens broen joiner dem
alle. Teksterne er derfor aldrig ens.

Rettelsen: serveren sender `run_id` med på de beskeder den ved hvem der skrev.
Det er en præcis nøgle, og den kan ikke brækkes af en omskrivning.
"""
from __future__ import annotations

import pytest

from core.services import besked_run_kobling as K


@pytest.fixture(autouse=True)
def _tomt_kort():
    K.ryd()
    yield
    K.ryd()


# ── kortet selv ─────────────────────────────────────────────────────────────

def test_den_der_skrev_beskeden_kan_slaas_op():
    K.noter("message-abc", "visible-bd1727a4")
    assert K.run_for("message-abc") == "visible-bd1727a4"


def test_en_ukendt_besked_giver_TOM_streng_ikke_et_gaet():
    """"" betyder «uvist» og skal få klienten til at falde tilbage paa sit
    tekst-match. Returnerede den et vilkaarligt run, ville broen blive droppet
    som «fremmed» — og saa forsvinder svaret i stedet for at staa dobbelt."""
    assert K.run_for("message-findes-ikke") == ""
    assert K.run_for("") == ""


def test_tomme_vaerdier_skriver_ikke():
    K.noter("", "visible-1")
    K.noter("message-1", "")
    assert K.antal() == 0


def test_kortet_er_BUNDET():
    """Et ubundet kort i en proces der lever i dage er en laekage der ikke viser
    sig foer den goer."""
    for i in range(K.MAKS + 50):
        K.noter(f"message-{i}", f"visible-{i}")
    assert K.antal() == K.MAKS
    # den nyeste er beholdt, den aeldste er faldet ud
    assert K.run_for(f"message-{K.MAKS + 49}") == f"visible-{K.MAKS + 49}"
    assert K.run_for("message-0") == ""


def test_en_gentaget_notering_overskriver_og_rykker_frem():
    K.noter("message-a", "visible-foerste")
    K.noter("message-a", "visible-anden")
    assert K.run_for("message-a") == "visible-anden"
    assert K.antal() == 1


# ── snapshottet, mod rigtig sqlite ──────────────────────────────────────────

def _session_med_svar() -> tuple[str, str]:
    """Opret en samtale med én brugerbesked og ét assistent-svar.

    Returnerer (session_id, assistentens message_id). Session-id'et kommer FRA
    serveren — `create_chat_session` laver det selv og tager ikke et med.
    """
    from core.services.chat_sessions import append_chat_message, create_chat_session

    sid = str(create_chat_session(title="t")["id"])
    append_chat_message(session_id=sid, role="user", content="spoergsmaal")
    svar = append_chat_message(session_id=sid, role="assistant", content="et svar der er langt nok")
    return sid, str(svar["id"])


def test_snapshottet_baerer_run_id_naar_vi_ved_det(isolated_runtime):
    from core.services.chat_sessions import get_chat_session

    sid, mid = _session_med_svar()
    K.noter(mid, "visible-bd1727a4")

    snapshot = get_chat_session(sid)
    svar = [m for m in snapshot["messages"] if m["role"] == "assistant"]
    assert len(svar) == 1
    assert svar[0]["run_id"] == "visible-bd1727a4"


def test_feltet_UDELADES_naar_vi_ikke_ved_det(isolated_runtime):
    """Efter en server-genstart er kortet tomt. Et tomt felt der betoed
    «fremmed» ville droppe en bro der skulle bevares."""
    from core.services.chat_sessions import get_chat_session

    sid, _mid = _session_med_svar()
    snapshot = get_chat_session(sid)
    svar = [m for m in snapshot["messages"] if m["role"] == "assistant"]
    assert "run_id" not in svar[0], svar[0]


def test_brugerbeskeder_faar_aldrig_feltet(isolated_runtime):
    from core.services.chat_sessions import get_chat_session

    sid, mid = _session_med_svar()
    K.noter(mid, "visible-bd1727a4")
    snapshot = get_chat_session(sid)
    for m in snapshot["messages"]:
        if m["role"] == "user":
            assert "run_id" not in m


# ── persist-stien noterer koblingen ─────────────────────────────────────────

def test_persist_stien_noterer_run_id(isolated_runtime, monkeypatch):
    """Uden denne linje er kortet altid tomt, og hele rettelsen er død kode —
    det hyppigste moenster i dette repo: korrekt kode, ingen kalder."""
    import core.services.visible_runs_outcomes as vro

    monkeypatch.setattr(
        vro, "_append_chat_message_with_retry",
        lambda **kw: {"id": "message-fra-persist", "role": "assistant",
                      "content": kw.get("content", "")})

    class _Run:
        run_id = "visible-3433cf05"
        session_id = "chat-1"
        provider = "ollama"
        model = "deepseek-v4-flash"
        autonomous = False
        user_message = "spoergsmaal"

    vro._persist_session_assistant_message(_Run(), "et svar der er langt nok")
    assert K.run_for("message-fra-persist") == "visible-3433cf05"
