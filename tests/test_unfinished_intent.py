"""Coverage-gate alias: real tests live in test_unfinished_intent_detector.py.

This file exists so the test-coverage pre-commit hook is satisfied for
edits to core/services/unfinished_intent.py — the actual test suite is
in test_unfinished_intent_detector.py and is imported here.
"""
from tests.test_unfinished_intent_detector import *  # noqa: F401,F403


def test_question_ending_suppresses_continuation():
    """Bjørn 2026-06-23: Jarvis spurgte 'skal jeg genstarte?', fik intet svar, og
    genstartede SELV (continuation fabrikerede samtykke). Et afsluttende spørgsmål =
    han venter bevidst på brugeren → ALDRIG continuation."""
    from core.services.unfinished_intent import detect_unfinished_intent as d
    assert d("Jeg lovede en genstart. Jeg genstarter den nu — skal jeg gøre det?") is None
    assert d("Vil du have at jeg implementerer specen nu og deployer med det samme?") is None
    assert d("Skal jeg genstarte serveren?") is None
    # Løfte UDEN spørgsmål fanges stadig (ingen over-suppression)
    assert d("Jeg går i gang!").pattern == "future_action_promise"
