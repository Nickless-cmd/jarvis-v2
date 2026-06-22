"""Tests for the merged single brain section (2026-06-22 round 3)."""
from unittest.mock import MagicMock, patch

from core.services.prompt_sections import jarvis_brain_facts as jbf


def _fact(title, content, fid="fact-id-test-0001"):
    e = MagicMock()
    e.id = fid
    e.title = title
    e.content = content
    return e


def test_uses_merged_relevance_header():
    facts = [_fact("Deploy note", "vi deployede prompt-redesign")]
    with patch("core.services.jarvis_brain.search_brain", return_value=facts), \
         patch("core.services.jarvis_brain.bump_salience", return_value=None):
        out = jbf.build_brain_facts_section(
            user_message="hvad lavede vi", session_id="s", top_k=5
        )
    assert "## Min hjerne — mest relevant for denne samtale" in out
    # the old generic header is gone
    assert "Relevante fakta fra min hjerne" not in out
    assert "Deploy note" in out


def test_empty_string_when_no_results():
    with patch("core.services.jarvis_brain.search_brain", return_value=[]):
        out = jbf.build_brain_facts_section(
            user_message="hej", session_id="s", top_k=5
        )
    assert out == ""


def test_failsoft_on_search_error():
    with patch("core.services.jarvis_brain.search_brain", side_effect=RuntimeError("db down")):
        out = jbf.build_brain_facts_section(
            user_message="hej", session_id="s", top_k=5
        )
    assert out == ""
