"""Tests for core/services/prompt_cache_probe.py.

Sonden skal svare på ét spørgsmål: hvor langt rækker det byte-identiske
prefix mellem to ture. DeepSeek genbruger kun en cache-enhed ved *fuldt*
match, så alt efter første afvigende byte er tabt — og det er præcis det
``stable_prefix_chars`` måler.
"""

from __future__ import annotations

import pytest

from core.services.prompt_cache_probe import ProbeVerdict, compare, flatten


def _blocks(role: str, text: str) -> dict:
    return {"role": role, "content": [{"type": "input_text", "text": text}]}


class TestFlatten:
    def test_block_form(self) -> None:
        assert flatten([_blocks("system", "abc")]) == [("system", "abc")]

    def test_plain_string_form(self) -> None:
        """OpenAI-compat-adapterne bruger content som ren streng."""
        assert flatten([{"role": "user", "content": "hej"}]) == [("user", "hej")]

    def test_multiple_blocks_are_joined(self) -> None:
        item = {"role": "user", "content": [{"text": "a"}, {"text": "b"}]}
        assert flatten([item]) == [("user", "ab")]

    @pytest.mark.parametrize("items", [None, [], [{}]])
    def test_degenerate_input_never_raises(self, items) -> None:
        assert isinstance(flatten(items), list)


class TestCompare:
    def test_identical_arrays(self) -> None:
        a = [("system", "S"), ("user", "u")]
        v = compare(a, list(a))
        assert v.identical is True
        assert v.stable_prefix_chars == 2
        assert v.first_diff_index is None

    def test_append_only_growth_keeps_full_prefix(self) -> None:
        """Den cache-venlige form: historik vokser, intet omskrives."""
        prev = [("system", "SYS"), ("user", "hej")]
        cur = prev + [("assistant", "svar"), ("user", "igen")]
        v = compare(prev, cur)
        assert v.stable_prefix_chars == 6      # "SYS" + "hej"
        assert v.msgs_stable == 2
        assert v.first_diff_index == 2

    def test_mutation_in_system_kills_everything(self) -> None:
        """En ændring i system-beskeden koster HELE prompten — kernen i fejlen."""
        prev = [("system", "SYS-A"), ("user", "x" * 5000)]
        cur = [("system", "SYS-B"), ("user", "x" * 5000)]
        v = compare(prev, cur)
        assert v.stable_prefix_chars == 0
        assert v.first_diff_index == 0
        assert v.first_diff_offset == 4

    def test_late_mutation_preserves_long_prefix(self) -> None:
        """Volatilt indhold TIL SIDST er billigt — det er hele designmålet."""
        head = [("system", "S" * 1000), ("user", "u" * 500)]
        v = compare(head + [("user", "hale-A")], head + [("user", "hale-B")])
        assert v.stable_prefix_chars == 1500
        assert v.msgs_stable == 2
        assert v.first_diff_index == 2
        assert v.first_diff_offset == 5

    def test_offset_points_at_first_differing_char(self) -> None:
        v = compare([("user", "abcdef")], [("user", "abcXef")])
        assert v.first_diff_offset == 3
        assert v.first_diff_role == "user"

    def test_truncated_array_is_a_diff_not_a_crash(self) -> None:
        v = compare([("system", "a"), ("user", "b")], [("system", "a")])
        assert v.identical is False
        assert v.first_diff_index == 1
        assert v.stable_prefix_chars == 1

    def test_excerpts_are_captured_from_both_sides(self) -> None:
        v = compare([("user", "fælles-DEL-A-tail")], [("user", "fælles-DEL-B-tail")])
        assert "A" in v.excerpt_a
        assert "B" in v.excerpt_b

    def test_sections_name_the_culprit(self) -> None:
        """Rapporten skal pege på hvilken sektion der muterede."""
        text_a = "[IDENTITET]\nstabil\n[INDRE LIV]\n· puls 12\nhale"
        text_b = "[IDENTITET]\nstabil\n[INDRE LIV]\n· puls 99\nhale"
        v = compare([("system", text_a)], [("system", text_b)])
        assert "[INDRE LIV]" in v.sections

    def test_both_empty(self) -> None:
        v = compare([], [])
        assert v.identical is True
        assert v.stable_prefix_chars == 0


class TestVerdictLine:
    def test_line_is_single_line_and_greppable(self) -> None:
        v = compare([("system", "a"), ("user", "b")], [("system", "a"), ("user", "c")])
        line = v.as_line()
        assert "\n" not in line
        assert line.startswith("PROMPT-CACHE-PROBE")
        assert "stable_prefix_chars=1" in line

    def test_identical_line_says_so(self) -> None:
        line = compare([("system", "a")], [("system", "a")]).as_line()
        assert "identiske" in line

    def test_default_verdict_is_safe(self) -> None:
        assert ProbeVerdict().as_line().startswith("PROMPT-CACHE-PROBE")


class TestGate:
    def test_probe_is_off_without_gate_file(self, monkeypatch) -> None:
        """Slukket som standard — må aldrig skrive til disk uden gate."""
        import core.services.prompt_cache_probe as mod
        monkeypatch.setattr(mod, "GATE_PATH", "/nonexistent/jarvis-msgdump-gate")
        assert mod.enabled() is False
        assert mod.probe([_blocks("system", "x")], session_id="s") is None

    def test_probe_roundtrip_writes_and_compares(self, monkeypatch, tmp_path) -> None:
        import core.services.prompt_cache_probe as mod
        gate = tmp_path / "gate"
        gate.write_text("")
        monkeypatch.setattr(mod, "GATE_PATH", str(gate))
        monkeypatch.setattr(mod, "DUMP_DIR", str(tmp_path / "dumps"))

        first = mod.probe([_blocks("system", "SYS"), _blocks("user", "a")], session_id="s1")
        assert first is None                      # ingen forrige tur endnu

        second = mod.probe([_blocks("system", "SYS"), _blocks("user", "b")], session_id="s1")
        assert second is not None
        assert second.identical is False
        assert second.stable_prefix_chars == 3    # kun "SYS" overlevede
        assert second.first_diff_index == 1

    def test_cross_session_comparison_is_skipped(self, monkeypatch, tmp_path) -> None:
        """En anden session siger intet om cachen — sammenlign ikke."""
        import core.services.prompt_cache_probe as mod
        gate = tmp_path / "gate"
        gate.write_text("")
        monkeypatch.setattr(mod, "GATE_PATH", str(gate))
        monkeypatch.setattr(mod, "DUMP_DIR", str(tmp_path / "dumps"))

        mod.probe([_blocks("system", "SYS")], session_id="s1")
        assert mod.probe([_blocks("system", "SYS")], session_id="s2") is None
