"""Coverage-gate alias: real tests live in test_unfinished_intent_detector.py.

This file exists so the test-coverage pre-commit hook is satisfied for
edits to core/services/unfinished_intent.py — the actual test suite is
in test_unfinished_intent_detector.py and is imported here.
"""
from tests.test_unfinished_intent_detector import *  # noqa: F401,F403
