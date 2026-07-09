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
