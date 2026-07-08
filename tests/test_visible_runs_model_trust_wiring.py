"""Harness Part 1: verify the earned-model-trust wiring is present in the agentic loop."""
import inspect
from core.services import visible_runs as vr


def test_run_degenerated_flag_and_record_present():
    src = inspect.getsource(vr)
    assert "_run_degenerated" in src
    assert "record_run_outcome" in src
    assert "from core.services.model_trust import record_run_outcome" in src


def test_degeneration_marks_at_no_progress_and_hollow_promise():
    src = inspect.getsource(vr)
    # marked at the two loop-spin points
    assert src.count("_run_degenerated = True") >= 2
    # finalize folds in terminal failure statuses
    assert '"failed", "interrupted", "cancelled"' in src or "'failed', 'interrupted', 'cancelled'" in src
