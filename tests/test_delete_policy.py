from __future__ import annotations


def test_owner_hard_delete_double_confirm() -> None:
    from core.services.delete_policy import resolve_delete_action

    a = resolve_delete_action(role="owner", is_own_workspace=True)
    assert a["mode"] == "hard"
    assert a["confirmations"] == 2


def test_owner_can_delete_any_workspace() -> None:
    from core.services.delete_policy import resolve_delete_action

    a = resolve_delete_action(role="owner", is_own_workspace=False)
    assert a["mode"] == "hard"
    assert a["confirmations"] == 2


def test_member_own_workspace_soft_delete() -> None:
    from core.services.delete_policy import resolve_delete_action

    a = resolve_delete_action(role="member", is_own_workspace=True)
    assert a["mode"] == "soft"          # grace-period-kopi
    assert a["confirmations"] == 0


def test_member_other_workspace_denied() -> None:
    from core.services.delete_policy import resolve_delete_action

    a = resolve_delete_action(role="member", is_own_workspace=False)
    assert a["mode"] == "deny"


def test_guest_denied() -> None:
    from core.services.delete_policy import resolve_delete_action

    a = resolve_delete_action(role="guest", is_own_workspace=True)
    assert a["mode"] == "deny"


def test_unbound_treated_as_owner() -> None:
    from core.services.delete_policy import resolve_delete_action

    a = resolve_delete_action(role="", is_own_workspace=True)
    assert a["mode"] == "hard" and a["confirmations"] == 2


def test_unknown_role_fail_closed() -> None:
    from core.services.delete_policy import resolve_delete_action

    assert resolve_delete_action(role="hacker", is_own_workspace=True)["mode"] == "deny"


def test_member_gdpr_erasure_is_real_hard_delete() -> None:
    # §15.2: member kan udøve GDPR-sletningsret på egne data → ægte hard-delete.
    from core.services.delete_policy import resolve_delete_action

    a = resolve_delete_action(role="member", is_own_workspace=True, gdpr_erasure=True)
    assert a["mode"] == "hard"          # ikke soft/skjult-kopi
    assert a["confirmations"] == 1

    # GDPR-erasure giver IKKE ret til andres data
    b = resolve_delete_action(role="member", is_own_workspace=False, gdpr_erasure=True)
    assert b["mode"] == "deny"


def test_confirm_count_tracking() -> None:
    # Owner skal bekræfte 2 gange før hard-delete udføres.
    from core.services.delete_policy import is_delete_confirmed

    assert is_delete_confirmed(role="owner", confirmations_received=0) is False
    assert is_delete_confirmed(role="owner", confirmations_received=1) is False
    assert is_delete_confirmed(role="owner", confirmations_received=2) is True
    # Member soft-delete kræver ingen bekræftelse
    assert is_delete_confirmed(role="member", confirmations_received=0) is True
    # Guest kan aldrig bekræftes
    assert is_delete_confirmed(role="guest", confirmations_received=99) is False
