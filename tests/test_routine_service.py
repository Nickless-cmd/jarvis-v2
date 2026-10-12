from core.services.routine_types import RoutinePrincipal


def test_routine_service_requires_a_principal(isolated_runtime):
    from core.services.routine_service import RoutineService

    service = RoutineService()
    assert service.principal is None
    assert RoutinePrincipal("u1").canonical_user_id == "u1"
