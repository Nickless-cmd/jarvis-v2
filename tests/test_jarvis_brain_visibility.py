"""Tests for core/services/jarvis_brain_visibility.py — privacy gate."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import pytest


@dataclass
class FakeSession:
    channel_kind: str = ""
    participants: Optional[List[str]] = None
    is_autonomous: bool = False
    is_inner_voice: bool = False


def _patch_owner(monkeypatch, owner_id="bjorn"):
    from core.services import jarvis_brain_visibility as v
    monkeypatch.setattr(v, "_resolve_owner_id", lambda: owner_id)


@pytest.mark.parametrize(
    "session,expected",
    [
        (FakeSession(channel_kind="dm", participants=["bjorn"]), "intimate"),
        (FakeSession(channel_kind="jarvisx_native", participants=["bjorn"]), "intimate"),
        (FakeSession(channel_kind="public_channel", participants=["bjorn", "mikkel"]), "public_safe"),
        (FakeSession(channel_kind="owner_private_channel", participants=["bjorn"]), "personal"),
        (FakeSession(channel_kind="dm", participants=["mikkel"]), "public_safe"),
        (FakeSession(is_autonomous=True), "personal"),
        (FakeSession(is_inner_voice=True), "personal"),
        (FakeSession(channel_kind="webhook", participants=None), "public_safe"),
        (FakeSession(channel_kind="email", participants=["random@example.com"]), "public_safe"),
    ],
)
def test_session_visibility_ceiling(session, expected, monkeypatch):
    _patch_owner(monkeypatch)
    from core.services.jarvis_brain_visibility import session_visibility_ceiling
    assert session_visibility_ceiling(session) == expected


def test_group_dm_with_third_party_is_public_safe(monkeypatch):
    _patch_owner(monkeypatch)
    from core.services.jarvis_brain_visibility import session_visibility_ceiling
    s = FakeSession(channel_kind="dm", participants=["bjorn", "mikkel"])
    assert session_visibility_ceiling(s) == "public_safe"


def test_can_recall_respects_levels():
    from core.services.jarvis_brain_visibility import can_recall
    assert can_recall("public_safe", "public_safe") is True
    assert can_recall("personal", "public_safe") is False
    assert can_recall("intimate", "personal") is False
    assert can_recall("intimate", "intimate") is True
    assert can_recall("public_safe", "intimate") is True


def test_default_deny_on_uncertain_session(monkeypatch):
    _patch_owner(monkeypatch)
    from core.services.jarvis_brain_visibility import session_visibility_ceiling
    s = FakeSession()
    assert session_visibility_ceiling(s) == "public_safe"


def test_unknown_channel_with_only_owner_falls_back_to_public_safe(monkeypatch):
    _patch_owner(monkeypatch)
    from core.services.jarvis_brain_visibility import session_visibility_ceiling
    # Owner-only but unknown channel kind → default deny
    s = FakeSession(channel_kind="unknown_channel_type", participants=["bjorn"])
    assert session_visibility_ceiling(s) == "public_safe"
