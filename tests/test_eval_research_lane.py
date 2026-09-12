from scripts.eval_research_lane import evaluate_cases


def test_twenty_case_research_eval_is_green():
    result = evaluate_cases()
    assert result["cases"] == 20
    assert result["failures"] == []
