from core.services import background_attention as attention


def test_success_without_attention_only_emits_telemetry(monkeypatch):
    emitted = []
    monkeypatch.setattr(attention, "_publish", lambda payload: emitted.append(payload))
    monkeypatch.setattr(attention, "_owner_user_id", lambda: "bjorn")
    monkeypatch.setattr(attention, "_existing_inbox", lambda **kwargs: None)
    monkeypatch.setattr(
        attention, "_write_inbox",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("no inbox write")),
    )

    result = attention.report_background_outcome(
        source_kind="periodic", source_id="health", status="completed",
        summary="Alt er grønt.",
    )

    assert result["status"] == "recorded"
    assert result["inbox"] == "skipped"
    assert emitted[0]["status"] == "completed"


def test_actionable_failure_is_deduplicated_into_inbox_and_side_task(monkeypatch):
    inbox = []
    tasks = []
    monkeypatch.setattr(attention, "_publish", lambda payload: None)
    monkeypatch.setattr(attention, "_owner_user_id", lambda: "bjorn")
    monkeypatch.setattr(attention, "_existing_inbox", lambda **kwargs: None)
    monkeypatch.setattr(
        attention, "_write_inbox",
        lambda **kwargs: inbox.append(kwargs) or {"status": "ok"},
    )
    monkeypatch.setattr(
        attention, "_write_side_task",
        lambda **kwargs: tasks.append(kwargs) or {
            "status": "ok", "side_task_id": "side-1", "deduplicated": False,
        },
    )

    result = attention.report_background_outcome(
        source_kind="runtime-inspection", source_id="disk-growth",
        run_id="run-1", session_id="chat-1", status="blocked",
        severity="high", summary="Telemetry grows without rotation.",
        suggested_next_step="Inspect rotation configuration and propose a bounded fix.",
        requires_attention=True, create_side_task=True,
        autonomy_mode="inspect", safe_to_continue=False,
    )

    assert result["inbox"] == "ok"
    assert result["side_task"] == "ok"
    assert inbox[0]["kilde_id"] == "background-runtime-inspection-disk-growth"
    assert tasks[0]["finding_key"] == "background:runtime-inspection:disk-growth"
    assert tasks[0]["autonomy_mode"] == "inspect"


def test_resolved_incident_gets_a_new_generation(monkeypatch):
    inbox = []
    monkeypatch.setattr(attention, "_publish", lambda payload: None)
    monkeypatch.setattr(attention, "_owner_user_id", lambda: "bjorn")
    monkeypatch.setattr(attention, "_existing_inbox", lambda **kwargs: {"status": "done"})
    monkeypatch.setattr(
        attention, "_write_inbox",
        lambda **kwargs: inbox.append(kwargs) or {"status": "ok"},
    )

    result = attention.report_background_outcome(
        source_kind="daemon", source_id="mail", run_id="run-2",
        status="failed", summary="Mail-daemon fejlede.", requires_attention=True,
    )

    assert inbox[0]["kilde_id"].endswith("-run-2")
    assert result["dedupe_key"].endswith(":run-2")


def test_invalid_autonomy_mode_fails_closed(monkeypatch):
    monkeypatch.setattr(attention, "_publish", lambda payload: None)
    result = attention.report_background_outcome(
        source_kind="daemon", source_id="x", status="failed",
        summary="Fejl", requires_attention=True, create_side_task=True,
        autonomy_mode="unbounded",
    )
    assert result["status"] == "error"
    assert "autonomy_mode" in result["error"]
