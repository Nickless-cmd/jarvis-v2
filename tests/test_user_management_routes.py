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


# ── Fase C: offentlige auth-routes (register/verify/login) ──

def test_register_then_login_flow(isolated_runtime, monkeypatch) -> None:
    from core.identity import email_verify
    captured = {}
    monkeypatch.setattr(email_verify, "_send_mail",
                        lambda a: captured.update(a) or {"success": True})
    c = _client(isolated_runtime)

    r = c.post("/api/auth/register", json={"email": "flow@b.dk", "name": "Flow", "password": "pw123456"})
    assert r.status_code == 200, r.text
    assert r.json()["email_verified"] is False

    # Login før verifikation afvises
    r = c.post("/api/auth/login", json={"email": "flow@b.dk", "password": "pw123456"})
    assert r.status_code == 403

    token = captured["body"].split("token=")[1].split()[0].strip()
    r = c.get(f"/api/auth/verify-email?token={token}")
    assert r.status_code == 200 and r.json()["verified"] is True

    r = c.post("/api/auth/login", json={"email": "flow@b.dk", "password": "pw123456"})
    assert r.status_code == 200
    assert r.json()["token"]


def test_login_wrong_password_401(isolated_runtime, monkeypatch) -> None:
    from core.identity import email_verify, user_db
    monkeypatch.setattr(email_verify, "_send_mail", lambda a: {"success": True})
    c = _client(isolated_runtime)
    _user, tok = user_db.register_user(email="w@b.dk", name="W", password="rigtig",
                                       base_url="http://t")
    user_db.verify_email_token(tok)
    r = c.post("/api/auth/login", json={"email": "w@b.dk", "password": "forkert"})
    assert r.status_code == 401


def test_register_duplicate_email_409(isolated_runtime, monkeypatch) -> None:
    from core.identity import email_verify
    monkeypatch.setattr(email_verify, "_send_mail", lambda a: {"success": True})
    c = _client(isolated_runtime)
    c.post("/api/auth/register", json={"email": "d@b.dk", "name": "A", "password": "pw123456"})
    r = c.post("/api/auth/register", json={"email": "d@b.dk", "name": "B", "password": "pw123456"})
    assert r.status_code == 409
