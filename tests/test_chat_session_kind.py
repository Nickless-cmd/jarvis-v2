"""Skiller sessionslisten chat fra code?"""
import pytest
from core.services.chat_sessions import create_chat_session, list_chat_sessions


def _ids(rows):
    return {r["id"] for r in rows}


def test_kind_er_chat_som_standard(isolated_runtime):
    s = create_chat_session(title="Almindelig")
    assert list_chat_sessions()[0]["kind"] == "chat"
    assert s["id"]


def test_code_sessioner_kan_skilles_ud(isolated_runtime):
    chat = create_chat_session(title="Almindelig")
    kode = create_chat_session(title="Noget kode", kind="code")
    assert _ids(list_chat_sessions(kind="code")) == {kode["id"]}
    assert _ids(list_chat_sessions(kind="chat")) == {chat["id"]}


def test_UDEN_kind_faar_man_stadig_ALT(isolated_runtime):
    # En ny parameter maa ikke stiltiende smalne det Mission Control faar.
    chat = create_chat_session(title="Almindelig")
    kode = create_chat_session(title="Noget kode", kind="code")
    assert _ids(list_chat_sessions()) == {chat["id"], kode["id"]}


def test_ukendt_art_bliver_til_chat_ikke_til_sig_selv(isolated_runtime):
    # En raekke med kind='kode' ville vaere usynlig i BEGGE lister.
    s = create_chat_session(title="Tastefejl", kind="kode")
    assert _ids(list_chat_sessions(kind="chat")) == {s["id"]}
    assert list_chat_sessions(kind="code") == []


def test_ukendt_FILTER_giver_alt_frem_for_ingenting(isolated_runtime):
    chat = create_chat_session(title="A")
    kode = create_chat_session(title="B", kind="code")
    assert _ids(list_chat_sessions(kind="vrøvl")) == {chat["id"], kode["id"]}


def test_filteret_virker_ogsaa_naar_der_scopes_paa_bruger(isolated_runtime):
    # To grene i SQL'en. Foerste udgave af arkiv-filteret ramte kun den ene.
    from core.services.chat_sessions import append_chat_message
    chat = create_chat_session(title="A")
    kode = create_chat_session(title="B", kind="code")
    append_chat_message(session_id=str(chat["id"]), role="user", content="hej", user_id="bjorn")
    append_chat_message(session_id=str(kode["id"]), role="user", content="hej", user_id="bjorn")
    assert _ids(list_chat_sessions(user_id="bjorn", kind="code")) == {kode["id"]}
    assert _ids(list_chat_sessions(user_id="bjorn", kind="chat")) == {chat["id"]}


def _drop_kind():
    """Efterlign en database fra FOER kolonnen fandtes."""
    from core.runtime.db import connect
    with connect() as conn:
        conn.execute("ALTER TABLE chat_sessions DROP COLUMN kind")


def test_gamle_Kode_sessioner_tilbagefyldes_EN_gang(isolated_runtime):
    # Titlen er den eneste oplysning der findes om de gamle raekker: desk's
    # CodeView har altid kaldt sessions.create('Kode-session').
    gammel = create_chat_session(title="Kode-session")
    anden = create_chat_session(title="Godmorgen ven :)")
    _drop_kind()
    assert _ids(list_chat_sessions(kind="code")) == {gammel["id"]}
    assert _ids(list_chat_sessions(kind="chat")) == {anden["id"]}


def test_tilbagefyldet_overskriver_IKKE_et_senere_valg(isolated_runtime):
    # `else` paa ALTER-forsoeget betyder at fyldet koerer praecis én gang pr.
    # database. Laa det udenfor, ville HVER listning skrive oven i en `kind`
    # nogen siden havde aendret - og en session man flyttede ville hoppe
    # tilbage naeste gang man aabnede menuen.
    from core.runtime.db import connect
    s = create_chat_session(title="Kode-session")
    _drop_kind()
    list_chat_sessions()                      # fylder tilbage: code
    with connect() as conn:                   # nogen flytter den til chat
        conn.execute("UPDATE chat_sessions SET kind = 'chat' WHERE session_id = ?", (s["id"],))
    assert _ids(list_chat_sessions(kind="chat")) == {s["id"]}
    assert list_chat_sessions(kind="code") == []
