"""Præfiks-låsen: samme tool-sæt gennem en session (2026-09-05).

Målt før: 14 ture i træk fik hver sit præfiks-sha, fordi routeren valgte et nyt
sæt pr. besked (58-88 værktøjer). Tools ligger lige efter systembeskeden i
DeepSeeks template, så hele historikken bagefter blev betalt fuldt hver tur —
hit frosset på 6.400-8.320 tokens mens miss voksede til 76k.
"""
from __future__ import annotations

import types

import pytest

from core.services import session_tool_pin as STP


@pytest.fixture
def state(monkeypatch):
    store: dict = {}
    monkeypatch.setattr("core.runtime.db.get_runtime_state_value",
                        lambda k, d=None: store.get(k, d))
    monkeypatch.setattr("core.runtime.db.set_runtime_state_value",
                        lambda k, v: store.__setitem__(k, v))
    monkeypatch.setattr(STP, "_compact_epoch", lambda _sid: 7)
    return store


def test_the_first_turn_decides_and_the_next_reuses(state):
    names, src = STP.resolve("s1", ["bash", "read_file", "recall_memories"])
    assert src == "pinned-new" and names == ["bash", "read_file", "recall_memories"]
    # Routeren vil noget andet naeste tur — laasen vinder, saa praefikset holder.
    again, src2 = STP.resolve("s1", ["calendar_create", "send_mail"])
    assert src2 == "pinned" and again == names


def test_the_set_is_order_stable(state):
    """Samme saet i en anden raekkefoelge maa give samme praefiks."""
    a, _ = STP.resolve("s1", ["read_file", "bash"])
    STP.clear("s1")
    b, _ = STP.resolve("s1", ["bash", "read_file"])
    assert a == b == ["bash", "read_file"]


def test_sessions_are_independent(state):
    STP.resolve("s1", ["bash"])
    names, src = STP.resolve("s2", ["calendar_create"])
    assert src == "pinned-new" and names == ["calendar_create"]
    assert STP.get_pinned("s1") == ["bash"]


def test_load_more_tools_extends_the_lock(state):
    STP.resolve("s1", ["bash"])
    STP.extend("s1", ["git_log", "read_file"])
    assert STP.get_pinned("s1") == ["bash", "git_log", "read_file"]
    # Naeste tur genbruger det udvidede saet — vaerktoejet forsvinder ikke igen.
    names, src = STP.resolve("s1", ["noget_helt_andet"])
    assert src == "pinned" and "git_log" in names


def test_extending_with_nothing_new_changes_nothing(state):
    STP.resolve("s1", ["bash", "git_log"])
    assert STP.extend("s1", ["bash"]) == ["bash", "git_log"]


def test_extend_before_anything_is_pinned_is_a_noop(state):
    assert STP.extend("s1", ["git_log"]) == []
    assert STP.get_pinned("s1") == []


def test_compaction_releases_the_lock(state, monkeypatch):
    """Compaction skriver historikken om og bryder cachen alligevel — dér maa
    routeren gerne vaelge forfra uden at det koster ekstra."""
    STP.resolve("s1", ["bash"])
    assert STP.get_pinned("s1") == ["bash"]
    monkeypatch.setattr(STP, "_compact_epoch", lambda _sid: 8)
    assert STP.get_pinned("s1") == []
    names, src = STP.resolve("s1", ["read_file"])
    assert src == "pinned-new" and names == ["read_file"]


def test_the_kill_switch_restores_the_old_behaviour(state, monkeypatch):
    STP.resolve("s1", ["bash"])
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: types.SimpleNamespace(session_tool_pin_enabled=False))
    names, src = STP.resolve("s1", ["calendar_create", "send_mail"])
    assert src == "router" and names == ["calendar_create", "send_mail"]
    assert STP.get_pinned("s1") == []


def test_it_is_on_by_default():
    from core.runtime.settings import load_settings
    assert getattr(load_settings(), "session_tool_pin_enabled", None) is True
    assert STP.pin_enabled() is True


def test_a_broken_state_store_never_blocks_the_turn(monkeypatch):
    def _boom(*_a, **_k):
        raise RuntimeError("state nede")
    monkeypatch.setattr("core.runtime.db.get_runtime_state_value", _boom)
    monkeypatch.setattr("core.runtime.db.set_runtime_state_value", _boom)
    names, src = STP.resolve("s1", ["bash", "read_file"])
    assert names == ["bash", "read_file"]


def test_an_empty_selection_is_left_alone(state):
    assert STP.resolve("s1", []) == ([], "router")
    assert STP.resolve("", ["bash"]) == (["bash"], "router")
