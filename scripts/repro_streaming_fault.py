#!/usr/bin/env python
"""Manuel repro af de tre streaming-fejl-former (Fase 0-harness).

Genbruger PRÆCIS samme fejl-injektor som ``tests/test_streaming_fault_injection.py``
(``core.services.visible_followup.inject_fault``). Kører ÉT minimalt agentisk
followup-run gennem det ægte ``_stream_visible_run``-spor med en injiceret fejl og
printer det observerede udfald (terminal-status, persisteret tekst, central-nerver).

Brug under Fase 1 til at SE et fix flippe baseline: kør FØR og EFTER retry-flaget,
samme kommando, og se status gå fra ``interrupted`` → (forhåbentlig) ``completed``.

    conda activate ai
    python scripts/repro_streaming_fault.py partial_deltas_then_drop
    python scripts/repro_streaming_fault.py clean_fail_before_delta
    python scripts/repro_streaming_fault.py http_400_overflow

Hermetisk: ingen netværk — injektoren erstatter provider-kaldet, og de tunge
baggrunds-daemons (memory/private-layer/kost) er no-op'et som i testen.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Gør repoet importérbart uanset cwd (standalone-script).
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import core.services.ollama_visible_prompt as ovp
import core.services.visible_runs as vr
from core.services import followup_observer as fo
from core.services import visible_followup as vf
from core.services.visible_model import (
    VisibleModelResult,
    VisibleModelStreamDone,
    VisibleModelToolCalls,
)

_SHAPES = (
    vf.FAULT_CLEAN_FAIL_BEFORE_DELTA,
    vf.FAULT_PARTIAL_DELTAS_THEN_DROP,
    vf.FAULT_HTTP_400_OVERFLOW,
)


def _install_hermetic_mocks(persisted: list[str], nerves: list[tuple[str, dict]]) -> None:
    def _fsm(**_k):
        yield VisibleModelToolCalls(tool_calls=[{
            "id": "c1", "type": "function",
            "function": {"name": "read_file", "arguments": '{"path": "x"}'},
        }])
        yield VisibleModelStreamDone(result=VisibleModelResult(
            text="", input_tokens=10, output_tokens=5, cost_usd=0.0))

    vr.stream_visible_model = _fsm
    vr._execute_simple_tool_calls = lambda _tc, **_k: [{
        "tool_name": "read_file", "tool_call_id": "c1", "status": "completed",
        "arguments": {"path": "x"}, "result_text": "file-contents", "result": {"ok": True},
    }]
    vr._build_visible_input = lambda *a, **k: [{"role": "user", "content": "hej"}]
    vr._visible_run_cancelled = lambda _r: False
    ovp.serialize_ollama_chat_messages = lambda x: list(x)
    vr._persist_session_assistant_message = lambda _r, t, **_k: persisted.append(t)
    vr.append_chat_message = lambda **_k: {"id": "m1"}
    vr.record_cost = lambda **_k: None
    vr.event_bus.publish = lambda *a, **k: None
    vr._run_memory_postprocess = lambda *a, **k: None
    vr._track_runtime_candidates = lambda *a, **k: None
    vr.write_private_terminal_layers = lambda *a, **k: None
    fo._observe = lambda nerve, run_id, **d: nerves.append((nerve, d))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("shape", choices=_SHAPES)
    ap.add_argument("--raise-drop", action="store_true",
                    help="for partial_deltas_then_drop: drop som rå exception "
                         "(default) vs yielded FollowupFailed")
    ap.add_argument("--yield-drop", action="store_true",
                    help="for partial_deltas_then_drop: drop som yielded FollowupFailed")
    args = ap.parse_args()

    persisted: list[str] = []
    nerves: list[tuple[str, dict]] = []
    _install_hermetic_mocks(persisted, nerves)

    inject_kwargs: dict = {}
    if args.shape == vf.FAULT_PARTIAL_DELTAS_THEN_DROP:
        inject_kwargs["drop_as_exception"] = not args.yield_drop

    run = vr.VisibleRun(
        run_id=f"repro-{args.shape}", lane="primary", provider="deepseek",
        model="deepseek-v4-flash", user_message="hej", session_id="repro-s")

    async def _go() -> list[str]:
        out: list[str] = []
        with vf.fault_injection(args.shape, **inject_kwargs):
            async for chunk in vr._stream_visible_run(run):
                out.append(chunk)
        return out

    chunks = asyncio.run(_go())

    status = ""
    for c in chunks:
        if "event: done" not in c:
            continue
        for line in c.splitlines():
            if line.startswith("data: "):
                try:
                    status = str(json.loads(line[6:]).get("status") or "")
                except Exception:
                    pass

    deltas = [c for c in chunks if "event: delta" in c and '"delta"' in c]
    print(f"\n=== {args.shape} ===")
    print(f"  retry-flag (AGENTIC_ROUND_RETRY_ENABLED): {vf.agentic_round_retry_enabled()}")
    print(f"  terminal status      : {status!r}")
    print(f"  delta events streamed: {len(deltas)}")
    print(f"  persisted (first 160): {(persisted[0][:160] if persisted else None)!r}")
    print(f"  central nerves fired : {[n for n, _ in nerves]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
