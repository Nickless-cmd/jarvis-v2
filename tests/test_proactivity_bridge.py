# tests/test_proactivity_bridge.py
from core.services import proactivity_bridge as pb


def _cand(kind="initiative", text="fix the thing", priority="medium", source_id="a", ts="2026-07-09T00:00:00+00:00"):
    return {"kind": kind, "text": text, "priority": priority, "source": "initiative_queue",
            "source_id": source_id, "ts": ts}


def test_classify_urgent_vs_normal():
    assert pb.classify(_cand(priority="high")) == "urgent"
    assert pb.classify(_cand(kind="critical_impulse", priority="low")) == "urgent"
    assert pb.classify(_cand(priority="medium")) == "normal"


def test_select_dedup_and_split_and_cap():
    cands = [_cand(source_id="a", priority="high"), _cand(source_id="a", priority="high"),  # dup
             *[_cand(source_id=f"n{i}", priority="medium") for i in range(8)]]
    out = pb.select(cands)
    assert len(out["urgent"]) == 1                       # dedup on source_id
    assert 1 <= len(out["normal"]) <= pb._DIGEST_MAX     # normal capped


def test_should_reach_owner_present_blocks():
    ok, reason = pb.should_reach_owner(owner_present=True, is_quiet=False, sent_today=0,
                                       cap=3, within_cooldown=False, urgent=False)
    assert ok is False and reason == "owner_present"


def test_should_reach_owner_quiet_blocks_normal_not_urgent():
    assert pb.should_reach_owner(owner_present=False, is_quiet=True, sent_today=0, cap=3,
                                 within_cooldown=False, urgent=False) == (False, "quiet_hours")
    ok, _ = pb.should_reach_owner(owner_present=False, is_quiet=True, sent_today=0, cap=3,
                                  within_cooldown=False, urgent=True)
    assert ok is True                                    # urgent bypasses quiet


def test_should_reach_owner_cap_and_cooldown_block():
    assert pb.should_reach_owner(owner_present=False, is_quiet=False, sent_today=3, cap=3,
                                 within_cooldown=False, urgent=False) == (False, "daily_cap")
    assert pb.should_reach_owner(owner_present=False, is_quiet=False, sent_today=0, cap=3,
                                 within_cooldown=True, urgent=False) == (False, "cooldown")


def test_should_reach_owner_ok():
    ok, reason = pb.should_reach_owner(owner_present=False, is_quiet=False, sent_today=0,
                                       cap=3, within_cooldown=False, urgent=False)
    assert ok is True and reason == "ok"


def test_build_digest_and_urgent_contain_text():
    d = pb.build_digest([_cand(text="ryd op i cachen"), _cand(text="spørg om X", source_id="b")])
    assert "ryd op i cachen" in d and "spørg om X" in d and d.strip()
    u = pb.build_urgent(_cand(text="noget vigtigt"))
    assert "noget vigtigt" in u and u.strip()


def test_digest_is_repeat_detects_last_identical(monkeypatch):
    """Digest der matcher sidste assistant-post i sessionen = gentagelse (whitespace/case-robust)."""
    text = pb.build_digest([_cand(text="er jeg blot en proces?")])
    # broen importerer recent_chat_session_messages lokalt fra chat_sessions
    import core.services.chat_sessions as cs
    monkeypatch.setattr(cs, "recent_chat_session_messages",
                        lambda *_a, **_k: [{"role": "assistant", "content": "  " + text.upper() + "  "}])
    assert pb._digest_is_repeat(text) is True


def test_digest_is_repeat_false_when_new(monkeypatch):
    import core.services.chat_sessions as cs
    monkeypatch.setattr(cs, "recent_chat_session_messages",
                        lambda *_a, **_k: [{"role": "assistant", "content": "en helt anden tanke"}])
    assert pb._digest_is_repeat(pb.build_digest([_cand(text="ny undren i dag")])) is False


def test_digest_is_repeat_false_when_empty_history(monkeypatch):
    import core.services.chat_sessions as cs
    monkeypatch.setattr(cs, "recent_chat_session_messages", lambda *_a, **_k: [])
    assert pb._digest_is_repeat(pb.build_digest([_cand(text="noget")])) is False


# ---------------------------------------------------------------------------
# Proaktive beskeder lander hos ham, ikke i en silo (8/9-2026)
#
# Bjørn: «de ligger i en session for sig selv så ser dem ikke rigtigt... de
# burde komme i den aktive og sidste aktive session».
#
# Autonome kørsler flyttes bevidst IKKE med: målt samme dag fyldte
# auto-recurring-20260907 **168 beskeder, hvoraf 155 var tool-resultater**. De
# ville både drukne samtalen og æde hans prompt-kontekst. Deres resultat når
# ham allerede gennem denne kanal.
# ---------------------------------------------------------------------------

def test_beskeden_lander_i_hans_sidst_aktive_samtale(monkeypatch):
    import core.services.proactivity_bridge as B

    skrevet: list = []
    monkeypatch.setattr(B, "_sidst_aktive_samtale", lambda: "chat-abc")
    monkeypatch.setattr(
        "core.services.chat_sessions.append_chat_message",
        lambda **kw: skrevet.append(kw) or {"id": "m1"},
    )
    assert B._persist_as_chat("u1", "💭 en tanke") == "chat-abc"
    assert skrevet[0]["session_id"] == "chat-abc"


def test_uden_en_frisk_samtale_falder_den_tilbage_til_siloen(monkeypatch):
    """Har han ikke skrevet i et døgn, hører beskeden ikke hjemme i en samtale
    han for længst har lukket."""
    import core.services.proactivity_bridge as B

    monkeypatch.setattr(B, "_sidst_aktive_samtale", lambda: "")
    monkeypatch.setattr(
        "core.services.chat_sessions.get_or_create_named_session",
        lambda sid, titel: sid,
    )
    monkeypatch.setattr(
        "core.services.chat_sessions.append_chat_message", lambda **kw: {"id": "m1"},
    )
    assert B._persist_as_chat("u1", "💭 en tanke") == B._PROACTIVITY_SESSION_ID


def test_kun_HANS_samtaler_taeller_som_sidst_aktive():
    """En autonom eller proaktiv session må aldrig blive målet — så ville
    beskeden lande i siloen igen ad bagvejen."""
    import inspect

    import core.services.proactivity_bridge as B

    src = inspect.getsource(B._sidst_aktive_samtale)
    assert "chat-%" in src, "forespørgslen begrænser ikke til hans egne samtaler"


def test_gentagelses_vaernet_kigger_samme_sted_som_beskeden_lander(monkeypatch):
    """Et værn der kigger det forkerte sted er ikke et værn."""
    import core.services.proactivity_bridge as B

    set_: list = []
    monkeypatch.setattr(B, "_sidst_aktive_samtale", lambda: "chat-abc")
    monkeypatch.setattr(
        "core.services.chat_sessions.recent_chat_session_messages",
        lambda sid, limit=8: set_.append(sid) or [],
    )
    B._digest_is_repeat("en digest")
    assert set_ == ["chat-abc"]


def test_opslaget_kaster_aldrig():
    import core.services.proactivity_bridge as B

    assert isinstance(B._sidst_aktive_samtale(), str)
