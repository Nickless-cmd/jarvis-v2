"""Integration-tests for owner-only user-admin routes (spec 2026-06-15 §4/§6)."""
from __future__ import annotations

from fastapi.testclient import TestClient


def _client(isolated_runtime) -> TestClient:
    from apps.api.jarvis_api.app import create_app
    return TestClient(create_app())


def _owner_token(isolated_runtime) -> tuple[dict, str]:
    from core.identity import user_db
    user = user_db.add_user(email="owner@b.dk", name="Owner", password="ownerpw",
                            role="owner", tier="owner")
    from core.runtime.jarvisx_auth import issue_token
    t = issue_token(user_id=user["user_id"], role="owner")["token"]
    return user, t


def test_list_users_requires_owner(isolated_runtime) -> None:
    c = _client(isolated_runtime)
    r = c.get("/api/users")
    assert r.status_code in (401, 403)


def test_owner_lists_and_mutes_and_deletes(isolated_runtime) -> None:
    from core.identity import user_db
    _owner, token = _owner_token(isolated_runtime)
    member = user_db.create_user(email="mem@b.dk", name="Mem", password="x",
                                 role="member", workspace="mem")
    c = _client(isolated_runtime)
    hdr = {"Authorization": f"Bearer {token}"}

    r = c.get("/api/users", headers=hdr)
    assert r.status_code == 200, r.text
    emails = {u["email"] for u in r.json()["users"]}
    assert "mem@b.dk" in emails

    r = c.patch(f"/api/users/{member['user_id']}", headers=hdr, json={"muted": True, "tier": "plus"})
    assert r.status_code == 200
    assert user_db.get_user(member["user_id"])["muted"] is True
    assert user_db.get_user(member["user_id"])["tier"] == "plus"

    r = c.request("DELETE", f"/api/users/{member['user_id']}", headers=hdr, json={"mode": "soft"})
    assert r.status_code == 200
    assert user_db.get_user(member["user_id"])["deleted_at"] is not None


def test_patch_unknown_user_404(isolated_runtime) -> None:
    _owner, token = _owner_token(isolated_runtime)
    c = _client(isolated_runtime)
    r = c.patch("/api/users/nope", headers={"Authorization": f"Bearer {token}"}, json={"muted": True})
    assert r.status_code == 404
