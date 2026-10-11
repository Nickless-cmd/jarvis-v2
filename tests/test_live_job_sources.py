from __future__ import annotations

from core.services import live_job_events, process_supervisor
from core.services.live_job_sources import LiveJobSourcePump


def _captured():
    subscription = live_job_events.subscribe(session_id="", after=0)
    events = list(subscription.initial_events)
    subscription.close()
    return events


def test_process_log_since_returns_only_new_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(process_supervisor, "_PROC_DIR", tmp_path)
    (tmp_path / "worker.log").write_bytes(b"a\nb\n")
    first = process_supervisor.read_process_log_since("worker", 0)
    with (tmp_path / "worker.log").open("ab") as fh:
        fh.write(b"c\n")
    second = process_supervisor.read_process_log_since("worker", first["offset"])
    assert first["output"] == "a\nb\n"
    assert second["output"] == "c\n"


def test_short_job_emits_started_output_finished_in_one_sample(tmp_path, monkeypatch):
    live_job_events.reset_for_tests()
    monkeypatch.setattr(process_supervisor, "_PROC_DIR", tmp_path)
    (tmp_path / "quick.log").write_text("done\n", encoding="utf-8")
    pump = LiveJobSourcePump(
        snapshot_reader=lambda: {"bridge_ok": True, "jobs": [{
            "id": "quick", "kilde": "supervisor", "status": "exited",
            "exit_code": 0, "navn": "quick",
        }]},
        user_id="owner",
    )
    pump.sample_once()
    events = _captured()
    assert [event.event_type for event in events] == [
        "job_started", "job_output", "job_finished",
    ]
    assert events[1].payload["chunk"] == "done\n"
    pump.sample_once()
    assert [event.event_type for event in _captured()] == [
        "job_started", "job_output", "job_finished",
    ]


def test_bridge_failure_marks_operator_unknown_and_keeps_server_events(
    tmp_path, monkeypatch,
):
    live_job_events.reset_for_tests()
    monkeypatch.setattr(process_supervisor, "_PROC_DIR", tmp_path)
    (tmp_path / "worker.log").write_text("server\n", encoding="utf-8")

    async def broken_reader(**_kwargs):
        raise RuntimeError("bridge nede")

    pump = LiveJobSourcePump(
        snapshot_reader=lambda: {"bridge_ok": True, "jobs": [
            {"id": "worker", "kilde": "supervisor", "status": "running"},
            {"id": "bg_aaaaaaaaaaaa", "kilde": "operator", "status": "running"},
        ]},
        operator_reader=broken_reader,
        user_id="owner",
    )
    pump.sample_once()
    events = _captured()
    assert any(event.source == "supervisor" and event.event_type == "job_output"
               for event in events)
    assert any(event.event_type == "source_status"
               and event.source == "operator"
               and event.payload["healthy"] is False for event in events)
