"""Tests for visible_runs_memory mood sync integration."""
import pytest
from unittest.mock import patch
from core.services.continuity import sync_capsule_mood


class TestVisibleRunsMemoryMoodSync:
    def test_mood_sync_uses_continuity(self):
        """visible_runs_memory should use sync_capsule_mood from continuity."""
        # This is a smoke test — the real integration is tested via
        # test_continuity_mood_sync.py. Here we just verify the import works.
        assert callable(sync_capsule_mood)

    def test_mood_sync_does_not_use_ad_hoc_bearing(self):
        """The old ad-hoc bearing code should be gone — replaced by sync_capsule_mood."""
        import inspect
        from core.services import visible_runs_memory as vrm
        source = inspect.getsource(vrm)
        # The old code had get_current_mood as _gcm — should be gone
        assert "_gcm" not in source
        # Should reference sync_capsule_mood
        assert "sync_capsule_mood" in source