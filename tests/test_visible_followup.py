"""Tests for visible_followup streaming dataclasses (live reasoning trace)."""
from dataclasses import FrozenInstanceError

import pytest

from core.services.visible_followup import (
    FollowupReasoningDelta,
    FollowupDelta,
    FollowupDone,
)


def test_reasoning_delta_carries_chunk():
    d = FollowupReasoningDelta(delta="Lad mig tænke…")
    assert d.delta == "Lad mig tænke…"


def test_reasoning_delta_is_frozen():
    d = FollowupReasoningDelta(delta="x")
    with pytest.raises(FrozenInstanceError):
        d.delta = "y"  # type: ignore[misc]


def test_reasoning_delta_is_distinct_from_text_delta():
    # Reasoning og prose er forskellige typer så consumers kan routes hver for
    # sig (thinking-block vs text-block).
    assert FollowupReasoningDelta(delta="a") != FollowupDelta(delta="a")


def test_done_still_carries_reasoning_for_persistence():
    # Live-delta er kun til visning; FollowupDone bærer stadig den fulde
    # reasoning_content til persistens på tværs af runder.
    done = FollowupDone(text="svar", reasoning_content="hele tanken")
    assert done.reasoning_content == "hele tanken"
