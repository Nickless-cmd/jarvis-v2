from fastapi.testclient import TestClient
from apps.api.jarvis_api.app import app
import apps.api.jarvis_api.routes.agent_loop as al

client = TestClient(app)


def test_flag_defaults_off():
    # Unknown flag key must read False (fail-safe: new behavior inert until enabled).
    assert al._flag("jc_agent_totally_unknown_flag_xyz") is False


def test_flag_reads_runtime_state(monkeypatch):
    monkeypatch.setattr(al, "get_runtime_state_value",
                        lambda key, default=None: True if key == "jc_agent_observability" else default)
    assert al._flag("jc_agent_observability") is True
    assert al._flag("jc_agent_user_scoping") is False


def test_seam_names_exist_for_monkeypatch():
    # Observability seams must be module-level names so tests can patch them.
    assert callable(al.record_cost)
    assert callable(al.note_empty_completion)


def _patch_model(monkeypatch, text="hej", tool_calls=None, tin=12, tout=7, cost=0.002, fr="stop"):
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    def _fake_chat(**kw):
        return {"text": text, "tool_calls": tool_calls or [], "input_tokens": tin,
                "output_tokens": tout, "cost_usd": cost, "finish_reason": fr}
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters._execute_openai_compatible_chat",
        _fake_chat)


def test_nonstream_envelope_additive(monkeypatch):
    _patch_model(monkeypatch)
    r = client.post("/v1/agent/step",
                    json={"messages": [{"role": "user", "content": "hej"}], "stream": False})
    assert r.status_code == 200
    b = r.json()
    # additive envelope
    assert b["status"] == "ok"
    assert b["tokens_in"] == 12 and b["tokens_out"] == 7
    assert b["cost_usd"] == 0.002
    assert isinstance(b["duration_ms"], int) and b["duration_ms"] >= 0
    assert b["result"] == "hej"
    assert b["finish_reason"] == "stop"
    # back-compat: old keys still present
    assert b["content"] == "hej" and b["done"] is True
    assert b["usage"]["prompt_tokens"] == 12


def test_nonstream_status_empty(monkeypatch):
    _patch_model(monkeypatch, text="", tool_calls=[])
    r = client.post("/v1/agent/step",
                    json={"messages": [{"role": "user", "content": "hej"}], "stream": False})
    assert r.json()["status"] == "empty"


def test_stream_done_has_cost_and_envelope(monkeypatch):
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    def _fake_iter(**kw):
        yield {"kind": "delta", "text": "hej"}
        yield {"kind": "done", "full_text": "hej", "input_tokens": 3, "output_tokens": 2,
               "cost_usd": 0.0009, "finish_reason": "stop"}
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_streaming._iter_openai_compatible_chat_events",
        _fake_iter)
    with client.stream("POST", "/v1/agent/step",
                       json={"messages": [{"role": "user", "content": "hej"}], "stream": True}) as r:
        body = "".join(chunk for chunk in r.iter_text())
    assert "event: done" in body
    import json as _j
    done = [ln for ln in body.splitlines() if ln.startswith("data:") and "cost_usd" in ln][-1]
    payload = _j.loads(done[len("data: "):])
    assert payload["cost_usd"] == 0.0009
    assert payload["status"] == "ok"
    assert payload["tokens_in"] == 3 and payload["tokens_out"] == 2
    assert payload["finish_reason"] == "stop"


def test_observability_off_by_default(monkeypatch):
    _patch_model(monkeypatch, text="", tool_calls=[])  # empty completion
    called = {"empty": 0, "nerve": 0}
    monkeypatch.setattr(al, "note_empty_completion",
                        lambda *a, **k: called.__setitem__("empty", called["empty"] + 1))
    monkeypatch.setattr(al, "_emit_agent_nerve",
                        lambda **k: called.__setitem__("nerve", called["nerve"] + 1))
    # flag defaults OFF -> no side effects
    r = client.post("/v1/agent/step",
                    json={"messages": [{"role": "user", "content": "x"}], "stream": False})
    assert r.status_code == 200
    assert called == {"empty": 0, "nerve": 0}


def test_observability_on_emits_nerve_and_empty(monkeypatch):
    # tout=0: an empty-completion fixture should carry zero output tokens,
    # consistent with the tokens_out==0 assertion below (plan's _patch_model
    # default is tout=7, which would contradict this assertion if left unset).
    _patch_model(monkeypatch, text="", tool_calls=[], tout=0)
    monkeypatch.setattr(al, "_flag",
                        lambda name, default=False: name == "jc_agent_observability")
    seen = {}
    monkeypatch.setattr(al, "note_empty_completion",
                        lambda run_id, **k: seen.__setitem__("empty", k))
    nerves = []
    monkeypatch.setattr(al, "_emit_agent_nerve", lambda **k: nerves.append(k))
    r = client.post("/v1/agent/step",
                    json={"messages": [{"role": "user", "content": "x"}],
                          "stream": False, "session_id": "s1"})
    assert r.status_code == 200
    assert seen["empty"]["path"] == "agent_step"
    assert nerves and nerves[0]["status"] == "empty"
    assert nerves[0]["tokens_out"] == 0


def test_observability_on_nonempty_only_nerve(monkeypatch):
    _patch_model(monkeypatch, text="svar", tout=4)
    monkeypatch.setattr(al, "_flag",
                        lambda name, default=False: name == "jc_agent_observability")
    empties = []
    monkeypatch.setattr(al, "note_empty_completion", lambda *a, **k: empties.append(k))
    nerves = []
    monkeypatch.setattr(al, "_emit_agent_nerve", lambda **k: nerves.append(k))
    client.post("/v1/agent/step",
                json={"messages": [{"role": "user", "content": "x"}], "stream": False})
    assert empties == []            # non-empty -> no empty_completion
    assert nerves[0]["status"] == "ok"


def test_adapter_returns_finish_reason(monkeypatch):
    import core.services.cheap_provider_runtime_adapters as ad
    fake_data = {"choices": [{"finish_reason": "length",
                              "message": {"content": "trunc", "tool_calls": []}}],
                 "usage": {"prompt_tokens": 5, "completion_tokens": 4}}

    class _Facade:
        def _require_credentials(self, **k): return {"api_key": "x"}
        def provider_runtime_defaults(self, p): return {"base_url": "http://x"}
        def _http_json(self, *a, **k): return fake_data, {}
    monkeypatch.setattr(ad, "_facade", lambda: _Facade())
    out = ad._execute_openai_compatible_chat(
        provider="deepseek", model="deepseek-v4-flash", auth_profile="deepseek",
        base_url="http://x", messages=[{"role": "user", "content": "hi"}])
    assert out["finish_reason"] == "length"
