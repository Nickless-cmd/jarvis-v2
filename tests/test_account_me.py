from apps.api.jarvis_api.routes.account import build_account_profile


def test_owner_profile_defaults():
    prof = build_account_profile("", get_user=lambda uid: None, get_tier=lambda uid: "owner")
    assert prof == {
        "user_id": "",
        "email": "",
        "email_verified": True,
        "language": "da",
        "role": "owner",
        "tier": "owner",
        "google_linked": False,
    }


def test_google_linked_flag_reflects_callback():
    prof = build_account_profile(
        "u_bjorn", get_user=lambda uid: {"role": "owner"}, get_tier=lambda uid: "owner",
        is_google_linked=lambda uid: uid == "u_bjorn",
    )
    assert prof["google_linked"] is True
    prof2 = build_account_profile(
        "u_other", get_user=lambda uid: {}, get_tier=lambda uid: "free",
        is_google_linked=lambda uid: False,
    )
    assert prof2["google_linked"] is False


def test_member_profile_from_user_db():
    row = {"user_id": "u_mikkel", "email": "m@x.dk", "email_verified": False,
           "role": "member", "tier": "plus", "language": "en"}
    prof = build_account_profile("u_mikkel", get_user=lambda uid: row, get_tier=lambda uid: "plus")
    assert prof["email"] == "m@x.dk"
    assert prof["email_verified"] is False
    assert prof["language"] == "en"
    assert prof["role"] == "member"
    assert prof["tier"] == "plus"


def test_member_missing_language_defaults_to_da():
    row = {"user_id": "u_a", "email": "a@x.dk", "email_verified": True, "role": "member"}
    prof = build_account_profile("u_a", get_user=lambda uid: row, get_tier=lambda uid: "free")
    assert prof["language"] == "da"
    assert prof["tier"] == "free"
