"""Regression: en provider UDEN followup-stoette maa ikke faelde turen.

ROD-AARSAK (maalt 12. sep 2026, run=autonomous-4b4f517d, provider=alibaba,
supports_followup=False):

`_a_truncated` blev KUN bundet pr. forsoeg INDE i agentic-loopet. To tidlige
udgange i loopets FOERSTE runde — ``provider-not-supported`` og ``shutdown`` —
``break``er FOER den binding. Laesningen EFTER loopet
(``if _a_truncated and _agentic_loop_exit_reason == "completed"``) stod derfor
paa en ubundet variabel → ``UnboundLocalError`` → hele turen doede med
"visible-run unhandled exception" i stedet for at blive afsluttet.

Fixet hoister initialiseringen til FOER loopet (ved siden af
``_agentic_loop_exit_reason``). Denne test driver det AEGTE
``_stream_visible_run`` hermetisk (ingen DB/netvaerk) med en provider der ikke
er i ``supported_followup_providers``, og kraever at turen afsluttes rent.
Uden fixet kaster den ``UnboundLocalError``.
"""
from __future__ import annotations

import asyncio

import core.services.ollama_visible_prompt as ovp
import core.services.visible_followup as vf
import core.services.visible_runs as vr
from core.services import followup_observer as fo
from core.services.visible_model import (
    VisibleModelResult,
    VisibleModelStreamDone,
    VisibleModelToolCalls,
)


def _patch_hermetic(monkeypatch) -> None:
    """Mock first-pass-model + tools + tunge baggrunds-daemons → ingen DB/net."""

    def _fake_stream_model(**_kw):
        # Ét tool-kald, saa stream-done med TOM prosa → first-pass-tool-stien
        # eksekveres (samme form som test_visible_runs_loop_not_blocked).
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


def test_provider_uden_followup_afslutter_turen_rent(monkeypatch) -> None:
    """Turen skal afsluttes — ikke kaste — naar provideren ikke kan followup.

    Uden fixet rammer loopet ``provider-not-supported``-breaket FOER
    ``_a_truncated`` blev bundet, og laesningen efter loopet kaster
    ``UnboundLocalError: cannot access local variable '_a_truncated'``."""
    _patch_hermetic(monkeypatch)

    # Provideren er IKKE i supported_followup_providers → loopet bremser ved
    # `provider-not-supported` FOER per-forsoeg-initialiseringen.
    monkeypatch.setattr(vf, "supported_followup_providers", lambda: ())

    run = vr.VisibleRun(
        run_id="visible-provider-not-supported",
        lane="primary",
        provider="alibaba",
        model="qwen-turbo",
        user_message="hej",
        session_id="s-provider-not-supported")

    async def _drive() -> list[str]:
        out: list[str] = []
        async for chunk in vr._stream_visible_run(run):
            out.append(chunk)
        return out

    # Uden fixet propagerer UnboundLocalError herfra.
    chunks = asyncio.run(_drive())

    joined = "".join(chunks)
    # Frame-navne kan IKKE skelne: fejl-stien lukker ogsaa med trace+done.
    # Det goer udfaldet. Den ydre handler (~5760) kalder
    # set_last_visible_run_outcome(status="failed") naar UnboundLocalError
    # fanges; en ren afslutning giver "completed". Maalt 12. sep 2026: uden
    # fixet fejler denne assertion, med fixet bestaar den.
    outcome = vr.get_last_visible_run_outcome() or {}
    assert outcome.get("status") == "completed", (
        f"turen fejlede i stedet for at afsluttes: {outcome} | frames: {joined[-300:]}")
