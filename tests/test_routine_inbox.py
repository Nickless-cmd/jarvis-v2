def test_routine_inbox_event_type_is_non_gating():
    from core.services.inbox_state import IKKE_GATENDE_KILDETYPER

    assert "routine_event" in IKKE_GATENDE_KILDETYPER
