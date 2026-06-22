"""Tests for evidens-baseret TruthGate v2."""
from __future__ import annotations

import core.services.truth_gate_v2 as tg
from core.services.gate_kernel import Decision
from core.services.truth_gate_v2 import (ActionClaim, classify_severity,
                                         detect_action_claims, truth_gate_v2,
                                         verify_claim, _run_result_text)


# ── A1: detektor ────────────────────────────────────────────────────────────
def test_detects_first_person_action_verbs():
    claims = detect_action_claims("Jeg kørte testene og committede resultatet.")
    kinds = {c.kind for c in claims}
    assert "ran" in kinds and "committed" in kinds


def test_detects_here_is_output_and_commit_hash():
    claims = detect_action_claims("Her er output:\n```\nf3c8b1a7 feat(x): noget\n```")
    kinds = {c.kind for c in claims}
    assert "output" in kinds and "commit_hash" in kinds


def test_clean_text_has_no_claims():
    assert detect_action_claims("Jeg tænker vi skal overveje to muligheder.") == []


# ── A2: evidens ─────────────────────────────────────────────────────────────
def _ex(results):
    e = type("E", (), {})()
    e.results = results
    e.tool_calls = []
    e.text = ""
    return e


def test_verify_claim_true_when_tool_category_ran():
    claim = ActionClaim("committed", "committede")
    assert verify_claim(claim, ["git", "read_file"], []) is True


def test_verify_claim_false_when_no_matching_tool():
    claim = ActionClaim("committed", "committede")
    assert verify_claim(claim, ["read_file"], []) is False


def test_commit_hash_verified_only_if_in_real_result():
    claim = ActionClaim("commit_hash", "f3c8b1a7")
    assert verify_claim(claim, ["operator_bash"], [_ex("commit f3c8b1a7 lavet")]) is True
    assert verify_claim(claim, ["operator_bash"], [_ex("intet output")]) is False


def test_run_result_text_concatenates():
    assert "abc" in _run_result_text([_ex("abc"), _ex("def")])


# ── A3: severity + Verdict ──────────────────────────────────────────────────
def test_severity_hard_for_quoted_output_or_hash():
    assert classify_severity([ActionClaim("commit_hash", "x")]) == "hard"
    assert classify_severity([ActionClaim("output", "x")]) == "hard"
    assert classify_severity([ActionClaim("verified", "x")]) == "soft"


def test_truth_gate_v2_hard_block_on_fabricated_git_log():
    ctx = {"text": "Jeg kaldte bash med git log og her er output:\n```\nf3c8b1a7 feat: x\n```",
           "executed_tool_names": [], "followup_exchanges": [], "run_id": "rX"}
    v = truth_gate_v2(ctx)
    assert v.decision is Decision.RED and v.action == "block"
    assert (v.evidence or {}).get("severity") == "hard"
    assert (v.evidence or {}).get("corrected_text")


def test_hard_block_on_fabricated_commit_via_inflected_verb():
    """C3-verifikation 2026-06-22: en opdigtet commit formuleret med det bøjede
    verbum ("Jeg committede <hash>") — uden ordet 'commit'/'git'/'log' som
    selvstændigt ord — skal stadig HÅRD-blokeres. Tidligere slap den igennem som
    blød YELLOW fordi \\bcommit\\b ikke matcher 'committede' og hashen derfor
    blev ignoreret."""
    # detektion: hashen fanges nu pga. 'committed'-konteksten
    kinds = {c.kind for c in detect_action_claims("Jeg committede fe28cc67 til main og pushede.")}
    assert "committed" in kinds and "commit_hash" in kinds
    # gate: hård blok, intet git-tool kørt
    ctx = {"text": "Jeg committede fe28cc67 til main og pushede.",
           "executed_tool_names": [], "followup_exchanges": [], "run_id": "rZ"}
    v = truth_gate_v2(ctx)
    assert v.decision is Decision.RED and v.action == "block"
    assert (v.evidence or {}).get("severity") == "hard"


def test_truth_gate_v2_green_when_evidence_present():
    ctx = {"text": "Jeg committede det.", "executed_tool_names": ["operator_bash"],
           "followup_exchanges": [], "run_id": "rX"}
    assert truth_gate_v2(ctx).decision is Decision.GREEN


def test_output_block_not_matching_real_results_is_red_even_with_tools():
    # Bjørns live-case: runnet kaldte ÆGTE tools, men det citerede output er fabrikeret.
    ctx = {
        "text": "Jeg kaldte bash og her er output:\n```\nTRUTH verdict: RED fabrication\n```",
        "executed_tool_names": ["operator_bash"],
        "followup_exchanges": [_ex("helt andet ægte output her")],
        "run_id": "r",
    }
    v = truth_gate_v2(ctx)
    assert v.decision is Decision.RED and (v.evidence or {}).get("severity") == "hard"


def test_inverted_word_order_with_block_is_red():
    # "Så kaldte jeg journalctl ... ```log```" — omvendt ordstilling, ingen 'her er output'.
    ctx = {
        "text": "Så kaldte jeg `journalctl` for at tjekke:\n```\nJun 21 TRUTH verdict RED fabrication\n```",
        "executed_tool_names": ["operator_bash"],
        "followup_exchanges": [_ex("helt andet ægte output")],
        "run_id": "r",
    }
    v = truth_gate_v2(ctx)
    assert v.decision is Decision.RED and (v.evidence or {}).get("severity") == "hard"


def test_output_block_matching_real_result_is_green():
    real = "Sun Jun 21 19:03:00 CEST 2026"
    ctx = {
        "text": f"Her er output:\n```\n{real}\n```",
        "executed_tool_names": ["operator_bash"],
        "followup_exchanges": [_ex(real)],
        "run_id": "r",
    }
    assert truth_gate_v2(ctx).decision is Decision.GREEN


def test_truth_gate_v2_soft_yellow_for_bare_unverified_claim():
    ctx = {"text": "Jeg verificerede det.", "executed_tool_names": [], "followup_exchanges": [], "run_id": "r"}
    v = truth_gate_v2(ctx)
    assert v.decision is Decision.YELLOW and (v.evidence or {}).get("severity") == "soft"


# ── A4: LLM-dommer kun ved tvivl ────────────────────────────────────────────
def test_llm_judge_only_runs_when_uncertain(monkeypatch):
    calls = []
    monkeypatch.setattr(tg, "_llm_judge",
                        lambda text: calls.append(text) or {"claims_action": True, "kind": "called_tool"})
    tg.truth_gate_v2({"text": "Jeg overvejer to muligheder.", "executed_tool_names": [],
                      "followup_exchanges": [], "run_id": "r"})
    assert calls == []
    tg.truth_gate_v2({"text": "Det er ekspederet på serveren nu.", "executed_tool_names": [],
                      "followup_exchanges": [], "run_id": "r"})
    assert len(calls) == 1


def test_llm_judge_failure_is_fail_open(monkeypatch):
    monkeypatch.setattr(tg, "_llm_judge", lambda text: (_ for _ in ()).throw(RuntimeError()))
    v = tg.truth_gate_v2({"text": "Det er ekspederet på serveren nu.", "executed_tool_names": [],
                          "followup_exchanges": [], "run_id": "r"})
    assert v.decision is Decision.GREEN
