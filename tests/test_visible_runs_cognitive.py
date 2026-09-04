"""Kognitive trackers pr. synlig tur — hvilke der stadig kører (blok B, 4/9).

De gamle ordmønster-detektorer er slukket: målt over 30 dage skrev de 1.756
forkastede USER.md-kandidater mod 9 anvendte, og 19.145 forkastede MEMORY.md-
kandidater med Bjørns egen besked ordret som titel.
"""
from __future__ import annotations

import types

import core.services.visible_runs_cognitive as VRC


def _run():
    return types.SimpleNamespace(
        run_id="run-1", session_id="s-1", user_message="ryd stale markers")


def test_detectors_are_off_unless_explicitly_re_enabled(monkeypatch):
    assert VRC._legacy_regex_detectors_enabled() is False
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: types.SimpleNamespace(legacy_regex_learning_detectors_enabled=True))
    assert VRC._legacy_regex_detectors_enabled() is True


def test_settings_lookup_failure_leaves_them_off(monkeypatch):
    def _boom():
        raise RuntimeError("config nede")
    monkeypatch.setattr("core.runtime.settings.load_settings", _boom)
    assert VRC._legacy_regex_detectors_enabled() is False


def test_disabled_detectors_are_never_called(monkeypatch):
    """Den dyre del er ikke gaten — det er de tre trackers bag den."""
    called: list[str] = []
    for name in (
        "track_runtime_user_understanding_signals_for_visible_turn",
        "track_runtime_user_md_update_proposals_for_visible_turn",
        "track_runtime_memory_md_update_proposals_for_visible_turn",
        "track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn",
        "track_runtime_contract_candidates_from_user_md_update_proposals_for_visible_turn",
    ):
        monkeypatch.setattr(VRC._vr, name,
                            lambda _n=name, **_kw: called.append(_n), raising=False)
    monkeypatch.setattr(VRC, "_legacy_regex_detectors_enabled", lambda: False)
    # Alle øvrige trackers stubbes til no-op via den fælles fejl-catcher.
    monkeypatch.setattr(VRC, "_track_step_failed", lambda: None)
    VRC._track_runtime_candidates(_run(), "et svar")
    assert called == []


def test_enabled_detectors_still_run(monkeypatch):
    called: list[str] = []
    for name in (
        "track_runtime_user_understanding_signals_for_visible_turn",
        "track_runtime_user_md_update_proposals_for_visible_turn",
    ):
        monkeypatch.setattr(VRC._vr, name,
                            lambda _n=name, **_kw: called.append(_n), raising=False)
    monkeypatch.setattr(VRC, "_legacy_regex_detectors_enabled", lambda: True)
    monkeypatch.setattr(VRC, "_track_step_failed", lambda: None)
    VRC._track_runtime_candidates(_run(), "et svar")
    assert "track_runtime_user_understanding_signals_for_visible_turn" in called
    assert "track_runtime_user_md_update_proposals_for_visible_turn" in called
