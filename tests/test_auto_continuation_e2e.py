"""Regressions for the server-owned continuation path.

The stream relay has an outer ID; the durable run journal uses the inner ID.
On 28 September a relay-side fallback started one paid continuation while the
journal dispatcher later resumed the same task again.
"""
import inspect
import time

from core.services import auto_continuation as ac
from core.services.visible_runs_sections import detached_run as dr


def test_detached_relay_cannot_settle_or_spawn_a_second_continuation():
    source = inspect.getsource(dr.start_user_run_detached)
    assert "settle_recovering" not in source
    assert "_fortsaet_hvis_budgettet_loeb_toert" not in source
    assert "start_user_run_detached(" not in source[source.index("def _in_thread"):]


def test_recoverable_inner_run_does_not_spawn_from_relay(monkeypatch):
    import core.services.run_event_log as rel
    import core.services.visible_runs as vr
    import core.services.visible_runs_sse_v2 as v2

    calls = []
    done = []
    aliases = []

    async def empty():
        if False:
            yield None

    async def frames():
        ac.noter_udfald("visible-inner", "pending-tool-intent", "s1")
        yield 'event: system_event\ndata: {"type":"system_event","kind":"run","payload":{"run_id":"visible-inner"}}\n\n'

    monkeypatch.setattr(rel, "create", lambda rid, sid: None)
    monkeypatch.setattr(rel, "set_surface", lambda rid, surface: None)
    monkeypatch.setattr(rel, "append", lambda rid, frame: None)
    monkeypatch.setattr(rel, "alias", lambda inner, outer: aliases.append((inner, outer)))
    monkeypatch.setattr(rel, "mark_done", lambda rid: done.append(rid))
    monkeypatch.setattr(rel, "prune", lambda: None)
    monkeypatch.setattr(vr, "start_visible_run", lambda **kw: calls.append(kw) or empty())
    monkeypatch.setattr(v2, "translate_to_v2", lambda iterator, **kw: frames())
    monkeypatch.setattr("core.services.in_flight_runs.settle_recovering",
                        lambda *args, **kw: (_ for _ in ()).throw(AssertionError(
                            "the relay must not rewrite the durable recovery claim")))

    dr.start_user_run_detached(message="hej", session_id="s1", run_id="visible-outer")
    deadline = time.monotonic() + 3
    while not done and time.monotonic() < deadline:
        time.sleep(0.01)

    assert done == ["visible-outer"]
    assert aliases == [("visible-inner", "visible-outer")]
    assert len(calls) == 1
