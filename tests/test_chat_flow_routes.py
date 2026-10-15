from __future__ import annotations

import importlib

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient


def _client(isolated_runtime) -> TestClient:
    import core.services.chat_flow_preferences as service
    import apps.api.jarvis_api.routes.chat_flow_preferences as routes
    from core.identity.workspace_context import reset_context, set_context

    importlib.reload(service)
    routes = importlib.reload(routes)
    app = FastAPI()

    @app.middleware("http")
    async def bind_identity(request: Request, call_next):
        role = request.headers.get("x-test-role", "")
        user = request.headers.get("x-test-user", "")
        token = set_context(workspace_name="test", user_id=user, role=role)
        try:
            return await call_next(request)
        finally:
            reset_context(token)

    app.include_router(routes.router)
    return TestClient(app)


def _headers(user: str, role: str = "member") -> dict[str, str]:
    return {"x-test-user": user, "x-test-role": role}


def test_preferences_are_self_scoped_and_default_to_living(isolated_runtime):
    client = _client(isolated_runtime)

    changed = client.patch(
        "/api/chat-flow/preferences",
        headers=_headers("user-a"),
        json={"preference": "calm"},
    )

    assert changed.status_code == 200
    assert changed.json()["preference"] == "calm"
    assert changed.json()["explicit_user_choice"] is True
    assert client.get(
        "/api/chat-flow/preferences", headers=_headers("user-b")
    ).json()["preference"] == "living"


def test_payload_cannot_choose_another_user(isolated_runtime):
    client = _client(isolated_runtime)

    response = client.patch(
        "/api/chat-flow/preferences",
        headers=_headers("owner-a", "owner"),
        json={"preference": "calm", "user_id": "victim"},
    )

    assert response.status_code == 422
    victim = client.get(
        "/api/chat-flow/preferences", headers=_headers("victim")
    )
    assert victim.json()["preference"] == "living"


def test_unauthenticated_mutation_is_rejected(isolated_runtime):
    client = _client(isolated_runtime)

    response = client.patch(
        "/api/chat-flow/preferences", json={"preference": "calm"}
    )

    assert response.status_code == 401


def test_verified_native_owner_with_empty_id_is_supported(isolated_runtime):
    client = _client(isolated_runtime)

    response = client.patch(
        "/api/chat-flow/preferences",
        headers=_headers("", "owner"),
        json={"preference": "adaptive"},
    )

    assert response.status_code == 200
    assert response.json()["preference"] == "adaptive"


def test_onboarding_claim_is_acknowledged_by_matching_token(isolated_runtime):
    client = _client(isolated_runtime)
    headers = _headers("user-a")

    claim = client.post(
        "/api/chat-flow/onboarding/claim", headers=headers, json={"run_id": "run-1"}
    )
    competing = client.post(
        "/api/chat-flow/onboarding/claim", headers=headers, json={"run_id": "run-2"}
    )

    assert claim.status_code == 200
    assert claim.json()["claimed"] is True
    assert competing.json()["claimed"] is False
    assert client.post(
        "/api/chat-flow/onboarding/ack", headers=headers, json={"claim_id": "wrong"}
    ).status_code == 409
    acknowledged = client.post(
        "/api/chat-flow/onboarding/ack",
        headers=headers,
        json={"claim_id": claim.json()["claim_id"]},
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["onboarding_seen"] is True


def test_observation_contract_rejects_raw_text(isolated_runtime):
    client = _client(isolated_runtime)

    response = client.post(
        "/api/chat-flow/observations",
        headers=_headers("user-a"),
        json={"meaningful_steps": 3, "expanded_work": True, "raw_text": "secret"},
    )

    assert response.status_code == 422
