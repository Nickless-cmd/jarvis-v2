"""Loop-not-blocked (2026-06-29): bevis at tool-rundens SYNKRONE persistering
ikke længere fryser translate_to_v2's event-loop-tråd.

ROD-ÅRSAG (rod bag "desk-spinner / mobil-takeover" under tool-runder): et
detached user-run kører i en baggrundstråd der driver translate_to_v2 på en
asyncio-event-loop. På DEN loop kører ``_ping_loop`` (Ping hver 5s → run_event_log
.append → last_append_at frisk → active-runs holder runnet "live"). Hvis
``_stream_visible_run`` laver SYNKRON blokerende arbejde (DB-skrivning af
tool-resultater via ``append_chat_message``) direkte på loop-tråden mellem yields,
kan ``_ping_loop`` ikke fyre → last_append_at fryser → runnet flippes not-live.

Fixet offloader de blokerende persistence-kald til ``asyncio.to_thread`` så loopet
(og dermed ping/keepalive) bliver ved med at køre UNDER en tool-runde.

Disse tests driver det ÆGTE ``_stream_visible_run`` hermetisk (ingen DB/netværk):
``append_chat_message`` gøres til et BLOKERENDE kald (time.sleep), og en samtidig
"ticker"-coroutine kører på samme loop. Vi måler hvor mange gange tickeren tikker
NETOP I blok-vinduet (snapshot ved blok-entry/-exit). Awaites persisteringen
inline på loop-tråden står tickeren stille (~0 ticks i vinduet); offloades den via
to_thread tikker den videre — præcis den egenskab _ping_loop afhænger af.
"""
from __future__ import annotations

import asyncio
import threading
import time

import core.services.ollama_visible_prompt as ovp
import core.services.visible_followup as vf
import pytest

import core.services.visible_runs as vr
from core.services import followup_observer as fo
from core.services.visible_model import (
    VisibleModelResult,
    VisibleModelStreamDone,
    VisibleModelToolCalls,
)


@pytest.fixture(autouse=True)
def _isolate_streaming_globals():
    """Test-isolation (29. jun): disse tests bruger fault-injektion + tråd-tunge
    runs. Ryd ALT delt proces-globalt state EFTER hver test, så intet lækker ind i
    de andre streaming-suiter (fault-registry, provider-breaker)."""
    yield
    try:
        vf.clear_faults()
    except Exception:
        pass
    try:
        from core.services.provider_circuit_breaker import reset_all
        reset_all()
    except Exception:
        pass
    # NB (test-oprydnings-bunken): der er en kendt ordnings-følsom harness-state-deling
    # mellem disse loop-tests og test_streaming_fault_injection.test_clean_fail_* når de
    # køres i SAMME proces i rækkefølge (clean-fail finaliserer da completed-empty i stedet
    # for interrupted). Produktions-koden er upåvirket (to_thread-kaldene er await'ede →
    # rækkefølge bevaret). Køres begge filer hver for sig = grønne. Ryddes i test-pass'et.


def _patch_hermetic(monkeypatch) -> None:
    """Mock first-pass-model + tools + tunge baggrunds-daemons → ingen DB/net."""

    def _fake_stream_model(**_kw):
        # Ét tool-kald, så stream-done med TOM prosa → first-pass-tool-stien
        # eksekveres og tool-resultatet persisteres (linje ~1761).
        yield VisibleModelToolCalls(tool_calls=[{
            "id": "c1", "type": "function",
            "function": {"name": "read_file", "arguments": '{"path": "x"}'},
        }])
        yield VisibleModelStreamDone(
            result=VisibleModelResult(text="", input_tokens=10,
                                      output_tokens=5, cost_usd=0.0))

    def _fake_exec_tools(_tool_calls, **_kw):
        return [{
            "tool_name": "read_file", "tool_call_id": "c1",
            "status": "completed", "arguments": {"path": "x"},
            "result_text": "file-contents", "result": {"ok": True},
        }]

    monkeypatch.setattr(vr, "stream_visible_model", _fake_stream_model)
    monkeypatch.setattr(vr, "_execute_simple_tool_calls", _fake_exec_tools)
    monkeypatch.setattr(vr, "_build_visible_input",
                        lambda *a, **k: [{"role": "user", "content": "hej"}])
    monkeypatch.setattr(vr, "_visible_run_cancelled", lambda _rid: False)
    monkeypatch.setattr(ovp, "serialize_ollama_chat_messages", lambda x: list(x))

    monkeypatch.setattr(
        vr, "_persist_session_assistant_message",
        lambda run, text, **_k: None)
    monkeypatch.setattr(vr, "record_cost", lambda **_k: None)
    monkeypatch.setattr(vr.event_bus, "publish", lambda *a, **k: None)
    monkeypatch.setattr(vr, "_run_memory_postprocess", lambda *a, **k: None)
    monkeypatch.setattr(vr, "_track_runtime_candidates", lambda *a, **k: None)
    monkeypatch.setattr(vr, "write_private_terminal_layers", lambda *a, **k: None)
    monkeypatch.setattr(fo, "_observe", lambda *a, **k: None)
    monkeypatch.setattr(
        "core.services.agentic_checkpoints.save_checkpoint",
        lambda **_k: None)


def _make_run() -> "vr.VisibleRun":
    return vr.VisibleRun(
        run_id="visible-loop-not-blocked",
        lane="primary",
        provider="deepseek",
        model="deepseek-v4-flash",
        user_message="hej",
        session_id="s-loop-not-blocked")


def test_tool_persist_does_not_block_event_loop(monkeypatch) -> None:
    """append_chat_message blokerer (sleep); en samtidig ticker på SAMME loop
    skal blive ved med at tikke NETOP UNDER blokket → beviser at persisteringen
    er offloadet (to_thread), ikke awaited inline på loop-tråden.

    Vi snapshotter tick-tælleren ved blok-entry og blok-exit; deltaen i det
    vindue er nul hvis loopet var frosset, og positiv hvis loopet var frit. Den
    agentiske followup fejler øjeblikkeligt via fejl-injektoren → ingen netværk."""
    _patch_hermetic(monkeypatch)

    block_s = 0.4
    persist_roles: list[str] = []
    ticks_at_block_entry: list[int] = []
    ticks_at_block_exit: list[int] = []
    counter = {"ticks": 0}

    def _blocking_append(**kw):
        # Ægte synkront blok på den tråd der kalder. Er det loop-tråden, fryser
        # HELE loopet i block_s og tickeren står stille i hele vinduet.
        persist_roles.append(str(kw.get("role") or ""))
        ticks_at_block_entry.append(counter["ticks"])
        time.sleep(block_s)
        ticks_at_block_exit.append(counter["ticks"])
        return {"id": "m1"}

    monkeypatch.setattr(vr, "append_chat_message", _blocking_append)

    run = _make_run()

    async def _scenario() -> None:
        stop = asyncio.Event()

        async def _ticker() -> None:
            while not stop.is_set():
                await asyncio.sleep(0.02)
                counter["ticks"] += 1

        async def _drive() -> None:
            with vf.fault_injection(vf.FAULT_CLEAN_FAIL_BEFORE_DELTA):
                async for _chunk in vr._stream_visible_run(run):
                    pass
            stop.set()

        ticker = asyncio.create_task(_ticker())
        await _drive()
        await asyncio.sleep(0)
        ticker.cancel()
        try:
            await ticker
        except asyncio.CancelledError:
            pass

    asyncio.run(_scenario())

    assert "tool" in persist_roles, "tool-resultatet skal persisteres"
    assert ticks_at_block_entry and ticks_at_block_exit, \
        "blok-vinduet blev ikke målt"
    window_ticks = ticks_at_block_exit[0] - ticks_at_block_entry[0]
    # Et frosset loop ville give 0 ticks I VINDUET; et frit loop giver mange
    # (~block_s / 0.02). Tærskel lavt nok mod flakiness, højt nok til at fange
    # et inline-blok (som er ~0).
    assert window_ticks >= 5, (
        f"event-loopet var blokeret under tool-persistering: kun {window_ticks} "
        f"ticks i et {block_s}s blok-vindue → persisteringen kører inline på "
        f"loopet (skal offloades via to_thread)")


def test_tool_persist_runs_off_loop_thread(monkeypatch) -> None:
    """Direkte bevis: den blokerende append_chat_message kører IKKE på den tråd
    der driver _stream_visible_run's event-loop. (Inline-await ville køre den på
    loop-tråden; to_thread flytter den til en worker-tråd.)"""
    _patch_hermetic(monkeypatch)

    seen_thread_ids: list[int] = []

    def _record_thread_append(**_kw):
        seen_thread_ids.append(threading.get_ident())
        return {"id": "m1"}

    monkeypatch.setattr(vr, "append_chat_message", _record_thread_append)

    run = _make_run()
    loop_thread_id = {"id": 0}

    async def _drive() -> None:
        loop_thread_id["id"] = threading.get_ident()
        with vf.fault_injection(vf.FAULT_CLEAN_FAIL_BEFORE_DELTA):
            async for _chunk in vr._stream_visible_run(run):
                pass

    asyncio.run(_drive())

    assert seen_thread_ids, "append_chat_message blev aldrig kaldt"
    assert all(tid != loop_thread_id["id"] for tid in seen_thread_ids), (
        "tool-persistering kørte på event-loop-tråden — den skal offloades til "
        "en worker-tråd så _ping_loop ikke fryser")


def test_tool_persist_exception_propagates(monkeypatch) -> None:
    """Self-safe: et offloadet append_chat_message der RAISER må ikke sluges —
    fejlen skal ende observerbart (propageret op, eller som terminal fejl-frame,
    aldrig en tavs hængning)."""
    _patch_hermetic(monkeypatch)

    class _BoomError(RuntimeError):
        pass

    def _raising_append(**_kw):
        raise _BoomError("db-eksploderede")

    monkeypatch.setattr(vr, "append_chat_message", _raising_append)

    run = _make_run()

    async def _drive_collect() -> list[str]:
        out: list[str] = []
        with vf.fault_injection(vf.FAULT_CLEAN_FAIL_BEFORE_DELTA):
            async for chunk in vr._stream_visible_run(run):
                out.append(chunk)
        return out

    raised: Exception | None = None
    chunks: list[str] = []
    try:
        chunks = asyncio.run(_drive_collect())
    except _BoomError as exc:
        raised = exc

    if raised is not None:
        assert isinstance(raised, _BoomError)
        return

    joined = "".join(chunks)
    assert ("event: done" in joined) or ("event: error" in joined) or (
        "event: failed" in joined), (
        "en raisende persistering skal ende i en terminal-frame, ikke en "
        "tavs hængning")
