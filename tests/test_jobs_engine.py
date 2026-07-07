

# --- 2026-06-15: prune-on-save (queue-bloat fix) ---


def test_prune_keeps_non_terminal_and_recent_terminal():
    from core.services.jobs_engine import _prune_completed_jobs, _KEEP_TERMINAL
    pending = [{"status": "pending", "job_id": "p1"}, {"status": "running", "job_id": "r1"}]
    terminal = [{"status": "ok", "job_id": f"t{i}", "finished_at": f"2026-06-15T{i % 24:02d}:00"} for i in range(_KEEP_TERMINAL + 500)]
    out = _prune_completed_jobs(pending + terminal)
    kept_ids = {j["job_id"] for j in out}
    assert "p1" in kept_ids and "r1" in kept_ids          # ikke-terminale bevaret
    n_terminal = sum(1 for j in out if j["status"] == "ok")
    assert n_terminal == _KEEP_TERMINAL                    # kun de seneste N terminale


def test_prune_noop_when_small():
    from core.services.jobs_engine import _prune_completed_jobs
    items = [{"status": "ok", "job_id": "a"}, {"status": "pending", "job_id": "b"}]
    assert _prune_completed_jobs(items) == items


# --- 2026-07-07: runaway-pending guard (GIL-wedge fix) ---


def test_prune_caps_runaway_pending():
    """202k pending governance-jobs wedgede GIL'en 13t — non-terminal SKAL hard-cappes."""
    from core.services.jobs_engine import _prune_completed_jobs, _KEEP_PENDING
    pending = [{"status": "pending", "job_id": f"p{i}", "job_type": "personality_snapshot",
                "enqueued_at": f"2026-06-{(i % 28) + 1:02d}T00:00:00"}
               for i in range(_KEEP_PENDING + 5000)]
    out = _prune_completed_jobs(pending)
    n_pending = sum(1 for j in out if j["status"] == "pending")
    assert n_pending == _KEEP_PENDING                      # hard-cappet
    # de NYESTE pending bevares (juni 28 > juni 01)
    kept = {j["job_id"] for j in out}
    newest = max(pending, key=lambda j: j["enqueued_at"])["job_id"]
    assert newest in kept


def test_enqueue_dedups_identical_pending(tmp_path, monkeypatch):
    """Governance re-enqueuede identiske keyless jobs hvert vindue → 18k pending. Dedup."""
    import core.services.jobs_engine as je
    monkeypatch.setattr(je, "_storage_path", lambda: tmp_path / "jobs_queue.json")
    je._LOAD_CACHE_KEY = None
    je._LOAD_CACHE_ITEMS = None
    id1 = je.enqueue_job(job_type="personality_snapshot")
    id2 = je.enqueue_job(job_type="personality_snapshot")
    assert id1 == id2                                       # samme job genbrugt
    items = je._load()
    assert sum(1 for j in items if j["job_type"] == "personality_snapshot") == 1


def test_enqueue_distinct_when_keys_differ(tmp_path, monkeypatch):
    """Forskellige window_key/scheduled_job_id må stadig give distinkte jobs."""
    import core.services.jobs_engine as je
    monkeypatch.setattr(je, "_storage_path", lambda: tmp_path / "jobs_queue.json")
    je._LOAD_CACHE_KEY = None
    je._LOAD_CACHE_ITEMS = None
    id1 = je.enqueue_job(job_type="chronicle_refresh", window_key="w1")
    id2 = je.enqueue_job(job_type="chronicle_refresh", window_key="w2")
    assert id1 != id2
