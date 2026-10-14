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


# ── Interne markører må ikke nå chatview ad denne vej (14/10-2026) ──────────
#
# `visible_runs` scrubber sine egne to veje, men `send_session_notification`
# er en FÆLLES tragt med fem kaldere uden om den. Uden vagten her kunne en
# gate-note der efterlignes i Jarvis' hale slippe ud uscrubvet — præcis den
# lækage `visible_text_scrub` blev bygget til at lukke, blot ad en anden vej.

_NOTE = (
    "[decision-signal: interceptor (verification: [interceptor:verification] "
    "R2 blød surface — uverificerede mutationer)]"
)


def _levering(monkeypatch):
    """Rigtig session + fanget push, saa vi maaler den tekst der FAKTISK sendes."""
    sess = cs.create_chat_session(title="markoer-bridge")
    sid = sess["id"] if isinstance(sess, dict) else getattr(sess, "id", sess)
    cs.append_chat_message(session_id=str(sid), role="user", content="hej", user_id="bjorn")
    sendt: list[str] = []
    monkeypatch.setattr(nb, "_push_proactive", lambda s, t: sendt.append(t))
    monkeypatch.setattr(nb, "get_pinned_session_id", lambda: str(sid))
    monkeypatch.setattr(si, "is_session_active", lambda s: False)
    return sendt


def test_en_efterlignet_note_midt_i_beskeden_naar_ikke_chatview(monkeypatch):
    """Det ægte tilfælde: noten staar INDE i en ellers normal besked."""
    sendt = _levering(monkeypatch)
    res = nb.send_session_notification(
        f"Her er hvad jeg fandt.\n\n{_NOTE}\n\nOg resten af svaret.",
        source="inner-voice",
    )
    assert res.get("status") == "ok"
    assert sendt, "beskeden blev slet ikke leveret"
    tekst = sendt[0]
    assert "decision-signal" not in tekst, "markoer-ordet slap ud"
    assert "R2 blød surface" not in tekst, "note-halen slap ud"
    assert "Her er hvad jeg fandt." in tekst, "den ægte tekst forsvandt"
    assert "Og resten af svaret." in tekst, "teksten EFTER noten forsvandt"


def test_en_besked_der_KUN_er_en_note_blokeres(monkeypatch):
    """En tom besked er værre end ingen: den banker på uden indhold."""
    sendt = _levering(monkeypatch)
    res = nb.send_session_notification(_NOTE, source="inner-voice")
    assert res.get("status") == "blocked"
    assert res.get("error") == "internal-marker-only-content"
    assert not sendt, "en tom besked blev alligevel sendt"


def test_en_normal_besked_roeres_ikke(monkeypatch):
    """Vagten maa ikke koste noget for de 99 % der ikke baerer en note."""
    sendt = _levering(monkeypatch)
    res = nb.send_session_notification("Kort besked uden noter.", source="inner-voice")
    assert res.get("status") == "ok"
    assert sendt == ["Kort besked uden noter."]
