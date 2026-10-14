from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.services.routine_types import RoutineCreate, RoutinePrincipal


@pytest.fixture(autouse=True)
def deterministic_user_keys(monkeypatch):
    import core.services.keyring_store as keyring_store

    monkeypatch.setattr(
        keyring_store,
        "get_user_key",
        lambda owner: (owner.encode("utf-8") + b"x" * 32)[:32],
    )


@pytest.fixture
def identity(monkeypatch):
    state = {"uid": "member-a", "role": "member"}
    monkeypatch.setattr(
        "core.identity.workspace_context.current_user_id", lambda: state["uid"]
    )
    monkeypatch.setattr(
        "core.identity.workspace_context.current_role", lambda: state["role"]
    )
    monkeypatch.setattr(
        "core.services.routine_identity.resolve_principal",
        lambda raw, role_hint="": RoutinePrincipal(raw, role=state["role"]),
    )
    return state


@pytest.fixture
def client(isolated_runtime, identity):
    from apps.api.jarvis_api.routes.routines import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def member_routine(isolated_runtime):
    from core.services.routine_service import RoutineService

    return RoutineService(RoutinePrincipal("member-a", role="member")).create_and_activate(
        RoutineCreate(
            name="Private",
            instruction=b"private instruction",
            capability_scope="chat",
            trigger_kind="manual",
        )
    )


def valid_create():
    return {
        "name": "Morning",
        "instruction": "Do the private task",
        "capability_scope": "chat",
        "trigger_kind": "manual",
        "trigger_config": {},
    }


def test_owner_cannot_get_members_private_routine(client, identity, member_routine):
    identity.update(uid="owner-a", role="owner")
    assert client.get(f"/api/routines/{member_routine.id}").status_code == 404


def test_stale_edit_returns_409(client, member_routine):
    res = client.patch(
        f"/api/routines/{member_routine.id}",
        json={"expected_version": 0, "name": "x"},
    )
    assert res.status_code == 409


def test_create_ignores_caller_supplied_owner(client):
    res = client.post(
        "/api/routines", json={**valid_create(), "owner_user_id": "owner-a"}
    )
    assert res.status_code == 422


def test_list_is_scoped_and_run_events_are_owner_only(
    client, identity, member_routine
):
    created = client.post(
        f"/api/routines/{member_routine.id}/runs", json={}
    )
    assert created.status_code == 200
    run_id = created.json()["run_id"]
    assert [item["routine_id"] for item in client.get("/api/routines").json()] == [
        member_routine.id
    ]

    identity.update(uid="owner-a", role="owner")
    assert client.get(f"/api/routines/{member_routine.id}/runs").status_code == 404
    assert client.get(f"/api/routines/runs/{run_id}/events").status_code == 404


def test_openapi_has_no_owner_selection_field(client):
    schema = client.get("/openapi.json").json()
    create_schema = schema["components"]["schemas"]["RoutineCreateBody"]
    assert "owner_user_id" not in create_schema.get("properties", {})


def test_principal_resolves_legacy_token_to_canonical_account(
    isolated_runtime, monkeypatch
):
    from apps.api.jarvis_api.routes import routines

    monkeypatch.setattr(
        "core.identity.workspace_context.current_user_id", lambda: "legacy-discord"
    )
    monkeypatch.setattr(
        "core.identity.workspace_context.current_role", lambda: "owner"
    )
    monkeypatch.setattr(
        "core.services.routine_identity.resolve_principal",
        lambda raw, role_hint="": RoutinePrincipal("canonical-owner", role="owner"),
    )

    principal = routines._principal()
    assert principal.canonical_user_id == "canonical-owner"


def test_unresolved_principal_is_unauthorized(isolated_runtime, monkeypatch):
    from apps.api.jarvis_api.routes import routines
    from core.services.routine_identity import UnresolvedRoutinePrincipal

    monkeypatch.setattr(
        "core.identity.workspace_context.current_user_id", lambda: "unknown"
    )
    monkeypatch.setattr(
        "core.identity.workspace_context.current_role", lambda: "owner"
    )
    monkeypatch.setattr(
        "core.services.routine_identity.resolve_principal",
        lambda raw, role_hint="": (_ for _ in ()).throw(
            UnresolvedRoutinePrincipal("unresolved")
        ),
    )

    with pytest.raises(Exception) as caught:
        routines._principal()
    assert getattr(caught.value, "status_code", None) == 401


def test_inbox_defaults_are_user_scoped(client, identity):
    assert client.put("/api/routines/inbox-defaults", json={"failed": True}).status_code == 200
    assert client.get("/api/routines/inbox-defaults").json() == {"failed": True}
    identity.update(uid="member-b", role="member")
    assert client.get("/api/routines/inbox-defaults").json() == {}


def test_owner_gets_only_redacted_member_failure(
    client, identity, member_routine
):
    from core.runtime.db_routines import claim_run, transition_run
    from core.services.routine_service import RoutineService

    service = RoutineService(RoutinePrincipal("member-a", role="member"))
    run = service.enqueue_run(member_routine.id, trigger_key="manual:failure")
    claim = claim_run(run.run_id, holder="test")
    transition_run(
        run.run_id, to_status="failed",
        expected_generation=claim["lease_generation"],
        diagnostic_code="model_error",
    )
    identity.update(uid="owner-a", role="owner")
    response = client.get(f"/api/routines/diagnostics/runs/{run.run_id}")
    assert response.status_code == 200
    encoded = response.text
    assert "private instruction" not in encoded
    assert member_routine.name not in encoded
    assert response.json()["error_code"] == "model_error"
