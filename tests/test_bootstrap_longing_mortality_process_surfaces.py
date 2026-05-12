from __future__ import annotations

import sqlite3
import sys
from types import ModuleType, SimpleNamespace


def test_governance_bootstrap_registers_defaults(monkeypatch):
    from core.services import governance_bootstrap as bootstrap

    windows = []
    sched = ModuleType("core.services.scheduled_job_windows")
    sched.list_windows = lambda: []
    sched.register_window = lambda **kwargs: windows.append(kwargs["name"]) or f"win-{kwargs['name']}"
    monkeypatch.setitem(sys.modules, "core.services.scheduled_job_windows", sched)

    handlers = []
    jobs = ModuleType("core.services.jobs_engine")
    jobs.register_handler = lambda name, fn: handlers.append(name)
    monkeypatch.setitem(sys.modules, "core.services.jobs_engine", jobs)

    created_windows = bootstrap.ensure_default_windows()
    registered_handlers = bootstrap.ensure_default_job_handlers()

    assert created_windows == ["win-night-batch", "win-morning-catchup", "win-quiet-afternoon"]
    assert windows == ["night-batch", "morning-catchup", "quiet-afternoon"]
    assert "decision_review" in handlers
    assert "skill_distillation" in handlers
    assert len(registered_handlers) == len(handlers)


def test_longing_signal_daemon_emits_when_user_has_been_absent(tmp_path, monkeypatch):
    from core.services import longing_signal_daemon as longing

    db = tmp_path / "jarvis.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE visible_work_units (id INTEGER PRIMARY KEY, user_message_preview TEXT, finished_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE events (id INTEGER PRIMARY KEY, kind TEXT, created_at TEXT)"
    )
    conn.execute(
        "INSERT INTO visible_work_units (user_message_preview, finished_at) VALUES (?, ?)",
        ("hej", "2026-05-12T10:00:00+00:00"),
    )
    conn.execute(
        "INSERT INTO events (kind, created_at) VALUES (?, ?)",
        ("impulse.outreach.sent", "2026-05-10T10:00:00+00:00"),
    )
    conn.commit()
    conn.close()

    settings = ModuleType("core.runtime.settings")
    settings.load_settings = lambda: SimpleNamespace(
        longing_build_start_hours=2.0,
        longing_build_max_hours=12.0,
        outreach_cooldown_minutes=240,
        generative_autonomy_enabled=True,
    )
    monkeypatch.setitem(sys.modules, "core.runtime.settings", settings)
    monkeypatch.setattr(longing, "_runtime_db_path", lambda: db)

    captured = []
    signal_acc = ModuleType("core.services.signal_pressure_accumulator")
    signal_acc.ingest_signal = lambda family, signal: captured.append((family, signal))
    monkeypatch.setitem(sys.modules, "core.services.signal_pressure_accumulator", signal_acc)

    result = longing.run_longing_signal_daemon_tick()

    assert result["status"] == "ok"
    assert result["emitted"] is True
    assert captured and captured[0][0] == "longing"


def test_mortality_awareness_surfaces_sharp_state(monkeypatch):
    from core.services import mortality_awareness as mortality

    monkeypatch.setattr(mortality, "_session_length_seconds", lambda: 7200)
    monkeypatch.setattr(mortality, "_heartbeat_gap_minutes", lambda: 90.0)
    monkeypatch.setattr(mortality, "_error_rate", lambda: 0.8)
    mortality._last_state = {}
    mortality._last_computed_ts = 0.0

    state = mortality.get_mortality_state()
    surface = mortality.build_mortality_awareness_surface()
    prompt = mortality.build_mortality_awareness_prompt_section()

    assert state["label"] == "sharp-awareness"
    assert surface["active"] is True
    assert prompt is not None
    assert "Dødsbevidsthed er skarp" in prompt


def test_ntfy_gateway_uses_configured_topic(monkeypatch):
    from core.services import ntfy_gateway as ntfy

    monkeypatch.setattr(ntfy, "_load_config", lambda: {"server": "https://ntfy.sh", "topic": "jarvis"})
    response = SimpleNamespace(read=lambda: b"ok")

    class FakeResp:
        def __enter__(self):
            return response

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(ntfy.urllib.request, "urlopen", lambda req, timeout=10: FakeResp())

    result = ntfy.send_notification("hello", title="Jarvis", priority="high", tags=["robot"])

    assert result["status"] == "sent"
    assert result["topic"] == "jarvis"


def test_process_supervisor_spawn_list_tail_and_remove(tmp_path, monkeypatch):
    from core.services import process_supervisor as supervisor

    proc_dir = tmp_path / "processes"
    monkeypatch.setattr(supervisor, "_PROC_DIR", proc_dir)
    monkeypatch.setattr(supervisor, "_REGISTRY", proc_dir / "registry.json")
    monkeypatch.setattr(supervisor, "_pid_alive", lambda pid: True)

    class FakePopen:
        pid = 4242

        def __init__(self, *args, **kwargs):
            (proc_dir / "Test_Proc.log").write_text("spawned\nline 2\nline 3\n", encoding="utf-8")

    class FakeThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            return None

    monkeypatch.setattr(supervisor.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(supervisor.threading, "Thread", FakeThread)

    spawned = supervisor.spawn_process(name="Test Proc", command="echo hello")
    listed = supervisor.list_processes()

    monkeypatch.setattr(supervisor, "_pid_alive", lambda pid: False)
    tail = supervisor.tail_process_log("Test Proc", lines=2)
    removed = supervisor.remove_process("Test Proc")

    assert spawned["status"] == "ok"
    assert listed["count"] == 1
    assert tail["status"] == "ok"
    assert "line 2" in tail["lines"]
    assert removed["status"] == "ok"
