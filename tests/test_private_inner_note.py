"""Tests for private_inner_note — focus on _derive_focus contract.

2026-05-25 (Claude): _derive_focus used to truncate raw user-message
to 48 chars, producing gibberish focus values that corrupted downstream
inner-voice outputs. Now returns short messages verbatim only when they
look like clean topic labels; otherwise falls back to "open conversation".
"""
from core.memory.private_inner_note import _derive_focus


def test_empty_returns_open_conversation():
    assert _derive_focus("") == "open conversation"
    assert _derive_focus(None) == "open conversation"
    assert _derive_focus("   ") == "open conversation"


def test_short_clean_phrase_kept():
    """Short single-clause messages pass through as topic labels."""
    assert _derive_focus("commit changes") == "commit changes"
    assert _derive_focus("Build the windows version") == "Build the windows version"


def test_trailing_punctuation_stripped():
    """One trailing ? is fine but stripped."""
    assert _derive_focus("How does cache work?") == "How does cache work"
    assert _derive_focus("commit!") == "commit"


def test_long_message_falls_back_to_generic():
    """Messages over 36 chars get the generic placeholder — they're not
    topic labels, they're user-message content."""
    long_msg = "hmm feks. hvis jeg skifter din model feks. til g"
    assert _derive_focus(long_msg) == "open conversation"


def test_multi_question_falls_back():
    """Multiple question marks indicate this isn't a clean topic."""
    assert _derive_focus("kl 16:40???") == "open conversation"
    assert _derive_focus("what?? when??") == "open conversation"


def test_multi_clause_falls_back():
    """More than one comma indicates multi-clause content, not a label."""
    msg = "1, du vælger selv. 2. Llm (vi bruger ollama elle"
    assert _derive_focus(msg) == "open conversation"


def test_borderline_length():
    """Exactly 36 chars passes; 37+ falls back."""
    s36 = "a" * 36
    s37 = "a" * 37
    assert _derive_focus(s36) == s36
    assert _derive_focus(s37) == "open conversation"


def test_whitespace_collapsed():
    """Multiple whitespace chars get collapsed."""
    out = _derive_focus("test   with    spaces")
    assert out == "test with spaces"
