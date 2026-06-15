"""users.json→SQLite cutover: hybrid workspace-resolution (additiv, nul regression)."""
from __future__ import annotations

import pytest


def test_workspace_dir_resolves_sqlite_user(isolated_runtime):
    # Nyregistreret SQLite-bruger (kun i tabellen) → workspace resolverer.
    from core.identity.user_db import add_user
    from core.runtime.workspace_paths import workspace_dir
    u = add_user(email="cut@b.dk", name="Cut", password="hemmelig123",
                 role="member", workspace="cutws")
    assert workspace_dir(u["user_id"]).name == "cutws"


def test_workspace_dir_still_resolves_legacy_users_json(isolated_runtime):
    # Legacy users.json prøves FØRST — uændret adfærd.
    import core.identity.users as legacy
    from core.runtime.workspace_paths import workspace_dir
    legacy.add_user(discord_id="999111", name="L", role="member", workspace="legws")
    assert workspace_dir("999111").name == "legws"


def test_workspace_dir_unknown_still_raises_loud(isolated_runtime):
    # Ukendt i BEGGE → stadig loud NoUserContextError (ingen stille default).
    from core.runtime.workspace_paths import workspace_dir, NoUserContextError
    with pytest.raises(NoUserContextError):
        workspace_dir("findes-ikke-nogen-steder-xyz")


def test_member_path_recognized_for_sqlite_member(isolated_runtime):
    # En SQLite-members workspace genkendes → krypteres (nøgle-id = user_id).
    import os
    from core.identity.user_db import add_user
    from core.services.workspace_crypto import member_user_id_for_path
    u = add_user(email="m2@b.dk", name="M2", password="hemmelig123",
                 role="member", workspace="mws")
    path = f"{os.environ['HOME']}/.jarvis-v2/workspaces/mws/USER.md"
    assert member_user_id_for_path(path) == u["user_id"]


def test_owner_sqlite_workspace_stays_plaintext(isolated_runtime):
    # Owner-workspace (SQLite) → None (plaintext, krypteres ikke).
    import os
    from core.identity.user_db import add_user
    from core.services.workspace_crypto import member_user_id_for_path
    add_user(email="own@b.dk", name="Own", password="hemmelig123",
             role="owner", workspace="ownws", tier="owner")
    path = f"{os.environ['HOME']}/.jarvis-v2/workspaces/ownws/USER.md"
    assert member_user_id_for_path(path) is None
