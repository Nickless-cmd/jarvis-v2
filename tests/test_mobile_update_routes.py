"""Tests for mobil auto-updater routes (/mobile/latest + /mobile/download)."""
from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

import apps.api.jarvis_api.routes.mobile_update as mod


def _client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    # auth: lad enhver kalder være en gyldig bruger
    monkeypatch.setattr(mod, "_current_user", lambda: "1246415163603816499")
    app = FastAPI()
    app.include_router(mod.router)
    return TestClient(app)


def test_latest_empty_when_no_manifest(monkeypatch, tmp_path) -> None:
    c = _client(monkeypatch, tmp_path)
    r = c.get("/mobile/latest")
    assert r.status_code == 200
    assert r.json() == {}


def test_latest_returns_manifest(monkeypatch, tmp_path) -> None:
    mobile = tmp_path / "mobile"
    mobile.mkdir(parents=True)
    (mobile / "latest.json").write_text(
        json.dumps(
            {
                "version": "0.1.29",
                "version_code": 30,
                "notes": "Test-noter",
                "filename": "jarvis-mobile-30.apk",
            }
        ),
        encoding="utf-8",
    )
    c = _client(monkeypatch, tmp_path)
    r = c.get("/mobile/latest")
    assert r.status_code == 200
    body = r.json()
    assert body["version_code"] == 30
    assert body["filename"] == "jarvis-mobile-30.apk"


def test_latest_unauthenticated(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setattr(mod, "_current_user", lambda: None)
    app = FastAPI()
    app.include_router(mod.router)
    c = TestClient(app)
    assert c.get("/mobile/latest").json() == {}


def test_download_serves_apk(monkeypatch, tmp_path) -> None:
    mobile = tmp_path / "mobile"
    mobile.mkdir(parents=True)
    (mobile / "latest.json").write_text(
        json.dumps(
            {"version": "0.1.29", "version_code": 30, "notes": "", "filename": "jarvis-mobile-30.apk"}
        ),
        encoding="utf-8",
    )
    (mobile / "jarvis-mobile-30.apk").write_bytes(b"PK\x03\x04 fake apk bytes")
    c = _client(monkeypatch, tmp_path)
    r = c.get("/mobile/download")
    assert r.status_code == 200
    assert r.content == b"PK\x03\x04 fake apk bytes"
    assert r.headers["content-type"] == "application/vnd.android.package-archive"


def test_download_404_when_missing(monkeypatch, tmp_path) -> None:
    mobile = tmp_path / "mobile"
    mobile.mkdir(parents=True)
    (mobile / "latest.json").write_text(
        json.dumps(
            {"version": "0.1.29", "version_code": 30, "notes": "", "filename": "jarvis-mobile-30.apk"}
        ),
        encoding="utf-8",
    )
    # APK-filen mangler bevidst
    c = _client(monkeypatch, tmp_path)
    assert c.get("/mobile/download").status_code == 404


def test_download_404_when_no_manifest(monkeypatch, tmp_path) -> None:
    c = _client(monkeypatch, tmp_path)
    assert c.get("/mobile/download").status_code == 404


def test_download_unauthenticated(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setattr(mod, "_current_user", lambda: None)
    app = FastAPI()
    app.include_router(mod.router)
    c = TestClient(app)
    assert c.get("/mobile/download").status_code == 401
