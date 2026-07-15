"""Fase B: tur-absorb — fyr den fulde post-tur-hjerne for en klient-drevet tur."""
import asyncio
import contextlib
from types import SimpleNamespace

from core.services import client_turn_absorb as cta


def _run(run_id="r1"):
    from core.services.visible_runs import VisibleRun
    return VisibleRun(run_id=run_id, lane="agent", provider="p", model="m",
                      user_message="u", session_id="s")


def _patch_ctx(monkeypatch):
    monkeypatch.setattr("core.identity.workspace_context.user_context",
                        lambda **kw: contextlib.nullcontext())


def test_do_absorb_fires_all_three_in_order(monkeypatch):
    _patch_ctx(monkeypatch)
    calls = []
    monkeypatch.setattr("core.services.visible_runs_outcomes.set_last_visible_run_outcome",
                        lambda run, **k: calls.append(("outcome", k.get("text_preview"))))
    monkeypatch.setattr("core.services.visible_runs_cognitive._track_runtime_candidates",
                        lambda run, txt: calls.append(("candidates", txt)))
    monkeypatch.setattr("core.services.visible_runs_memory._run_memory_postprocess",
                        lambda run, txt: calls.append(("memory", txt)))
    cta._do_absorb(_run(), "the answer", "")
    assert [c[0] for c in calls] == ["outcome", "candidates", "memory"]
    assert calls[0][1] == "the answer"   # text_preview
    assert calls[1][1] == "the answer"


def test_do_absorb_self_safe_when_one_raises(monkeypatch):
    _patch_ctx(monkeypatch)
    calls = []

    def _boom(run, **k):
        raise RuntimeError("outcome exploded")

    monkeypatch.setattr("core.services.visible_runs_outcomes.set_last_visible_run_outcome", _boom)
    monkeypatch.setattr("core.services.visible_runs_cognitive._track_runtime_candidates",
                        lambda run, txt: calls.append("candidates"))
    monkeypatch.setattr("core.services.visible_runs_memory._run_memory_postprocess",
                        lambda run, txt: calls.append("memory"))
    cta._do_absorb(_run(), "x", "")  # må IKKE rejse
    assert calls == ["candidates", "memory"]  # de øvrige fyrer stadig


def test_absorb_client_turn_constructs_run_and_threads(monkeypatch):
    captured = {}

    class _FakeThread:
        def __init__(self, target=None, args=(), daemon=None):
            self.target, self.args = target, args

        def start(self):
            captured["run"] = self.args[0]
            captured["resp"] = self.args[1]

    monkeypatch.setattr(cta.threading, "Thread", _FakeThread)
    cta.absorb_client_turn(session_id="s", run_id="r9", user_message="u",
                           assistant_response="A", provider="deepseek", model="m", user_id="")
    run = captured["run"]
    assert run.run_id == "r9" and run.session_id == "s"
    assert run.provider == "deepseek" and run.lane == "agent"
    assert captured["resp"] == "A"


def test_settings_flag_default_false():
    from core.runtime.settings import load_settings
    assert load_settings().agent_turn_absorb_enabled is False


# --- Fase C1: persist_client_turn (delte sessioner) -------------------------


def test_persist_skips_local_uuid_session(monkeypatch):
    called = []
    monkeypatch.setattr("core.services.chat_sessions.append_chat_message",
                        lambda **kw: called.append(kw))
    ok = cta.persist_client_turn(session_id="a1b2c3d4-uuid", user_message="u",
                                 assistant_response="a")
    assert ok is False
    assert called == []  # lokal uuid → ingen orphan-rækker


def test_persist_appends_user_then_assistant_for_server_session(monkeypatch):
    called = []
    monkeypatch.setattr("core.services.chat_sessions.append_chat_message",
                        lambda **kw: called.append((kw["role"], kw["content"], kw.get("user_id"))))
    ok = cta.persist_client_turn(session_id="chat-abc123", user_message="hej",
                                 assistant_response="svar", user_id="")
    assert ok is True
    assert [(r, c) for r, c, _ in called] == [("user", "hej"), ("assistant", "svar")]


def test_endpoint_returns_persisted_flag_on(monkeypatch):
    from apps.api.jarvis_api.routes import agent_loop as al
    monkeypatch.setattr(al, "_settings",
                        lambda: SimpleNamespace(agent_turn_absorb_enabled=True))
    appended = []
    monkeypatch.setattr("core.services.chat_sessions.append_chat_message",
                        lambda **kw: appended.append(kw["role"]))
    monkeypatch.setattr("core.services.client_turn_absorb.absorb_client_turn",
                        lambda **kw: None)
    body = al._AbsorbBody(session_id="chat-xyz", run_id="r", user_message="u",
                          assistant_response="a")
    r = asyncio.run(al.agent_turn_absorb(body))
    assert r["ok"] is True and r["persisted"] is True
    assert appended == ["user", "assistant"]


def test_endpoint_flag_off_is_noop():
    from apps.api.jarvis_api.routes import agent_loop as al
    body = al._AbsorbBody(session_id="s", run_id="r", assistant_response="a")
    r = asyncio.run(al.agent_turn_absorb(body))
    assert r["ok"] is False and r["skipped"] == "flag_off"


def test_endpoint_flag_on_dispatches(monkeypatch):
    from apps.api.jarvis_api.routes import agent_loop as al
    monkeypatch.setattr(al, "_settings",
                        lambda: SimpleNamespace(agent_turn_absorb_enabled=True))
    seen = {}
    monkeypatch.setattr("core.services.client_turn_absorb.absorb_client_turn",
                        lambda **kw: seen.update(kw))
    body = al._AbsorbBody(session_id="s", run_id="r7", user_message="u", assistant_response="a")
    r = asyncio.run(al.agent_turn_absorb(body))
    assert r["ok"] is True and r["run_id"] == "r7"
    assert seen["run_id"] == "r7" and seen["assistant_response"] == "a"
