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

    def test_includes_current_query_recall(self) -> None:
        seen = {}
        with patch(
            "core.services.recall.recall",
            side_effect=lambda query, **kwargs: (
                seen.update(query=query, kwargs=kwargs) or {
                    "delivery_status": "delivered",
                    "results": [{"source": "brain", "text": "current line"}],
                }
            ),
        ), patch(
            "core.services.prompt_sections.memory_recall._recent_tool_recall_lines",
            return_value=[],
        ):
            result = _module()._visible_memory_recall_bundle_section(
                session_id="session-1",
                user_message="test",
                compact=False,
            )
            assert result is not None
            assert seen["query"] == "test"
            assert "[brain] current line" in result

    def test_includes_tool_section(self) -> None:
        with patch(
            "core.services.recall.recall",
            return_value={"delivery_status": "empty", "results": []},
        ), patch(
            "core.services.prompt_sections.memory_recall._recent_tool_recall_lines",
            return_value=["tool: read file"],
        ):
            result = _module()._visible_memory_recall_bundle_section(
                session_id="session-1",
                user_message="test",
                compact=False,
            )
            assert result is not None
            assert "Internal tool observations" in result
            assert "tool: read file" in result

    def test_does_not_include_pending_candidate_or_stale_private_sections(self) -> None:
        with patch(
            "core.services.recall.recall",
            return_value={"delivery_status": "empty", "results": []},
        ), patch(
            "core.services.prompt_sections.memory_recall._recent_tool_recall_lines",
            return_value=[],
        ), patch(
            "core.services.prompt_sections.memory_recall._memory_candidate_recall_lines",
            return_value=["candidate: test"],
        ) as candidates:
            result = _module()._visible_memory_recall_bundle_section(
                session_id="session-1",
                user_message="test",
                compact=False,
            )
            assert result is None
            candidates.assert_not_called()

    def test_compact_reduces_limits(self) -> None:
        """Compact mode requests fewer current-query hits."""
        with patch(
            "core.services.recall.recall",
            return_value={"delivery_status": "empty", "results": []},
        ) as mock_recall, patch(
            "core.services.prompt_sections.memory_recall._recent_tool_recall_lines",
            return_value=[],
        ) as mock_tool:
            _module()._visible_memory_recall_bundle_section(
                session_id="session-1",
                user_message="test",
                compact=True,
            )
            assert mock_recall.call_args[1]["limit"] == 3
            assert mock_tool.call_args[1]["limit"] == 3

    def test_non_compact_uses_full_limits(self) -> None:
        with patch(
            "core.services.recall.recall",
            return_value={"delivery_status": "empty", "results": []},
        ) as mock_recall, patch(
            "core.services.prompt_sections.memory_recall._recent_tool_recall_lines",
            return_value=[],
        ) as mock_tool:
            _module()._visible_memory_recall_bundle_section(
                session_id="session-1",
                user_message="test",
                compact=False,
            )
            assert mock_recall.call_args[1]["limit"] == 5
            assert mock_tool.call_args[1]["limit"] == 5

    def test_appends_continuity_disclaimer(self) -> None:
        with patch(
            "core.services.recall.recall",
            return_value={
                "delivery_status": "delivered",
                "results": [{"source": "brain", "text": "brain line"}],
            },
        ), patch(
            "core.services.prompt_sections.memory_recall._recent_tool_recall_lines",
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


def test_md_line_vecs_genbruger_uaendrede_linjer(monkeypatch, tmp_path):
    """11/10-2026: `_build` gen-indlejrede ALLE MEMORY.md-linjer ved hvert mtime-skift.

    Målt: MEMORY.md var 16.642 linjer (10.102 embeddet), og hver skrivning til
    filen udløste en fuld gen-indlejring — ~2.000 embed-kald i minuttet i bursts.

    Nøglen er linje-TEKSTEN, og en vektor er deterministisk for sin tekst. Så en
    linje der ikke er ændret har præcis samme vektor og skal IKKE embeddes igen.
    Denne test låser det: efter en skrivning der tilføjer 2 linjer, må KUN de 2
    embeddes — ikke alle 52.
    """
    import os
    import time

    import numpy as np

    from core.services.prompt_sections import memory_recall as mr

    kaldte: list[list[str]] = []

    def _fake_embed(texts):
        kaldte.append(list(texts))
        return [np.zeros(4, dtype=np.float32) for _ in texts]

    monkeypatch.setattr("core.services.jarvis_brain._embed_texts", _fake_embed)

    md = tmp_path / "MEMORY.md"
    md.write_text("start", encoding="utf-8")
    monkeypatch.setattr(
        "core.runtime.workspace_paths.workspace_dir", lambda *a, **k: tmp_path
    )

    def _vent() -> None:
        for _ in range(500):
            if not mr._MD_VECS_CACHE.get("building"):
                return
            time.sleep(0.01)
        raise AssertionError("baggrunds-traaden byggede aldrig faerdig")

    linjer = [f"linje nummer {i} med tilstraekkeligt indhold til at blive embeddet" for i in range(50)]
    monkeypatch.setattr(mr, "_memory_md_lines", lambda user_id="": list(linjer))

    # ── foerste bygning: alle 50 embeddes (kold cache) ──
    mr._MD_VECS_CACHE.update(mtime=None, vecs={}, building=False)
    kaldte.clear()
    mr._md_line_vecs("")
    _vent()
    assert sum(len(k) for k in kaldte) == 50, "foerste bygning skulle embedde alle 50"
    assert len(mr._MD_VECS_CACHE["vecs"]) == 50

    # ── filen skrives: ny mtime + 2 nye linjer ──
    md.write_text("aendret", encoding="utf-8")
    os.utime(md, (time.time() + 5, time.time() + 5))  # garanteret ny mtime
    linjer2 = linjer + ["helt ny linje et", "helt ny linje to"]
    monkeypatch.setattr(mr, "_memory_md_lines", lambda user_id="": list(linjer2))

    kaldte.clear()
    mr._md_line_vecs("")
    _vent()

    embeddet = sum(len(k) for k in kaldte)
    assert embeddet == 2, (
        f"gen-indlejrede {embeddet} linjer — kun de 2 nye skulle embeddes. "
        "Genbruget af uaendrede linjer er brudt."
    )
    assert len(mr._MD_VECS_CACHE["vecs"]) == 52


def test_disk_cachen_goer_at_ny_proces_ikke_embedder_alt(monkeypatch, tmp_path):
    """11/10-2026: hver genstart var en KOLD bygning — alle ~10.100 MEMORY.md-linjer
    skulle embeddes foerste gang cachen byggedes, og /api/embed er maalt til 7,7-15,8 s
    pr. kald. Det gav ~2.000 kald i minuttet i bursts lige efter hver genstart.

    Disk-cachen skal goere at en NY proces (tom in-memory cache) laeser vektorerne
    fra disk og embedder NUL.

    Testen kalder _build-KROPPEN direkte (ikke gennem baggrundstraaden), saa den er
    deterministisk: ingen delt global tilstand fra andre tests kan forstyrre den."""
    from core.services.prompt_sections import memory_recall as mr

    md = tmp_path / "MEMORY.md"
    md.write_text("start", encoding="utf-8")
    monkeypatch.setattr(
        "core.runtime.workspace_paths.workspace_dir", lambda *a, **k: tmp_path
    )

    kaldte: list[list[str]] = []
    monkeypatch.setattr(
        "core.services.jarvis_brain._embed_texts",
        lambda tekster: (kaldte.append(list(tekster)), [[0.1] * 8 for _ in tekster])[1],
    )

    linjer = [f"linje nummer {i} med tilstraekkeligt indhold til at blive embeddet" for i in range(40)]

    def _byg(lines: list[str]) -> dict:
        """Praecis _build-kroppens logik, kaldt synkront."""
        gamle = mr._load_md_vecs_from_disk("")
        vecs = {ln: gamle[ln] for ln in lines if ln in gamle}
        nye = [ln for ln in lines if ln not in gamle]
        if nye:
            from core.services.jarvis_brain import _embed_texts
            for ln, v in zip(nye, _embed_texts(nye)):
                vecs[ln] = v
        mr._save_md_vecs_to_disk(vecs, "")
        return vecs

    # ── proces 1: kold bygning, alt embeddes, skrives til disk ──
    vecs1 = _byg(linjer)
    assert sum(len(k) for k in kaldte) == 40, "foerste bygning skulle embedde alle 40"
    assert len(vecs1) == 40
    cache_fil = tmp_path / mr._MD_VECS_CACHE_PATH_NAME
    assert cache_fil.exists(), "disk-cachen blev aldrig skrevet"

    # ── proces 2 (genstart): tom in-memory cache, MEN disk-filen staar ──
    kaldte.clear()
    vecs2 = _byg(linjer)

    embeddet = sum(len(k) for k in kaldte)
    assert embeddet == 0, (
        f"ny proces gen-indlejrede {embeddet} linjer — disk-cachen blev ikke brugt. "
        "Uden den er hver genstart en kold bygning af hele MEMORY.md."
    )
    assert len(vecs2) == 40, "vektorerne kom ikke med fra disk"
