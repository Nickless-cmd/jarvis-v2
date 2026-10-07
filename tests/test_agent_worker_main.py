"""C6b: worker-entryen i-proces over en socketpair (sandbox-vejen er dækket af runner-testene)."""
from __future__ import annotations

import resource
import socket
import threading

import pytest

from core.services import agent_worker_main as W
from core.services import agent_worker_protocol as proto


@pytest.fixture
def harness():
    server, child = socket.socketpair()
    fd = child.detach()                       # main() overtager fd'en
    out = {}
    t = threading.Thread(target=lambda: out.setdefault("rc", W.main(["x", "--fd", str(fd)])), daemon=True)
    t.start()
    reader = proto.FrameReader(server)
    yield server, reader, out, t
    server.close()
    t.join(timeout=5)


def test_hello_job_model_call_and_result_in_loop_mode(harness):
    server, reader, out, t = harness
    hello = reader.read(5)
    assert hello["op"] == "hello" and hello["pid"] > 0
    proto.send(server, {"op": "job", "mode": "loop", "prompt": "P", "tools_payload": [], "provider": "p",
                        "model": "m", "max_rounds": 2, "synthesis_directive": "S"})
    call = reader.read(5)
    assert call["op"] == "model" and call["tools_mode"] == "none" and call["messages"] == [{"role": "user", "content": "P"}]
    assert "provider" not in call and "model" not in call            # workeren vaelger ikke model
    proto.send(server, {"id": call["id"], "ok": True, "result": {"text": "svar", "input_tokens": 2}})
    res = reader.read(5)
    t.join(timeout=5)
    assert res["op"] == "result" and res["outcome"]["final_text"] == "svar" and res["outcome"]["total_input"] == 2
    assert out["rc"] == 0


def test_text_mode_asks_the_server_for_the_servers_own_prompt(harness):
    server, reader, out, t = harness
    reader.read(5)
    proto.send(server, {"op": "job", "mode": "text", "prompt": "SERVERENS-PROMPT", "requires_tools": True})
    call = reader.read(5)
    assert call["op"] == "model_text" and call["requires_tools"] is True
    proto.send(server, {"id": call["id"], "ok": True, "result": {"text": "x"}})
    assert reader.read(5)["op"] == "result"


def test_a_refused_broker_call_becomes_a_loop_error_not_a_crash(harness):
    server, reader, out, t = harness
    reader.read(5)
    proto.send(server, {"op": "job", "mode": "loop", "prompt": "P", "tools_payload": [], "max_rounds": 1})
    call = reader.read(5)
    proto.send(server, {"id": call["id"], "ok": False, "error": "TOOL_NOT_ALLOWED: bash"})
    res = reader.read(5)
    assert res["op"] == "result" and res["outcome"]["error_str"] == "TOOL_NOT_ALLOWED: bash"


def test_a_missing_job_is_reported(harness):
    server, reader, out, t = harness
    reader.read(5)
    proto.send(server, {"op": "noget-andet"})
    assert reader.read(5) == {"op": "error", "error": "intet job modtaget"}
    t.join(timeout=5)
    assert out["rc"] == 2


def test_an_unexpected_exception_is_reported_with_exit_1(harness):
    server, reader, out, t = harness
    reader.read(5)
    proto.send(server, {"op": "job", "mode": "loop", "prompt": "P", "max_rounds": "ikke-et-tal"})
    res = reader.read(5)
    t.join(timeout=5)
    assert res["op"] == "error" and "ValueError" in res["error"] and out["rc"] == 1


def test_limits_can_only_be_tightened_never_raised(monkeypatch):
    seen = {}
    monkeypatch.setattr(resource, "getrlimit", lambda n: (1000, 5000))
    monkeypatch.setattr(resource, "setrlimit", lambda n, v: seen.setdefault(n, v))
    W._apply_limits({"address_space": 10 ** 9, "open_files": 100})
    assert seen[resource.RLIMIT_AS] == (5000, 5000)                  # kan ikke over hard graense
    assert seen[resource.RLIMIT_NOFILE] == (100, 5000)
    seen.clear()
    W._apply_limits({})
    assert seen == {}
