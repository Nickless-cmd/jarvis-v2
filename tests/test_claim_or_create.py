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


def test_et_gammelt_run_erstattes_ikke_paa_alder_alene():
    """Et langt run er normalt. Siden 6642a5dea (17/9-2026) må et run aldrig
    erstattes ud fra alder alene — den detached ejer markerer det færdigt ved
    ren afslutning eller crash. stale_cap_s er kun kaldskompatibilitet.

    Testen stod tilbage på den gamle adfærd (nyt run efter stale_cap) og
    fejlede i hver kørsel; den pinner nu det der er meningen."""
    rel._RUNS.clear()
    rid, new = rel.claim_or_create("sess-stale")
    assert new is True
    rel._RUNS[rid]["created_at"] = rel.time.monotonic() - 999  # ældre end stale_cap
    rid2, new2 = rel.claim_or_create("sess-stale")
    assert (rid2, new2) == (rid, False), "et gammelt, ikke-færdigt run claimes stadig"
    rel.mark_done(rid)
    rid3, new3 = rel.claim_or_create("sess-stale")
    assert new3 is True and rid3 != rid, "først mark_done giver et nyt run"


def test_claim_attaches_to_live_run():
    rel._RUNS.clear()
    rid, new = rel.claim_or_create("sess-live")
    rid2, new2 = rel.claim_or_create("sess-live")
    assert new is True and new2 is False
    assert rid2 == rid
