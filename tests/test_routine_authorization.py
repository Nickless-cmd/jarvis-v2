from core.services.routine_types import RoutinePrincipal


def test_house_owner_has_no_private_content_override():
    from core.services.routine_authorization import authorize

    decision = authorize(
        RoutinePrincipal("owner", role="owner"),
        "read_content",
        {"owner_user_id": "member", "access_scope": "user_private"},
    )
    assert decision.allowed is False
