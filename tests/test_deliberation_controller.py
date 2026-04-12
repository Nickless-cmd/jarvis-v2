"""Tests for council_deliberation_controller — cosine similarity, deadlock, witness, recruitment."""
from __future__ import annotations

from unittest.mock import patch


def _similarity(a: str, b: str) -> float:
    from apps.api.jarvis_api.services.council_deliberation_controller import _cosine_similarity
    return _cosine_similarity(a, b)


def _is_deadlocked(round_outputs: list[list[str]]) -> bool:
    from apps.api.jarvis_api.services.council_deliberation_controller import _is_deadlocked
    return _is_deadlocked(round_outputs)


def test_identical_texts_have_similarity_1():
    assert abs(_similarity("the cat sat on the mat", "the cat sat on the mat") - 1.0) < 0.001


def test_completely_different_texts_have_low_similarity():
    score = _similarity("quantum physics relativity spacetime", "apple banana fruit salad kitchen")
    assert score < 0.3


def test_similar_texts_have_high_similarity():
    score = _similarity("autonomy limits freedom constraint", "autonomy constraint freedom limit")
    assert score > 0.6


def test_empty_strings_give_zero():
    assert _similarity("", "") == 0.0
    assert _similarity("hello", "") == 0.0


def test_deadlock_not_detected_with_fewer_than_3_rounds():
    assert _is_deadlocked([["abc"], ["abc"]]) is False


def test_deadlock_detected_when_rounds_are_similar():
    # Very similar text triggers deadlock (high overlap in bag-of-words)
    round1 = ["autonomy limit freedom constraint autonomy limit freedom constraint autonomy"]
    round2 = ["creativity music art painting expression"]
    round3 = ["autonomy limit freedom constraint autonomy limit freedom constraint limit"]
    assert _is_deadlocked([round1, round2, round3]) is True


def test_deadlock_not_detected_when_rounds_diverge():
    round1 = ["autonomy freedom constraint limit pressure goal"]
    round2 = ["creativity art music painting sculpture expression"]
    round3 = ["database architecture microservices deployment scaling"]
    assert _is_deadlocked([round1, round2, round3]) is False


def test_witness_escalation_detected():
    from apps.api.jarvis_api.services.council_deliberation_controller import _check_witness_escalation
    assert _check_witness_escalation("[ESKALERER] Jeg ser noget afgørende der overses.") is True


def test_witness_no_escalation_without_marker():
    from apps.api.jarvis_api.services.council_deliberation_controller import _check_witness_escalation
    assert _check_witness_escalation("This is a normal observation.") is False


def test_witness_escalation_case_insensitive():
    from apps.api.jarvis_api.services.council_deliberation_controller import _check_witness_escalation
    assert _check_witness_escalation("[eskalerer] Something important.") is True


def test_witness_prompt_contains_marker_instruction():
    from apps.api.jarvis_api.services.council_deliberation_controller import build_witness_prompt
    prompt = build_witness_prompt(transcript="Filosof: text\nKritiker: text")
    assert "[ESKALERER]" in prompt


def test_recruitment_returns_none_when_llm_says_nej():
    from apps.api.jarvis_api.services.council_deliberation_controller import _analyze_recruitment_need
    with patch(
        "apps.api.jarvis_api.services.council_deliberation_controller._call_recruitment_llm",
        return_value="nej",
    ):
        role = _analyze_recruitment_need(topic="test", transcript="x", active_members=["filosof"])
    assert role is None


def test_recruitment_returns_role_when_llm_suggests_one():
    from apps.api.jarvis_api.services.council_deliberation_controller import _analyze_recruitment_need
    with patch(
        "apps.api.jarvis_api.services.council_deliberation_controller._call_recruitment_llm",
        return_value="etiker",
    ):
        role = _analyze_recruitment_need(topic="test", transcript="x", active_members=["filosof"])
    assert role == "etiker"


def test_recruitment_skips_already_active_role():
    from apps.api.jarvis_api.services.council_deliberation_controller import _analyze_recruitment_need
    with patch(
        "apps.api.jarvis_api.services.council_deliberation_controller._call_recruitment_llm",
        return_value="filosof",
    ):
        role = _analyze_recruitment_need(topic="test", transcript="x", active_members=["filosof"])
    assert role is None


def test_recruitment_normalizes_llm_response():
    from apps.api.jarvis_api.services.council_deliberation_controller import _analyze_recruitment_need
    with patch(
        "apps.api.jarvis_api.services.council_deliberation_controller._call_recruitment_llm",
        return_value="  Etiker  ",
    ):
        role = _analyze_recruitment_need(topic="test", transcript="x", active_members=["filosof"])
    assert role == "etiker"


def _make_controller(topic="Test topic", members=None, max_rounds=8):
    from apps.api.jarvis_api.services.council_deliberation_controller import DeliberationController
    return DeliberationController(
        topic=topic,
        members=members or ["filosof", "kritiker", "synthesizer"],
        max_rounds=max_rounds,
    )


def test_controller_run_returns_deliberation_result():
    from apps.api.jarvis_api.services.council_deliberation_controller import DeliberationResult
    ctrl = _make_controller()
    with patch.object(ctrl, "_run_round", return_value=["filosof: interesting.", "kritiker: valid point.", "synthesizer: agreed."]):
        with patch.object(ctrl, "_synthesize", return_value="Council concludes: proceed."):
            result = ctrl.run()
    assert isinstance(result, DeliberationResult)
    assert result.rounds_run >= 1
    assert result.conclusion == "Council concludes: proceed."


def test_controller_forces_conclusion_at_max_rounds():
    ctrl = _make_controller(max_rounds=2)
    # Different enough outputs to avoid deadlock, but will hit max_rounds
    round_outputs = [
        ["filosof: alpha beta gamma delta epsilon"],
        ["kritiker: zeta eta theta iota kappa"],
    ]
    call_iter = iter(round_outputs)
    with patch.object(ctrl, "_run_round", side_effect=lambda: next(call_iter, ["done"])):
        with patch.object(ctrl, "_synthesize", return_value="Forced conclusion."):
            result = ctrl.run()
    assert result.conclusion == "Forced conclusion."


def test_controller_detects_deadlock():
    ctrl = _make_controller(max_rounds=8)
    similar = ["autonomy constraint limit pressure limit constraint autonomy system"]
    different = ["creativity music art painting expression color beauty"]
    # Rounds: similar, different, similar → deadlock at round 3
    call_iter = iter([similar, different, similar, similar, similar])
    with patch.object(ctrl, "_run_round", side_effect=lambda: next(call_iter, ["done"])):
        with patch.object(ctrl, "_synthesize", return_value="Done."):
            result = ctrl.run()
    assert result.deadlock_occurred is True


def test_controller_witness_escalation_flag():
    ctrl = _make_controller()
    escalating_output = ["filosof: hmm.", "[ESKALERER] I see something critical here."]
    normal_output = ["filosof: final.", "synthesizer: agreed."]
    call_iter = iter([escalating_output, normal_output, normal_output])
    with patch.object(ctrl, "_run_round", side_effect=lambda: next(call_iter, ["done"])):
        with patch.object(ctrl, "_synthesize", return_value="Done."):
            result = ctrl.run()
    assert result.witness_escalated is True
