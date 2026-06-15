

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
