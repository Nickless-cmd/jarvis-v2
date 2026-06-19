import time
import core.services.run_event_log as rel


def setup_function():
    rel._RUNS.clear()


def test_append_read_offset_and_done():
    rel.create("r1", "s1")
    rel.append("r1", "f0")
    rel.append("r1", "f1")
    frames, done = rel.read("r1", 0)
    assert frames == ["f0", "f1"] and done is False
    frames, done = rel.read("r1", 1)
    assert frames == ["f1"] and done is False
    rel.mark_done("r1")
    _, done = rel.read("r1", 2)
    assert done is True


def test_read_unknown_run():
    assert rel.read("nope", 0) == ([], False)


def test_active_run_for_session_returns_latest_not_done():
    rel.create("r1", "s1")
    rel.mark_done("r1")
    rel.create("r2", "s1")
    assert rel.active_run_for_session("s1") == "r2"


def test_is_live_and_live_run_ids():
    rel.create("r1", "s1")
    rel.append("r1", "f")
    assert rel.is_live("r1") is True
    assert rel.live_run_ids() == ["r1"]
    rel.mark_done("r1")
    assert rel.is_live("r1") is False
    assert rel.live_run_ids() == []


def test_is_live_false_when_stale():
    rel.create("r1", "s1")
    # Stale kraever BAADE gammelt append OG gammel oprettelse (create-grace
    # holder et nyt run live i det synkrone assembly-vindue).
    rel._RUNS["r1"]["last_append_at"] = time.monotonic() - 999
    rel._RUNS["r1"]["created_at"] = time.monotonic() - 999
    assert rel.is_live("r1") is False


def test_create_grace_keeps_new_run_live_without_appends():
    # Et frisk-oprettet run uden appends (det 14-19s sync assembly blokerer
    # ping-loopet) skal taelle som live i grace-vinduet, ellers flakker
    # /active-runs + /live og desktop-follow trigger ikke.
    rel.create("r1", "s1")
    rel._RUNS["r1"]["last_append_at"] = time.monotonic() - 999  # ingen nylig append
    assert rel.is_live("r1") is True
    assert "r1" in rel.live_run_ids()


def test_frame_cap():
    rel.create("r1", "s1")
    for i in range(rel._MAX_FRAMES + 50):
        rel.append("r1", f"f{i}")
    frames, _ = rel.read("r1", 0)
    assert len(frames) == rel._MAX_FRAMES


def test_prune_keeps_latest_per_session():
    rel.create("r1", "s1")
    rel.mark_done("r1")
    rel.create("r2", "s1")
    rel.mark_done("r2")
    rel.prune()
    assert "r1" not in rel._RUNS
    assert "r2" in rel._RUNS


def test_subscriber_tracking_and_consumed():
    rel.create("rsub1", "s1")
    assert rel.was_consumed_or_active("rsub1") is False
    rel.subscriber_opened("rsub1")
    assert rel.was_consumed_or_active("rsub1") is True
    rel.subscriber_closed("rsub1")
    assert rel.was_consumed_or_active("rsub1") is False
    rel.mark_consumed("rsub1")
    assert rel.was_consumed_or_active("rsub1") is True


def test_consumed_unknown_run_is_false():
    assert rel.was_consumed_or_active("ukendt-run") is False
