"""Tests for core/services/visible_turn_blocks.py.

FUNDET LIVE 2026-09-02 (Bjørn): «under streaming vises synteser og resultater
korrekt, men når streaming slutter falder hans synteser sammen og tool results
bliver flyttet op i toppen af beskeden.»

Målt på en ægte tur: content_json havde 22 blokke — 7 tool_use, 7 tool_result,
ÉN text og 7 tomme progress. Alle værktøjer lå på index 0-13, teksten på 14.

Årsagen var at builderen kun fik én samlet tekst-streng og derfor kun kunne
placere den ét sted. Rettelsen er tekst-SEGMENTER: ét pr. sammenhængende
stykke tekst mellem værktøjskald.
"""

from __future__ import annotations

from core.services.visible_turn_blocks import _build_turn_blocks


def _call(i: str, name: str = "bash") -> dict:
    return {"id": i, "name": name, "input": {"command": f"cmd-{i}"}}


def _result(i: str, content: str = "ok") -> dict:
    return {"tool_use_id": i, "status": "done", "content": content}


def _types(blocks: list[dict]) -> list[str]:
    """Rækkefølgen af tekst og værktøj — progress-sporet er et separat,
    fladt spor til sidst (spec §5) og siger intet om rækkefølgen i tråden."""
    return [str(b.get("type")) for b in blocks if b.get("type") != "progress"]


def _texts(blocks: list[dict]) -> list[str]:
    return [str(b.get("text")) for b in blocks if b.get("type") == "text"]


class TestSegmenterGenskaberRækkefølgen:
    def test_fortælling_værktøj_fortælling(self) -> None:
        """Selve fejlen: turen skal kunne læses som den blev til."""
        blocks = _build_turn_blocks(
            text="Først kigger jeg.Så konkluderer jeg.",
            tool_calls=[_call("a")],
            tool_results=[_result("a")],
            interleave=["text", "tool", "text"],
            text_segments=["Først kigger jeg.", "Så konkluderer jeg."],
        )
        assert _types(blocks) == ["text", "tool_use", "tool_result", "text"]
        assert _texts(blocks) == ["Først kigger jeg.", "Så konkluderer jeg."]

    def test_flere_runder_bevarer_hver_syntese(self) -> None:
        blocks = _build_turn_blocks(
            text="ABC",
            tool_calls=[_call("a"), _call("b")],
            tool_results=[_result("a"), _result("b")],
            interleave=["text", "tool", "text", "tool", "text"],
            text_segments=["A", "B", "C"],
        )
        assert _types(blocks) == [
            "text", "tool_use", "tool_result",
            "text", "tool_use", "tool_result",
            "text",
        ]
        assert _texts(blocks) == ["A", "B", "C"]

    def test_intet_segment_går_tabt_selv_uden_markør(self) -> None:
        """Undertæller interleave, skal resten stadig med — aldrig tabt tekst."""
        blocks = _build_turn_blocks(
            text="AB",
            tool_calls=[_call("a")],
            tool_results=[_result("a")],
            interleave=["text", "tool"],
            text_segments=["A", "B"],
        )
        assert _texts(blocks) == ["A", "B"]

    def test_tomme_segmenter_ignoreres(self) -> None:
        blocks = _build_turn_blocks(
            text="A",
            tool_calls=[_call("a")],
            tool_results=[_result("a")],
            interleave=["text", "tool"],
            text_segments=["A", "   ", ""],
        )
        assert _texts(blocks) == ["A"]


class TestUdenSegmenterErAdfærdenUændret:
    def test_gammel_adfærd_bevares(self) -> None:
        """Bagudkompatibilitet: kaldere der ikke sender segmenter må ikke ændre sig."""
        blocks = _build_turn_blocks(
            text="Svaret",
            tool_calls=[_call("a")],
            tool_results=[_result("a")],
            interleave=["text", "tool", "text"],
        )
        # Én blob placeres ved SIDSTE text-markør — som før rettelsen.
        assert _types(blocks) == ["tool_use", "tool_result", "text"]

    def test_uden_interleave_kommer_værktøjer_først(self) -> None:
        blocks = _build_turn_blocks(
            text="Svaret",
            tool_calls=[_call("a")],
            tool_results=[_result("a")],
        )
        assert _types(blocks) == ["tool_use", "tool_result", "text"]


class TestRobusthed:
    def test_værktøjer_uden_resultat_droppes_ikke(self) -> None:
        blocks = _build_turn_blocks(
            text="A",
            tool_calls=[_call("a"), _call("b")],
            tool_results=[_result("a")],
            interleave=["tool", "tool", "text"],
            text_segments=["A"],
        )
        assert _types(blocks).count("tool_use") == 2

    def test_ren_tekst_tur(self) -> None:
        blocks = _build_turn_blocks(
            text="Bare et svar", tool_calls=[], tool_results=[],
            interleave=["text"], text_segments=["Bare et svar"],
        )
        assert _types(blocks) == ["text"]
