"""Server-siden af en sandboxet agent-worker: spawn, broker og draeb (agent-contract-v1 C6b).

Spec: docs/specs/2026-10-07-agentorkestrering-og-subagenter.md (2, 12.1, 9, 11.1).

Agentens model-/vaerktoejsloekke koerer i en EGEN proces (``agent_worker_main`` i en bwrap-sandbox
uden netvaerk, uden ``~/.jarvis-v2`` og uden credentials). Serveren er broker:

* ``model``  - serveren kalder udbyderen med SIN model/provider og SIT vaerktoejsskema; workeren
  kan kun bede om "med" eller "uden" vaerktoejer, aldrig vaelge model eller udvide skemaet.
* ``tool``   - kun vaerktoejer i agentens allowlist, kun mens leasen er gaeldende, op til et
  loft; udfoeres gennem det samme guardede dispatch som foer (godkendelser, scoping).
* ``after_*`` - bogfoering, som kun serveren kan skrive.

Serveren draeber workerens processgruppe ved tabt lease, annullering, tidsloft eller brud paa
protokollen - det er det der goer ``interrupt_agent`` til et rigtigt stop. En doed worker tager
hverken soeskende eller serverens synlige run med sig. Kan sandboxen ikke etableres, koerer agenten
ikke (``SandboxUnavailable``): ingen stille tilbagegang til en usandboxet proces.
"""
from __future__ import annotations

import json
import logging
import os
import signal
import socket
import tempfile
import threading
import time
from typing import Any

from core.services import agent_worker_protocol as proto
from core.services.agent_sandbox import SandboxUnavailable, sandbox_usable, spawn_in_sandbox

logger = logging.getLogger(__name__)

WORKER_FLAG = "agent_worker.enabled"
DEFAULT_TIMEOUT_S = 4 * 3600.0           # standardbudgettet for aktiv koerselstid (§12.3)
MAX_TOOL_CALLS = 200
MAX_TOOL_OUTPUT = 200_000
MAX_PROMPT_MESSAGES_CHARS = 2_000_000
_LOG_LIMIT = 1024 * 1024
_TICK_S = 0.5
_CANCEL_POLL_S = 1.0
_HANDSHAKE_S = 60.0

_sandbox_ok: tuple[bool, str] | None = None
_sandbox_lock = threading.Lock()


class WorkerError(RuntimeError):
    """Workeren fejlede eller blev draebt. ``code`` er stabil."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.detail = code, detail


def worker_mode_enabled() -> bool:
    """Fail-closed: enhver laesefejl er ``False`` (= den eksisterende in-process-vej)."""
    try:
        from core.runtime.db_core import get_runtime_state_bool
        return bool(get_runtime_state_bool(WORKER_FLAG, False))
    except Exception:
        logger.warning("kunne ikke laese %s - worker-tilstand er slukket", WORKER_FLAG, exc_info=True)
        return False


def set_worker_mode(enabled: bool, *, role: str = "") -> bool:
    """At TAENDE er en ejerbeslutning; at slukke er altid tilladt."""
    if enabled and role != "owner":
        return worker_mode_enabled()
    from core.runtime.db_core import set_runtime_state_value
    set_runtime_state_value(WORKER_FLAG, bool(enabled))
    return bool(enabled)


def _require_sandbox() -> None:
    global _sandbox_ok
    with _sandbox_lock:
        if _sandbox_ok is None:
            _sandbox_ok = sandbox_usable()
        ok, why = _sandbox_ok
    if not ok:
        raise SandboxUnavailable(why or "sandbox ikke tilgaengelig")


def _kill_group(proc) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        logger.debug("worker-gruppen %s var allerede vaek", proc.pid)
    except Exception:
        logger.warning("kunne ikke draebe worker-gruppen %s", proc.pid, exc_info=True)
        proc.kill()
    try:
        proc.wait(timeout=10)
    except Exception:
        logger.warning("worker %s doede ikke efter SIGKILL", proc.pid, exc_info=True)


def _safe(obj: Any) -> Any:
    return json.loads(json.dumps(obj, ensure_ascii=False, default=str))


class _Broker:
    """Politik ved sømmen: hvad en worker maa faa serveren til at goere."""

    def __init__(self, *, agent: dict, run_id: str, prompt: str, tools_payload: list[dict],
                 provider: str, model: str, max_tool_calls: int, resume: dict | None = None) -> None:
        from core.services import agent_runtime_base as base

        self._base = base
        self.agent, self.run_id, self.prompt = agent, run_id, prompt
        self.tools_payload, self.provider, self.model = tools_payload, provider, model
        self.allowed = {str((t.get("function") or {}).get("name") or "") for t in tools_payload} - {""}
        self.max_tool_calls = max_tool_calls
        self.tool_calls = 0
        self._started: set[str] = set()
        self._io = base._InProcessLoopIO(agent=agent, run_id=run_id, resume=resume)
        self.last_text_result: dict[str, Any] | None = None

    def handle(self, msg: dict[str, Any]) -> Any:
        op = msg.get("op")
        if op == "model":
            return self._model(msg)
        if op == "model_text":
            return self._model_text(msg)
        if op == "tool":
            return self._tool(msg)
        if op == "after_tool":
            tc = msg.get("tc") or {}
            if str(tc.get("id") or "") not in self._started:
                raise WorkerError("PROTOCOL", "after_tool for et kald der ikke er udfoert")
            self._io.after_tool(tc, str(msg.get("tool_out") or ""))
            return None
        if op == "after_round":
            self._io.after_round(int(msg.get("rounds") or 0),
                                 [{"function": {"name": n}} for n in (msg.get("tool_names") or [])])
            return None
        raise WorkerError("PROTOCOL", f"ukendt op {op!r}")

    def _model(self, msg: dict[str, Any]) -> dict[str, Any]:
        messages = msg.get("messages")
        if not isinstance(messages, list) or not all(isinstance(m, dict) for m in messages):
            raise WorkerError("PROTOCOL", "messages er ugyldige")
        if len(json.dumps(messages, default=str)) > MAX_PROMPT_MESSAGES_CHARS:
            raise WorkerError("PROTOCOL", "messages over graensen")
        tools = self.tools_payload if msg.get("tools_mode") == "full" else []
        from core.services.agent_model_router import call_agent_model
        try:
            res = call_agent_model(
                agent=self.agent, tools_executed=self.tool_calls > 0, facade=self._base._facade(),
                provider=self.provider, model=self.model,
                requires_tools=bool(msg.get("requires_tools")) and bool(tools),
                messages=messages, tools=tools, lane="agent", run_id=self._io.run_id)
        finally:
            self._adopt_live_run()
        return _safe(res)

    def _adopt_live_run(self) -> None:
        """G: et failover har afloest runnet - bogfoering og logs foelger det nye forsoeg."""
        from core.runtime.db_agent_attempts import live_run_id
        self._io._run_id = self.run_id = live_run_id(self._io.run_id)

    def _model_text(self, msg: dict[str, Any]) -> dict[str, Any]:
        # prompten er serverens egen - workerens "message" ignoreres bevidst
        from core.services.agent_model_router import call_agent_model
        try:
            res = call_agent_model(
                agent=self.agent, tools_executed=self.tool_calls > 0, facade=self._base._facade(),
                message=self.prompt, provider=self.provider, model=self.model,
                requires_tools=bool(msg.get("requires_tools")), lane="agent", run_id=self._io.run_id)
        finally:
            self._adopt_live_run()
        self.last_text_result = _safe(res)
        return self.last_text_result

    def _tool(self, msg: dict[str, Any]) -> str:
        tc = msg.get("tc")
        name = str(((tc or {}).get("function") or {}).get("name") or "") if isinstance(tc, dict) else ""
        if not name or name not in self.allowed:
            raise WorkerError("TOOL_NOT_ALLOWED", f"{name or '(intet navn)'} er ikke i agentens skema")
        if self.tool_calls >= self.max_tool_calls:
            raise WorkerError("CAPACITY", f"vaerktoejsloft {self.max_tool_calls} naaet")
        self.tool_calls += 1
        self._started.add(str(tc.get("id") or ""))
        from core.services.agent_bridge import BridgeHalt
        from core.services.agent_loop_core import ApprovalPending
        try:
            out = self._io.tool(tc)
        except ApprovalPending as ap:
            # Workeren skal parkere: den faar approval-id'et og stopper sin loekke ved checkpointen.
            raise WorkerError("APPROVAL_PENDING", f"{ap.approval_id}:{ap.tool_call_id}") from ap
        except BridgeHalt as halt:
            # Uafgjort bro-kald: workeren stoppes; runnet er sat i outcome_unknown af broen.
            raise WorkerError("OUTCOME_UNKNOWN", str(halt)) from halt
        return out if len(out) <= MAX_TOOL_OUTPUT else out[:MAX_TOOL_OUTPUT] + "\n[afkortet af brokeren]"


def _agent_cancelled(agent_id: str) -> bool:
    try:
        from core.runtime.db_agent_runtime import get_agent_registry_entry
        return str((get_agent_registry_entry(agent_id) or {}).get("status") or "") in {"cancelled", "expired"}
    except Exception:
        logger.warning("kunne ikke laese agentstatus for %s - antages ikke annulleret", agent_id, exc_info=True)
        return False


def _save_logs(agent: dict, run_id: str, out_path: str, err_path: str) -> None:
    try:
        from core.runtime import db_agent_artifacts as art
        from core.runtime.db_agent_contract import open_assignment_for_agent
        a = open_assignment_for_agent(str(agent.get("agent_id") or ""))
        if a is None:
            return
        for name, path in (("stdout.log", out_path), ("stderr.log", err_path)):
            with open(path, "rb") as fh:
                data = fh.read(_LOG_LIMIT)
            if data:
                art.write_artifact(agent_id=str(agent["agent_id"]), run_id=run_id, name=name, data=data,
                                   assignment_id=a["assignment_id"], owner_user_id=a["owner_user_id"],
                                   status="partial" if len(data) >= _LOG_LIMIT else "complete")
    except Exception:
        logger.warning("worker-logs kunne ikke gemmes for %s", run_id, exc_info=True)


def run_agent_in_worker(
    *, agent: dict[str, Any], prompt: str, requires_tools: bool, run_id: str,
    tools_payload: list[dict] | None = None, timeout_s: float = DEFAULT_TIMEOUT_S,
    max_tool_calls: int = MAX_TOOL_CALLS, address_space: int = 2 * 1024 ** 3,
    worker_files: dict[str, str] | None = None, worker_command: list[str] | None = None,
    resume: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Koer agentens tur i en sandboxet worker og returner resultatet i SAMME form som in-process-vejen."""
    from core.runtime.db_agent_lease import scope_is_current
    from core.services import agent_runtime_base as base
    import sys

    _require_sandbox()
    tools_payload = list(tools_payload or [])
    provider, model = str(agent.get("provider") or ""), str(agent.get("model") or "")
    scout = (str(agent.get("role") or "") == "researcher"
             and str(agent.get("tool_policy") or "") in {"read-only-runtime", "read-only-workstation"})
    broker = _Broker(agent=agent, run_id=run_id, prompt=prompt, tools_payload=tools_payload,
                     provider=provider, model=model, max_tool_calls=max_tool_calls, resume=resume)
    parent, child = socket.socketpair()
    os.set_inheritable(child.fileno(), True)
    out_f = tempfile.NamedTemporaryFile(prefix="agent-worker-out-", delete=False)
    err_f = tempfile.NamedTemporaryFile(prefix="agent-worker-err-", delete=False)
    cmd = ([c.replace("{fd}", str(child.fileno())) for c in worker_command] if worker_command
           else [sys.executable, "/worker/agent_worker_main.py", "--fd", str(child.fileno())])
    proc = None
    try:
        proc = spawn_in_sandbox(cmd, pass_fds=(child.fileno(),), stdout=out_f, stderr=err_f,
                                address_space=address_space + 512 * 1024 ** 2,
                                cpu_seconds=int(timeout_s) + 60, worker_files=worker_files)
        child.close()
        reader = proto.FrameReader(parent)
        hello = reader.read(_HANDSHAKE_S)
        if not hello or hello.get("op") != "hello":
            raise WorkerError("PROTOCOL", "ingen hello fra workeren")
        ns_pid = int(hello.get("pid") or 0)       # pid INDE i workerens eget pid-namespace
        proto.send(parent, {"op": "job", "mode": "loop" if tools_payload else "text", "prompt": prompt,
                            "tools_payload": tools_payload, "requires_tools": bool(requires_tools),
                            "provider": provider, "model": model, "scout": scout,
                            "max_rounds": base._AGENT_TOOL_LOOP_MAX_ROUNDS,
                            "synthesis_directive": base._AGENT_SYNTHESIS_DIRECTIVE,
                            "limits": {"address_space": address_space}, "resume": resume})
        started, last_cancel = time.monotonic(), 0.0
        outcome: dict[str, Any] | None = None
        while outcome is None:
            if not scope_is_current():
                _kill_group(proc)
                raise WorkerError("LEASE_LOST", "workerens lease er ikke laengere gaeldende")
            now = time.monotonic()
            if now - started > timeout_s:
                _kill_group(proc)
                raise WorkerError("TIMEOUT", f"over {timeout_s:.0f}s")
            if now - last_cancel > _CANCEL_POLL_S:
                last_cancel = now
                if _agent_cancelled(str(agent.get("agent_id") or "")):
                    _kill_group(proc)
                    raise WorkerError("CANCELLED", "agenten blev annulleret")
            try:
                msg = reader.read(_TICK_S)
            except EOFError:
                proc.wait(timeout=10)
                raise WorkerError("WORKER_DIED", f"workeren lukkede forbindelsen (exit {proc.returncode})")
            except proto.ProtocolError as exc:
                _kill_group(proc)
                raise WorkerError("PROTOCOL", str(exc)) from exc
            if msg is None:
                if proc.poll() is not None:
                    raise WorkerError("WORKER_DIED", f"workeren er afsluttet (exit {proc.returncode})")
                continue
            op = msg.get("op")
            if op == "result":
                outcome = msg.get("outcome") or {}
            elif op == "error":
                raise WorkerError("WORKER_ERROR", str(msg.get("error") or "")[:400])
            else:
                reply: dict[str, Any] = {"id": msg.get("id")}
                try:
                    reply.update(ok=True, result=broker.handle(msg))
                except WorkerError as exc:
                    reply.update(ok=False, error=str(exc))
                except Exception as exc:                       # vaerktoej-/udbyderfejl: workeren faar den, loekken afgoer
                    logger.warning("broker-kald %s fejlede", op, exc_info=True)
                    reply.update(ok=False, error=f"{type(exc).__name__}: {exc}"[:400])
                proto.send(parent, reply)
        proc.wait(timeout=30)
        if broker.last_text_result is not None and not tools_payload:
            result = dict(broker.last_text_result)
        else:
            result = base._loop_result(outcome, scout=scout, provider=provider, model=model)
        result["worker_pid"] = proc.pid           # vaertens pid for workerens proces(gruppe)
        result["worker_ns_pid"] = ns_pid
        return result
    finally:
        if proc is not None:
            _kill_group(proc)
        for s in (parent, child):
            try:
                s.close()
            except Exception:
                logger.debug("socket kunne ikke lukkes", exc_info=True)
        out_f.close()
        err_f.close()
        _save_logs(agent, broker.run_id, out_f.name, err_f.name)   # G: det forsoeg der koerte til sidst
        for p in (out_f.name, err_f.name):
            try:
                os.unlink(p)
            except OSError:
                logger.debug("kunne ikke slette %s", p, exc_info=True)
