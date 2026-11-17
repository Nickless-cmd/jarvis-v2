def test_routine_trigger_adapter_public_api():
    from core.services.routine_trigger_adapters import (
        enqueue_recurring,
        enqueue_scheduled,
        enqueue_system,
    )

    assert all(callable(item) for item in (enqueue_recurring, enqueue_scheduled, enqueue_system))


def test_cutover_paa_umigreret_kilde_falder_tilbage_til_legacy(monkeypatch):
    """Cutover-listen er en hensigt, ikke en garanti.

    Regression 17/11-2026: en kilde der stod paa listen uden et gyldigt
    migrerings-link kunne hverken gaa rutine-vejen (intet link) eller
    legacy-vejen (cutover spaerrer) — og doede hvert minut, 1.440 gange i
    doegnet. Legacy-vejen er den vej der faktisk virker.
    """
    import core.services.routine_trigger_adapters as ad

    monkeypatch.setenv("JARVIS_ROUTINES_CUTOVER", "recurring:rec-umigreret")
    kaldt: list[bool] = []

    class _Stub:
        def enqueue_recurring(self, source_id, *, occurrence_id=None):
            raise ad.UnmigratedRoutineSource("no verified link")

    res = ad.dispatch_recurring(
        "rec-umigreret", legacy=lambda: kaldt.append(True), adapters=_Stub(),
    )

    assert kaldt == [True], "legacy-vejen skal koere naar rutine-vejen ikke kan"
    assert res is None, "None = legacy tog beslutningen, ikke en afvisning"
