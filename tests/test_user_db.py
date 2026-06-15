"""Tests for users-tabellen + user_db-adapter (spec 2026-06-15)."""
from __future__ import annotations


def test_insert_and_get_user_row(isolated_runtime) -> None:
    from core.runtime.db import insert_user_row, get_user_row
    insert_user_row(
        user_id="u1", email_hash="h1", email_enc=b"E", name="Bjørn",
        role="owner", workspace="bjorn", password_hash="$2b$x",
        discord_id_enc=b"", totp_seed_enc=b"", created_at="t", updated_at="t",
    )
    r = get_user_row("u1")
    assert r is not None
    assert r["email_hash"] == "h1"
    assert r["role"] == "owner"
    assert r["email_verified"] == 0
    assert r["muted"] == 0
    assert r["deleted_at"] is None


def test_get_user_row_by_email_hash(isolated_runtime) -> None:
    from core.runtime.db import insert_user_row, get_user_row_by_email_hash
    insert_user_row(user_id="u2", email_hash="hh", email_enc=b"", name="x",
                    role="member", workspace="x", password_hash="p",
                    discord_id_enc=b"", totp_seed_enc=b"", created_at="t", updated_at="t")
    r = get_user_row_by_email_hash("hh")
    assert r is not None and r["user_id"] == "u2"


def test_update_user_fields(isolated_runtime) -> None:
    from core.runtime.db import insert_user_row, update_user_row, get_user_row
    insert_user_row(user_id="u3", email_hash="h3", email_enc=b"", name="x",
                    role="member", workspace="x", password_hash="p",
                    discord_id_enc=b"", totp_seed_enc=b"", created_at="t", updated_at="t")
    update_user_row("u3", {"email_verified": 1, "muted": 1, "tier": "plus", "updated_at": "t2"})
    r = get_user_row("u3")
    assert r["email_verified"] == 1 and r["muted"] == 1 and r["tier"] == "plus"


def test_soft_delete_sets_timestamp(isolated_runtime) -> None:
    from core.runtime.db import insert_user_row, soft_delete_user_row, get_user_row
    insert_user_row(user_id="u4", email_hash="h4", email_enc=b"", name="x",
                    role="member", workspace="x", password_hash="p",
                    discord_id_enc=b"", totp_seed_enc=b"", created_at="t", updated_at="t")
    soft_delete_user_row("u4", deleted_at="gone")
    assert get_user_row("u4")["deleted_at"] == "gone"


def test_hard_delete_removes_row(isolated_runtime) -> None:
    from core.runtime.db import insert_user_row, hard_delete_user_row, get_user_row
    insert_user_row(user_id="u5", email_hash="h5", email_enc=b"", name="x",
                    role="member", workspace="x", password_hash="p",
                    discord_id_enc=b"", totp_seed_enc=b"", created_at="t", updated_at="t")
    assert hard_delete_user_row("u5") is True
    assert get_user_row("u5") is None


def test_list_users_excludes_soft_deleted_by_default(isolated_runtime) -> None:
    from core.runtime.db import insert_user_row, soft_delete_user_row, list_user_rows
    insert_user_row(user_id="a", email_hash="ha", email_enc=b"", name="x", role="member",
                    workspace="a", password_hash="p", discord_id_enc=b"", totp_seed_enc=b"",
                    created_at="t", updated_at="t")
    insert_user_row(user_id="b", email_hash="hb", email_enc=b"", name="y", role="member",
                    workspace="b", password_hash="p", discord_id_enc=b"", totp_seed_enc=b"",
                    created_at="t", updated_at="t")
    soft_delete_user_row("b", deleted_at="gone")
    ids = {r["user_id"] for r in list_user_rows()}
    assert ids == {"a"}
    ids_all = {r["user_id"] for r in list_user_rows(include_deleted=True)}
    assert ids_all == {"a", "b"}
