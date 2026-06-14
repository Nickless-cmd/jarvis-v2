from __future__ import annotations

KNOWN = [
    {"id": "u-bjorn", "name": "Bjørn"},
    {"id": "u-mikkel", "name": "Mikkel"},
    {"id": "u-mor", "name": "Mor"},
]


def test_mentions_other_user_needs_confirmation() -> None:
    from core.services.cross_user_share_guard import check_outbound

    r = check_outbound(
        "Mikkel sagde i går at han var træt af projektet.",
        current_user_id="u-bjorn",
        known_users=KNOWN,
    )
    assert r["needs_confirmation"] is True
    assert "Mikkel" in r["mentioned_users"]
    assert r["prompt"]  # ikke-tom


def test_no_cross_user_mention_is_fine() -> None:
    from core.services.cross_user_share_guard import check_outbound

    r = check_outbound(
        "Klart, jeg fixer den fil med det samme.",
        current_user_id="u-bjorn",
        known_users=KNOWN,
    )
    assert r["needs_confirmation"] is False
    assert r["mentioned_users"] == []


def test_mentioning_only_current_user_is_fine() -> None:
    from core.services.cross_user_share_guard import check_outbound

    # At tale med Bjørn om Bjørn selv er ikke kryds-bruger-deling
    r = check_outbound(
        "Bjørn, du bad mig om at huske det.",
        current_user_id="u-bjorn",
        known_users=KNOWN,
    )
    assert r["needs_confirmation"] is False


def test_case_insensitive_word_boundary() -> None:
    from core.services.cross_user_share_guard import check_outbound

    # 'mikkel' lower-case skal fanges
    assert check_outbound("Jeg talte med mikkel.", current_user_id="u-bjorn", known_users=KNOWN)["needs_confirmation"] is True
    # Men ikke som delstreng inde i et andet ord
    assert check_outbound("Mormor kom på besøg.", current_user_id="u-bjorn", known_users=KNOWN)["needs_confirmation"] is False


def test_empty_inputs_safe() -> None:
    from core.services.cross_user_share_guard import check_outbound

    assert check_outbound("", current_user_id="u-bjorn", known_users=KNOWN)["needs_confirmation"] is False
    assert check_outbound("hej Mikkel", current_user_id="u-bjorn", known_users=[])["needs_confirmation"] is False


def test_multiple_other_users() -> None:
    from core.services.cross_user_share_guard import check_outbound

    r = check_outbound(
        "Både Mikkel og Mor spurgte til dig.",
        current_user_id="u-bjorn",
        known_users=KNOWN,
    )
    assert r["needs_confirmation"] is True
    assert set(r["mentioned_users"]) == {"Mikkel", "Mor"}


def test_check_against_registry(tmp_path, monkeypatch) -> None:
    # Isolér users.json og registrér to brugere.
    monkeypatch.setattr("core.runtime.config.CONFIG_DIR", tmp_path)
    from core.identity.users import add_user
    from core.services.cross_user_share_guard import check_against_registry

    add_user(discord_id="d-bjorn", name="Bjørn", role="owner")
    add_user(discord_id="d-mikkel", name="Mikkel", role="member")

    # Bjørns session, svar nævner Mikkel → flag
    r = check_against_registry("Mikkel bad mig sige hej.", current_user_id="d-bjorn")
    assert r["needs_confirmation"] is True and "Mikkel" in r["mentioned_users"]

    # Svar uden cross-user-omtale → ok
    r2 = check_against_registry("Klart, det fixer jeg.", current_user_id="d-bjorn")
    assert r2["needs_confirmation"] is False
