"""End-to-end: hele owner-override-flowet (TOTP Fase 7, spec §10.6).

Service-niveau e2e (ingen live Discord-klient): seed → !override (forkert+rigtig) →
elevering → fornyelse → to-akse-tjek (kontrol ja, privatliv nej) → revoke → udløb.
"""
from __future__ import annotations

import time


SEED = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
FSESSION = "mikkel-discord-1"  # fremmed (member) session


def _code(ts=None):
    from core.services.totp_verifier import generate_code
    return generate_code(SEED, timestamp=ts if ts is not None else time.time())


def test_full_override_flow(isolated_runtime) -> None:
    from core.identity.workspace_context import set_context, reset_context, effective_role
    from core.services.override_command import handle_override_command
    from core.services.override_store import is_active

    now = time.time()

    # 1. Fremmed member-session UDEN override → member-rolle (ingen elevering)
    tok = set_context(workspace_name="mikkel", user_id="u-mikkel", role="member", session_id=FSESSION)
    try:
        assert effective_role() == "member"
    finally:
        reset_context(tok)

    # 2. Forkert kode → afvist, ingen override
    r = handle_override_command("!override 000000", session_id=FSESSION, owner_seed=SEED, now=now)
    assert r["ok"] is False and r["reason"] == "invalid_code"
    assert is_active(FSESSION, now=now) is False

    # 3. Rigtig kode → override aktiveret
    r = handle_override_command(f"!override {_code(now)}", session_id=FSESSION, owner_seed=SEED, now=now)
    assert r["ok"] is True and r["action"] == "granted"
    assert is_active(FSESSION, now=now) is True

    # 4. Nu eleverer samme session til owner (kontrol-aksen)
    tok = set_context(workspace_name="mikkel", user_id="u-mikkel", role="member", session_id=FSESSION)
    try:
        assert effective_role() == "owner"
    finally:
        reset_context(tok)

    # 5. !revoke-override → lukket → tilbage til member
    r = handle_override_command("!revoke-override", session_id=FSESSION, owner_seed=SEED, now=now)
    assert r["action"] == "revoked"
    assert is_active(FSESSION, now=now) is False
    tok = set_context(workspace_name="mikkel", user_id="u-mikkel", role="member", session_id=FSESSION)
    try:
        assert effective_role() == "member"
    finally:
        reset_context(tok)


def test_override_auto_expires(isolated_runtime) -> None:
    from core.services.override_command import handle_override_command
    from core.services.override_store import is_active

    now = 1_000_000.0
    handle_override_command(f"!override {_code(now)}", session_id="s-exp", owner_seed=SEED, now=now)
    assert is_active("s-exp", now=now + 50) is True       # inden for 90s-vindue
    assert is_active("s-exp", now=now + 120) is False     # udløbet (ingen aktivitet)


def test_override_does_not_bypass_privacy_axis(isolated_runtime) -> None:
    # To-akse-modellen (§6.0): override giver KONTROL, men §4.4 share-guard +
    # §5.3 plugin-regelsæt forbliver hardblock selv med aktiv override.
    from core.services.override_store import grant
    from core.services.cross_user_share_guard import check_outbound
    from core.services.plugin_ruleset import is_allowed

    grant(FSESSION, now=time.time())

    # Share-guard flagger STADIG cross-user-omtale (override bypasser ikke privatliv)
    res = check_outbound("Mor sagde det til mig", current_user_id="u-mikkel",
                         known_users=[{"id": "u-mor", "name": "Mor"}])
    assert res["needs_confirmation"] is True

    # Plugin-regelsæt er hardblock for ALLE inkl. override (override_active ignoreres)
    ok, _ = is_allowed({"channel": "random"}, {"allowed_channels": ["general"]}, override_active=True)
    assert ok is False
