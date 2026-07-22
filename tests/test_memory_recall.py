"""Unit tests for memory recall section builder — udskilt fra prompt_contract.py.

Dækker alle funktioner i core.services.prompt_sections.memory_recall.
Kræver ingen runtime-setup — alle eksterne afhængigheder mockes.
"""
from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest


def _module():
    return importlib.import_module(
        "core.services.prompt_sections.memory_recall"
    )


# ---------------------------------------------------------------------------
# _clip_line — ren funktion, ingen mocking
# ---------------------------------------------------------------------------


class TestClipLine:
    def test_short_line_unchanged(self) -> None:
        result = _module()._clip_line("short", limit=100)
        assert result == "short"

    def test_long_line_clipped(self) -> None:
        long_text = "a" * 200
        result = _module()._clip_line(long_text, limit=100)
        # clip_text (default hard=False) keeps `limit` content chars and appends
        # the ellipsis on top — total may exceed limit by one char.
        assert len(result) == 101
        assert result.endswith("…")

    def test_exact_fit(self) -> None:
        text = "x" * 50
        result = _module()._clip_line(text, limit=50)
        assert result == text
        assert not result.endswith("…")

    def test_whitespace_collapsed(self) -> None:
        result = _module()._clip_line("hello    world", limit=100)
        assert result == "hello world"

    def test_none_handling(self) -> None:
        result = _module()._clip_line(None, limit=100)  # type: ignore
        assert result == ""

    def test_custom_limit(self) -> None:
        result = _module()._clip_line("hello world", limit=5)
        # 5 content chars ("hello") + ellipsis = 6 (default hard=False).
        assert len(result) == 6
        assert result.endswith("…")


# ---------------------------------------------------------------------------
# _private_brain_recall_lines — kræver mock af session_distillation
# ---------------------------------------------------------------------------


class TestPrivateBrainRecallLines:
    def test_returns_empty_on_import_error(self) -> None:
        """Hvis session_distillation ikke kan importeres, returner []."""
        with patch.dict("sys.modules", {"core.services.session_distillation": None}):
            result = _module()._private_brain_recall_lines(limit=3)
            assert result == []

    def test_returns_empty_when_no_active_brain(self) -> None:
        """Hvis brain ikke er active, returner []."""
        mock_brain = MagicMock()
        mock_brain.build_private_brain_context.return_value = {"active": False}

        with patch(
            "core.services.session_distillation.build_private_brain_context",
            return_value={"active": False},
        ):
            result = _module()._private_brain_recall_lines(limit=3)
            assert result == []

    def test_returns_lines_from_active_brain(self) -> None:
        brain_data = {
            "active": True,
            "continuity_summary": "This is a continuity summary for testing.",
            "excerpts": [
                {"summary": "Excerpt one content.", "focus": "focus1"},
                {"summary": "Excerpt two content.", "focus": None},
            ],
        }

        with patch(
            "core.services.session_distillation.build_private_brain_context",
            return_value=brain_data,
        ):
            result = _module()._private_brain_recall_lines(limit=3)
            assert len(result) == 3  # summary + 2 excerpts
            assert "continuity summary" in result[0]
            assert "focus1: Excerpt one" in result[1]

    def test_respects_limit(self) -> None:
        brain_data = {
            "active": True,
            "continuity_summary": "Summary.",
            "excerpts": [
                {"summary": f"Excerpt {i}.", "focus": None}
                for i in range(10)
            ],
        }

        with patch(
            "core.services.session_distillation.build_private_brain_context",
            return_value=brain_data,
        ):
            result = _module()._private_brain_recall_lines(limit=2)
            # summary + 1 excerpt (limit applies to excerpt count)
            assert len(result) <= 3


# ---------------------------------------------------------------------------
# _recent_tool_recall_lines — kræver mock af chat_sessions + tool_result_store
# ---------------------------------------------------------------------------


class TestRecentToolRecallLines:
    def test_returns_empty_without_session_id(self) -> None:
        result = _module()._recent_tool_recall_lines(None, limit=3)
        assert result == []

    def test_returns_lines_for_session(self) -> None:
        mock_messages = [
            {"content": "Tool result: file read ok"},
            {"content": "Tool result: search found 3 items"},
        ]

        with patch(
            "core.services.prompt_sections.memory_recall.recent_chat_tool_messages",
            return_value=mock_messages,
        ), patch(
            "core.services.prompt_sections.memory_recall.render_tool_result_for_prompt",
            return_value="rendered content",
        ):
            result = _module()._recent_tool_recall_lines("session-1", limit=3)
            assert len(result) == 2
            assert all("rendered content" in line for line in result)

    def test_respects_limit(self) -> None:
        mock_messages = [{"content": f"msg {i}"} for i in range(10)]

        with patch(
            "core.services.prompt_sections.memory_recall.recent_chat_tool_messages",
            return_value=mock_messages,
        ), patch(
            "core.services.prompt_sections.memory_recall.render_tool_result_for_prompt",
            return_value="rendered",
        ):
            result = _module()._recent_tool_recall_lines("session-1", limit=3)
            assert len(result) == 3

    def test_handles_exception_gracefully(self) -> None:
        with patch(
            "core.services.prompt_sections.memory_recall.recent_chat_tool_messages",
            side_effect=Exception("DB error"),
        ):
            result = _module()._recent_tool_recall_lines("session-1", limit=3)
            assert result == []

    def test_skips_empty_content(self) -> None:
        mock_messages = [
            {"content": "valid"},
            {"content": ""},
            {"content": "also valid"},
        ]

        with patch(
            "core.services.prompt_sections.memory_recall.recent_chat_tool_messages",
            return_value=mock_messages,
        ), patch(
            "core.services.prompt_sections.memory_recall.render_tool_result_for_prompt",
            side_effect=lambda c, **kw: c if c else "",
        ):
            result = _module()._recent_tool_recall_lines("session-1", limit=5)
            assert len(result) == 2


# ---------------------------------------------------------------------------
# _memory_candidate_recall_lines — kræver mock af db.list_runtime_contract_candidates
# ---------------------------------------------------------------------------


class TestMemoryCandidateRecallLines:
    def test_returns_empty_on_exception(self) -> None:
        with patch(
            "core.services.prompt_sections.memory_recall.list_runtime_contract_candidates",
            side_effect=Exception("DB error"),
        ):
            result = _module()._memory_candidate_recall_lines(limit=3)
            assert result == []

    def test_returns_lines_from_candidates(self) -> None:
        # Summaries skal være ≥5 ord (vag-filter) og ikke-vage/dubletter.
        candidates = [
            {"summary": "Bjørn foretrækker korte svar på simple repo-opgaver", "confidence": "high"},
            {"summary": "Brug altid conda activate ai til Python-miljøet her", "confidence": "medium"},
        ]
        with patch(
            "core.services.prompt_sections.memory_recall.list_runtime_contract_candidates",
            return_value=candidates,
        ), patch(
            "core.services.prompt_sections.memory_recall._resolve_user_id", return_value="",
        ), patch(
            "core.services.prompt_sections.memory_recall._is_semantic_dup_of_memory", return_value=False,
        ):
            result = _module()._memory_candidate_recall_lines(limit=3)
            assert len(result) == 2
            assert "confidence=high" in result[0]
            assert "confidence=medium" in result[1]

    def test_respects_limit(self) -> None:
        candidates = [
            {"summary": f"Konkret lærings-kandidat nummer {i} med nok ord her", "confidence": "low"}
            for i in range(10)
        ]
        with patch(
            "core.services.prompt_sections.memory_recall.list_runtime_contract_candidates",
            return_value=candidates,
        ), patch(
            "core.services.prompt_sections.memory_recall._resolve_user_id", return_value="",
        ), patch(
            "core.services.prompt_sections.memory_recall._is_semantic_dup_of_memory", return_value=False,
        ):
            result = _module()._memory_candidate_recall_lines(limit=2)
            assert len(result) == 2


# ---------------------------------------------------------------------------
# _visible_memory_recall_bundle_section — integration af alle ovenstående
# ---------------------------------------------------------------------------


class TestVisibleMemoryRecallBundleSection:
    def test_returns_none_when_no_content(self) -> None:
        """Hvis alle sub-funktioner returnerer tomme lister, returner None."""
        with patch(
            "core.services.prompt_sections.memory_recall._private_brain_recall_lines",
            return_value=[],
        ), patch(
            "core.services.prompt_sections.memory_recall._recent_tool_recall_lines",
            return_value=[],
        ), patch(
            "core.services.prompt_sections.memory_recall._memory_candidate_recall_lines",
            return_value=[],
        ):
            result = _module()._visible_memory_recall_bundle_section(
                session_id="session-1",
                user_message="test",
                compact=False,
            )
            assert result is None

    def test_includes_private_brain_section(self) -> None:
        with patch(
            "core.services.prompt_sections.memory_recall._private_brain_recall_lines",
            return_value=["brain line 1", "brain line 2"],
        ), patch(
            "core.services.prompt_sections.memory_recall._recent_tool_recall_lines",
            return_value=[],
        ), patch(
            "core.services.prompt_sections.memory_recall._memory_candidate_recall_lines",
            return_value=[],
        ):
            result = _module()._visible_memory_recall_bundle_section(
                session_id="session-1",
                user_message="test",
                compact=False,
            )
            assert result is not None
            assert "Private continuity" in result
            assert "brain line 1" in result

    def test_includes_tool_section(self) -> None:
        with patch(
            "core.services.prompt_sections.memory_recall._private_brain_recall_lines",
            return_value=[],
        ), patch(
            "core.services.prompt_sections.memory_recall._recent_tool_recall_lines",
            return_value=["tool: read file"],
        ), patch(
            "core.services.prompt_sections.memory_recall._memory_candidate_recall_lines",
            return_value=[],
        ):
            result = _module()._visible_memory_recall_bundle_section(
                session_id="session-1",
                user_message="test",
                compact=False,
            )
            assert result is not None
            assert "Internal tool observations" in result
            assert "tool: read file" in result

    def test_includes_candidate_section(self) -> None:
        with patch(
            "core.services.prompt_sections.memory_recall._private_brain_recall_lines",
            return_value=[],
        ), patch(
            "core.services.prompt_sections.memory_recall._recent_tool_recall_lines",
            return_value=[],
        ), patch(
            "core.services.prompt_sections.memory_recall._memory_candidate_recall_lines",
            return_value=["candidate: test"],
        ):
            result = _module()._visible_memory_recall_bundle_section(
                session_id="session-1",
                user_message="test",
                compact=False,
            )
            assert result is not None
            assert "Pending memory candidates" in result

    def test_compact_reduces_limits(self) -> None:
        """Compact mode sender lavere limits til sub-funktioner."""
        with patch(
            "core.services.prompt_sections.memory_recall._private_brain_recall_lines",
            return_value=["brain"] * 3,
        ) as mock_brain, patch(
            "core.services.prompt_sections.memory_recall._recent_tool_recall_lines",
            return_value=["tool"] * 5,
        ) as mock_tool, patch(
            "core.services.prompt_sections.memory_recall._memory_candidate_recall_lines",
            return_value=["candidate"] * 3,
        ) as mock_cand:
            _module()._visible_memory_recall_bundle_section(
                session_id="session-1",
                user_message="test",
                compact=True,
            )
            # Compact = limit=3 for brain, 3 for tool, 2 for candidates
            assert mock_brain.call_args[1]["limit"] == 3
            assert mock_tool.call_args[1]["limit"] == 3
            assert mock_cand.call_args[1]["limit"] == 2

    def test_non_compact_uses_full_limits(self) -> None:
        with patch(
            "core.services.prompt_sections.memory_recall._private_brain_recall_lines",
            return_value=["brain"],
        ) as mock_brain, patch(
            "core.services.prompt_sections.memory_recall._recent_tool_recall_lines",
            return_value=["tool"],
        ) as mock_tool, patch(
            "core.services.prompt_sections.memory_recall._memory_candidate_recall_lines",
            return_value=["candidate"],
        ) as mock_cand:
            _module()._visible_memory_recall_bundle_section(
                session_id="session-1",
                user_message="test",
                compact=False,
            )
            assert mock_brain.call_args[1]["limit"] == 4
            assert mock_tool.call_args[1]["limit"] == 5
            assert mock_cand.call_args[1]["limit"] == 3

    def test_appends_continuity_disclaimer(self) -> None:
        with patch(
            "core.services.prompt_sections.memory_recall._private_brain_recall_lines",
            return_value=["brain line"],
        ), patch(
            "core.services.prompt_sections.memory_recall._recent_tool_recall_lines",
            return_value=[],
        ), patch(
            "core.services.prompt_sections.memory_recall._memory_candidate_recall_lines",
            return_value=[],
        ):
            result = _module()._visible_memory_recall_bundle_section(
                session_id="session-1",
                user_message="test",
                compact=False,
            )
            assert result is not None
            assert "bounded continuity support" in result


def test_md_line_vecs_cached_and_semantic_dup_uses_cache(monkeypatch, tmp_path):
    """Audit 2026-07-23: the semantic dedup must embed ONLY the candidate text against
    cached MEMORY.md line vectors — not re-embed the (long) MEMORY.md lines every turn."""
    import numpy as np
    from core.services.prompt_sections import memory_recall as mr

    calls = {"n": 0, "sizes": []}

    def _fake_embed(texts):
        calls["n"] += 1
        calls["sizes"].append(len(texts))
        # deterministic unit vectors; identical text → identical vector
        out = []
        for t in texts:
            v = np.zeros(8, dtype=np.float32)
            v[len(t) % 8] = 1.0
            out.append(v)
        return out

    monkeypatch.setattr("core.services.jarvis_brain._embed_texts", _fake_embed)
    # seed the vector cache directly (skip the background thread / real file)
    lines = ["cluster priority auth loop scheduling fix landed today", "unrelated note about voice mic gain"]
    mr._MD_VECS_CACHE.update(
        mtime="test", building=False,
        vecs={ln: _fake_embed([ln])[0] for ln in lines},
    )
    monkeypatch.setattr(mr, "_md_line_vecs", lambda user_id="": mr._MD_VECS_CACHE["vecs"])
    calls["n"] = 0
    calls["sizes"] = []
    # a candidate that shares ≥2 keywords with a cached line
    mr._is_semantic_dup_of_memory("cluster priority auth loop scheduling fix", "")
    # exactly ONE embed call, of size 1 (only the candidate) — the corpus is cached
    assert calls["n"] == 1
    assert calls["sizes"] == [1]


def test_md_line_vecs_empty_cache_falls_back(monkeypatch):
    from core.services.prompt_sections import memory_recall as mr
    monkeypatch.setattr(mr, "_md_line_vecs", lambda user_id="": {})
    # empty cache → no crash, returns False (literal match handles it)
    assert mr._is_semantic_dup_of_memory("some candidate text with words", "") is False
