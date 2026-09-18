from __future__ import annotations

import json

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


@pytest.fixture
def owner_client(isolated_runtime, monkeypatch):
    import apps.api.jarvis_api.routes.cheap_lane_control as routes

    monkeypatch.setattr(routes, "_require_owner", lambda: None)
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


@pytest.fixture
def non_owner_client(isolated_runtime, monkeypatch):
    import apps.api.jarvis_api.routes.cheap_lane_control as routes

    def deny():
        raise HTTPException(status_code=403, detail="owner only")

    monkeypatch.setattr(routes, "_require_owner", deny)
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


@pytest.fixture
def seeded_calls():
    from core.runtime.db_cheap_provider import record_cheap_provider_invocation

    rows = []
    for provider, status in (("groq", "failed"), ("groq", "failed"),
                             ("mistral", "completed")):
        rows.append(record_cheap_provider_invocation(
            provider=provider, model="small", status=status,
            input_tokens=10, output_tokens=5,
            error_code="rate-limited" if status == "failed" else "",
        ))
    return rows


def test_dashboard_requires_owner(non_owner_client):
    assert non_owner_client.get("/mc/cheap-lane/dashboard").status_code == 403


def test_logs_are_cursor_paginated_and_filterable(owner_client, seeded_calls):
    response = owner_client.get(
        "/mc/cheap-lane/logs?provider=groq&status=failed&limit=1"
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["next_cursor"]
    second = owner_client.get(
        "/mc/cheap-lane/logs?provider=groq&status=failed&limit=1"
        f"&cursor={response.json()['next_cursor']}"
    )
    assert len(second.json()["items"]) == 1
    assert second.json()["items"][0]["invocation_id"] != response.json()["items"][0]["invocation_id"]


def test_log_detail_404_and_existing(owner_client, seeded_calls):
    assert owner_client.get("/mc/cheap-lane/logs/missing").status_code == 404
    response = owner_client.get(
        f"/mc/cheap-lane/logs/{seeded_calls[0]['invocation_id']}"
    )
    assert response.status_code == 200
    assert response.json()["provider"] == "groq"


def test_export_has_no_payload_or_secret(owner_client, seeded_calls):
    body = owner_client.get(
        "/mc/cheap-lane/logs/export?format=json&hours=24"
    ).text
    assert "Authorization" not in body
    assert '"prompt"' not in body
    csv_response = owner_client.get(
        "/mc/cheap-lane/logs/export?format=csv&hours=24"
    )
    assert csv_response.status_code == 200
    assert csv_response.text.startswith("invocation_id,")


def test_diagnostic_package_links_sources_without_secrets(
    owner_client, seeded_calls, monkeypatch
):
    import apps.api.jarvis_api.routes.cheap_lane_control as routes

    monkeypatch.setattr(routes, "build_cheap_lane_dashboard", lambda **_kw: {
        "status": "complete", "sections": {}, "kpis": {},
    })
    monkeypatch.setattr(routes, "diagnose_cheap_lane", lambda: {"findings": []})
    response = owner_client.get(
        "/mc/cheap-lane/diagnostics/export?hours=24"
    )
    assert response.status_code == 200
    data = response.json()
    assert set(data) >= {
        "snapshot", "findings", "logs", "config_fingerprints", "schema_versions",
    }
    assert "api_key" not in json.dumps(data).lower()
    serialized = json.dumps(data).lower()
    assert '"payload":' not in serialized
    assert '"prompt":' not in serialized


def test_bounds_and_format_are_validated(owner_client):
    assert owner_client.get("/mc/cheap-lane/dashboard?hours=0").status_code == 422
    assert owner_client.get(
        "/mc/cheap-lane/logs/export?hours=1441&format=json"
    ).status_code == 422
    assert owner_client.get(
        "/mc/cheap-lane/logs/export?hours=24&format=xml"
    ).status_code == 422
