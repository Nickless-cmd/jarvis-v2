from __future__ import annotations

import json
import threading
import time
from types import SimpleNamespace

from core.tools import bash_session as bs


def test_live_frame_send_drops_when_socket_would_block():
    class StalledSocket:
        def send(self, _data, _flags=0):
            raise BlockingIOError

    assert bs._send_live_nonblocking(
        StalledSocket(), {"type": "output_delta", "chunk": "x"}
    ) is False


class FakeSocket:
    def __init__(self, chunks: list[bytes]):
        self.chunks = iter(chunks)
        self.sent = b""

    def settimeout(self, _timeout):
        pass

    def connect(self, _path):
        pass

    def sendall(self, data):
        self.sent += data

    def recv(self, _size):
        return next(self.chunks, b"")

    def close(self):
        pass


def test_client_accepts_delta_frames_then_terminal_result(monkeypatch):
    wire = (
        b'{"type":"output_delta","stream":"combined","seq":1,"chunk":"hej"}\n'
        b'{"type":"result","status":"ok","exit_code":0,"output":"hej"}\n'
    )
    fake = FakeSocket([wire[:23], wire[23:]])
    monkeypatch.setattr(bs, "_ensure_daemon_running", lambda: True)
    monkeypatch.setattr(bs.socket, "socket", lambda *_args: fake)
    seen = []

    result = bs._client_call_once(
        {"op": "run"}, on_output=lambda **delta: seen.append(delta)
    )

    assert seen == [{"stream": "combined", "seq": 1, "chunk": "hej"}]
    assert result == {"status": "ok", "exit_code": 0, "output": "hej"}


def test_client_accepts_legacy_one_line_result(monkeypatch):
    fake = FakeSocket([b'{"status":"ok","exit_code":0,"output":"legacy"}\n'])
    monkeypatch.setattr(bs, "_ensure_daemon_running", lambda: True)
    monkeypatch.setattr(bs.socket, "socket", lambda *_args: fake)
    assert bs._client_call_once({"op": "run"})["output"] == "legacy"


def test_session_streams_split_marker_and_split_utf8_without_leaking_marker(monkeypatch):
    session = bs._Session.__new__(bs._Session)
    session.session_id = "test"
    session.lock = threading.Lock()
    session.last_used = time.time()
    session.running_command = ""
    session.fd = 12
    session.pid = 34
    session._drain_pending = lambda timeout: None
    session.alive = lambda: True
    monkeypatch.setattr(bs.uuid, "uuid4", lambda: SimpleNamespace(hex="fixed"))
    monkeypatch.setattr(bs.os, "write", lambda *_args: 1)
    monkeypatch.setattr(bs.select, "select", lambda *_args: ([12], [], []))
    chunks = iter([b"h\xc3", b"\xa6j __JAR", b"VIS_END_fixed__ 0\n"])
    monkeypatch.setattr(bs.os, "read", lambda *_args: next(chunks))
    seen = []

    result = session.run("printf hej", on_output=seen.append)

    assert "".join(seen) == "hæj "
    assert "JARVIS_END" not in "".join(seen)
    assert result["output"] == "hæj "
    assert result["exit_code"] == 0


def test_second_call_reports_time_waiting_for_session_lock():
    session = bs._Session("stream-lock-test")
    first = threading.Thread(target=lambda: session.run("sleep 0.25"))
    first.start()
    time.sleep(0.05)
    try:
        result = session.run("printf queued")
        first.join(timeout=2)
        assert result["output"] == "queued"
        assert result["_timing"]["dispatch_to_lock_ms"] >= 100
    finally:
        session.close()
