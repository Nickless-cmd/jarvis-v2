"""Fase 2 — Central-observability-huller H4/H5/H3 (spec §2 "Central-integrations-huller").

Disse er REN observabilitet (nerver) + ét bundet H3-watchdog-re-arm. De ÆNDRER
IKKE control-flow på happy-path. Testene er hermetiske (ingen live-modeller/netværk)
og asserterer at de tre fejl-modes nu LANDER i Centralen i stedet for at være tavse:

  H4 — openai-responses + openai-codex-banerne kastede UDEN provider-error-observe.
  H5 — `_persist_session_assistant_message` i `except: pass` → "vist live, væk ved
       reload" uden nerve.
  H3 — ollama inter-byte-frys: watchdog disarmede efter byte 1 → mid-stream-frys
       ubundet. Nu re-armer den + observerer `ollama_inter_byte_stall`.
"""
from __future__ import annotations

import asyncio
import threading

import pytest

import core.services.central_core as cc
import core.services.visible_model as vm


# ── Fælles central-sink ──────────────────────────────────────────────────────
class _CentralSink:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def observe(self, ev) -> None:
        self.events.append(dict(ev))


def _install_sink(monkeypatch) -> _CentralSink:
    sink = _CentralSink()
    monkeypatch.setattr(cc, "central", lambda: sink)
    return sink


class _UrllibShim:
    """Mirror af det rigtige ``urllib.request``-modul med KUN ``urlopen`` overrided.

    HVORFOR: ``monkeypatch.setattr(vm.urllib_request, "urlopen", ...)`` muterer
    det DELTE ``urllib.request``-modul-objekt globalt i processen. Under en
    testkørsel rammer enhver ANDEN ``urllib.request.urlopen``-kalder (fx cheap-
    lane-fan-out fra baggrunds-daemons) så mock'en og fejler med
    ``'_StallingResponse' object has no attribute 'read'`` — og de fejl blev
    skrevet i den ægte ``cheap_provider_invocations``-DB (testene requester ikke
    ``isolated_runtime``). Ved i stedet at rebinde NAVNET ``urllib_request`` på
    ``visible_model``-modulet rammer patch'en kun vm's egne kald; det globale
    modul er urørt. ``__getattr__`` delegerer alle øvrige attrs (Request m.fl.)
    til det ægte modul.
    """

    def __init__(self, real, urlopen) -> None:
        self._real = real
        self.urlopen = urlopen

    def __getattr__(self, name):
        return getattr(self._real, name)


def _patch_vm_urlopen(monkeypatch, fake_urlopen) -> None:
    """Scoped erstatning af ``visible_model.urllib_request.urlopen`` uden at
    lække ind i det globale ``urllib.request``-modul. Se ``_UrllibShim``."""
    monkeypatch.setattr(
        vm, "urllib_request", _UrllibShim(vm.urllib_request, fake_urlopen))


# ── H4: openai-responses-banen ───────────────────────────────────────────────
def test_h4_openai_responses_observes_provider_error_before_raise(monkeypatch):
    """`_stream_openai_model` skal observe provider_error FØR den re-raiser når
    SSE-iteratoren kaster. FØR var den except-stille (modsat ollama-lanen)."""
    sink = _install_sink(monkeypatch)
    monkeypatch.setattr(vm, "_load_openai_api_key", lambda: "sk-test")
    monkeypatch.setattr(vm, "_build_visible_input",
                        lambda *a, **k: [{"role": "user", "content": "hej"}])

    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def close(self):
            pass

    _patch_vm_urlopen(monkeypatch, lambda *a, **k: _FakeResp())

    def _boom_sse(*_a, **_k):
        raise RuntimeError("simuleret responses-stream-drop")
        yield  # pragma: no cover — gør funktionen til en generator

    monkeypatch.setattr(vm, "_iter_sse_events", _boom_sse)

    with pytest.raises(RuntimeError):
        list(vm._stream_openai_model(message="hej", model="gpt-5.4"))

    errs = [e for e in sink.events if e.get("nerve") == "provider_error"]
    assert errs, f"forventede provider_error-nerve, fik: {sink.events}"
    assert errs[0]["lane"] == "visible"
    assert errs[0]["provider"] == "openai"
    assert errs[0]["model"] == "gpt-5.4"


def test_h4_openai_responses_observe_is_self_safe(monkeypatch):
    """Observe må ALDRIG maskere/erstatte den oprindelige fejl, selv hvis central
    selv kaster. Den oprindelige RuntimeError skal stadig propagere."""
    monkeypatch.setattr(cc, "central",
                        lambda: (_ for _ in ()).throw(RuntimeError("central nede")))
    monkeypatch.setattr(vm, "_load_openai_api_key", lambda: "sk-test")
    monkeypatch.setattr(vm, "_build_visible_input",
                        lambda *a, **k: [{"role": "user", "content": "hej"}])

    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def close(self):
            pass

    _patch_vm_urlopen(monkeypatch, lambda *a, **k: _FakeResp())

    def _boom_sse(*_a, **_k):
        raise RuntimeError("oprindelig-fejl")
        yield  # pragma: no cover

    monkeypatch.setattr(vm, "_iter_sse_events", _boom_sse)

    with pytest.raises(RuntimeError, match="oprindelig-fejl"):
        list(vm._stream_openai_model(message="hej", model="gpt-5.4"))


# ── H4: openai-codex-banen ───────────────────────────────────────────────────
def test_h4_openai_codex_observes_provider_error_before_raise(monkeypatch):
    """`_stream_openai_codex_model` skal observe provider_error FØR re-raise når
    codex-event-iteratoren kaster."""
    sink = _install_sink(monkeypatch)
    monkeypatch.setattr(vm, "_provider_router_config",
                        lambda *, provider: {"auth_profile": "codex", "base_url": ""})
    monkeypatch.setattr(vm, "_build_openai_codex_visible_prompt",
                        lambda **_k: "PROMPT")

    import core.tools.copilot_tool_pruning as ctp
    monkeypatch.setattr(ctp, "select_tools_for_visible", lambda *a, **k: [])
    import core.tools.simple_tools as st
    monkeypatch.setattr(st, "get_tool_definitions", lambda *a, **k: [])

    import core.services.cheap_provider_runtime as cpr

    def _boom_codex(*_a, **_k):
        raise RuntimeError("simuleret codex-stream-drop")
        yield  # pragma: no cover

    monkeypatch.setattr(cpr, "_iter_openai_codex_chat_events", _boom_codex)

    with pytest.raises(RuntimeError):
        list(vm._stream_openai_codex_model(message="hej", model="gpt-5.4-codex"))

    errs = [e for e in sink.events if e.get("nerve") == "provider_error"]
    assert errs, f"forventede provider_error-nerve, fik: {sink.events}"
    assert errs[0]["provider"] == "openai-codex"
    assert errs[0]["model"] == "gpt-5.4-codex"


# ── H5: persisterings-fejl-nerve ─────────────────────────────────────────────
def test_h5_persist_failed_helper_fires_nerve(monkeypatch):
    """`_observe_persist_failed` skal sende en stream/persist_failed-nerve med
    run_id/session_id/provider/model + fejlen."""
    import core.services.visible_runs as vr
    sink = _install_sink(monkeypatch)

    run = vr.VisibleRun(
        run_id="r-h5", lane="primary", provider="deepseek",
        model="deepseek-v4-flash", user_message="hej", session_id="s-h5")
    vr._observe_persist_failed(run, RuntimeError("db locked"))

    pf = [e for e in sink.events if e.get("nerve") == "persist_failed"]
    assert pf, f"forventede persist_failed-nerve, fik: {sink.events}"
    e = pf[0]
    assert e["cluster"] == "stream"
    assert e["run_id"] == "r-h5"
    assert e["session_id"] == "s-h5"
    assert e["provider"] == "deepseek"
    assert e["model"] == "deepseek-v4-flash"
    assert "db locked" in e["error"]


def test_h5_persist_failed_helper_is_self_safe(monkeypatch):
    """Nerven må aldrig kaste videre ind i stream-stien — heller ikke hvis central
    selv kaster."""
    import core.services.visible_runs as vr
    monkeypatch.setattr(cc, "central",
                        lambda: (_ for _ in ()).throw(RuntimeError("central nede")))
    run = vr.VisibleRun(
        run_id="r", lane="primary", provider="p", model="m",
        user_message="x", session_id="s")
    # Må IKKE kaste:
    vr._observe_persist_failed(run, RuntimeError("boom"))


def test_h5_persist_failure_in_run_fires_nerve(monkeypatch):
    """Ægte spor: når `_persist_session_assistant_message` kaster midt i et run,
    skal except-blokken rute til persist_failed-nerven i stedet for tavst `pass`.
    Driver det rigtige `_stream_visible_run` hermetisk (mønstret fra
    test_streaming_fault_injection)."""
    import core.services.visible_runs as vr
    import core.services.ollama_visible_prompt as ovp
    from core.services.visible_model import (
        VisibleModelResult, VisibleModelStreamDone,
    )

    sink = _install_sink(monkeypatch)

    def _fake_stream_model(**_kw):
        yield VisibleModelStreamDone(
            result=VisibleModelResult(text="et synligt svar", input_tokens=5,
                                      output_tokens=3, cost_usd=0.0))

    monkeypatch.setattr(vr, "stream_visible_model", _fake_stream_model)
    monkeypatch.setattr(vr, "_build_visible_input",
                        lambda *a, **k: [{"role": "user", "content": "hej"}])
    monkeypatch.setattr(vr, "_visible_run_cancelled", lambda _rid: False)
    monkeypatch.setattr(ovp, "serialize_ollama_chat_messages", lambda x: list(x))

    # Persistering KASTER → except-blokken skal observe i stedet for at sluge.
    def _raise_persist(run, text, **_k):
        raise RuntimeError("disk full ved persist")

    monkeypatch.setattr(vr, "_persist_session_assistant_message", _raise_persist)
    monkeypatch.setattr(vr, "append_chat_message", lambda **_k: {"id": "m1"})
    monkeypatch.setattr(vr, "record_cost", lambda **_k: None)
    monkeypatch.setattr(vr.event_bus, "publish", lambda *a, **k: None)
    monkeypatch.setattr(vr, "_run_memory_postprocess", lambda *a, **k: None)
    monkeypatch.setattr(vr, "_track_runtime_candidates", lambda *a, **k: None)
    monkeypatch.setattr(vr, "write_private_terminal_layers", lambda *a, **k: None)

    run = vr.VisibleRun(
        run_id="r-h5-run", lane="primary", provider="deepseek",
        model="deepseek-v4-flash", user_message="hej", session_id="s-h5-run")

    async def _run() -> list[str]:
        out: list[str] = []
        async for chunk in vr._stream_visible_run(run):
            out.append(chunk)
        return out

    chunks = asyncio.run(_run())
    # Runnet må ikke kaste (self-safe) og skal stadig nå en terminal-frame.
    assert any('"type": "done"' in c or "message_stop" in c for c in chunks)
    pf = [e for e in sink.events if e.get("nerve") == "persist_failed"]
    assert pf, (f"forventede persist_failed-nerve fra et ægte run, fik nerver: "
                f"{[e.get('nerve') for e in sink.events]}")
    assert pf[0]["run_id"] == "r-h5-run"
    assert "disk full" in pf[0]["error"]


# ── H3: ollama inter-byte-frys ───────────────────────────────────────────────
def test_h3_inter_byte_watchdog_fires_and_observes_on_midstream_freeze(monkeypatch):
    """Watchdog'en skal RE-ARME efter første byte: når næste linje fryser ud over
    INTER_BYTE_BUDGET_S, force-lukker den socketen OG observerer
    ollama_inter_byte_stall. FØR (disarm efter byte 1) var frysen ubundet."""
    sink = _install_sink(monkeypatch)

    # Korte budgetter så testen er hurtig og deterministisk.
    monkeypatch.setattr(vm, "_OLLAMA_FIRST_BYTE_BUDGET_S", 5)
    monkeypatch.setattr(vm, "_OLLAMA_INTER_BYTE_BUDGET_S", 1)

    # Undgå netværks-/settings-afhængigheder i prompt-byggeriet.
    monkeypatch.setattr(vm, "_build_visible_input",
                        lambda *a, **k: [{"role": "user", "content": "hej"}])
    import core.services.ollama_visible_prompt as ovp
    monkeypatch.setattr(ovp, "serialize_ollama_chat_messages",
                        lambda x: [{"role": "user", "content": "hej"}])
    import core.tools.copilot_tool_pruning as ctp
    monkeypatch.setattr(ctp, "select_tools_for_visible", lambda *a, **k: [])
    import core.tools.simple_tools as st
    monkeypatch.setattr(st, "get_tool_definitions", lambda *a, **k: [])

    closed = threading.Event()

    class _StallingResponse:
        """Yielder ÉN gyldig NDJSON-linje og fryser så på næste read indtil
        watchdog'en kalder close() (sætter `closed` → vi raiser som en ægte
        socket-luk ville)."""

        def __init__(self):
            self._first = True

        def __iter__(self):
            return self

        def __next__(self):
            if self._first:
                self._first = False
                return (b'{"message": {"content": "hej "}, "done": false}\n')
            # Frys indtil watchdog'en lukker os (max ~5s sikkerhedsloft).
            if closed.wait(timeout=5):
                raise OSError("stream force-closed by watchdog")
            raise OSError("stream force-closed (timeout-safety)")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def close(self):
            closed.set()

    _patch_vm_urlopen(monkeypatch, lambda *a, **k: _StallingResponse())

    deltas: list[str] = []
    with pytest.raises(Exception):
        for ev in vm._stream_ollama_model(message="hej", model="glm-5.2:cloud"):
            if isinstance(ev, vm.VisibleModelDelta):
                deltas.append(ev.delta)

    # Vi fik den første delta FØR frysen.
    assert deltas == ["hej "], deltas
    # Watchdog'en lukkede socketen (re-arm virkede).
    assert closed.is_set(), "watchdog force-lukkede ikke socketen ved mid-stream-frys"
    # ... og gjorde frysen MÅLBAR i Centralen.
    stalls = [e for e in sink.events
              if "ollama_inter_byte_stall" in str(e.get("detail", ""))]
    assert stalls, (f"forventede ollama_inter_byte_stall-observe, fik: "
                    f"{[e.get('detail') for e in sink.events]}")
    assert stalls[0]["provider"] == "ollama"
    assert stalls[0]["model"] == "glm-5.2:cloud"
