"""The first-pass worker carries the current run identity into prompt assembly."""
from __future__ import annotations

from types import SimpleNamespace


def test_pump_binds_run_identity_for_prompt_builder(monkeypatch):
    from core.services.visible_first_pass_pump import pump_first_pass
    from core.services.run_autonomy_context import current_run_id, is_autonomous

    seen = []

    def stream(**kwargs):
        seen.append((current_run_id(), is_autonomous()))
        yield "done"

    class Loop:
        def call_soon_threadsafe(self, fn, item):
            fn(item)

    class Queue:
        def __init__(self):
            self.items = []

        def put_nowait(self, item):
            self.items.append(item)

    monkeypatch.setattr("core.services.visible_model.stream_visible_model", stream)
    run = SimpleNamespace(
        run_id="run-abc", user_message="Hej", provider="deepseek", model="v4",
        session_id="session-1", thinking_mode="think", local_tool_exec=False,
        autonomous=True,
    )
    queue = Queue()
    sentinel = object()
    pump_first_pass(run, controller=None, tool_scope="", loop=Loop(), queue=queue, sentinel=sentinel)
    assert seen == [("run-abc", True)]
    assert queue.items == ["done", sentinel]
