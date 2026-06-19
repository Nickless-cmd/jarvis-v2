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
