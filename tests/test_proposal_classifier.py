from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.api.jarvis_api.services.proposal_classifier import classify_fragment


def test_no_action_in_plain_fragment():
    """Fragment without action language returns has_action=False."""
    result = classify_fragment("Mørket udenfor er stille. Lyset er slukket.")
    assert result["has_action"] is False


def test_detects_danish_action_language():
    """Fragment with 'vil gerne' triggers action detection."""
    result = classify_fragment("Det er interessant — jeg vil gerne undersøge hvad brugeren tænker om det.")
    assert result["has_action"] is True
    assert result["action_description"] != ""


def test_detects_english_action_language():
    """Fragment with 'I could' triggers action detection."""
    result = classify_fragment("This feels incomplete. I could look into it more deeply.")
    assert result["has_action"] is True


def test_non_destructive_score_below_threshold():
    """Research/ask actions score below 0.5 destructive."""
    result = classify_fragment("Lyst til at spørge brugeren om hans mening om det her emne.")
    assert result["has_action"] is True
    assert result["destructive_score"] < 0.5
    assert result["proposal_type"] == "non_destructive"


def test_destructive_keywords_raise_score():
    """Fragment mentioning deletion scores above 0.5."""
    result = classify_fragment("Måske burde jeg slette de gamle logfiler og rydde op.")
    assert result["has_action"] is True
    assert result["destructive_score"] >= 0.5
    assert result["proposal_type"] == "needs_approval"


def test_destructive_english_keywords():
    """Fragment mentioning 'delete' scores above 0.5."""
    result = classify_fragment("I want to delete the old cache files to free up space.")
    assert result["has_action"] is True
    assert result["destructive_score"] >= 0.5
    assert result["proposal_type"] == "needs_approval"


def test_action_description_is_non_empty_when_action_found():
    """When has_action is True, action_description must be a non-empty string."""
    result = classify_fragment("Jeg vil gerne prøve at skrive en note om det her.")
    assert result["has_action"] is True
    assert isinstance(result["action_description"], str)
    assert len(result["action_description"]) > 0


def test_result_keys_always_present():
    """classify_fragment always returns all required keys."""
    result = classify_fragment("Bare en tanke om ingenting.")
    assert set(result.keys()) >= {"has_action", "action_description", "destructive_score", "proposal_type", "destructive_reason"}
