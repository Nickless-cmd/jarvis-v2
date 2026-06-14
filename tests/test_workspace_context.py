from __future__ import annotations

T0 = 1_700_000_000


def test_owner_role_unchanged_no_override_check(isolated_runtime) -> None:
    from core.identity.workspace_context import set_context, reset_context, effective_role

    tok = set_context(workspace_name="bjorn", user_id="u-bjorn", role="owner", session_id="s1")
    try:
        assert effective_role() == "owner"
    finally:
        reset_context(tok)


def test_member_without_override_stays_member(isolated_runtime) -> None:
    from core.identity.workspace_context import set_context, reset_context, effective_role

    tok = set_context(workspace_name="mikkel", user_id="u-mikkel", role="member", session_id="s-x")
    try:
        assert effective_role() == "member"
    finally:
        reset_context(tok)


def test_member_with_active_override_elevates_to_owner(isolated_runtime) -> None:
    from core.identity.workspace_context import set_context, reset_context, effective_role
    from core.services.override_store import grant

    grant("s-x", now=T0 + 10**9)  # gyldig langt ud i fremtiden ift. realtid
    tok = set_context(workspace_name="mikkel", user_id="u-mikkel", role="member", session_id="s-x")
    try:
        assert effective_role() == "owner"
    finally:
        reset_context(tok)


def test_override_in_different_session_does_not_elevate(isolated_runtime) -> None:
    from core.identity.workspace_context import set_context, reset_context, effective_role
    from core.services.override_store import grant

    grant("s-other", now=T0 + 10**9)
    tok = set_context(workspace_name="mikkel", user_id="u-mikkel", role="member", session_id="s-mine")
    try:
        assert effective_role() == "member"  # override hører til en anden session
    finally:
        reset_context(tok)


def test_effective_role_renews_override_window(isolated_runtime) -> None:
    # Aktivitet (effective_role) fornyer 5-min-vinduet (§9): touch flytter
    # expires_at fra realtid+90 (grant) til realtid+300.
    from core.identity.workspace_context import set_context, reset_context, effective_role
    from core.services import override_store

    override_store.grant("s-y")  # realtid → expires realtid+90
    before = override_store._read("s-y")["expires_at"]
    tok = set_context(workspace_name="mikkel", role="member", session_id="s-y")
    try:
        assert effective_role() == "owner"
    finally:
        reset_context(tok)
    after = override_store._read("s-y")["expires_at"]
    assert after > before  # fornyet fra +90 til +300
