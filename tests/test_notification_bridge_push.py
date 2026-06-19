import core.services.notification_bridge as nb
import core.services.chat_sessions as cs
import core.services.session_inbox as si


def test_proactive_delivery_triggers_push(monkeypatch):
    sess = cs.create_chat_session(title="push-bridge")
    sid = sess["id"] if isinstance(sess, dict) else getattr(sess, "id", sess)
    cs.append_chat_message(session_id=str(sid), role="user", content="hej", user_id="bjorn")
    calls = []
    monkeypatch.setattr(nb, "_push_proactive", lambda s, t: calls.append((s, t)))
    monkeypatch.setattr(nb, "get_pinned_session_id", lambda: str(sid))
    monkeypatch.setattr(si, "is_session_active", lambda s: False)  # tving direkte levering
    res = nb.send_session_notification("Jeg har en tanke", source="inner-voice")
    assert res.get("status") == "ok"
    assert calls == [(str(sid), "Jeg har en tanke")]
