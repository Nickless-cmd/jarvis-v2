"""Tests for run_follow — follow-buffer til desk token-streaming af wakeup-runs."""
from __future__ import annotations

from core.services import run_follow as rf


def test_begin_publish_snapshot_end():
    rf.begin_follow("s1", "run-1")
    assert rf.has_active_follow("s1") is True
    rf.publish_follow_frame("s1", "event: a\ndata: 1\n\n")
    rf.publish_follow_frame("s1", "event: b\ndata: 2\n\n")
    frames, done = rf._snapshot("s1", 0)
    assert len(frames) == 2 and done is False
    # inkrementel: fra idx 2 → ingen nye endnu
    frames2, _ = rf._snapshot("s1", 2)
    assert frames2 == []
    rf.end_follow("s1")
    _, done2 = rf._snapshot("s1", 0)
    assert done2 is True
    assert rf.has_active_follow("s1") is False


def test_begin_resets_buffer():
    rf.begin_follow("s2", "run-a")
    rf.publish_follow_frame("s2", "x")
    rf.begin_follow("s2", "run-b")  # nyt run → catch-up forfra
    frames, _ = rf._snapshot("s2", 0)
    assert frames == []


def test_snapshot_unknown_session():
    frames, done = rf._snapshot("nope", 0)
    assert frames == [] and done is False
