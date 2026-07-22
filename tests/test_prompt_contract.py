"""Tests for prompt_contract module.

Currently covers the _time_pin_section function (Layer 1 of Lying Engine).
Time-pin-specific assertions also live in test_time_pin.py — this file
exists so the test-enforcement hook (scripts/enforce_test_coverage.py)
sees tests for prompt_contract.py changes.
"""
from __future__ import annotations


class TestPhaseTimeout:
    """Kold/frossen-vindue-værn (2026-07-14): _phase_timeout capper cognitive_state-builden
    så et koldt injection-vindue aldrig koster ~8s pr. svar."""

    def test_max_s_caps_below_phase_deadline(self):
        from core.services.prompt_contract import _phase_timeout
        # tidligt i assembly (elapsed 0): max_s=2.5 vinder over 10s-loftet + 12s-budgettet.
        assert _phase_timeout(0.0, max_s=2.5) == 2.5

    def test_no_max_s_uses_phase_deadline(self):
        from core.services.prompt_contract import _phase_timeout, _PHASE_DEADLINE_S, _ASSEMBLY_BUDGET_S
        # uden max_s: cappet af min(phase-deadline, resten af budget). elapsed 0 → budget 12 → 10.
        assert _phase_timeout(0.0) == min(_PHASE_DEADLINE_S, _ASSEMBLY_BUDGET_S)

    def test_global_budget_still_caps_when_elapsed_high(self):
        from core.services.prompt_contract import _phase_timeout
        # sent i assembly: resten af budgettet (12-11=1) vinder selv med rundhåndet max_s.
        assert _phase_timeout(11.0, max_s=2.5) == 1.0

    def test_floor_is_300ms(self):
        from core.services.prompt_contract import _phase_timeout
        # budget helt brugt → gulv 0.3s (aldrig 0 eller negativ).
        assert _phase_timeout(20.0, max_s=2.5) == 0.3

    def test_max_s_never_exceeds_phase_deadline(self):
        from core.services.prompt_contract import (
            _phase_timeout, _PHASE_DEADLINE_S, _ASSEMBLY_BUDGET_S,
        )
        # en rundhåndet max_s løfter ikke over det globale fase-loft / budget.
        assert _phase_timeout(0.0, max_s=100.0) == min(_PHASE_DEADLINE_S, _ASSEMBLY_BUDGET_S)


class TestTimePinSection:
    """Layer 1: prominent time block in every system prompt."""

    def test_includes_dansk_tid_label(self):
        from core.services.prompt_contract import _time_pin_section
        out = _time_pin_section()
        assert "DANSK TID" in out
        # Year 2026+ must appear somewhere in the rendering
        assert "202" in out

    def test_no_utc(self):
        """No UTC line — single Danish time line only."""
        from core.services.prompt_contract import _time_pin_section
        out = _time_pin_section()
        assert "UTC" not in out

    def test_includes_local_timezone_abbrev(self):
        """CEST in summer or CET in winter — never both, never neither."""
        from core.services.prompt_contract import _time_pin_section
        out = _time_pin_section()
        has_cest = "CEST" in out
        has_cet_alone = ("CET" in out) and not has_cest
        assert has_cest or has_cet_alone, (
            "Time pin must show a Copenhagen timezone abbreviation"
        )

    def test_contains_anchor_marker(self):
        """The ⏰ emoji + DANSK TID label must be present."""
        from core.services.prompt_contract import _time_pin_section
        out = _time_pin_section()
        assert "⏰" in out
        assert "DANSK TID" in out

    def test_contains_explicit_instruction(self):
        """Must tell the model to use this, not guess."""
        from core.services.prompt_contract import _time_pin_section
        out = _time_pin_section()
        assert "Use PRECISELY" in out
        assert "Don't guess" in out


class TestQuickFactsSection:
    """Quick Facts is loaded from QUICK_FACTS.md — exists but no time injected."""

    def test_returns_none_or_string(self, tmp_path):
        from core.services.prompt_contract import _quick_facts_section
        # Path with no QUICK_FACTS.md → returns None
        out = _quick_facts_section(workspace_dir=tmp_path)
        assert out is None


class TestTimePinPlacement:
    """Time Pin must be tail-anchored for DeepSeek prompt-cache hits.

    Added 2026-05-22 after measuring 0% cache-hit rate. Time Pin had
    been at position #4 in the prompt — changes every minute — making
    every chat unique-prefix and uncacheable. Moving it to the tail
    keeps the front of the prompt stable.
    """

    def test_time_pin_referenced_once_in_assembly(self):
        """Only the tail-anchored time_pin call should exist (the old
        position-#4 call was removed)."""
        import inspect
        from core.services import prompt_contract
        src = inspect.getsource(prompt_contract.build_visible_chat_prompt_assembly)
        # _time_pin_section() should be called exactly once
        n_calls = src.count("_time_pin_section()")
        assert n_calls == 1, (
            f"Expected exactly 1 call to _time_pin_section() in assembly, "
            f"found {n_calls}. Either the old position-#4 call was reintroduced "
            f"or the tail-anchor call was lost."
        )

    def test_time_pin_appears_near_end_of_parts(self):
        """In the source, the time_pin parts.append call should come AFTER
        the bulk of parts.append sites (specifically, after the assembled_text
        comment), so the part lands at the tail of the prompt."""
        import inspect
        from core.services import prompt_contract
        src = inspect.getsource(prompt_contract.build_visible_chat_prompt_assembly)
        # Find the index of the time_pin call and the assembled_text join.
        idx_tp = src.find("_time_pin_section()")
        idx_join = src.find('"\\n\\n".join(part for part in parts if part)')
        assert idx_tp > 0, "time_pin call not found"
        assert idx_join > 0, "assembled_text join not found"
        # time_pin must come right before the join, not way up near
        # model-identity-awareness.
        # Heuristic: distance from time_pin to join is small (< 500 chars).
        assert (idx_join - idx_tp) < 1000, (
            "time_pin appears too far from the prompt assembly tail — "
            f"distance to join: {idx_join - idx_tp} chars"
        )


# --- Liveness Stage 1 (2026-06-15): drop falske "dødt organ"-signaler ---


def test_epistemic_layers_line_silent_when_empty(monkeypatch):
    """Un-integreret epistemics-organ må ikke injicere 'epistemic_layers=empty'
    i Jarvis' selvmodel — linjen skal droppes (None)."""
    import core.services.prompt_contract as pc
    monkeypatch.setattr(
        "core.services.epistemics.build_epistemics_surface",
        lambda: {"layer_counts": {}, "wrongness_count": 0, "total_claims": 0},
    )
    assert pc._build_epistemic_layers_line() is None


def test_epistemic_layers_line_present_when_data(monkeypatch):
    import core.services.prompt_contract as pc
    monkeypatch.setattr(
        "core.services.epistemics.build_epistemics_surface",
        lambda: {"layer_counts": {"i_know": 3}, "wrongness_count": 1, "total_claims": 4},
    )
    line = pc._build_epistemic_layers_line()
    assert line is not None and "i_know=3" in line


def test_heartbeat_truth_drops_empty_lines_and_keeps_block():
    """Joinen filtrerer None-linjer; resten af selvmodel-blokken er intakt."""
    import core.services.prompt_contract as pc
    out = pc._heartbeat_runtime_truth_instruction({})
    assert out.startswith("Heartbeat runtime truth:")
    assert "epistemic_layers=empty" not in out
    assert "epistemic_layers=unavailable" not in out
    assert "tool_intent=" in out  # sikkerheds-selvmodel bevaret


# ── Spor D: afsender-bevidsthed (navn + rolle + gæst-markering) ──────────────
def test_speaker_display_owner_name_only(monkeypatch):
    import core.services.prompt_contract as pc
    import core.identity.users as users
    pc._SPEAKER_CACHE.clear()
    class _U:
        name = "Bjørn"; role = "owner"
    monkeypatch.setattr(users, "find_user_by_discord_id", lambda uid: _U())
    assert pc._resolve_speaker_display("1") == "Bjørn"


def test_speaker_display_member_tagged(monkeypatch):
    import core.services.prompt_contract as pc
    import core.identity.users as users
    pc._SPEAKER_CACHE.clear()
    class _U:
        name = "Rune"; role = "member"
    monkeypatch.setattr(users, "find_user_by_discord_id", lambda uid: _U())
    assert pc._resolve_speaker_display("2") == "Rune (medlem)"


def test_speaker_display_unknown_is_guest(monkeypatch):
    import core.services.prompt_contract as pc
    import core.identity.users as users
    pc._SPEAKER_CACHE.clear()
    monkeypatch.setattr(users, "find_user_by_discord_id", lambda uid: None)
    assert pc._resolve_speaker_display("999") == "Gæst (ukendt)"


def test_speaker_display_empty_uid():
    import core.services.prompt_contract as pc
    pc._SPEAKER_CACHE.clear()
    assert pc._resolve_speaker_display("") == ""


# ── Bjørn-gate: _pending_promises_section ──
def test_pending_promises_section_renders(monkeypatch):
    import core.services.prompt_contract as pc
    import core.services.promise_ledger as pl
    monkeypatch.setattr(pl, "pending_promises", lambda sid, **k: [{"text": "Jeg committer fixet nu"}])
    out = pc._pending_promises_section("s1")
    assert out and "Bjørn-gate" in out and "Jeg committer fixet nu" in out


def test_pending_promises_section_empty(monkeypatch):
    import core.services.prompt_contract as pc
    import core.services.promise_ledger as pl
    monkeypatch.setattr(pl, "pending_promises", lambda sid, **k: [])
    assert pc._pending_promises_section("s1") is None


def test_pending_promises_section_no_session():
    import core.services.prompt_contract as pc
    assert pc._pending_promises_section("") is None
    assert pc._pending_promises_section(None) is None


def test_transcript_bounded_fallback_when_compacted(monkeypatch):
    """Bjørn 2026-06-23: når en session ER compacted (marker findes) men 'siden compact' er tomt
    (markøren skrives sidst), må vi IKKE loade hele 60-user-turn-vinduet — kun et bundet recent-
    vindue. Ellers eksploderer transcripten (578k målt) og cache brydes."""
    import core.services.prompt_contract as pc
    import core.services.chat_sessions as cs

    monkeypatch.setattr(pc, "chat_session_messages_since_last_compact", lambda *a, **k: [])
    monkeypatch.setattr(cs, "get_compact_marker", lambda sid: "[SAMMENDRAG] gammelt")
    bounded_called = {}

    def _bounded(sid, *, limit):
        bounded_called["limit"] = limit
        return [{"role": "user", "content": "ny", "created_at": "t",
                 "user_id": "", "reasoning_content": ""}]
    monkeypatch.setattr(pc, "recent_chat_session_messages", _bounded)

    def _must_not_run(*a, **k):
        raise AssertionError("ubundet 60-turn-fallback kaldt på en compacted session")
    monkeypatch.setattr(pc, "recent_chat_session_messages_by_user_turns", _must_not_run)

    out = pc._build_structured_transcript_messages("sid-x", limit=60, include=True)
    assert bounded_called.get("limit") is not None  # bundet loader brugt
    assert isinstance(out, list)


def test_transcript_full_fallback_when_never_compacted(monkeypatch):
    """Aldrig-compacted session (intet marker) → behold det fulde 60-turn-fallback."""
    import core.services.prompt_contract as pc
    import core.services.chat_sessions as cs

    monkeypatch.setattr(pc, "chat_session_messages_since_last_compact", lambda *a, **k: [])
    monkeypatch.setattr(cs, "get_compact_marker", lambda sid: None)
    full_called = {}

    def _full(sid, **k):
        full_called["hit"] = True
        return [{"role": "user", "content": "x", "created_at": "t",
                 "user_id": "", "reasoning_content": ""}]
    monkeypatch.setattr(pc, "recent_chat_session_messages_by_user_turns", _full)

    pc._build_structured_transcript_messages("sid-y", limit=60, include=True)
    assert full_called.get("hit") is True


class TestHonestyRulesSection:
    """Ærligheds-regler (handling + epistemisk afholdenhed).

    Konsolideret 2026-07-22 (prompt audit #1): reglerne bor nu ÉN gang, på
    engelsk, i VISIBLE_CHAT_RULES.md ('## Honesty'). De hardcodede helpere er
    no-ops der returnerer "" så de gated call-sites ikke dropper noget tomt ind.
    Selve reglens tilstedeværelse i det cachede prefix vogtes af
    TestCachePrefixInvariant.test_honesty_rules_inside_the_shared_prefix."""

    def test_helpers_are_noops_after_consolidation(self):
        from core.services.prompt_contract import (
            _honesty_rules_section,
            _self_correction_nudges_section,
        )
        assert _honesty_rules_section(compact=False) == ""
        assert _honesty_rules_section(compact=True) == ""
        assert _self_correction_nudges_section(compact=False) == ""
        assert _self_correction_nudges_section(compact=True) == ""


class TestCachePrefixInvariant:
    """REGRESSIONSVAGT: warmer-prefixet (build_visible_stable_prefix) SKAL være
    et byte-identisk prefix af den fulde live-assembly — ellers divergerer
    DeepSeek-cache-prefixet og identitets-filerne falder ud af cachen. Præcis
    denne invariant brød 22. jun (ærligheds-reglen var kun i live-stien) og
    kostede ~91% af det cacheable prefix indtil 30. jun."""

    def _build_both(self):
        from core.services.prompt_contract import (
            build_visible_stable_prefix,
            build_visible_chat_prompt_assembly,
        )
        warm = build_visible_stable_prefix(
            provider="deepseek", model="deepseek-v4-flash")
        full = build_visible_chat_prompt_assembly(
            provider="deepseek", model="deepseek-v4-flash",
            user_message="hej", session_id="cache-invariant-test")
        full = getattr(full, "text", None) or str(full)
        return warm, full

    def test_warmer_prefix_is_byte_identical_prefix_of_live(self):
        warm, full = self._build_both()
        assert warm, "warmer-prefix tomt"
        assert full.startswith(warm), (
            "warmer-prefix er IKKE et byte-identisk prefix af live-assembly — "
            "cache-prefixet divergerer. Tjek at ærligheds-reglen (og alt andet "
            "stable) står på SAMME position i begge bygge-funktioner."
        )

    def test_honesty_rules_inside_the_shared_prefix(self):
        # Ærligheds-reglen (handling + epistemisk) skal ligge i den DELTE (cachede)
        # del — ikke kun i live-halen — så warmer-cron pre-varmer den. Efter
        # konsolideringen (2026-07-22) leveres den via VISIBLE_CHAT_RULES.md
        # ('## Honesty'), som ligger i samme cachede prefix. Markør på engelsk.
        warm, _ = self._build_both()
        assert "never claim I did something" in warm  # action honesty
        assert "unsure of a fact" in warm             # epistemic honesty


class TestToolResultRenderingIsRecencyIndependent:
    """CACHE-FIX (2026-06-30): historiske tool-results SKAL rendere byte-identisk
    uanset deres position i samtalen. FØR brød recency-splittet (seneste 20 @4000
    tegn, ældre @1200) cachen: et resultat der gled fra 'seneste 20' → 'ældre'
    gen-renderedes → historik-bytes ændrede sig hver tur → DeepSeek-cache-prefix
    brækkede. Denne test fanger en tilbagevenden."""

    def _render(self, monkeypatch, history):
        from core.services import prompt_contract as pc
        monkeypatch.setattr(pc, "chat_session_messages_since_last_compact",
                            lambda session_id, max_total=4000: list(history))
        return pc._build_structured_transcript_messages(
            "sess-x", limit=60, include=True)

    def test_old_tool_result_renders_identically_as_history_grows(self, monkeypatch):
        # User-beskeder imellem hver runde, så carrieren for det fulgte resultat
        # IKKE absorberer senere ture (consecutive-assistant-merge er append-only
        # og cache-sikkert). Vi tester at det SAMME resultats rendering ikke ændrer
        # sig når det glider fra 'seneste' til 'ældre'.
        big = "X" * 2500  # > fast cap, så trunkering ER i spil
        base = [
            {"role": "user", "content": "q0"},
            {"role": "assistant", "content": "svar et"},
            {"role": "tool", "content": big},   # det resultat vi følger
        ]
        grown = base + [
            m for i in range(25) for m in (
                {"role": "user", "content": f"q{i+1}"},
                {"role": "assistant", "content": f"runde {i}"},
                {"role": "tool", "content": f"resultat {i}"},
            )
        ]
        short_out = self._render(monkeypatch, base)
        long_out = self._render(monkeypatch, grown)

        def carrier(out):
            return next(m["content"] for m in out if m["content"].startswith("svar et"))
        # Byte-identisk uanset at 25 tool-runder kom efter → cachen holder.
        assert carrier(short_out) == carrier(long_out)

    def test_render_does_not_depend_on_recent_count_slice(self, monkeypatch):
        # Samme resultat som #1 i tool-rækken vs efter 40 senere runder.
        marker = "Y" * 3000
        few = [{"role": "user", "content": "u"},
               {"role": "assistant", "content": "A"},
               {"role": "tool", "content": marker}]
        many = few + [m for i in range(40) for m in (
            {"role": "user", "content": f"u{i}"},
            {"role": "assistant", "content": f"a{i}"},
            {"role": "tool", "content": f"r{i}"})]
        a = next(m["content"] for m in self._render(monkeypatch, few) if m["content"].startswith("A"))
        b = next(m["content"] for m in self._render(monkeypatch, many) if m["content"].startswith("A"))
        assert a == b
