"""Fail-open synlighed for upload malware-scan (audit 2026-07-04).

Kaster check_upload springes scannen OVER og uploaden tillades — en SECURITY fail-open.
Den MÅ ikke være tavs: en incident skal flagges, mens fail-open-adfærden (upload igennem)
bevares, og hele stien er self-safe.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.jarvis_api.routes.attachments import router, _registry

app = FastAPI()
app.include_router(router)
client = TestClient(app)

FAKE_SESSION = "chat-scansession123"


@pytest.fixture(autouse=True)
def _harness(tmp_path, monkeypatch):
    _registry.clear()
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.attachments.get_chat_session",
        lambda sid: {"id": sid} if sid == FAKE_SESSION else None,
    )
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.attachments._UPLOAD_DIR",
        tmp_path / "uploads",
    )
    yield
    _registry.clear()


def test_scan_raises_records_incident_and_allows_upload(monkeypatch):
    def _boom(_path):
        raise RuntimeError("ClamAV krasjede")

    monkeypatch.setattr("core.services.gate_execution.check_upload", _boom)

    flagged: list[dict] = []
    monkeypatch.setattr(
        "core.runtime.db_central_incidents.record_central_incident",
        lambda **k: flagged.append(k))

    data = b"\x89PNG\r\n" + b"x" * 100
    resp = client.post(
        "/attachments/upload",
        data={"session_id": FAKE_SESSION},
        files={"file": ("photo.png", io.BytesIO(data), "image/png")},
    )

    # Fail-open adfærd uændret: uploaden tillades trods scan-fejl.
    assert resp.status_code == 200
    assert len(flagged) == 1
    assert flagged[0]["cluster"] == "execution"
    assert flagged[0]["nerve"] == "upload_scan"
    assert flagged[0]["kind"] == "fail_open"


def test_scan_incident_failure_is_self_safe(monkeypatch):
    monkeypatch.setattr(
        "core.services.gate_execution.check_upload",
        lambda _p: (_ for _ in ()).throw(RuntimeError("scan nede")))
    monkeypatch.setattr(
        "core.runtime.db_central_incidents.record_central_incident",
        lambda **k: (_ for _ in ()).throw(RuntimeError("incident nede")))

    data = b"\x89PNG\r\n" + b"x" * 100
    resp = client.post(
        "/attachments/upload",
        data={"session_id": FAKE_SESSION},
        files={"file": ("photo.png", io.BytesIO(data), "image/png")},
    )
    # Upload lykkes stadig trods incident-fejl (self-safe).
    assert resp.status_code == 200
