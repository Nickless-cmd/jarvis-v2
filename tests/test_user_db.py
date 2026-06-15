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


def test_create_user_roundtrip_decrypts_email(isolated_runtime) -> None:
    from core.identity.user_db import create_user, get_user
    u = create_user(email="Bjorn@Example.com ", name="Bjørn", password="hemmelig",
                    role="owner", workspace="bjorn")
    assert u["email"] == "bjorn@example.com"
    assert u["email_verified"] is False
    got = get_user(u["user_id"])
    assert got["email"] == "bjorn@example.com"
    assert got["name"] == "Bjørn"


def test_find_user_by_email_is_case_insensitive(isolated_runtime) -> None:
    from core.identity.user_db import create_user, find_user_by_email
    create_user(email="a@b.dk", name="A", password="x", role="member", workspace="a")
    assert find_user_by_email("A@B.DK") is not None
    assert find_user_by_email("nope@b.dk") is None


def test_duplicate_email_rejected(isolated_runtime) -> None:
    import pytest
    from core.identity.user_db import create_user
    create_user(email="dup@b.dk", name="A", password="x", role="member", workspace="a")
    with pytest.raises(ValueError):
        create_user(email="DUP@b.dk", name="B", password="y", role="member", workspace="b")


def test_verify_login_checks_password(isolated_runtime) -> None:
    from core.identity.user_db import create_user, verify_login
    create_user(email="l@b.dk", name="L", password="rigtig", role="member", workspace="l")
    ok = verify_login("l@b.dk", "rigtig")
    assert ok is not None and ok["email"] == "l@b.dk"
    assert verify_login("l@b.dk", "forkert") is None
    assert verify_login("ukendt@b.dk", "x") is None


def test_mute_and_set_quota(isolated_runtime) -> None:
    from core.identity.user_db import create_user, mute_user, unmute_user, set_quota_tier, get_user
    u = create_user(email="m@b.dk", name="M", password="x", role="member", workspace="m")
    uid = u["user_id"]
    mute_user(uid)
    assert get_user(uid)["muted"] is True
    unmute_user(uid)
    assert get_user(uid)["muted"] is False
    set_quota_tier(uid, "pro")
    assert get_user(uid)["tier"] == "pro"


def test_add_user_is_pre_verified_and_gets_key_for_owner(isolated_runtime) -> None:
    from core.identity.user_db import add_user, get_user
    u = add_user(email="boss@b.dk", name="Boss", password="x", role="owner", tier="owner")
    assert u["email_verified"] is True
    assert u["has_api_key"] is True
    assert u["api_key"]
    assert get_user(u["user_id"])["api_key_jti"]


def test_create_api_key_gated_on_tier(isolated_runtime) -> None:
    from core.identity.user_db import create_user, create_api_key, get_user, set_quota_tier
    u = create_user(email="free@b.dk", name="F", password="x", role="member", workspace="f")
    assert create_api_key(u["user_id"]) is None
    assert get_user(u["user_id"])["has_api_key"] is False
    set_quota_tier(u["user_id"], "plus")
    key = create_api_key(u["user_id"])
    assert key and get_user(u["user_id"])["has_api_key"] is True


def test_revoke_api_key_blocklists_jti(isolated_runtime) -> None:
    from core.identity.user_db import add_user, revoke_api_key, is_api_key_revoked, get_user
    u = add_user(email="rev@b.dk", name="R", password="x", role="owner", tier="owner")
    jti = get_user(u["user_id"])["api_key_jti"]
    assert is_api_key_revoked(jti) is False
    assert revoke_api_key(u["user_id"]) is True
    assert is_api_key_revoked(jti) is True
    assert get_user(u["user_id"])["has_api_key"] is False


def test_register_user_creates_unverified_and_returns_token(isolated_runtime, monkeypatch) -> None:
    from core.identity import user_db, email_verify
    sent = {}
    monkeypatch.setattr(email_verify, "_send_mail", lambda a: sent.update(a) or {"success": True})
    user, token = user_db.register_user(email="new@b.dk", name="Ny", password="pw",
                                        base_url="https://jarvis.srvlab.dk")
    assert user["email_verified"] is False
    assert token and sent["to"] == "new@b.dk"
    assert user_db.verify_email_token(token) is True
    assert user_db.get_user(user["user_id"])["email_verified"] is True


def test_soft_delete_marks_user(isolated_runtime) -> None:
    from core.identity.user_db import create_user, delete_user, get_user
    u = create_user(email="sd@b.dk", name="S", password="x", role="member", workspace="s")
    assert delete_user(u["user_id"], mode="soft", actor="owner") is True
    assert get_user(u["user_id"])["deleted_at"] is not None


def test_hard_delete_removes_user_and_key(isolated_runtime) -> None:
    from core.identity.user_db import create_user, delete_user, get_user
    from core.runtime.db import get_user_row
    u = create_user(email="hd@b.dk", name="H", password="x", role="member", workspace="h")
    uid = u["user_id"]
    assert delete_user(uid, mode="hard", actor="owner") is True
    assert get_user(uid) is None
    assert get_user_row(uid) is None


def test_delete_writes_audit_entry(isolated_runtime) -> None:
    from core.identity.user_db import create_user, delete_user, read_audit_log
    u = create_user(email="au@b.dk", name="A", password="x", role="member", workspace="a")
    delete_user(u["user_id"], mode="soft", actor="bjorn")
    log = read_audit_log()
    assert any(e["user_id"] == u["user_id"] and e["action"] == "delete:soft"
               and e["actor"] == "bjorn" for e in log)


def _bootstrapped_ws_dir(workspace: str):
    # bootstrap skriver til WORKSPACES_DIR/<workspace> direkte (uden users.json-
    # opslag, som workspace_dir() ellers kræver — det er #154-cutover-gappet).
    import os
    from pathlib import Path
    return Path(os.environ["JARVIS_WORKSPACES_DIR"]) / workspace


def test_add_user_provisions_workspace(isolated_runtime) -> None:
    # add_user skal oprette workspace-mappe + baseline-filer (USER.md/MEMORY.md).
    from core.identity.user_db import add_user
    u = add_user(email="ws@b.dk", name="Mikkel", password="hemmelig123", role="member")
    wsdir = _bootstrapped_ws_dir(u["workspace"])
    assert wsdir.exists() and wsdir.is_dir()
    # USER.md findes som plaintext eller krypteret (.enc) afhængigt af flag.
    has_user = (wsdir / "USER.md").exists() or (wsdir / "USER.md.enc").exists()
    has_mem = (wsdir / "MEMORY.md").exists() or (wsdir / "MEMORY.md.enc").exists()
    assert has_user and has_mem


def test_register_user_provisions_workspace(isolated_runtime, monkeypatch) -> None:
    from core.identity import user_db
    monkeypatch.setattr(user_db, "create_api_key", lambda uid: None)
    import core.identity.email_verify as ev
    monkeypatch.setattr(ev, "send_verification_email", lambda **kw: "tok")
    user, _tok = user_db.register_user(
        email="reg@b.dk", name="Reg", password="hemmelig123", base_url="http://x")
    assert _bootstrapped_ws_dir(user["workspace"]).exists()
