def test_routine_reconciler_public_api():
    from core.services.routine_reconciler import RoutineReconciler

    assert callable(RoutineReconciler.reconcile_once)
    assert callable(RoutineReconciler.sweep_retention)
