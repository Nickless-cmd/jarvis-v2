"""Tests for core.context.compaction_policy — model-aware, round-atomic compaction."""
from __future__ import annotations

from core.context.compaction_policy import (
    CompactionDecision,
    build_structured_summary_prompt,
    compaction_decision,
    fold_old_tool_results,
    group_rounds,
    render_transcript_for_summary,
    round_is_open,
    select_for_compaction,
    summary_looks_valid,
)


# Fake windows: glm-5.1 256k, glm-5.2 / deepseek-flash 1M, unknown 0.
def _win(provider: str, model: str) -> int:
    m = (model or "").lower()
    if "glm-5.1" in m:
        return 256_000
    if "glm-5.2" in m or "flash" in m:
        return 1_000_000
    return 0


def _decide(tokens, model="deepseek-v4-flash", budget=35_000, low=15_000, frac=0.85):
    return compaction_decision(
        tokens, provider="deepseek", model=model,
        attention_budget=budget, low_water=low, safety_fraction=frac,
        model_window_fn=_win,
    )


# ── trigger decision ────────────────────────────────────────────────────────

def test_below_attention_budget_does_not_compact():
    d = _decide(20_000)
    assert not d.should_compact
    assert d.reason == "below-threshold"


def test_at_attention_budget_compacts_regardless_of_huge_window():
    # deepseek-flash has a 1M window, but 35k attention budget still fires — the whole point.
    d = _decide(35_000)
    assert d.should_compact
    assert d.reason == "attention"
    assert d.low_water_target == 15_000


def test_attention_budget_is_model_independent():
    # Same 40k transcript triggers on BOTH a 1M and a 256k model via the attention budget.
    assert _decide(40_000, model="deepseek-v4-flash").reason == "attention"
    assert _decide(40_000, model="glm-5.1").reason == "attention"


def test_safety_ceiling_scales_with_small_window():
    # Contrived: raise attention budget so ONLY the safety ceiling can fire. glm-5.1 256k
    # * 0.85 = 217_600.
    d = compaction_decision(
        220_000, provider="z", model="glm-5.1",
        attention_budget=500_000, low_water=15_000, safety_fraction=0.85,
        model_window_fn=_win,
    )
    assert d.should_compact
    assert d.reason == "safety"
    assert d.safety_ceiling == 217_600


def test_safety_ceiling_higher_for_big_window():
    # Same 220k on a 1M model does NOT hit the safety ceiling (850k) and (with a huge
    # attention budget) does not compact.
    d = compaction_decision(
        220_000, provider="deepseek", model="deepseek-v4-flash",
        attention_budget=500_000, low_water=15_000, safety_fraction=0.85,
        model_window_fn=_win,
    )
    assert not d.should_compact


def test_unknown_window_disables_safety_only():
    d = compaction_decision(
        50_000, provider="x", model="mystery",
        attention_budget=500_000, low_water=15_000, safety_fraction=0.85,
        model_window_fn=_win,
    )
    assert d.safety_ceiling == 0
    assert not d.should_compact  # below attention budget, no safety ceiling


def test_empty_transcript():
    d = _decide(0)
    assert not d.should_compact
    assert d.reason == "empty"


# ── round grouping ──────────────────────────────────────────────────────────

def test_group_rounds_basic():
    msgs = [
        {"role": "user", "content": "a"},
        {"role": "assistant", "content": "b"},
        {"role": "user", "content": "c"},
        {"role": "assistant", "content": "d"},
    ]
    rounds = group_rounds(msgs)
    assert len(rounds) == 2
    assert rounds[0][0]["content"] == "a"
    assert rounds[1][0]["content"] == "c"


def test_round_open_when_tool_call_unresolved():
    open_round = [
        {"role": "user", "content": "do it"},
        {"role": "assistant", "content": "", "tool_calls": [{"name": "bash"}, {"name": "read"}]},
        {"role": "tool", "name": "bash", "content": "ok"},
        # read result missing → open
    ]
    assert round_is_open(open_round)


def test_round_closed_when_all_results_arrived():
    closed = [
        {"role": "user", "content": "do it"},
        {"role": "assistant", "content": "", "tool_calls": [{"name": "bash"}]},
        {"role": "tool", "name": "bash", "content": "ok"},
        {"role": "assistant", "content": "done"},
    ]
    assert not round_is_open(closed)


# ── round-atomic selection ──────────────────────────────────────────────────

def _round(u, extra=None):
    r = [{"role": "user", "content": u}]
    r += extra or [{"role": "assistant", "content": "reply-" + u}]
    return r


def test_select_keeps_last_round_and_splits_on_boundary():
    # 6 small rounds; keep_recent budget small so only recent rounds are kept.
    msgs = []
    for k in range(6):
        msgs += _round(f"u{k}")
    old, kept = select_for_compaction(msgs, keep_recent_tokens=5)
    # last round always kept
    assert kept[0]["content"] == kept[0]["content"]
    assert kept[-1]["content"] == "reply-u5"
    # old is a whole-round prefix
    assert old[0]["content"] == "u0"
    # boundary is between user messages — kept starts on a user message
    assert kept[0]["role"] == "user"


def test_select_never_splits_a_tool_pair():
    # A round with a tool_use + tool_result. Whatever the boundary, the pair stays together.
    msgs = _round("u0") + _round("u1", extra=[
        {"role": "assistant", "content": "", "tool_calls": [{"name": "bash"}]},
        {"role": "tool", "name": "bash", "content": "RESULT"},
        {"role": "assistant", "content": "done"},
    ]) + _round("u2")
    old, kept = select_for_compaction(msgs, keep_recent_tokens=1)
    # The tool_call and its result must be in the SAME partition (never one in old, one in kept).
    def has_call(ms): return any(m.get("tool_calls") for m in ms)
    def has_result(ms): return any(m.get("role") == "tool" for m in ms)
    assert has_call(old) == has_result(old)
    assert has_call(kept) == has_result(kept)


def test_select_nothing_to_compact_returns_unchanged():
    msgs = _round("only")
    old, kept = select_for_compaction(msgs, keep_recent_tokens=5)
    assert old == []
    assert kept == msgs


def test_select_big_recent_budget_keeps_everything():
    msgs = _round("u0") + _round("u1")
    old, kept = select_for_compaction(msgs, keep_recent_tokens=10_000)
    assert old == []
    assert len(kept) == len(msgs)


# ── Stage-A tool stubbing ───────────────────────────────────────────────────

def test_fold_old_tool_results_stubs_old_keeps_newest():
    msgs = []
    for k in range(8):
        msgs.append({"role": "assistant", "content": "", "tool_calls": [{"name": "bash"}]})
        msgs.append({"role": "tool", "name": "bash", "content": "X" * 1000})
    folded, n = fold_old_tool_results(msgs, keep=3)
    tool_msgs = [m for m in folded if m.get("role") == "tool"]
    stubbed = [m for m in tool_msgs if str(m["content"]).startswith("[tool-result ryddet")]
    full = [m for m in tool_msgs if not str(m["content"]).startswith("[tool-result ryddet")]
    assert len(full) == 3      # newest 3 kept full
    assert len(stubbed) == 5   # older 5 stubbed
    assert n == 5


def test_fold_leaves_non_tool_messages_untouched():
    msgs = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "", "tool_calls": [{"name": "bash"}]},
        {"role": "tool", "name": "bash", "content": "A" * 500},
        {"role": "assistant", "content": "", "tool_calls": [{"name": "bash"}]},
        {"role": "tool", "name": "bash", "content": "B" * 500},
    ]
    folded, n = fold_old_tool_results(msgs, keep=1)
    assert folded[0]["content"] == "hi"          # user untouched
    assert folded[1].get("tool_calls")           # assistant tool_call untouched
    assert n == 1


def test_fold_is_idempotent_on_stubs():
    msgs = [{"role": "tool", "name": "b", "content": "Z" * 400} for _ in range(4)]
    once, n1 = fold_old_tool_results(msgs, keep=1)
    twice, n2 = fold_old_tool_results(once, keep=1)
    assert n2 == 0  # already stubbed → nothing more to fold
    assert once == twice


def test_fold_noop_when_few_tools():
    msgs = [{"role": "tool", "name": "b", "content": "x"}]
    folded, n = fold_old_tool_results(msgs, keep=5)
    assert n == 0
    assert folded == msgs


# ── summary rendering + prompt + quality gate ───────────────────────────────

def test_render_transcript_labels_speakers_and_tools():
    msgs = [
        {"role": "user", "content": "find X"},
        {"role": "assistant", "content": "searching", "tool_calls": [{"function": {"name": "grep"}}]},
        {"role": "tool", "name": "grep", "content": "hit"},
    ]
    text = render_transcript_for_summary(msgs)
    assert "[Bjørn] find X" in text
    assert "kalder værktøj: grep" in text
    assert "[tool:grep] hit" in text


def test_structured_prompt_contains_sections_and_focus():
    p = build_structured_summary_prompt(
        [{"role": "user", "content": "hej"}], focus="behold API-kontrakten")
    assert "<summary>" in p
    assert "Beslutning: X. Hvorfor: Y. Forkastet: Z." in p
    assert "behold API-kontrakten" in p
    assert "ORDRET" in p  # verbatim-constraint guard present
    assert "ANTI-OPFINDELSE" in p  # anti-hallucination guard (live-test fix)


def test_transcript_cap_keeps_head_and_tail():
    from core.context.compaction_policy import _cap_transcript
    t = "HEAD" + ("x" * 5000) + "TAIL"
    out = _cap_transcript(t, max_chars=200)
    assert out.startswith("HEAD")
    assert out.rstrip().endswith("TAIL")
    assert "udeladt" in out
    assert len(out) < len(t)
    # under the cap → unchanged
    assert _cap_transcript("short", max_chars=200) == "short"
    assert _cap_transcript("anything", max_chars=0) == "anything"  # 0 = unbounded


def test_structured_prompt_respects_transcript_cap():
    big = [{"role": "user", "content": "x" * 40000}]
    p = build_structured_summary_prompt(big, max_transcript_chars=5000)
    assert "udeladt" in p  # middle elided
    assert len(p) < 20000


def test_structured_prompt_injects_ground_truth():
    gt = "=== GROUND TRUTH ===\nCurrent git HEAD: abc123\n=== END ==="
    p = build_structured_summary_prompt(
        [{"role": "user", "content": "hej"}], ground_truth=gt)
    assert "Current git HEAD: abc123" in p
    # ground truth must come BEFORE the transcript so it anchors the model.
    assert p.index("Current git HEAD") < p.index("--- HISTORIK ---")


def test_summary_quality_gate():
    assert summary_looks_valid("x" * 100)
    assert not summary_looks_valid("")
    assert not summary_looks_valid("short")
    assert not summary_looks_valid("[Kontekst komprimeret — detaljer ikke tilgængelige]")


def test_gate_rejects_thinking_and_meta_commentary():
    # The live-test failure: cheap model narrated the task instead of writing the summary.
    assert not summary_looks_valid("<thinking>Okay let me process this and figure out</thinking>")
    assert not summary_looks_valid("Okay, let me process this. The structure should follow the format")
    assert not summary_looks_valid("Let me process the conversation and write a good summary of it")


def test_extract_summary_strips_thinking_and_pulls_tag():
    from core.context.compaction_policy import extract_summary
    raw = "<thinking>Okay, I should walk the conversation...</thinking>\n<summary>1. Bjørn vil bygge compaction. 2. Igangværende: test.</summary>"
    out = extract_summary(raw)
    assert out.startswith("1. Bjørn vil bygge compaction")
    assert "thinking" not in out.lower()


def test_extract_summary_handles_truncated_open_tag():
    from core.context.compaction_policy import extract_summary
    raw = "<summary>Bjørn er ejeren; igangværende arbejde er compaction"  # no close tag
    out = extract_summary(raw)
    assert out.startswith("Bjørn er ejeren")


def test_extract_summary_then_gate_end_to_end():
    from core.context.compaction_policy import extract_summary
    # A thinking-only response (no real summary) → extraction yields the preamble → gate rejects.
    raw = "<thinking>reasoning...</thinking>Okay, let me process this and outline the sections"
    assert not summary_looks_valid(extract_summary(raw))
    # A proper tagged summary → extraction + gate passes.
    good = "<summary>" + ("Bjørn bygger visible-lane compaction. " * 5) + "</summary>"
    assert summary_looks_valid(extract_summary(good))
