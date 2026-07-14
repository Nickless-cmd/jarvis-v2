"""Fase 6 Task 4 — server-side fault-injection regression tests for
/v1/agent/step: the O1 envelope, A6 finish_reason plumbing, note_empty_completion,
and A8 typed-forwarded-error contract, plus proof the Fase-0 default-OFF flag
is inert. Monkeypatches the provider seam only — no real network/provider.
"""
from fastapi.testclient import TestClient

from apps.api.jarvis_api.app import app
import apps.api.jarvis_api.routes.agent_loop as al

from .server_mock_provider import fake_chat, fake_stream, raising_chat

client = TestClient(app)


def _patch_chat(monkeypatch, fn):
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters._execute_openai_compatible_chat", fn)


def _patch_stream(monkeypatch, fn):
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_streaming._iter_openai_compatible_chat_events", fn)


def test_stream_done_carries_finish_reason(monkeypatch):
    _patch_stream(monkeypatch, fake_stream(text="delvist svar", fr="length"))
    with client.stream("POST", "/v1/agent/step",
                       json={"messages": [{"role": "user", "content": "hej"}],
                             "stream": True}) as r:
        body = "".join(chunk for chunk in r.iter_text())
    assert "event: done" in body
    import json as _j
    done_line = [ln for ln in body.splitlines()
                if ln.startswith("data:") and "finish_reason" in ln][-1]
    payload = _j.loads(done_line[len("data: "):])
    assert payload["finish_reason"] == "length"


def test_empty_completion_emits_note_and_envelope(monkeypatch):
    _patch_chat(monkeypatch, fake_chat(text="", tool_calls=[]))
    monkeypatch.setattr(al, "_flag", lambda name, default=False: name == "jc_agent_observability")
    seen = {}
    monkeypatch.setattr(al, "note_empty_completion", lambda run_id, **k: seen.update(k))
    r = client.post("/v1/agent/step",
                    json={"messages": [{"role": "user", "content": "hej"}], "stream": False})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "empty"
    assert seen.get("path") == "agent_step"


def test_agent_step_envelope_has_o1_fields(monkeypatch):
    _patch_chat(monkeypatch, fake_chat(text="svar", tin=11, tout=6, cost=0.0015, fr="stop"))
    monkeypatch.setattr(al, "_flag", lambda name, default=False: name == "jc_agent_observability")
    rec = {}
    monkeypatch.setattr(al, "record_cost", lambda **k: rec.update(k))
    r = client.post("/v1/agent/step",
                    json={"messages": [{"role": "user", "content": "hej"}],
                          "stream": False, "user_id": "member_x"})
    assert r.status_code == 200
    body = r.json()
    for field in ("status", "tokens_in", "tokens_out", "cost_usd", "duration_ms",
                 "finish_reason", "result", "tool_calls"):
        assert field in body, f"missing O1 field {field}"
    assert body["status"] == "ok"
    assert body["tokens_in"] == 11 and body["tokens_out"] == 6
    assert body["usage"]["prompt_tokens"] == 11
    assert rec["user_id"] == "member_x"


def test_forwarded_provider_error_returns_typed_not_500crash(monkeypatch):
    _patch_chat(monkeypatch, raising_chat(RuntimeError("upstream tool 500: forwarded failure")))
    r = client.post("/v1/agent/step",
                    json={"messages": [{"role": "user", "content": "hej"}], "stream": False})
    # A8/O2: a forwarded provider failure must surface as a TYPED 502 envelope,
    # never an unhandled 500 crash.
    assert r.status_code == 502
    body = r.json()
    assert "error" in body
    assert body["error"]["type"] == "upstream_error"
    assert "upstream tool 500" in body["error"]["message"]


def test_flag_off_is_inert(monkeypatch):
    _patch_chat(monkeypatch, fake_chat(text="", tool_calls=[], reasoning="secret-thinking"))
    calls = {"empty": 0, "nerve": 0, "cost": 0}
    monkeypatch.setattr(al, "note_empty_completion",
                        lambda *a, **k: calls.__setitem__("empty", calls["empty"] + 1))
    monkeypatch.setattr(al, "_emit_agent_nerve",
                        lambda **k: calls.__setitem__("nerve", calls["nerve"] + 1))
    monkeypatch.setattr(al, "record_cost",
                        lambda **k: calls.__setitem__("cost", calls["cost"] + 1))
    r = client.post("/v1/agent/step",
                    json={"messages": [{"role": "user", "content": "x"}], "stream": False})
    assert r.status_code == 200
    body = r.json()
    # default-OFF flags: none of the observability side effects fire ...
    assert calls == {"empty": 0, "nerve": 0, "cost": 0}
    # ... and the Fase-4 additive fields stay absent (byte-identical baseline).
    assert "reasoning_content" not in body
    assert "cache_hit_tokens" not in body.get("usage", {})
    assert "effective_approval_mode" not in body
    # the O1 envelope itself is unconditional (Fase 0), so it's still present.
    assert body["status"] == "empty"
