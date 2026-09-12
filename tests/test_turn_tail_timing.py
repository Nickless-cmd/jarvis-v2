"""Maaleinstrumentet for halen efter svaret."""
import logging

from core.services import turn_tail_timing as tt


def setup_function():
    tt._nulstil_for_tests()


def test_en_KORT_hale_logger_ikke(caplog):
    # En linje pr. tur ville drukne i journalen og blive filtreret vaek.
    with caplog.at_level(logging.WARNING):
        tt.start("r1")
        tt.mark("r1", "persist")
        tt.slut("r1")
    assert "turn-tail" not in caplog.text


def test_en_LANG_hale_logger_HELE_opdelingen(caplog, monkeypatch):
    # Et samlet tal siger at det var langsomt, ikke HVOR.
    ur = iter([0.0, 0.1, 0.9, 1.4])
    monkeypatch.setattr(tt.time, "monotonic", lambda: next(ur))
    with caplog.at_level(logging.WARNING):
        tt.start("r1")
        tt.mark("r1", "persist")
        tt.mark("r1", "changelog")
        tt.slut("r1")
    assert "turn-tail" in caplog.text
    assert "persist=100ms" in caplog.text
    assert "changelog=800ms" in caplog.text


def test_mark_UDEN_start_er_gratis_og_tavs():
    # Instrumentet maa aldrig kunne vaelte det det maaler.
    tt.mark("aldrig-startet", "x")
    assert tt.slut("aldrig-startet") == 0.0


def test_et_tomt_run_id_ignoreres():
    tt.start("")
    assert tt._haler == {}


def test_haler_der_aldrig_slutter_hober_sig_IKKE_op():
    # Et run der doer midt i efterlader sin hale. Uden loftet ville de samle
    # sig for evigt i en proces der koerer i doegn.
    for i in range(tt._MAKS + 20):
        tt.start(f"r{i}")
    assert len(tt._haler) <= tt._MAKS


def test_det_er_den_AELDSTE_der_smides_ud(monkeypatch):
    # Den nye hale er den vi faktisk maaler; den gamle er netop den slags der
    # aldrig sluttede.
    monkeypatch.setattr(tt, "_MAKS", 3)
    for i in range(4):
        tt.start(f"r{i}")
    assert "r0" not in tt._haler and "r3" in tt._haler


def test_instrumentet_er_KOBLET_PAA():
    """Mekanismen findes-kalderen-mangler er husets hyppigste fejl.

    Et maaleinstrument ingen kalder maaler ingenting - og det er svaerere at
    opdage end en funktion der er brudt, fordi tavshed ligner «ikke langsomt».
    """
    import inspect
    from core.services import visible_runs
    kilde = inspect.getsource(visible_runs)
    for led in ("impact", "outcome", "persist", "changelog", "cost"):
        assert f'_hale.mark(run.run_id or "", "{led}")' in kilde, led
    assert '_hale.start(run.run_id or "")' in kilde
    assert '_hale.slut(run.run_id or "")' in kilde
