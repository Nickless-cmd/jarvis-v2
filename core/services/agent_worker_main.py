"""Entry for en sandboxet agent-worker (agent-contract-v1 C6b).

Koerer INDE i bwrap-sandboxen med KUN standardbiblioteket: ingen DB, ingen credentials, intet
netvaerk. Workeren ejer selve loekken (``agent_loop_core.run_tool_loop``); al I/O - modelkald,
vaerktoejer, bogfoering - gaar som RPC over den arvede socket til serverens broker, som haandhaever
policy. Workeren kan hverken vaelge model, udvide vaerktoejsskemaet eller kalde andre vaerktoejer
end brokeren tillader.
"""
from __future__ import annotations

import os
import resource
import socket
import sys
import traceback
from typing import Any

try:                                   # i repoet
    from core.services.agent_loop_core import ApprovalPending, run_tool_loop
    from core.services.agent_worker_protocol import FrameReader, send
except ImportError:                    # i sandboxen: filerne ligger side om side i /worker
    from agent_loop_core import ApprovalPending, run_tool_loop
    from agent_worker_protocol import FrameReader, send

REPLY_TIMEOUT_S = 6 * 3600.0


class RpcIO:
    """LoopIO der sender hvert kald til brokeren og venter paa svaret."""

    def __init__(self, sock: socket.socket, reader: FrameReader) -> None:
        self._sock, self._reader, self._n = sock, reader, 0

    def call(self, op: str, **payload: Any) -> Any:
        self._n += 1
        send(self._sock, {"id": self._n, "op": op, **payload})
        while True:
            msg = self._reader.read(REPLY_TIMEOUT_S)
            if msg is None:
                raise TimeoutError(f"intet svar paa {op}")
            if msg.get("id") != self._n:
                continue
            if not msg.get("ok"):
                raise RuntimeError(str(msg.get("error") or "broker afviste kaldet"))
            return msg.get("result")

    # LoopIO
    def model(self, *, messages, tools, requires_tools, provider, model):
        # provider/model/tools vaelges af serveren; workeren oplyser kun om afslutnings-kaldet er vaerktoejsfrit
        return self.call("model", messages=messages, tools_mode="full" if tools else "none",
                         requires_tools=bool(requires_tools))

    def tool(self, tc):
        try:
            return str(self.call("tool", tc=tc))
        except RuntimeError as exc:
            msg = str(exc)
            if msg.startswith("APPROVAL_PENDING: "):               # brokeren: kaldet kraever en godkendelse
                approval_id, _, tc_id = msg[len("APPROVAL_PENDING: "):].partition(":")
                raise ApprovalPending(approval_id, tc_id) from exc
            raise

    def after_tool(self, tc, tool_out):
        self.call("after_tool", tc=tc, tool_out=tool_out)

    def after_round(self, rounds, tool_calls):
        self.call("after_round", rounds=rounds,
                  tool_names=[str((t.get("function") or {}).get("name") or "") for t in tool_calls])


def _apply_limits(limits: dict[str, Any]) -> None:
    """Kun stramninger (en soft-graense under den arvede hard-graense); aldrig en haevning."""
    for name, key in (("RLIMIT_AS", "address_space"), ("RLIMIT_NOFILE", "open_files")):
        value = limits.get(key)
        if value:
            _soft, hard = resource.getrlimit(getattr(resource, name))
            new = int(value) if hard == resource.RLIM_INFINITY else min(int(value), hard)
            resource.setrlimit(getattr(resource, name), (new, hard))


def main(argv: list[str]) -> int:
    fd = int(argv[argv.index("--fd") + 1])
    sock = socket.socket(fileno=fd)
    reader = FrameReader(sock)
    send(sock, {"op": "hello", "pid": os.getpid(), "uid": os.getuid()})
    job = reader.read(60.0)
    if not job or job.get("op") != "job":
        send(sock, {"op": "error", "error": "intet job modtaget"})
        return 2
    try:
        _apply_limits(job.get("limits") or {})
        io = RpcIO(sock, reader)
        if job.get("mode") == "text":
            io.call("model_text", message=job["prompt"], requires_tools=bool(job.get("requires_tools")))
            outcome: dict[str, Any] = {}
        else:
            outcome = run_tool_loop(
                io, prompt=job["prompt"], tools_payload=job.get("tools_payload") or [],
                requires_tools=bool(job.get("requires_tools")), provider=job.get("provider", ""),
                model=job.get("model", ""), scout=bool(job.get("scout")),
                max_rounds=int(job.get("max_rounds") or 8),
                synthesis_directive=str(job.get("synthesis_directive") or ""),
                resume=job.get("resume") or None)
        send(sock, {"op": "result", "outcome": outcome})
        return 0
    except BaseException as exc:                       # noqa: BLE001 - alt rapporteres til serveren
        try:
            send(sock, {"op": "error", "error": f"{type(exc).__name__}: {exc}"[:400],
                        "trace": traceback.format_exc()[-1500:]})
        finally:
            return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
