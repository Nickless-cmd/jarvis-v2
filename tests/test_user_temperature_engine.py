"""Tests for core.services.user_temperature_engine — combine_streams fix.

Pre-commit coverage gate requires tests/test_user_temperature_engine.py.
Existing tests live in tests/services/test_user_temperature_engine.py.
This file adds combine_streams-specific tests and re-exports the rest.
"""
from __future__ import annotations

from core.services.user_temperature_engine import combine_streams


class TestCombineStreamsLLMConfidence:
    """2026-06-11: LLM confidence override rules."""

    def test_llm_wins_when_structural_uncertain(self):
        """LLM confidence > 0.7 AND structural < 0.3 → LLM wins."""
        struct = {"valens": 0.0, "arousal": 0.18, "texture": "restless", "confidence": 0.18}
        llm = {"valens": -0.7, "arousal": 0.8, "texture": "frustrated", "confidence": 0.9}
        result = combine_streams(struct=struct, llm=llm)
        assert result["field_valens"] == -0.7, f"expected -0.7, got {result['field_valens']}"
        assert result["field_arousal"] == 0.8
        assert result["field_texture"] == "frustrated"
        assert result["field_conflict"] is True

    def test_structural_wins_when_no_llm(self):
        """No LLM → structural unchanged."""
        struct = {"valens": 0.0, "arousal": 0.18, "texture": "restless", "confidence": 0.5}
        result = combine_streams(struct=struct, llm=None)
        assert result["field_valens"] == 0.0
        assert result["field_texture"] == "restless"
        assert result["field_conflict"] is False

    def test_structural_wins_when_llm_low_confidence(self):
        """LLM confidence < 0.3 → structural unchanged."""
        struct = {"valens": 0.0, "arousal": 0.18, "texture": "restless", "confidence": 0.5}
        llm = {"valens": -0.7, "arousal": 0.8, "texture": "frustrated", "confidence": 0.2}
        result = combine_streams(struct=struct, llm=llm)
        assert result["field_valens"] == 0.0
        assert result["field_texture"] == "restless"

    def test_weighted_average_on_conflict_low_llm_confidence(self):
        """Conflict with moderate LLM confidence → weighted average."""
        struct = {"valens": 0.0, "arousal": 0.18, "texture": "restless", "confidence": 0.6}
        llm = {"valens": -0.5, "arousal": 0.6, "texture": "frustrated", "confidence": 0.5}
        result = combine_streams(struct=struct, llm=llm)
        # weighted: closer to structural (0.6 vs 0.5)
        assert -0.5 < result["field_valens"] < 0.0
        assert result["field_conflict"] is True

    def test_agreement_averages(self):
        """No conflict → simple average."""
        struct = {"valens": 0.3, "arousal": 0.4, "texture": "playful", "confidence": 0.6}
        llm = {"valens": 0.5, "arousal": 0.6, "texture": "playful", "confidence": 0.7}
        result = combine_streams(struct=struct, llm=llm)
        assert result["field_valens"] == 0.4  # (0.3 + 0.5) / 2
        assert result["field_conflict"] is False

    def test_llm_override_not_overridden_by_texture_mismatch(self):
        """Texture mismatch should NOT veto LLM override (override comes first)."""
        struct = {"valens": 0.1, "arousal": 0.1, "texture": "cool", "confidence": 0.2}
        llm = {"valens": -0.7, "arousal": 0.8, "texture": "frustrated", "confidence": 0.9}
        result = combine_streams(struct=struct, llm=llm)
        assert result["field_valens"] == -0.7  # LLM wins, not structural
        assert result["field_texture"] == "frustrated"
