"""Tests for Fact-Gate — DETEKTERENDE output gate for unverifiable factual claims.

2026-07-06 (Bjørn+Jarvis): gaten BLOKERER IKKE længere. Detektionen af
uverificerede tal-/status-påstande er uændret (block_reasons fyldes), men i
stedet for at ERSTATTE beskeden BEVARER vi Jarvis' tekst og APPENDER en
✋-fodnote i bunden. blocked er altid False; annotated_text bærer teksten+fodnote.
"""

from __future__ import annotations

from core.services.fact_gate import (
    fact_gate_enforce,
    blocking_categories,
    _has_tool_evidence,
    _BLOCK_PATTERNS,
)


# ── blocking_categories ──────────────────────────────────────────────

def test_blocking_categories_contains_commit_count():
    cats = blocking_categories()
    assert "commit_count" in cats


def test_blocking_categories_contains_self_stats():
    cats = blocking_categories()
    assert "self_stats" in cats


def test_blocking_categories_contains_service_active():
    cats = blocking_categories()
    assert "service_active" in cats


def test_blocking_categories_contains_cache_percentage():
    cats = blocking_categories()
    assert "cache_percentage" in cats


# ── BLOCK: commit_count ──────────────────────────────────────────────

def test_block_commit_count_no_tools():
    """45 commits uden git_log: detekteres + fodnote, men beskeden bevares."""
    r = fact_gate_enforce("45 commits")
    assert r["blocked"] is False
    assert r["block_reasons"][0]["pattern"] == "commit_count"
    assert r["original"] in r["annotated_text"]
    assert "✋" in r["annotated_text"]


def test_block_commit_count_with_circa():
    """~3000 commits uden værktøj: detekteres (fodnote), ikke blokeret."""
    r = fact_gate_enforce("~3000 commits")
    assert r["blocked"] is False
    assert r["block_reasons"]
    assert "✋" in r["annotated_text"]


def test_block_commit_count_danish():
    """over 30 commits på dansk: detekteres (fodnote), ikke blokeret."""
    r = fact_gate_enforce("over 30 commits i dag")
    assert r["blocked"] is False
    assert r["block_reasons"]


def test_pass_commit_count_with_bash():
    """45 commits med bash i run → passér."""
    r = fact_gate_enforce("45 commits", tool_names=["bash"])
    assert r["blocked"] is False


def test_pass_commit_count_with_git_log():
    """45 commits med git_log i run → passér."""
    r = fact_gate_enforce("45 commits", tool_names=["git_log"])
    assert r["blocked"] is False


def test_pass_commit_count_with_verification_text():
    """Tekst der selv verificerer ('git log viser...') → passér."""
    r = fact_gate_enforce("git log viser 45 commits i dag")
    assert r["blocked"] is False


def test_pass_commit_count_with_verified():
    """'jeg tjekkede — 45 commits' → passér (verification hint)."""
    r = fact_gate_enforce("jeg tjekkede — 45 commits")
    assert r["blocked"] is False


# ── BLOCK: self_stats ────────────────────────────────────────────────

def test_block_tests_no_tools():
    """35 tests uden værktøj: detekteres (fodnote), beskeden bevares."""
    r = fact_gate_enforce("Der er 35 tests der kører")
    assert r["blocked"] is False
    assert r["block_reasons"][0]["pattern"] == "self_stats"
    assert "Der er 35 tests der kører" in r["annotated_text"]
    assert "✋" in r["annotated_text"]


def test_block_daemons_no_tools():
    """12 daemons uden daemon_status: detekteres (fodnote), ikke blokeret."""
    r = fact_gate_enforce("12 daemons kører lige nu")
    assert r["blocked"] is False
    assert r["block_reasons"]


def test_block_calls_no_tools():
    """250 kald uden værktøj: detekteres (fodnote), ikke blokeret."""
    r = fact_gate_enforce("250 kald i dag")
    assert r["blocked"] is False
    assert r["block_reasons"]


def test_pass_tests_with_bash():
    """35 tests med bash i run → passér."""
    r = fact_gate_enforce("35 tests", tool_names=["bash"])
    assert r["blocked"] is False


# ── BLOCK: service_active ────────────────────────────────────────────

def test_block_service_claim_no_tools():
    """jarvis-api kører uden service_status → detekteres (fodnote), ikke blokeret."""
    r = fact_gate_enforce("jarvis-api kører fint")
    assert r["blocked"] is False
    assert r["block_reasons"][0]["pattern"] == "service_active"
    assert "jarvis-api kører fint" in r["annotated_text"]


def test_block_service_is_active_no_tools():
    """'servicen er aktiv' uden værktøj → detekteres (fodnote), ikke blokeret."""
    r = fact_gate_enforce("servicen er aktiv")
    assert r["blocked"] is False
    assert r["block_reasons"]


def test_pass_service_claim_with_service_status():
    """jarvis-api kører med service_status → passér."""
    r = fact_gate_enforce("jarvis-api kører fint", tool_names=["service_status"])
    assert r["blocked"] is False


def test_pass_service_claim_with_bash():
    """jarvis-api kører med bash (service x | grep) → passér."""
    r = fact_gate_enforce("jarvis-api kører", tool_names=["bash"])
    assert r["blocked"] is False


# ── BLOCK: cache_percentage ───────────────────────────────────────────

def test_block_cache_claim_no_tools():
    """12.4% cache uden db_query → detekteres (fodnote), ikke blokeret."""
    r = fact_gate_enforce("12.4% cache")
    assert r["blocked"] is False
    assert r["block_reasons"][0]["pattern"] == "cache_percentage"
    assert "12.4% cache" in r["annotated_text"]


def test_block_cache_hit_rate_no_tools():
    """27.5% hit rate uden værktøj → detekteres (fodnote), ikke blokeret."""
    r = fact_gate_enforce("27.5% hit rate lige nu")
    assert r["blocked"] is False
    assert r["block_reasons"]


def test_pass_cache_claim_with_db_query():
    """12.4% cache med db_query → passér."""
    r = fact_gate_enforce("12.4% cache", tool_names=["db_query"])
    assert r["blocked"] is False


def test_pass_cache_claim_with_bash():
    """12.4% cache med bash (sqlite3 direkte) → passér."""
    r = fact_gate_enforce("12.4% cache", tool_names=["bash"])
    assert r["blocked"] is False


# ── PASS: safe / whitelisted text ────────────────────────────────────

def test_pass_whitelist_phrase():
    """'jeg er en stor fan' er whitelisted og skal passere."""
    r = fact_gate_enforce("jeg er en stor fan af den nye app")
    assert r["blocked"] is False


def test_pass_whitelist_good_idea():
    """'det var en god idé' er whitelisted og skal passere."""
    r = fact_gate_enforce("det var en god idé du havde")
    assert r["blocked"] is False


def test_pass_natural_language():
    """Almindelig tekst uden tal skal passere."""
    r = fact_gate_enforce("Hej Bjørn, hvordan går det?")
    assert r["blocked"] is False


def test_pass_subjective_statement():
    """Uskarpe påstande ('mange', 'hurtig') skal passere."""
    r = fact_gate_enforce("mange commits i dag, det går hurtigt")
    assert r["blocked"] is False


def test_pass_empty_string():
    """Tom tekst skal altid passere."""
    r = fact_gate_enforce("")
    assert r["blocked"] is False


def test_pass_none_input():
    """None skal altid passere."""
    r = fact_gate_enforce(None)
    assert r["blocked"] is False


def test_pass_whitespace():
    """Whitespace skal altid passere."""
    r = fact_gate_enforce("   \n  ")
    assert r["blocked"] is False


# ── Fodnote (tidligere: replacement) ──────────────────────────────────

def test_footnote_preserves_message_and_appends_warning():
    """BEVAR beskeden + append ✋-fodnote i bunden — erstat/blokér ALDRIG."""
    r = fact_gate_enforce("45 commits")
    assert r["blocked"] is False
    assert r["annotated_text"].startswith("45 commits")  # original bevaret først
    assert "✋" in r["annotated_text"]
    assert "45 commits" in r["annotated_text"]


def test_footnote_mentions_required_tools():
    """Fodnoten skal nævne hvilke tools der kræves."""
    r = fact_gate_enforce("12 daemons")
    assert r["blocked"] is False
    assert "bash" in r["annotated_text"] or "daemon_status" in r["annotated_text"]


def test_replacement_alias_equals_annotated():
    """replacement er bevaret som alias for annotated_text (bagudkompat)."""
    r = fact_gate_enforce("45 commits")
    assert r["replacement"] == r["annotated_text"]


def test_replacement_contains_original():
    """Original tekst bevares i 'original'-feltet."""
    r = fact_gate_enforce("45 commits")
    assert r["original"] == "45 commits"


def test_unblocked_has_no_replacement():
    """Ikke-blokeret besked skal have replacement = original."""
    r = fact_gate_enforce("Hej, hvordan går det?")
    assert r["replacement"] == r["original"]


# ── Multiple blocks ──────────────────────────────────────────────────

def test_multiple_patterns_blocked():
    """Flere samtidige påstande — alle blokeres."""
    r = fact_gate_enforce("45 commits og 12.4% cache og 35 tests")
    patterns = [br["pattern"] for br in r["block_reasons"]]
    assert "commit_count" in patterns
    assert "cache_percentage" in patterns
    assert "self_stats" in patterns


# ── _has_tool_evidence ────────────────────────────────────────────────

def test_has_tool_evidence_exact_match():
    """Tool i required → evidence."""
    assert _has_tool_evidence("45 commits", None, ("bash", "git_log"), ["bash"]) is True


def test_has_tool_evidence_no_match():
    """Intet tool i required → ingen evidence."""
    assert _has_tool_evidence("45 commits", None, ("bash", "git_log"), ["web_search"]) is False


def test_has_tool_evidence_empty_tools():
    """Tom tool-liste → ingen evidence."""
    assert _has_tool_evidence("45 commits", None, ("bash",), []) is False


def test_has_tool_evidence_verification_hint():
    """'git log viser' i teksten → evidence (selv uden tools)."""
    assert _has_tool_evidence("git log viser 45 commits", None, ("bash",), []) is True


def test_has_tool_evidence_verified_hint():
    """'tallet er 45' i teksten → evidence."""
    assert _has_tool_evidence("tallet er 45 commits", None, ("bash",), []) is True


# ── Edge: numbers in non-claim context ────────────────────────────────

def test_pass_time_mentions():
    """Klokkeslæt skal ikke blokeres — ikke en claim."""
    r = fact_gate_enforce("klokken er 14:32")
    assert r["blocked"] is False


def test_pass_year_mention():
    """Årstal skal ikke blokeres."""
    r = fact_gate_enforce("I 2025 skete der noget stort")
    assert r["blocked"] is False


def test_pass_ip_address():
    """IP-adresser matcher ikke self_stats-mønstret."""
    r = fact_gate_enforce("serveren er 10.0.0.2")
    assert r["blocked"] is False


# ── Edge: tool_names casing ──────────────────────────────────────────

def test_tool_names_case_insensitive():
    """Tool names matches case-insensitivt — 'Bash' = 'bash'."""
    r = fact_gate_enforce("45 commits", tool_names=["Bash"])
    assert r["blocked"] is False  # case-normaliseret match


# ── Edge: fail-open ──────────────────────────────────────────────────

def test_pattern_without_required_tools_never_blocks():
    """Hvis required_tools er tom, skal den ikke blokere (fail-open)."""
    # Ingen af de fire default patterns har tom required — test er strukturel.
    for name, _pattern, required, _desc in _BLOCK_PATTERNS:
        assert len(required) > 0, f"Pattern {name} har ingen required_tools — kan aldrig blokere"
