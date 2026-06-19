import core.services.chat_sessions as cs


def test_owner_from_user_message():
    sess = cs.create_chat_session(title="ejer-test")
    sid = sess["id"] if isinstance(sess, dict) else getattr(sess, "id", sess)
    cs.append_chat_message(session_id=str(sid), role="user", content="hej", user_id="bjorn")
    assert cs.get_session_owner(str(sid)) == "bjorn"


def test_owner_none_when_no_stamp():
    sess = cs.create_chat_session(title="ingen-ejer")
    sid = sess["id"] if isinstance(sess, dict) else getattr(sess, "id", sess)
    assert cs.get_session_owner(str(sid)) is None
