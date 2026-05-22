"""Tests for hallucination_guard (factual question protection)."""
from __future__ import annotations

from core.services.hallucination_guard import (
    classify_question,
    inject_memory_into_prompt,
)


class TestClassifyQuestion:
    def test_factual_subdomain(self):
        assert classify_question("hvad er mit subdomain?") == "factual"

    def test_factual_ip_question(self):
        assert classify_question("hvad er IP-adressen?") == "factual"

    def test_factual_path(self):
        assert classify_question("hvor ligger den fil?") == "factual"

    def test_tool_call_prefix(self):
        for msg in ("kør backup", "byg dashboard", "slet gammel fil"):
            assert classify_question(msg) == "tool_call", msg

    def test_casual_short(self):
        assert classify_question("hej") == "casual"
        assert classify_question("ok tak") == "casual"


class TestInjectMemoryIntoPrompt:
    def test_passes_through_casual(self):
        msgs = [{"role": "user", "content": "hi"}]
        out = inject_memory_into_prompt("hej der", msgs)
        # Casual → no guard inserted
        assert all("[HALLUCINATION GUARD" not in m.get("content", "") for m in out)

    def test_injects_for_factual_with_keywords(self, tmp_path):
        # Build a tiny fake MEMORY.md
        mem = tmp_path / "MEMORY.md"
        mem.write_text(
            "# MEMORY\n## Infrastructure\n- Subdomains: jarvis.srvlab.dk, srvlab.dk (no assets subdomain)\n",
            encoding="utf-8",
        )
        msgs = [{"role": "system", "content": "primary instruction"}]
        out = inject_memory_into_prompt(
            "hvad er mit subdomain?", msgs, memory_path=str(mem)
        )
        # Guard message must be present
        guards = [m for m in out if "[HALLUCINATION GUARD" in m.get("content", "")]
        assert len(guards) == 1
        # And it must contain the MEMORY.md excerpt
        assert "jarvis.srvlab.dk" in guards[0]["content"]

    def test_no_guard_when_no_matching_section(self, tmp_path):
        # MEMORY.md doesn't contain anything matching the keywords
        mem = tmp_path / "MEMORY.md"
        mem.write_text("# MEMORY\nNothing relevant here.\n", encoding="utf-8")
        msgs = [{"role": "system", "content": "x"}]
        out = inject_memory_into_prompt(
            "hvad er mit subdomain?", msgs, memory_path=str(mem)
        )
        # No section matched → no guard
        guards = [m for m in out if "[HALLUCINATION GUARD" in m.get("content", "")]
        assert len(guards) == 0

    def test_strong_language_in_guard(self, tmp_path):
        """The 2026-05-22 stronger guard wording must be load-bearing."""
        mem = tmp_path / "MEMORY.md"
        mem.write_text(
            "## Subdomains\nOnly jarvis.srvlab.dk exists.\n", encoding="utf-8"
        )
        out = inject_memory_into_prompt(
            "hvad er mit subdomain?",
            [{"role": "system", "content": "x"}],
            memory_path=str(mem),
        )
        guard = next(m for m in out if "[HALLUCINATION GUARD" in m.get("content", ""))
        c = guard["content"]
        # Critical instructions must be present
        assert "FABULÉR IKKE" in c
        assert "Det står ikke i min hukommelse" in c
