from core.services.routine_types import (
    AccessScope,
    RoutineCreate,
    RoutinePatch,
    RoutineStatus,
    RunStatus,
)


def test_routine_value_objects_keep_domain_states_and_sparse_patches():
    command = RoutineCreate(
        name="Morgen",
        instruction=b"goer noget",
        capability_scope="chat",
        trigger_kind="manual",
    )
    assert command.access_scope is AccessScope.USER_PRIVATE
    assert {state.value for state in RoutineStatus} == {
        "draft", "active", "paused", "stopped", "archived", "deleted",
    }
    assert "cancelling" in {state.value for state in RunStatus}
    assert RoutinePatch(name="Nyt").changes() == {"name": "Nyt"}
