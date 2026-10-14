from __future__ import annotations

import json

import pytest


@pytest.fixture(autouse=True)
def deterministic_user_keys(monkeypatch, isolated_runtime):
    import core.services.keyring_store as keyring_store
    from core.runtime import db

    monkeypatch.setattr(
        keyring_store,
        "get_user_key",
        lambda owner: (owner.encode("utf-8") + b"x" * 32)[:32],
    )
    original_get_state = db.get_runtime_state_value
    monkeypatch.setattr(
        db,
        "get_runtime_state_value",
        lambda key, default=None: (
            "test-wrapped-key" if str(key).startswith("user_dek:")
            else original_get_state(key, default)
        ),
    )


def _write_legacy_users(home, users):
    path = home / ".jarvis-v2" / "config" / "users.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"users": users}), encoding="utf-8")


def test_dry_run_plans_opaque_canonical_accounts_without_writing(
    isolated_runtime, monkeypatch
):
    from pathlib import Path
    import os

    home = Path(os.environ["HOME"])
    _write_legacy_users(home, [{
        "discord_id": "123456789",
        "name": "Owner",
        "role": "owner",
        "workspace": "owner-ws",
        "created_at": "2026-01-01T00:00:00Z",
    }])

    from core.services.routine_identity_migration import plan_legacy_identity_cutover
    from core.runtime import db

    report = plan_legacy_identity_cutover()
    assert report.create_count == 1
    assert report.conflict_count == 0
    assert report.items[0].canonical_user_id != "123456789"
    assert db.list_user_rows() == []


def test_apply_is_exact_idempotent_and_enables_canonical_resolution(isolated_runtime):
    from pathlib import Path
    import os

    home = Path(os.environ["HOME"])
    _write_legacy_users(home, [{
        "discord_id": "123456789",
        "name": "Owner",
        "role": "owner",
        "workspace": "owner-ws",
        "created_at": "2026-01-01T00:00:00Z",
    }])

    from core.services.routine_identity_migration import (
        IdentitySourceChanged,
        apply_legacy_identity_cutover,
        plan_legacy_identity_cutover,
    )
    from core.services.routine_identity import resolve_principal

    report = plan_legacy_identity_cutover()
    result = apply_legacy_identity_cutover(expected_watermark=report.watermark)
    assert result.created == 1
    canonical = resolve_principal("123456789")
    assert canonical.canonical_user_id == report.items[0].canonical_user_id
    assert canonical.role == "owner"

    second_report = plan_legacy_identity_cutover()
    assert second_report.conflict_count == 0, second_report.items
    second = apply_legacy_identity_cutover(
        expected_watermark=second_report.watermark
    )
    assert second.created == 0
    assert second.already_linked == 1

    with pytest.raises(IdentitySourceChanged):
        apply_legacy_identity_cutover(expected_watermark="stale")


def test_workspace_collision_fails_closed(isolated_runtime):
    from pathlib import Path
    import os

    from core.runtime import db

    db.insert_user_row(
        user_id="existing", email_hash="existing-hash", email_enc=b"",
        name="Someone else", role="member", workspace="shared-ws",
        password_hash="", discord_id_enc=b"", totp_seed_enc=b"",
        created_at="t", updated_at="t",
    )
    home = Path(os.environ["HOME"])
    _write_legacy_users(home, [{
        "discord_id": "987654321",
        "name": "Legacy",
        "role": "member",
        "workspace": "shared-ws",
        "created_at": "2026-01-01T00:00:00Z",
    }])

    from core.services.routine_identity_migration import (
        IdentityMigrationConflict,
        apply_legacy_identity_cutover,
        plan_legacy_identity_cutover,
    )

    report = plan_legacy_identity_cutover()
    assert report.conflict_count == 1
    with pytest.raises(IdentityMigrationConflict):
        apply_legacy_identity_cutover(expected_watermark=report.watermark)
