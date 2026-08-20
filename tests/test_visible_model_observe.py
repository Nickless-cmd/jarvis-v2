from core.services.visible_model_observe import _reasoning_fallback_text


def test_reasoning_fallback_rejects_truncated_internal_plan() -> None:
    assert _reasoning_fallback_text(
        "<think>intern plan</think>", finish_reason="length",
    ) == ""


def test_reasoning_fallback_accepts_cleanly_completed_answer() -> None:
    assert _reasoning_fallback_text(
        "<think>Det endelige svar.</think>", finish_reason="stop",
    ) == "Det endelige svar."
