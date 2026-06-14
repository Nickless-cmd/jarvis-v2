from __future__ import annotations

T0 = 1_700_000_000


def test_grant_makes_active(isolated_runtime) -> None:
    from core.services.override_store import grant, is_active, level

    grant("sess-1", level="help", now=T0)
    assert is_active("sess-1", now=T0) is True
    assert level("sess-1", now=T0) == "help"


def test_initial_window_expires_after_90s(isolated_runtime) -> None:
    from core.services.override_store import grant, is_active

    grant("sess-1", now=T0)
    assert is_active("sess-1", now=T0 + 89) is True
    assert is_active("sess-1", now=T0 + 91) is False


def test_touch_renews_to_five_minutes(isolated_runtime) -> None:
    from core.services.override_store import grant, is_active, touch

    grant("sess-1", now=T0)
    # Aktivitet ved t+60 (inden for 90s-vinduet) → forny til +300s
    assert touch("sess-1", now=T0 + 60) is True
    # Ville være udløbet på initial-vindue (90s), men er nu aktiv til t+360
    assert is_active("sess-1", now=T0 + 200) is True
    assert is_active("sess-1", now=T0 + 361) is False


def test_touch_on_expired_does_not_revive(isolated_runtime) -> None:
    from core.services.override_store import grant, is_active, touch

    grant("sess-1", now=T0)
    assert touch("sess-1", now=T0 + 200) is False  # allerede udløbet
    assert is_active("sess-1", now=T0 + 201) is False


def test_revoke_deactivates(isolated_runtime) -> None:
    from core.services.override_store import grant, is_active, revoke

    grant("sess-1", now=T0)
    revoke("sess-1")
    assert is_active("sess-1", now=T0) is False


def test_no_grant_is_inactive(isolated_runtime) -> None:
    from core.services.override_store import is_active, level

    assert is_active("never", now=T0) is False
    assert level("never", now=T0) is None


def test_private_level_never_granted(isolated_runtime) -> None:
    # §6.4: private er hardblock — kan ALDRIG aktiveres som override-niveau.
    from core.services.override_store import grant, level

    grant("sess-1", level="private", now=T0)
    assert level("sess-1", now=T0) != "private"


def test_sessions_are_isolated(isolated_runtime) -> None:
    from core.services.override_store import grant, is_active

    grant("sess-A", now=T0)
    assert is_active("sess-A", now=T0) is True
    assert is_active("sess-B", now=T0) is False
