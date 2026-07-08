from core.services import model_trust as mt


def test_unknown_model_is_weak(isolated_runtime):
    assert mt.model_strength("brand-new-model") == "weak"


def test_promotes_after_threshold_clean_runs(isolated_runtime, monkeypatch):
    monkeypatch.setattr(mt, "_PROMOTE_THRESHOLD", 3)
    for _ in range(3):
        mt.record_run_outcome("m1", degenerated=False)
    assert mt.model_strength("m1") == "strong"


def test_single_degeneration_reverts_strong_to_weak(isolated_runtime, monkeypatch):
    monkeypatch.setattr(mt, "_PROMOTE_THRESHOLD", 2)
    mt.record_run_outcome("m2", degenerated=False)
    mt.record_run_outcome("m2", degenerated=False)
    assert mt.model_strength("m2") == "strong"
    mt.record_run_outcome("m2", degenerated=True)
    assert mt.model_strength("m2") == "weak"


def test_degeneration_resets_streak(isolated_runtime, monkeypatch):
    monkeypatch.setattr(mt, "_PROMOTE_THRESHOLD", 3)
    mt.record_run_outcome("m3", degenerated=False)
    mt.record_run_outcome("m3", degenerated=True)
    mt.record_run_outcome("m3", degenerated=False)
    mt.record_run_outcome("m3", degenerated=False)
    assert mt.model_strength("m3") == "weak"


def test_owner_pin_overrides_earned(isolated_runtime, monkeypatch):
    monkeypatch.setattr(mt, "_PROMOTE_THRESHOLD", 1)
    mt.record_run_outcome("m4", degenerated=False)
    mt.set_pin("m4", "weak")
    assert mt.model_strength("m4") == "weak"
    mt.set_pin("m4", "strong")
    assert mt.model_strength("m4") == "strong"
    mt.set_pin("m4", "auto")
    assert mt.model_strength("m4") == "strong"


def test_model_strength_fails_open_weak(monkeypatch):
    monkeypatch.setattr(mt, "connect", lambda: (_ for _ in ()).throw(RuntimeError("db")))
    assert mt.model_strength("x") == "weak"


def test_surface_shape(isolated_runtime, monkeypatch):
    monkeypatch.setattr(mt, "_PROMOTE_THRESHOLD", 1)
    mt.record_run_outcome("claude-x", degenerated=False)
    surf = mt.build_model_trust_surface()
    assert surf["active"] and surf["threshold"] == 1
    assert any(m["model"] == "claude-x" and m["strength"] == "strong" for m in surf["models"])
