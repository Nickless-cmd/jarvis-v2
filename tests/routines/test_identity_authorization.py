from __future__ import annotations

import pytest

from core.services.routine_types import RoutinePrincipal


@pytest.fixture
def principals():
    return {
        "owner_of_record": RoutinePrincipal("member-a", role="member"),
        "other_member": RoutinePrincipal("member-b", role="member"),
        "house_owner": RoutinePrincipal("house-owner", role="owner"),
        "jarvis": RoutinePrincipal("jarvis", role="system", actor_kind="jarvis"),
    }


@pytest.fixture
def private_record():
    return {
        "routine_id": "routine-opaque",
        "owner_user_id": "member-a",
        "access_scope": "user_private",
    }


@pytest.mark.parametrize(
    ("actor", "action", "expected"),
    [
        ("owner_of_record", "read_content", True),
        ("owner_of_record", "mutate", True),
        ("other_member", "read_content", False),
        ("other_member", "read_redacted_failure", False),
        ("house_owner", "read_content", False),
        ("house_owner", "mutate", False),
        ("house_owner", "read_redacted_failure", True),
        ("jarvis", "read_content", False),
        ("jarvis", "execute_sealed", True),
        ("jarvis", "read_redacted_failure", True),
    ],
)
def test_private_access_matrix(actor, action, expected, principals, private_record):
    from core.services.routine_authorization import authorize

    assert authorize(principals[actor], action, private_record).allowed is expected


def test_system_owner_is_visible_only_to_its_owner_role_and_jarvis_executes_sealed(principals):
    from core.services.routine_authorization import authorize

    record = {
        "routine_id": "system-routine",
        "owner_user_id": "house-owner",
        "access_scope": "system_owner",
    }
    assert authorize(principals["house_owner"], "read_content", record).allowed
    assert not authorize(principals["owner_of_record"], "read_content", record).allowed
    assert not authorize(principals["jarvis"], "read_content", record).allowed
    assert authorize(principals["jarvis"], "execute_sealed", record).allowed


def test_require_authorized_raises_without_leaking_record(principals, private_record):
    from core.services.routine_authorization import RoutineForbidden, require_authorized

    with pytest.raises(RoutineForbidden) as caught:
        require_authorized(principals["house_owner"], "read_content", private_record)
    assert "routine-opaque" not in str(caught.value)


def test_discord_and_canonical_tokens_converge(isolated_runtime):
    from core.identity import user_db
    from core.runtime import db
    from core.services.routine_identity import resolve_principal

    user = user_db.create_user(
        email="routine@example.test",
        name="Routine user",
        password="password",  # pragma: allowlist secret -- inert test credential
        role="member",
    )
    db.update_user_row(
        user["user_id"],
        {"discord_id_enc": user_db._enc(user["user_id"], "123456789")},
    )
    by_account = resolve_principal(user["user_id"])
    by_discord = resolve_principal("123456789")
    assert by_account.canonical_user_id == by_discord.canonical_user_id == user["user_id"]


def test_unknown_external_identity_fails_closed(isolated_runtime):
    from core.services.routine_identity import UnresolvedRoutinePrincipal, resolve_principal

    with pytest.raises(UnresolvedRoutinePrincipal):
        resolve_principal("userA")


def test_duplicate_external_match_fails_closed(isolated_runtime, monkeypatch):
    from core.identity import user_db
    from core.services.routine_identity import AmbiguousRoutineIdentity, resolve_principal

    monkeypatch.setattr(
        user_db,
        "list_users",
        lambda: [
            {"user_id": "u1", "discord_id": "123456789", "role": "member", "deleted_at": None},
            {"user_id": "u2", "discord_id": "123456789", "role": "member", "deleted_at": None},
        ],
    )
    with pytest.raises(AmbiguousRoutineIdentity):
        resolve_principal("123456789")


def test_role_hint_cannot_elevate_a_member(isolated_runtime):
    from core.identity import user_db
    from core.services.routine_identity import resolve_principal

    user = user_db.create_user(
        email="member@example.test", name="Member",
        password="password", role="member",  # pragma: allowlist secret -- inert test credential
    )
    principal = resolve_principal(user["user_id"], role_hint="owner")
    assert principal.role == "member"
