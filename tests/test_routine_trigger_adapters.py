def test_routine_trigger_adapter_public_api():
    from core.services.routine_trigger_adapters import (
        enqueue_recurring,
        enqueue_scheduled,
        enqueue_system,
    )

    assert all(callable(item) for item in (enqueue_recurring, enqueue_scheduled, enqueue_system))
