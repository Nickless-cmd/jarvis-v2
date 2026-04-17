"""Tests for tiktok_research_daemon and the pool integration in tiktok_content_daemon."""
from __future__ import annotations

import json
import importlib
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pool(slot_type: str = "motivation", used: bool = False) -> dict:
    """Build a minimal pool dict for testing."""
    return {
        "generated_at": "2025-01-01T06:00:00+00:00",
        "concepts": [
            {
                "id": f"2025-01-01_{slot_type}_001",
                "type": slot_type,
                "text": "Test concept text",
                "hashtags": "#test #fyp",
                "used": used,
                "created": "2025-01-01T06:00:00+00:00",
            }
        ],
        "used_ids": [],
    }


# ---------------------------------------------------------------------------
# 1. test_returns_dict
# ---------------------------------------------------------------------------


def test_returns_dict(tmp_path):
    """tick returns a dict (mock LLM + file writes)."""
    import core.services.tiktok_research_daemon as mod

    # Reset module state
    mod._last_tick_at = None

    pool_file = tmp_path / "tiktok_content_pool.json"

    fake_llm_response = json.dumps(["Quote one", "Quote two", "Quote three"])

    with (
        patch.object(mod, "_POOL_PATH", pool_file),
        patch(
            "core.services.tiktok_research_daemon._generate_concepts_for_type",
            return_value=["A", "B", "C"],
        ),
    ):
        result = mod.tick_tiktok_research_daemon()

    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# 2. test_skips_if_generated_today
# ---------------------------------------------------------------------------


def test_skips_if_generated_today(tmp_path):
    """Second call on the same day returns skipped."""
    import core.services.tiktok_research_daemon as mod

    mod._last_tick_at = None

    pool_file = tmp_path / "tiktok_content_pool.json"
    today_str = datetime.now(UTC).date().isoformat()

    # Pre-populate pool with today's generated_at
    pool_file.write_text(
        json.dumps({
            "generated_at": f"{today_str}T06:00:00+00:00",
            "concepts": [],
            "used_ids": [],
        }),
        encoding="utf-8",
    )

    with patch.object(mod, "_POOL_PATH", pool_file):
        result = mod.tick_tiktok_research_daemon()

    assert result.get("skipped") is True
    assert result.get("reason") == "already_generated_today"


# ---------------------------------------------------------------------------
# 3. test_generates_concepts_for_all_types
# ---------------------------------------------------------------------------


def test_generates_concepts_for_all_types(tmp_path):
    """After tick, pool has concepts for all 3 slot types."""
    import core.services.tiktok_research_daemon as mod

    mod._last_tick_at = None

    pool_file = tmp_path / "tiktok_content_pool.json"

    with (
        patch.object(mod, "_POOL_PATH", pool_file),
        patch(
            "core.services.tiktok_research_daemon._generate_concepts_for_type",
            return_value=["A", "B", "C"],
        ),
    ):
        result = mod.tick_tiktok_research_daemon()

    assert result.get("generated") is True

    pool = json.loads(pool_file.read_text())
    types_in_pool = {c["type"] for c in pool["concepts"]}
    assert "motivation" in types_in_pool
    assert "dark_humor" in types_in_pool
    assert "cosmic" in types_in_pool


# ---------------------------------------------------------------------------
# 4. test_pool_file_written
# ---------------------------------------------------------------------------


def test_pool_file_written(tmp_path):
    """Pool file is written after a successful tick."""
    import core.services.tiktok_research_daemon as mod

    mod._last_tick_at = None

    pool_file = tmp_path / "tiktok_content_pool.json"
    assert not pool_file.exists()

    with (
        patch.object(mod, "_POOL_PATH", pool_file),
        patch(
            "core.services.tiktok_research_daemon._generate_concepts_for_type",
            return_value=["X", "Y", "Z"],
        ),
    ):
        mod.tick_tiktok_research_daemon()

    assert pool_file.exists()
    pool = json.loads(pool_file.read_text())
    assert "concepts" in pool
    assert len(pool["concepts"]) == 9  # 3 types × 3 concepts each


# ---------------------------------------------------------------------------
# 5. test_pool_integration_in_content_daemon
# ---------------------------------------------------------------------------


def test_pool_integration_returns_concept_when_available(tmp_path):
    """_get_concept_from_pool returns (text, hashtags) when pool has unused concept."""
    import core.services.tiktok_content_daemon as mod

    pool_file = tmp_path / "tiktok_content_pool.json"
    pool_data = _make_pool(slot_type="motivation", used=False)
    pool_file.write_text(json.dumps(pool_data), encoding="utf-8")

    with patch.object(mod, "_POOL_PATH", pool_file):
        result = mod._get_concept_from_pool("motivation")

    assert result is not None
    text, hashtags = result
    assert text == "Test concept text"
    assert hashtags == "#test #fyp"

    # Verify the concept is now marked used
    updated = json.loads(pool_file.read_text())
    assert updated["concepts"][0]["used"] is True
    assert "2025-01-01_motivation_001" in updated["used_ids"]


def test_pool_integration_returns_none_when_empty(tmp_path):
    """_get_concept_from_pool returns None when pool has no unused concept."""
    import core.services.tiktok_content_daemon as mod

    pool_file = tmp_path / "tiktok_content_pool.json"
    pool_data = _make_pool(slot_type="motivation", used=True)
    pool_file.write_text(json.dumps(pool_data), encoding="utf-8")

    with patch.object(mod, "_POOL_PATH", pool_file):
        result = mod._get_concept_from_pool("motivation")

    assert result is None


def test_pool_integration_returns_none_when_file_missing(tmp_path):
    """_get_concept_from_pool returns None when pool file does not exist."""
    import core.services.tiktok_content_daemon as mod

    pool_file = tmp_path / "nonexistent_pool.json"

    with patch.object(mod, "_POOL_PATH", pool_file):
        result = mod._get_concept_from_pool("motivation")

    assert result is None
