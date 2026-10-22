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


def test_pump_grounds_explicit_memory_question_before_model(monkeypatch):
    from core.services.visible_first_pass_pump import pump_first_pass
    from core.tools.tool_scoping import current_local_exec, current_tool_scope

    seen = []

    def stream(**kwargs):
        seen.append(kwargs["message"])
        yield "done"

    class Loop:
        def call_soon_threadsafe(self, fn, item):
            fn(item)

    class Queue:
        def __init__(self):
            self.items = []

        def put_nowait(self, item):
            self.items.append(item)

    monkeypatch.setattr(
        "core.services.visible_memory_grounding.ground_memory_question",
        lambda message: message + "\n\n[grounded]",
    )
    run = SimpleNamespace(
        run_id="run-memory", user_message="Hvor arbejder jeg?", provider="deepseek",
        model="v4", session_id="session-1", thinking_mode="think",
        local_tool_exec=False, autonomous=False,
    )
    queue = Queue()
    sentinel = object()
    pump_first_pass(
        run, controller=None, tool_scope="chat", loop=Loop(), queue=queue,
        sentinel=sentinel, stream_fn=stream,
    )
    assert seen == ["Hvor arbejder jeg?\n\n[grounded]"]
    assert queue.items == ["done", sentinel]
    assert current_tool_scope() == ""
    assert current_local_exec() is False
