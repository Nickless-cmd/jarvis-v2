

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


# ── to processer skrev hele koeen oven i hinanden — Fase 7 ──────────────
#
# BEVIST 10/9-2026, ikke ræsonneret: `run_next_job` tog et oejebliksbillede af
# HELE koeen, kaldte handleren, og skrev sit forældede billede tilbage. Alt
# hvad andre skrev i mellemtiden blev slettet.
#
# Det bider fordi `jarvis-api` og `jarvis-runtime` koerer SAMME app: begge
# draener jobs i heartbeat'et, og `periodic_jobs_scheduler` laegger i koe fra
# begge. 2007 jobs i produktion, 17 typer.
#
# FAELDE: i ÉN proces skjules det, fordi `_load()` returnerer den DELTE
# cache-liste — to kaldere muterer det samme objekt. En naiv proeve bestod
# derfor, og fejlen viste sig foerst da proeven blev aegte (subproces).

def test_anden_proces_job_slettes_ikke(tmp_path, monkeypatch):
    import os
    import subprocess
    import sys
    import threading
    import time

    from core.services import jobs_engine as je

    monkeypatch.setenv("HOME", str(tmp_path))
    je._LOAD_CACHE_KEY = None
    monkeypatch.setattr(je, "_storage_path", lambda: tmp_path / "jobs_queue.json")

    def _langsom(job):
        time.sleep(1.0)
        return {"status": "completed"}

    je.register_handler("langsom", _langsom)
    a = je.enqueue_job(job_type="langsom", payload={})
    t = threading.Thread(target=je.run_next_job)
    t.start()
    time.sleep(0.25)

    ud = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, %r)\n"
         "from pathlib import Path\n"
         "from core.services import jobs_engine as je\n"
         "je._storage_path = lambda: Path(%r)\n"
         "print(je.enqueue_job(job_type='fra-anden-proces', payload={}))"
         % (os.getcwd(), str(tmp_path / "jobs_queue.json"))],
        capture_output=True, text=True, timeout=120,
    )
    t.join(timeout=20)
    b = ud.stdout.strip()
    assert b.startswith("job-"), ud.stderr[-500:]

    je._LOAD_CACHE_KEY = None
    ider = {j["job_id"] for j in je.list_jobs(limit=100)}
    assert b in ider, (
        "et job lagt i koe af en ANDEN proces blev slettet da det koerende "
        "job gemte sit forældede oejebliksbillede af hele koeen")


def test_afbrydelse_undervejs_overskrives_ikke(tmp_path, monkeypatch):
    """Samme regel som for agenter: en terminal status er endelig.

    Handleren arbejder faerdig — vi standser ikke et kald midt i det — men
    udfaldet er afbrydelsen, og `afbrudt_undervejs` fortaeller at arbejdet
    naaede at blive gjort.
    """
    import threading
    import time

    from core.services import jobs_engine as je

    je._LOAD_CACHE_KEY = None
    monkeypatch.setattr(je, "_storage_path", lambda: tmp_path / "jobs_queue.json")
    je.register_handler("langsom2", lambda job: time.sleep(0.8) or {"status": "completed"})

    a = je.enqueue_job(job_type="langsom2", payload={})
    t = threading.Thread(target=je.run_next_job)
    t.start()
    time.sleep(0.25)
    assert je.cancel_job(a) is True, "afbrydelsen blev ikke registreret"
    t.join(timeout=20)

    je._LOAD_CACHE_KEY = None
    job = next(j for j in je.list_jobs(limit=100) if j["job_id"] == a)
    assert job["status"] == "cancelled", (
        "jobbet overskrev sin egen afbrydelse med udfaldet")
    assert job.get("afbrudt_undervejs") is True, (
        "afbrydelsen bevaredes, men det staar ikke at arbejdet naaede at ske")


def test_doed_proces_giver_lost_ikke_error(tmp_path, monkeypatch):
    """Fase 7-kriterium 1. En proces der doede er ikke en handler der fejlede.

    Foer stod den ene slags blandt de aegte fejl og lignede en fejl i koden.
    """
    from datetime import UTC, datetime, timedelta

    from core.services import jobs_engine as je

    je._LOAD_CACHE_KEY = None
    monkeypatch.setattr(je, "_storage_path", lambda: tmp_path / "jobs_queue.json")
    je.register_handler("x", lambda job: {"status": "completed"})
    a = je.enqueue_job(job_type="x", payload={})

    gammel = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    je._opdater_job(a, status="running", started_at=gammel)

    ud = je.sweep_zombie_jobs(stale_seconds=600)
    assert ud["swept"] == 1

    je._LOAD_CACHE_KEY = None
    job = next(j for j in je.list_jobs(limit=100) if j["job_id"] == a)
    assert job["status"] == "lost", (
        f"processdoed blev bogfoert som {job['status']!r} — den kan ikke "
        "skelnes fra en handler der fejlede")


def test_laasen_stopper_ikke_jobs_hvis_den_ikke_kan_faas(tmp_path, monkeypatch):
    """En manglende laas maa goere jobs lige saa usikre som foer — ikke stoppe
    dem. Et koe-system der gaar i staa er vaerre end et der taber en skrivning."""
    from core.services import jobs_engine as je

    je._LOAD_CACHE_KEY = None
    monkeypatch.setattr(je, "_storage_path", lambda: tmp_path / "jobs_queue.json")

    def _naegt(*a, **kw):
        raise OSError("ingen laas her")

    monkeypatch.setattr(je.fcntl, "flock", _naegt)
    je.register_handler("y", lambda job: {"status": "completed"})
    a = je.enqueue_job(job_type="y", payload={})
    assert a.startswith("job-"), "jobbet kunne ikke laegges i koe uden en laas"
    assert je.run_next_job() is not None


def test_afbrudte_og_tabte_jobs_skubber_ikke_ventende_ud(tmp_path, monkeypatch):
    """`cancelled` og `lost` er FAERDIGE. Stod de i «ikke-terminal»-bunken,
    konkurrerede de med aegte ventende jobs om de 2000 pladser — et afbrudt
    job kunne skubbe et job der skulle koere ud af koeen."""
    from core.services import jobs_engine as je

    assert "cancelled" in je._TERMINAL_STATUSES
    assert "lost" in je._TERMINAL_STATUSES

    je._LOAD_CACHE_KEY = None
    monkeypatch.setattr(je, "_storage_path", lambda: tmp_path / "jobs_queue.json")
    monkeypatch.setattr(je, "_KEEP_PENDING", 3)

    # Distinkte window_keys: `enqueue_job` deduplikerer ellers identiske
    # pending jobs og genbruger id'et — saa proeven ville maale dedup, ikke
    # udrensning.
    ider = [je.enqueue_job(job_type="t", payload={}, window_key=f"w{i}")
            for i in range(3)]
    for jid in ider[:2]:
        je._opdater_job(jid, status="cancelled")
    nyt = je.enqueue_job(job_type="t", payload={}, window_key="w99")

    je._LOAD_CACHE_KEY = None
    ventende = [j["job_id"] for j in je.list_jobs(limit=100)
                if j.get("status") == "pending"]
    assert nyt in ventende and ider[2] in ventende, (
        "et afbrudt job skubbede et ventende job ud af koeen")
