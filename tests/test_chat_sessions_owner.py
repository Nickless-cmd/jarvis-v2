import core.services.chat_sessions as cs


def test_owner_from_user_message():
    sess = cs.create_chat_session(title="ejer-test")
    sid = sess["id"] if isinstance(sess, dict) else getattr(sess, "id", sess)
    cs.append_chat_message(session_id=str(sid), role="user", content="hej", user_id="bjorn")
    assert cs.get_session_owner(str(sid)) == "bjorn"


def test_assistant_stamp_does_not_take_ownership():
    sess = cs.create_chat_session(title="assistent-ejer-ikke")
    sid = sess["id"] if isinstance(sess, dict) else getattr(sess, "id", sess)
    cs.append_chat_message(session_id=str(sid), role="user", content="hej", user_id="michelle")
    cs.append_chat_message(session_id=str(sid), role="assistant", content="svar", user_id="bjorn")

    assert cs.get_session_owner(str(sid)) == "michelle"


def test_owner_none_when_no_stamp():
    sess = cs.create_chat_session(title="ingen-ejer")
    sid = sess["id"] if isinstance(sess, dict) else getattr(sess, "id", sess)
    assert cs.get_session_owner(str(sid)) is None


# ── STEMPLET VED OPRETTELSEN (19/10-2026) ────────────────────────────────────
# Bjørn: «stemple ejerskab på sessionen ved oprettelsen». Indtil nu blev ejeren
# UDLEDT af den seneste brugerbesked, så beviset afhang af hvem der tilfældigvis
# skrev sidst. Testene her låser at stemplet sættes hvor vi VED hvem der bad om
# samtalen — og at det ikke kan flyttes bagefter.


def _stempel(sid: str) -> str:
    """Læs kolonnen DIREKTE. `get_session_owner` har en faldback der kan svare
    ejeren på en ustemplet række, så den kan ikke bruges til at måle stemplet."""
    from core.runtime.db import connect
    with connect() as c:
        row = c.execute(
            "SELECT owner_user_id FROM chat_sessions WHERE session_id = ?", (sid,)
        ).fetchone()
    return str(row[0] or "") if row else ""


def test_stemplet_saettes_ved_oprettelsen():
    from core.identity.workspace_context import set_context

    set_context(workspace_name="bjorn", user_id="opretter-id")
    sess = cs.create_chat_session(title="stemplet")
    assert _stempel(str(sess["id"])) == "opretter-id"


def test_uden_kontekst_stemples_intet():
    """Et ærligt «ved det ikke» — en oprettelse uden en request må ikke gætte."""
    from core.identity.workspace_context import set_context

    set_context(workspace_name="", user_id="")
    sess = cs.create_chat_session(title="uden-kontekst")
    assert _stempel(str(sess["id"])) == ""


def test_stemplet_vinder_over_en_senere_besked():
    """Kernen i beviset: en anden der skriver bagefter flytter IKKE ejerskabet."""
    from core.identity.workspace_context import set_context

    set_context(workspace_name="bjorn", user_id="opretter-id")
    sess = cs.create_chat_session(title="delt-bagefter")
    sid = str(sess["id"])
    cs.append_chat_message(session_id=sid, role="user", content="hej", user_id="anden-id")
    assert cs.get_session_owner(sid) == "opretter-id"


def test_legacy_uden_stempel_falder_tilbage_til_beskeden():
    """Historik fra før kolonnen må ikke miste sin ejer ved migreringen."""
    from core.identity.workspace_context import set_context

    set_context(workspace_name="", user_id="")
    sess = cs.create_chat_session(title="legacy")
    sid = str(sess["id"])
    assert _stempel(sid) == ""
    cs.append_chat_message(session_id=sid, role="user", content="hej", user_id="gammel-ejer")
    assert cs.get_session_owner(sid) == "gammel-ejer"


def test_presence_afgoeres_af_stemplet_ikke_af_beskedtaelling():
    """Grænsen i `is_owner_app_session` skal læse stemplet først.

    Målt før rettelsen: en delt samtale blev afvist fordi den havde to
    user_id'er — men en samtale oprettet i HANS navn er hans, uanset hvem der
    skriver i den bagefter. Og en samtale oprettet i en ANDENS navn er ikke
    hans, uanset at hans id optræder i beskederne.
    """
    from core.identity.owner_resolver import is_owner_app_session, owner_user_id
    from core.identity.workspace_context import set_context

    ejer = owner_user_id()
    assert ejer, "testen kræver en kendt ejer"

    set_context(workspace_name="bjorn", user_id=ejer)
    hans = cs.create_chat_session(title="hans")
    cs.append_chat_message(session_id=str(hans["id"]), role="user", content="a", user_id="anden")
    assert is_owner_app_session(str(hans["id"])) is True

    set_context(workspace_name="michelle", user_id="michelle")
    hendes = cs.create_chat_session(title="hendes")
    cs.append_chat_message(session_id=str(hendes["id"]), role="user", content="a", user_id=ejer)
    assert is_owner_app_session(str(hendes["id"])) is False
