from contextlib import nullcontext

from core.services import run_finding_accounting, side_tasks


def _lager(monkeypatch):
    tasks = []
    findings = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _k, _d: list(tasks))
    monkeypatch.setattr(side_tasks, "save_json", lambda _k, rows: tasks.__setitem__(slice(None), rows))
    monkeypatch.setattr(side_tasks, "med_laas", lambda _k: nullcontext())
    monkeypatch.setattr(run_finding_accounting, "load_json", lambda _k, _d: list(findings))
    monkeypatch.setattr(run_finding_accounting, "save_json", lambda _k, rows: findings.__setitem__(slice(None), rows))
    monkeypatch.setattr(run_finding_accounting, "med_laas", lambda _k: nullcontext())
    return tasks, findings


def test_coverage_gap_is_recorded_once_and_flagged_as_side_task(monkeypatch):
    tasks, findings = _lager(monkeypatch)
    args = dict(
        kind="coverage_gap", disposition="side_task", path="apps/mobile/RullendeTal.tsx",
        behavior="first frame wheel position", evidence="The start-position test was removed",
        title="Verificér første frame", next_step="Skriv en render-test for første frame",
        run_id="run-1", session_id="chat-1",
    )
    first = run_finding_accounting.record_finding(**args)
    again = run_finding_accounting.record_finding(**{**args, "run_id": "run-2"})
    assert first["status"] == "ok" and first["side_task_id"] == again["side_task_id"]
    assert len(tasks) == 1 and tasks[0]["finding_key"]
    assert len(findings) == 2
    assert findings[1]["deduplicated"] is True


def test_new_related_test_failure_cannot_be_deferred(monkeypatch):
    tasks, findings = _lager(monkeypatch)
    result = run_finding_accounting.record_finding(
        kind="new_test_failure", disposition="side_task", path="x.test.tsx",
        behavior="changed feature fails", evidence="test failed", title="Fix test",
        next_step="Fix it", run_id="r", session_id="s",
    )
    assert result["status"] == "error"
    assert tasks == findings == []


def test_fixed_or_declined_findings_leave_a_record_without_a_task(monkeypatch):
    tasks, findings = _lager(monkeypatch)
    for decision in ("fixed_now", "declined"):
        assert run_finding_accounting.record_finding(
            kind="coverage_gap", disposition=decision, path="x.tsx", behavior="initial frame",
            evidence="attempted test", title="Check frame", next_step="", reason="verified elsewhere",
            run_id="run-3", session_id="chat-3",
        )["status"] == "ok"
    assert tasks == [] and len(findings) == 2


def test_explicit_uncovered_test_admission_is_caught_if_tool_was_not_called(monkeypatch):
    tasks, findings = _lager(monkeypatch)
    text = (
        "RullendeTal.tsx blev ændret. Det betyder at startpositionen ikke er "
        "dækket af en test. Jeg fjernede den forsøgs-test der målte forkert."
    )
    result = run_finding_accounting.audit_final_response(
        run_id="run-4", session_id="chat-4", text=text,
    )
    assert result["created"] == 1
    assert len(tasks) == len(findings) == 1
    assert "RullendeTal.tsx" in tasks[0]["prompt"]
    assert run_finding_accounting.audit_final_response(
        run_id="run-4", session_id="chat-4", text=text,
    )["created"] == 0


def test_unrelated_red_suite_does_not_automatically_create_side_task(monkeypatch):
    tasks, findings = _lager(monkeypatch)
    result = run_finding_accounting.audit_final_response(
        run_id="run-5", session_id="chat-5",
        text="MessageList.test.tsx fejler i hele suiten; den er ikke ændret.",
    )
    assert result["created"] == 0 and tasks == findings == []


def test_jarvis_existing_flag_tool_accepts_structured_finding(monkeypatch):
    tasks, findings = _lager(monkeypatch)
    from core.services import session_context_resolve
    monkeypatch.setattr(session_context_resolve, "aktiv_session_id", lambda _d="": "chat-live")
    monkeypatch.setattr(session_context_resolve, "aktivt_run_id", lambda _d="": "run-live")
    result = side_tasks._exec_flag_side_task({
        "title": "Verificér første frame", "prompt": "Test initial position",
        "finding_kind": "coverage_gap", "disposition": "side_task",
        "path": "RullendeTal.tsx", "behavior": "initial wheel position",
        "evidence": "attempted test was removed",
    })
    assert result["status"] == "ok"
    assert tasks[0]["source_run_id"] == "run-live"
    assert tasks[0]["session_id"] == "chat-live"
    assert findings[0]["disposition"] == "side_task"
    assert run_finding_accounting.audit_final_response(
        run_id="run-live", session_id="chat-live",
        text="RullendeTal.tsx er ikke dækket af en test for første frame.",
    )["created"] == 0
    assert len(tasks) == 1
