def test_delivery_service_has_no_session_surface():
    from core.services.routine_delivery import RoutineDeliveryService

    assert not hasattr(RoutineDeliveryService(), "session_id")
