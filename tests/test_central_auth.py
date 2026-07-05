from __future__ import annotations

import pytest
from fastapi import HTTPException

import apps.api.jarvis_api.routes.central_auth as ca


def _patch(monkeypatch, *, role="", uid=None, db_role=None):
    monkeypatch.setattr("core.identity.workspace_context.current_role", lambda: role)
    monkeypatch.setattr("core.identity.workspace_context.current_user_id", lambda: uid or "")

    class _U:
        pass
    u = _U()
    if db_role is not None:
        u.role = db_role
    monkeypatch.setattr("core.identity.users.find_user_by_discord_id",
                        lambda _id: (u if db_role is not None else None))


def test_owner_token_passes_even_without_db_user(monkeypatch):
    # THE BUG: valid owner token but no matching DB user → must NOT 403.
    _patch(monkeypatch, role="owner", uid="someid", db_role=None)
    ca.require_central_owner()  # no raise


def test_unbound_context_is_owner(monkeypatch):
    _patch(monkeypatch, role="", uid=None)
    ca.require_central_owner()  # no raise (localhost / single-user dev)


def test_db_owner_fallback_passes(monkeypatch):
    _patch(monkeypatch, role="member", uid="x", db_role="owner")
    ca.require_central_owner()  # DB fallback still works


def test_member_token_and_non_owner_db_is_rejected(monkeypatch):
    _patch(monkeypatch, role="member", uid="x", db_role="member")
    with pytest.raises(HTTPException) as ei:
        ca.require_central_owner()
    assert ei.value.status_code == 403
