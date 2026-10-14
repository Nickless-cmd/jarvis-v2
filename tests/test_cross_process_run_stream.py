from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from fastapi import HTTPException


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_port(port: int, process: subprocess.Popen, timeout: float = 8.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"producer exited early with {process.returncode}")
        with socket.socket() as sock:
            sock.settimeout(0.1)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.05)
    raise AssertionError("producer port did not open")


async def _body_text(response) -> str:
    chunks: list[str] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
    return "".join(chunks)


async def _read_until(response, marker: str) -> str:
    chunks: list[str] = []
    iterator = response.body_iterator
    try:
        async for chunk in iterator:
            text = chunk.decode() if isinstance(chunk, bytes) else chunk
            chunks.append(text)
            if marker in "".join(chunks):
                break
    finally:
        await iterator.aclose()
    return "".join(chunks)


def test_runtime_owned_stream_survives_api_recreation_and_multiple_cursors(
    isolated_runtime,
    monkeypatch,
    tmp_path: Path,
) -> None:
    from apps.api.jarvis_api.routes import chat_run_streams as routes
    from core.runtime import state_store

    run_id = "run-cross-process"
    session_id = "session-cross-process"
    port = _free_port()
    shared_home = tmp_path / "shared-home"
    shared_state = shared_home / ".jarvis-v2" / "state"
    shared_state.mkdir(parents=True)
    monkeypatch.setattr(state_store, "_STATE_DIR", shared_state)
    monkeypatch.setenv("JARVIS_ENABLE_RUNTIME_SERVICES", "0")
    monkeypatch.setenv("JARVIS_RUNTIME_PORT", str(port))
    monkeypatch.setenv("JARVIS_INTERNAL_DISPATCH_TOKEN", "cross-process-test-token")
    monkeypatch.setattr(
        "core.identity.session_access.maa_tilgaa_session",
        lambda _session_id: True,
    )
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: type("Settings", (), {"server_authoritative_runs": True})(),
    )

    counter = tmp_path / "producer-count.txt"
    phase_one = tmp_path / "phase-one"
    proceed = tmp_path / "proceed"
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(shared_home),
            "JARVIS_ENABLE_RUNTIME_SERVICES": "1",
            "JARVIS_RUNTIME_PORT": str(port),
            "JARVIS_INTERNAL_DISPATCH_TOKEN": "cross-process-test-token",
            "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
        }
    )
    process = subprocess.Popen(
        [
            sys.executable,
            "tests/helpers/run_stream_producer.py",
            "--port",
            str(port),
            "--run-id",
            run_id,
            "--session-id",
            session_id,
            "--counter",
            str(counter),
            "--phase-one",
            str(phase_one),
            "--proceed",
            str(proceed),
        ],
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_port(port, process)
        deadline = time.time() + 3.0
        payload = {"session_ids": []}
        while time.time() < deadline:
            payload = routes.chat_active_runs()
            if session_id in payload["session_ids"]:
                break
            time.sleep(0.03)
        assert {
            "session_id": session_id,
            "run_id": run_id,
            "status": "working",
        } in payload["sessions"]

        async def _exercise() -> tuple[str, str, str]:
            full_response = await routes.chat_run_subscribe(run_id, 0)
            early_response = await routes.chat_run_subscribe(run_id, 0)
            full_task = asyncio.create_task(_body_text(full_response))
            early_text = await _read_until(early_response, "alpha")
            assert "message_start" in early_text and "alpha" in early_text

            deadline = time.monotonic() + 3.0
            while not phase_one.exists() and time.monotonic() < deadline:
                await asyncio.sleep(0.02)
            assert phase_one.exists()

            # Recreate the public API routing surface while the owner continues.
            from fastapi import FastAPI

            recreated = FastAPI()
            recreated.include_router(routes.router)
            assert any(
                route.path == "/chat/runs/{run_id}/subscribe"
                for route in recreated.routes
            )

            resumed_response = await routes.chat_run_subscribe(run_id, 2)
            resumed_task = asyncio.create_task(_body_text(resumed_response))
            proceed.write_text("go\n", encoding="utf-8")
            return early_text, await full_task, await resumed_task

        early, full, resumed = asyncio.run(_exercise())
        assert "alpha" in early
        assert "alpha" in full and "beta" in full
        assert full.count("message_stop") >= 1
        assert "alpha" not in resumed
        assert "beta" in resumed and "message_stop" in resumed
        assert counter.read_text(encoding="utf-8").splitlines() == ["1"]

        process.terminate()
        process.wait(timeout=5)
        with pytest.raises(HTTPException) as exc:
            asyncio.run(routes.chat_run_subscribe(run_id, 0))
        assert exc.value.status_code in {410, 503}
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
