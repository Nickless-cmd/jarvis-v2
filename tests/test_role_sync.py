"""Tests for `core.identity.role_sync` — ét rolleskift, tre kilder.

MÅLT 20/11-2026: et skift i `users.json` alene lod Google-login udstede den
GAMLE rolle, fordi `google_login_links` har sin egen kopi — og for en bruger
uden password er det den eneste vej ind. Testene her vogter at alle tre
kilder flytter sig ved ét kald, og at et ukendt rollenavn afvises frem for at
blive skrevet halvt.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def bruger_i_alle_tre_kilder(isolated_runtime):
    """En bruger der findes i users.json, users-tabellen OG har to Google-links.

    De to links bærer bevidst HVER SIN id-form: `google_login_links.user_id` er
    ikke normaliseret i den levende base (målt 20/11-2026: Michelles link bar
    discord-id, mens users-tabellen bar UUID). En opdatering der kun rammer den
    ene form er derfor tavst virkningsløs — og det er netop fejlen der skal
    fanges.
    """
    from core.identity.users import add_user
    from core.runtime import db_users as dbu
    from core.runtime.db import insert_user_row
    from core.services.encryption import encrypt
    from core.services.keyring_store import get_user_key

    did, uid = "d-1", "uuid-1"
    add_user(discord_id=did, name="Test", role="member")
    insert_user_row(
        user_id=uid, email_hash="h-1", email_enc=b"", name="Test", role="member",
        workspace="test", password_hash="",
        discord_id_enc=encrypt(did.encode("utf-8"), get_user_key(uid)),
        totp_seed_enc=b"", created_at="t", updated_at="t",
    )
    dbu.set_google_link("gh-discord", did, "member", "t")
    dbu.set_google_link("gh-uuid", uid, "member", "t")
    return {"discord_id": did, "user_id": uid}


def test_et_kald_flytter_alle_tre_kilder(bruger_i_alle_tre_kilder) -> None:
    from core.identity.role_sync import set_role
    from core.identity.users import find_user_by_discord_id
    from core.runtime.db import get_user_row
    from core.runtime.db_users import get_google_link

    ud = set_role(discord_id="d-1", role="partner", actor="test")

    assert ud["ok"] is True
    assert ud["kilder"]["users_json"] is True
    assert ud["kilder"]["users_tabel"] is True
    # Begge id-former i link-tabellen skal være ramt.
    assert ud["kilder"]["google_login_links"] == 2

    assert find_user_by_discord_id("d-1").role == "partner"
    assert get_user_row("uuid-1")["role"] == "partner"
    assert get_google_link("gh-discord")["role"] == "partner"
    assert get_google_link("gh-uuid")["role"] == "partner"


def test_ukendt_rolle_afvises_uden_at_skrive(bruger_i_alle_tre_kilder) -> None:
    from core.identity.role_sync import set_role
    from core.identity.users import find_user_by_discord_id
    from core.runtime.db import get_user_row
    from core.runtime.db_users import get_google_link

    ud = set_role(discord_id="d-1", role="superadmin")

    assert ud["ok"] is False
    assert "ukendt rolle" in ud["error"]
    assert find_user_by_discord_id("d-1").role == "member"
    assert get_user_row("uuid-1")["role"] == "member"
    assert get_google_link("gh-discord")["role"] == "member"


def test_bruger_kun_i_users_json_rammer_kun_filen(isolated_runtime) -> None:
    from core.identity.role_sync import set_role
    from core.identity.users import add_user, find_user_by_discord_id

    add_user(discord_id="d-2", name="KunFil", role="member")
    ud = set_role(discord_id="d-2", role="partner")

    assert ud["ok"] is True
    assert ud["kilder"]["users_json"] is True
    assert ud["kilder"]["users_tabel"] == "findes ikke"
    assert ud["kilder"]["google_login_links"] == 0
    assert find_user_by_discord_id("d-2").role == "partner"


def test_ukendt_bruger_afvises(isolated_runtime) -> None:
    from core.identity.role_sync import set_role

    ud = set_role(discord_id="fremmed", role="partner")

    assert ud["ok"] is False
    assert "ukendt bruger" in ud["error"]


def test_manglende_discord_id_afvises(isolated_runtime) -> None:
    from core.identity.role_sync import set_role

    assert set_role(discord_id="  ", role="partner")["ok"] is False


def test_svaret_naevner_at_tokens_skal_fornyes(bruger_i_alle_tre_kilder) -> None:
    """Et rolleskift er ikke aktivt i en åben session — det skal siges, ikke skjules."""
    from core.identity.role_sync import set_role

    ud = set_role(discord_id="d-1", role="partner")
    assert "token" in ud["bemaerk"].lower()


def test_patch_ruten_flytter_alle_tre_kilder(isolated_runtime) -> None:
    """PATCH /api/users/{id} skrev før KUN users-tabellen (målt 20/11-2026).

    Ruten er den vej et rolleskift faktisk tages i drift, så en funktion der
    virker men ikke kaldes ville være teater. Testen går gennem HTTP-laget.
    """
    from fastapi.testclient import TestClient

    from apps.api.jarvis_api.app import create_app
    from core.identity import user_db
    from core.identity.users import add_user, find_user_by_discord_id
    from core.runtime import db_users as dbu
    from core.runtime.db import update_user_row
    from core.runtime.jarvisx_auth import issue_token
    from core.services.encryption import encrypt
    from core.services.keyring_store import get_user_key

    owner = user_db.add_user(email="owner@b.dk", name="Owner",
                             password="ownerpw",  # noqa: literal-credential  # pragma: allowlist secret — test-fixture
                             role="owner", tier="owner")
    token = issue_token(user_id=owner["user_id"], role="owner")["token"]

    did = "d-rute"
    member = user_db.create_user(email="mem@b.dk", name="Mem",
                                 password="x",  # noqa: literal-credential  # pragma: allowlist secret — test-fixture
                                 role="member", workspace="mem")
    mid = member["user_id"]
    update_user_row(mid, {"discord_id_enc": encrypt(did.encode("utf-8"), get_user_key(mid))})
    add_user(discord_id=did, name="Mem", role="member")
    dbu.set_google_link("gh-rute", did, "member", "t")

    c = TestClient(create_app())
    r = c.patch(f"/api/users/{mid}", headers={"Authorization": f"Bearer {token}"},
                json={"role": "partner"})

    assert r.status_code == 200, r.text
    assert r.json()["kilder"]["google_login_links"] == 1
    assert find_user_by_discord_id(did).role == "partner"          # lag 1
    assert user_db.get_user(mid)["role"] == "partner"              # lag 2
    assert dbu.get_google_link("gh-rute")["role"] == "partner"     # lag 3


def test_rolleskift_efterlader_spor_med_actor(bruger_i_alle_tre_kilder) -> None:
    """Et rolleskift skal kunne spores — ikke kun ligge i en roterende log.

    MÅLT 20/11-2026: `role_sync` kaldte aldrig `user_db._audit`, så et skift
    efterlod nul poster i `user_audit_log`. Et rolleskift uden spor kan ikke
    efterprøves bagefter — og det var netop hvad der gjorde formiddagens
    halve skift så svært at finde.
    """
    from core.identity.role_sync import set_role
    from core.identity.user_db import read_audit_log

    foer = len(read_audit_log())
    ud = set_role(discord_id=bruger_i_alle_tre_kilder["discord_id"],
                  role="partner", actor="test-owner")
    assert ud["ok"] is True

    log = read_audit_log()
    assert len(log) == foer + 1
    post = log[-1]
    assert post["actor"] == "test-owner"
    assert post["action"] == "role_change:member->partner"
    assert post["user_id"] == bruger_i_alle_tre_kilder["user_id"]
