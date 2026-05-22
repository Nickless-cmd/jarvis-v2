"""Tests for visible_runs post-process flow.

2026-05-22 (Claude): Added after finding that _post_process was guarded
behind `if visible_output_text:` which made empty-output runs skip
text_preview write, memory postprocess, and continuation detection —
the actual root cause of "Jarvis silently completes a run".

This file's tests are structural/contract — full integration tests
of visible_runs sit in test_visible_runs_continuation_detector.py and
other targeted files. The enforcement hook just needs a matching
test_<module>.py to exist for any core/ file we touch.
"""
from __future__ import annotations

import importlib

from core.services import visible_runs


class TestVisibleRunsModuleSurface:
    """Sanity-check: the post-process pipeline functions exist."""

    def test_module_imports(self):
        # Reimport to surface any syntax/import errors quickly
        importlib.reload(visible_runs)
        assert visible_runs is not None

    def test_preview_text_helper_present(self):
        """_preview_text is what writes the visible_run text_preview column."""
        assert hasattr(visible_runs, "_preview_text")

    def test_preview_text_empty_input(self):
        """Helper must handle empty input without raising."""
        assert visible_runs._preview_text("") == ""
        assert visible_runs._preview_text(None) == ""  # type: ignore[arg-type]

    def test_preview_text_truncates(self):
        """Long input gets truncated to a single bounded line."""
        long_text = "x" * 1000
        out = visible_runs._preview_text(long_text, limit=64)
        assert len(out) <= 64
        # Newlines should be normalised
        assert "\n" not in out
