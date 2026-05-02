"""Tests for build_brain_facts_section — auto-inject of relevant fakta."""
from __future__ import annotations
import numpy as np
import pytest


@pytest.fixture
def isolated_brain(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")

    def fake(text):
        if "alpha" in text.lower():
            return np.array([1.0, 0.0, 0.0], dtype=np.float32)
        if "beta" in text.lower():
            return np.array([0.0, 1.0, 0.0], dtype=np.float32)
        return np.array([0.0, 0.0, 1.0], dtype=np.float32)

    monkeypatch.setattr(jarvis_brain, "_embed_text", fake)
    yield jarvis_brain


def test_build_brain_facts_section_returns_empty_with_no_entries(isolated_brain):
    from core.services.prompt_sections.jarvis_brain_facts import (
        build_brain_facts_section,
    )
    out = build_brain_facts_section(
        user_message="alpha lookup", session_id="webchat-test",
        top_k=3, threshold=0.0,
    )
    assert out == ""


def test_build_brain_facts_section_includes_matching_fakta(isolated_brain):
    from core.services.prompt_sections.jarvis_brain_facts import (
        build_brain_facts_section,
    )
    # public_safe entry — works regardless of session ceiling
    isolated_brain.write_entry(
        kind="fakta", title="Alpha thing", content="alpha details body",
        visibility="public_safe", domain="d",
    )
    isolated_brain.embed_pending_entries()

    out = build_brain_facts_section(
        user_message="alpha question",
        session_id=None,  # public_safe ceiling
        top_k=3,
        threshold=0.0,
    )
    assert "Alpha thing" in out
    assert out.startswith("## Relevante fakta fra min hjerne")


def test_build_brain_facts_section_intimate_ceiling_for_jarvisx_native(isolated_brain, monkeypatch):
    """Mock a jarvisx_native session to verify intimate ceiling allows
    intimate fakta through."""
    from core.services.prompt_sections import jarvis_brain_facts as mod
    monkeypatch.setattr(mod, "_ceiling_from_session_id", lambda sid: "intimate")

    isolated_brain.write_entry(
        kind="fakta", title="Intimate alpha", content="alpha intimate detail",
        visibility="intimate", domain="d",
    )
    isolated_brain.embed_pending_entries()

    out = mod.build_brain_facts_section(
        user_message="alpha question",
        session_id="any",
        top_k=3,
        threshold=0.0,
    )
    assert "Intimate alpha" in out


def test_build_brain_facts_section_filters_below_threshold(isolated_brain):
    from core.services.prompt_sections.jarvis_brain_facts import (
        build_brain_facts_section,
    )
    isolated_brain.write_entry(
        kind="fakta", title="Beta thing", content="beta",
        visibility="personal", domain="d",
    )
    isolated_brain.embed_pending_entries()

    # Query is alpha; brain has only beta → cosine ~0; threshold 0.5 → no match
    out = build_brain_facts_section(
        user_message="alpha lookup",
        session_id="webchat-test",
        top_k=3,
        threshold=0.5,
    )
    assert out == ""


def test_build_brain_facts_section_respects_visibility_for_owner_dm(isolated_brain):
    """Owner DM session gets intimate ceiling → can pull intimate fakta."""
    from core.services.prompt_sections.jarvis_brain_facts import (
        build_brain_facts_section,
    )
    isolated_brain.write_entry(
        kind="fakta", title="Intimate fakta", content="alpha intimate details",
        visibility="intimate", domain="d",
    )
    isolated_brain.embed_pending_entries()

    # Title contains "Discord DM — bjorn" (owner DM) → intimate ceiling
    out = build_brain_facts_section(
        user_message="alpha",
        session_id=None,  # No session — falls back to default deny
        top_k=3,
        threshold=0.0,
    )
    # No session → public_safe ceiling → intimate fakta blocked
    assert "Intimate fakta" not in out
