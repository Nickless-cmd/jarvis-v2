import time
from unittest import mock


def _make_async_iter(items):
    async def _gen():
        for item in items:
            yield item
    return _gen()


def _patch(monkeypatch, frames):
    import core.services.run_event_log as rel
    import core.services.visible_runs as vr
    import core.services.visible_runs_sse_v2 as v2
    created, appended, done = [], [], []
    monkeypatch.setattr(rel, "create", lambda rid, sid: created.append((rid, sid)))
    monkeypatch.setattr(rel, "append", lambda rid, f: appended.append((rid, f)))
    monkeypatch.setattr(rel, "mark_done", lambda rid: done.append(rid))
    monkeypatch.setattr(rel, "prune", lambda: None)
    monkeypatch.setattr(vr, "start_visible_run", lambda **kw: _make_async_iter([]))
    monkeypatch.setattr(v2, "translate_to_v2", lambda it, **kw: _make_async_iter(frames))
    return created, appended, done


def test_detached_run_creates_log_appends_and_marks_done(monkeypatch):
    created, appended, done = _patch(monkeypatch, ["a", "b", "c"])
    from core.services.visible_runs_sections.detached_run import start_user_run_detached
    rid = start_user_run_detached(
        message="hej", session_id="s1", eff_model="m", eff_provider="p", lane="l"
    )
    assert rid and created and created[0][1] == "s1"
    assert created[0][0] == rid
    for _ in range(60):
        if len(appended) >= 3 and done:
            break
        time.sleep(0.05)
    assert [f for _r, f in appended] == ["a", "b", "c"]
    assert done and done[0] == rid


def test_detached_run_selects_research_iterator_when_requested(monkeypatch):
    created, appended, done = _patch(monkeypatch, ["research-frame"])
    import core.services.research_orchestrator as research
    calls = []
    monkeypatch.setattr(research, "research_enabled", lambda: True)
    monkeypatch.setattr(
        research,
        "stream_research_run",
        lambda **kwargs: calls.append(kwargs) or _make_async_iter([]),
    )
    from core.services.visible_runs_sections.detached_run import start_user_run_detached
    rid = start_user_run_detached(
        message="model message", original_message="original", session_id="s1",
        eff_model="m", eff_provider="p", lane="l", research_mode=True,
    )
    for _ in range(60):
        if calls and done:
            break
        time.sleep(0.05)
    assert calls[0]["message"] == "model message"
    assert calls[0]["original_query"] == "original"
    assert calls[0]["visible_run_id"] == rid


def test_genoptaget_tur_lukker_opgaven_fra_synkron_journal(monkeypatch):
    from core.services.visible_runs_sections import detached_run as d
    from core.services import in_flight_runs as ifr
    closed = []
    monkeypatch.setattr(ifr, "get_record", lambda rid: {"status": "completed"})
    monkeypatch.setattr(ifr, "current_owner", lambda: "owner-1")
    monkeypatch.setattr(ifr, "settle_terminal",
                        lambda *args, **kw: closed.append((args, kw)))
    monkeypatch.setattr("core.services.visible_runs_outcomes.run_er_terminal",
                        lambda rid: False)
    d._afregn_genoptaget_run("task-1", "inner-1", generation=1)
    assert closed == [(("task-1",), {
        "status": "completed", "reason": "recovery-run-terminal",
        "expected_generation": 1, "expected_owner": "owner-1",
    })]


def test_afbrudt_genoptagelse_giver_samme_krav_tilbage(monkeypatch):
    from core.services.visible_runs_sections import detached_run as d
    from core.services import in_flight_runs as ifr
    released = []
    monkeypatch.setattr(ifr, "get_record", lambda rid: {
        "status": "recovering", "exit_reason": "budget-opbrugt",
    })
    monkeypatch.setattr(ifr, "current_owner", lambda: "owner-1")
    monkeypatch.setattr(ifr, "release_recovery_claim",
                        lambda *args, **kw: released.append((args, kw)) or True)
    d._afregn_genoptaget_run("task-1", "inner-1", generation=2)
    assert released == [(("task-1", 2), {
        "owner": "owner-1", "reason": "budget-opbrugt", "retry_after_s": 30.0,
    })]


def test_genoptaget_tur_opretter_ikke_et_nyt_krav(monkeypatch):
    _patch(monkeypatch, ["frame"])
    from core.services.visible_runs_sections import detached_run as d
    settled, nested = [], []
    monkeypatch.setattr(d, "_afregn_genoptaget_run", lambda *a, **kw: settled.append(a))
    monkeypatch.setattr(d, "_fortsaet_hvis_budgettet_loeb_toert",
                        lambda **kw: nested.append(kw))
    d.start_user_run_detached(message="fortsæt", session_id="s1",
                              recovery_task_id="task-1", recovery_generation=2)
    for _ in range(60):
        if settled:
            break
        time.sleep(0.05)
    assert settled and not nested
