"""I1-heal: thinking-felt-parse-hul (spec §11.5).

Reasoning-modeller (glm-5.2:cloud, deepseek thinking, ...) lægger NOGLE GANGE
hele svaret i `message.thinking` mens `message.content` er tom. FØR raiste
parseren "returned no streamed response" → empty_completion → brugeren fik en
fallback-besked i stedet for svaret. Disse tests verificerer den lokale,
model-agnostiske kur i BEGGE ollama-stier (streaming first-pass + resend),
HELT hermetisk (ingen live model-kald).
"""
from __future__ import annotations

import json
import io
import contextlib

import pytest

import core.services.visible_model as vm


# ---------------------------------------------------------------------------
# Fælles stubs: afkobl _stream_ollama_model / _execute_ollama_model fra alt
# der ellers ville lave rigtige kald (prompt-bygning, tool-katalog, central).
# ---------------------------------------------------------------------------
@pytest.fixture
def _stub_visible_env(monkeypatch):
    monkeypatch.setattr(vm, "_build_visible_input", lambda *a, **k: [])
    monkeypatch.setattr(
        "core.services.ollama_visible_prompt.serialize_ollama_chat_messages",
        lambda x: list(x),
    )
    import core.tools.simple_tools as st
    import core.tools.copilot_tool_pruning as ctp
    monkeypatch.setattr(st, "get_tool_definitions", lambda *a, **k: [])
    monkeypatch.setattr(ctp, "select_tools_for_visible", lambda *a, **k: [])
    # base_url-resolver — undgå provider-router-opslag
    import core.runtime.provider_router as pr
    monkeypatch.setattr(pr, "load_provider_router_registry", lambda *a, **k: {})
    monkeypatch.setattr(pr, "_provider_base_url", lambda **k: "http://127.0.0.1:11434")


@pytest.fixture
def _capture_observes(monkeypatch):
    """Fang alt der lander på central().observe — uden at importere det rigtige."""
    events: list[dict] = []

    class _FakeCentral:
        def observe(self, payload):
            events.append(dict(payload))

    monkeypatch.setattr("core.services.central_core.central", lambda: _FakeCentral())
    return events


def _ndjson_response(events: list[dict]):
    """Byg et urlopen-stub der returnerer en context-manager hvis iteration
    giver én NDJSON-linje pr. event (præcis som ollama streamer)."""
    lines = [json.dumps(e).encode("utf-8") + b"\n" for e in events]

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def __iter__(self):
            return iter(lines)

        def close(self):
            pass

    return _Resp()


def _drain_stream(gen):
    """Kør generatoren færdig, returnér (deltas, done_result)."""
    deltas: list[str] = []
    done = None
    for ev in gen:
        if isinstance(ev, vm.VisibleModelDelta):
            deltas.append(ev.delta)
        elif isinstance(ev, vm.VisibleModelStreamDone):
            done = ev.result
    return deltas, done


# ===========================================================================
# STREAMING FIRST-PASS
# ===========================================================================
def test_stream_content_empty_thinking_surfaced_as_answer(
    monkeypatch, _stub_visible_env, _capture_observes
):
    """(i) tekst = thinking, (ii) ingen raise, (iii) nerve fyret."""
    events = [
        {"message": {"thinking": "Her er det rigtige svar.", "content": ""}},
        {"done": True, "prompt_eval_count": 10, "eval_count": 5},
    ]
    monkeypatch.setattr(
        vm.urllib_request, "urlopen", lambda *a, **k: _ndjson_response(events)
    )

    gen = vm._stream_ollama_model(message="hej", model="glm-5.2:cloud")
    deltas, done = _drain_stream(gen)

    assert done is not None, "ingen StreamDone — raised?"
    assert done.text == "Her er det rigtige svar."  # (i)
    # reasoning_content bevares stadig til replay (uændret)
    assert "Her er det rigtige svar." in done.reasoning_content
    # (iii) nerve fyret
    fired = [e for e in _capture_observes
             if e.get("nerve") == "content_empty_thinking_fallback"]
    assert len(fired) == 1
    assert fired[0]["path"] == "stream_first_pass"
    assert fired[0]["model"] == "glm-5.2:cloud"
    assert fired[0]["thinking_len"] > 0


def test_stream_no_raise_when_thinking_present(
    monkeypatch, _stub_visible_env, _capture_observes
):
    """(ii) den gamle 'returned no streamed response' raiser IKKE længere."""
    events = [
        {"message": {"thinking": "svar i thinking", "content": ""}},
        {"done": True},
    ]
    monkeypatch.setattr(
        vm.urllib_request, "urlopen", lambda *a, **k: _ndjson_response(events)
    )
    # Må ikke raise:
    _, done = _drain_stream(vm._stream_ollama_model(message="x", model="m"))
    assert done.text == "svar i thinking"


def test_stream_content_present_thinking_not_surfaced(
    monkeypatch, _stub_visible_env, _capture_observes
):
    """(iv) REGRESSIONS-GUARD: når content er til stede, er thinking REN reasoning
    — svaret = content, og fallback-nerven fyrer IKKE."""
    events = [
        {"message": {"thinking": "min interne ræsonnering", "content": "Det rigtige svar."}},
        {"done": True},
    ]
    monkeypatch.setattr(
        vm.urllib_request, "urlopen", lambda *a, **k: _ndjson_response(events)
    )
    deltas, done = _drain_stream(vm._stream_ollama_model(message="x", model="m"))

    assert done.text == "Det rigtige svar."          # content vinder
    assert "min interne ræsonnering" in done.reasoning_content  # replay uændret
    assert "min interne ræsonnering" not in done.text          # IKKE lækket ind
    fired = [e for e in _capture_observes
             if e.get("nerve") == "content_empty_thinking_fallback"]
    assert fired == []                               # nerve IKKE fyret


def test_stream_truly_empty_still_raises(
    monkeypatch, _stub_visible_env, _capture_observes
):
    """Hverken content NELLER thinking → den gamle raise står (intet at surface)."""
    events = [
        {"message": {"content": "", "thinking": ""}},
        {"done": True},
    ]
    monkeypatch.setattr(
        vm.urllib_request, "urlopen", lambda *a, **k: _ndjson_response(events)
    )
    with pytest.raises(RuntimeError, match="returned no streamed response"):
        _drain_stream(vm._stream_ollama_model(message="x", model="m"))


def test_stream_thinking_delimiters_stripped(
    monkeypatch, _stub_visible_env, _capture_observes
):
    """Løse think-tags ryddes når thinking surfaces som svar."""
    events = [
        {"message": {"thinking": "<think>Svaret er 42.</think>", "content": ""}},
        {"done": True},
    ]
    monkeypatch.setattr(
        vm.urllib_request, "urlopen", lambda *a, **k: _ndjson_response(events)
    )
    _, done = _drain_stream(vm._stream_ollama_model(message="x", model="m"))
    assert done.text == "Svaret er 42."


def test_stream_tool_calls_unaffected(
    monkeypatch, _stub_visible_env, _capture_observes
):
    """Tool-call-håndtering urørt: thinking + tool_calls (ingen content) → tool-calls
    yields, INGEN thinking-fallback (der er værktøjer at køre)."""
    events = [
        {"message": {"thinking": "lad mig kalde et tool",
                      "content": "",
                      "tool_calls": [{"function": {"name": "foo", "arguments": "{}"}}]}},
        {"done": True},
    ]
    monkeypatch.setattr(
        vm.urllib_request, "urlopen", lambda *a, **k: _ndjson_response(events)
    )
    tool_yields = []
    done = None
    for ev in vm._stream_ollama_model(message="x", model="m"):
        if isinstance(ev, vm.VisibleModelToolCalls):
            tool_yields.append(ev)
        elif isinstance(ev, vm.VisibleModelStreamDone):
            done = ev.result
    assert tool_yields and tool_yields[0].tool_calls
    assert done.text == "[tool calls only]"
    fired = [e for e in _capture_observes
             if e.get("nerve") == "content_empty_thinking_fallback"]
    assert fired == []  # tool-calls til stede → ikke fallback


# ===========================================================================
# RESEND (non-streaming)
# ===========================================================================
class _FakeUrlopenResp:
    def __init__(self, data: dict):
        self._buf = json.dumps(data).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._buf


def _patch_resend(monkeypatch, payload: dict):
    monkeypatch.setattr(
        vm.urllib_request, "urlopen", lambda *a, **k: _FakeUrlopenResp(payload)
    )


def test_resend_content_empty_thinking_surfaced(
    monkeypatch, _stub_visible_env, _capture_observes
):
    _patch_resend(monkeypatch, {
        "message": {"content": "", "thinking": "Resend-svar fra thinking."},
        "prompt_eval_count": 7, "eval_count": 3,
    })
    res = vm._execute_ollama_model(message="hej", model="deepseek-v4:cloud")
    assert res.text == "Resend-svar fra thinking."
    fired = [e for e in _capture_observes
             if e.get("nerve") == "content_empty_thinking_fallback"]
    assert len(fired) == 1
    assert fired[0]["path"] == "resend"


def test_resend_content_present_thinking_not_surfaced(
    monkeypatch, _stub_visible_env, _capture_observes
):
    """REGRESSIONS-GUARD resend: content vinder, ingen fallback-nerve."""
    _patch_resend(monkeypatch, {
        "message": {"content": "Rigtigt resend-svar.", "thinking": "intern note"},
    })
    res = vm._execute_ollama_model(message="hej", model="m")
    assert res.text == "Rigtigt resend-svar."
    fired = [e for e in _capture_observes
             if e.get("nerve") == "content_empty_thinking_fallback"]
    assert fired == []


def test_resend_truly_empty_still_raises(
    monkeypatch, _stub_visible_env, _capture_observes
):
    _patch_resend(monkeypatch, {"message": {"content": "", "thinking": ""}})
    with pytest.raises(RuntimeError, match="returned no response"):
        vm._execute_ollama_model(message="hej", model="m")


# ===========================================================================
# strip-helper enhed
# ===========================================================================
@pytest.mark.parametrize("raw,expected", [
    ("<think>hej</think>", "hej"),
    ("◁think▷svar◁/think▷", "svar"),
    ("[THINK]abc[/THINK]", "abc"),
    ("ren tekst", "ren tekst"),
    ("", ""),
])
def test_strip_thinking_delimiters(raw, expected):
    assert vm._strip_thinking_delimiters(raw) == expected
