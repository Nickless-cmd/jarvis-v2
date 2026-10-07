"""Cross-client duplicate user-message dedup at append_chat_message.

Background (2026-07-12, verified in prod data: 249 consecutive identical
user-message dupes): sessions are held by the server and SHARED across live
clients (desk chat/code, mobile companion, jarvis-code) that mirror/stream to
each other. The same user message can therefore reach append_chat_message twice
(mirror/retry), so the model sees it twice ("jeg fik din besked to gange"). We
dedup at the convergence point: if the most-recent message in the session is an
IDENTICAL user message within a window (no assistant reply between), the second
append is a duplicate — return the existing row, do not insert again.
"""
from __future__ import annotations


def _mk_session():
    from core.services.chat_sessions import create_chat_session
    sess = create_chat_session(title="dedup-test")
    return str(sess.get("session_id") or sess.get("id"))


def _count_user_rows(sid, content):
    from core.runtime.db_core import connect
    with connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) c FROM chat_messages WHERE session_id=? AND role='user' AND content=?",
            (sid, content),
        ).fetchone()["c"]


def test_consecutive_identical_user_message_is_deduped(isolated_runtime):
    from core.services.chat_sessions import append_chat_message
    sid = _mk_session()
    first = append_chat_message(session_id=sid, role="user", content="samme besked")
    second = append_chat_message(session_id=sid, role="user", content="samme besked")
    assert _count_user_rows(sid, "samme besked") == 1          # only one row inserted
    assert second["id"] == first["id"]                          # dup returns the existing row


def test_identical_user_after_assistant_is_kept(isolated_runtime):
    """A real repeat (assistant replied between) is NOT a duplicate."""
    from core.services.chat_sessions import append_chat_message
    sid = _mk_session()
    append_chat_message(session_id=sid, role="user", content="igen")
    append_chat_message(session_id=sid, role="assistant", content="gjort")
    append_chat_message(session_id=sid, role="user", content="igen")
    assert _count_user_rows(sid, "igen") == 2                   # both kept — genuine turns


def test_different_user_messages_both_kept(isolated_runtime):
    from core.services.chat_sessions import append_chat_message
    sid = _mk_session()
    append_chat_message(session_id=sid, role="user", content="besked A")
    append_chat_message(session_id=sid, role="user", content="besked B")
    assert _count_user_rows(sid, "besked A") == 1
    assert _count_user_rows(sid, "besked B") == 1


def test_assistant_duplicates_not_deduped(isolated_runtime):
    """Dedup targets user messages only; assistant rows are never dropped."""
    from core.services.chat_sessions import append_chat_message
    from core.runtime.db_core import connect
    sid = _mk_session()
    append_chat_message(session_id=sid, role="user", content="hej")
    append_chat_message(session_id=sid, role="assistant", content="svar")
    append_chat_message(session_id=sid, role="assistant", content="svar")
    with connect() as conn:
        n = conn.execute(
            "SELECT COUNT(*) c FROM chat_messages WHERE session_id=? AND role='assistant' AND content='svar'",
            (sid,),
        ).fetchone()["c"]
    assert n == 2


# --- Ikke-svar mellem de to identiske beskeder (målt 7/10-2026) -------------
#
# De tre dublet-par Bjørn ramte 7/10 havde alle noget imellem sig der IKKE var
# et svar: fire `tool`-rækker i det ene, `assistant: "Generation cancelled."` i
# det andet. Den gamle regel krævede at den SENESTE række var den identiske
# besked, så den var blind præcis når dubletten opstod.

def test_dublet_med_tool_raekker_imellem_dedupes(isolated_runtime):
    """Et afbrudt run skriver værktøjs-output mellem de to identiske beskeder."""
    from core.services.chat_sessions import append_chat_message
    sid = _mk_session()
    first = append_chat_message(session_id=sid, role="user", content="send notifikation")
    append_chat_message(session_id=sid, role="tool", content="[bash]: foerste output")
    append_chat_message(session_id=sid, role="tool", content="[bash]: andet output")
    second = append_chat_message(session_id=sid, role="user", content="send notifikation")
    assert _count_user_rows(sid, "send notifikation") == 1
    assert second["id"] == first["id"]


def test_dublet_med_afbrydelses_markor_imellem_dedupes(isolated_runtime):
    """«Generation cancelled.» er en syntetisk markør, ikke et svar."""
    from core.services.chat_sessions import append_chat_message
    sid = _mk_session()
    first = append_chat_message(session_id=sid, role="user", content="men mente i cc desktop appen..")
    append_chat_message(session_id=sid, role="assistant", content="Generation cancelled.")
    second = append_chat_message(session_id=sid, role="user", content="men mente i cc desktop appen..")
    assert _count_user_rows(sid, "men mente i cc desktop appen..") == 1
    assert second["id"] == first["id"]


def test_rigtigt_svar_bryder_stadig_kaeden(isolated_runtime):
    """Værnet må ikke blive så bredt at ÆGTE gentagelser droppes."""
    from core.services.chat_sessions import append_chat_message
    sid = _mk_session()
    append_chat_message(session_id=sid, role="user", content="proev igen")
    append_chat_message(session_id=sid, role="assistant", content="her er svaret")
    append_chat_message(session_id=sid, role="user", content="proev igen")
    assert _count_user_rows(sid, "proev igen") == 2


def test_anden_brugerbesked_bryder_kaeden(isolated_runtime):
    """En ANDEN brugerbesked er ikke en dublet — heller ikke efter tool-rækker."""
    from core.services.chat_sessions import append_chat_message
    sid = _mk_session()
    append_chat_message(session_id=sid, role="user", content="besked A")
    append_chat_message(session_id=sid, role="tool", content="[bash]: output")
    append_chat_message(session_id=sid, role="user", content="besked B")
    assert _count_user_rows(sid, "besked A") == 1
    assert _count_user_rows(sid, "besked B") == 1


def test_fem_identiske_beskeder_bliver_til_en(isolated_runtime):
    """Kæden holder også når retry rammer flere gange i træk."""
    from core.services.chat_sessions import append_chat_message
    sid = _mk_session()
    for _ in range(5):
        append_chat_message(session_id=sid, role="user", content="samme fem gange")
    assert _count_user_rows(sid, "samme fem gange") == 1
