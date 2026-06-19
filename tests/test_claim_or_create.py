import threading
import core.services.run_event_log as rel


def test_claim_atomic_single_create_under_concurrency():
    rel._RUNS.clear()
    results = []
    barrier = threading.Barrier(8)
    def worker():
        barrier.wait()  # alle starter samtidig → maksimal race
        results.append(rel.claim_or_create("sess-race"))
    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads: t.start()
    for t in threads: t.join()
    news = [r for r in results if r[1]]
    rids = {r[0] for r in results}
    assert len(news) == 1, f"praecis ét nyt run forventet, fik {len(news)}"
    assert len(rids) == 1, f"alle skal dele samme run_id, fik {rids}"


def test_claim_stale_cap_starts_fresh():
    rel._RUNS.clear()
    rid, new = rel.claim_or_create("sess-stale")
    assert new is True
    # gør kørslen "gammel" (ældre end stale_cap)
    rel._RUNS[rid]["created_at"] = rel.time.monotonic() - 999
    rid2, new2 = rel.claim_or_create("sess-stale")
    assert new2 is True, "stale run skal IKKE claimes — frisk run forventet"
    assert rid2 != rid


def test_claim_attaches_to_live_run():
    rel._RUNS.clear()
    rid, new = rel.claim_or_create("sess-live")
    rid2, new2 = rel.claim_or_create("sess-live")
    assert new is True and new2 is False
    assert rid2 == rid
