"""Persist-lag for private signals — novelty-gate mod retained-memory-ekko (aug 2026)."""
from __future__ import annotations


def test_norm_retained_collapses_whitespace_and_case():
    from core.runtime.db_private_signals import _norm_retained
    assert _norm_retained("  Keep   Carrying  What HELPED ") == "keep carrying what helped"
    assert _norm_retained("") == ""
    assert _norm_retained(None) == ""  # type: ignore[arg-type]


def test_novelty_gate_skips_echo_persist(isolated_runtime):
    """record_private_retained_memory_record skipper en record hvis retained_value ==
    seneste (normaliseret). Regression: ~20 identiske "keep carrying what helped…"."""
    from core.runtime.db_private_signals import (
        record_private_retained_memory_record as rec,
        recent_private_retained_memory_records as recent,
    )
    common = dict(source="s", work_id="w", retained_kind="reinforced pattern",
                  retention_scope="development", retention_horizon="persistent", confidence="high")
    rec(record_id="a", run_id="run-a", retained_value="keep carrying what helped",
        created_at="2026-08-15T00:00:00+00:00", **common)
    # identisk value (kun whitespace/case forskel), ny run → ekko → skal skippes
    rec(record_id="b", run_id="run-b", retained_value="  Keep   carrying what HELPED ",
        created_at="2026-08-15T01:00:00+00:00", **common)
    assert len(recent(limit=10)) == 1
    # genuint ny value → persisteres
    rec(record_id="c", run_id="run-c", retained_value="en helt ny lektie i dag",
        created_at="2026-08-15T02:00:00+00:00", **common)
    assert len(recent(limit=10)) == 2
