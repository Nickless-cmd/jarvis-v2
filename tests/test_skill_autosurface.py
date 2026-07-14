"""Tests for core.services.skill_autosurface — owner-approved allowlist that
governs which skills jarvis-code is allowed to auto-surface (Fase 3, Task 1).

Uses a tmp_path-rooted store file so tests never touch the real
~/.jarvis-v2/config/skill_autosurface.json.
"""
import pytest

from core.runtime import settings as settings_mod
from core.services import skill_autosurface as sa
from core.services import skill_engine


@pytest.fixture
def isolated_store(monkeypatch, tmp_path):
    """Point the allowlist store at a clean tmp file for each test."""
    store_path = tmp_path / "skill_autosurface.json"
    monkeypatch.setattr(sa, "_STORE_PATH", store_path)
    return store_path


@pytest.fixture
def flag_on(monkeypatch):
    defaults = settings_mod.RuntimeSettings(skill_autosurface_enabled=True)
    monkeypatch.setattr(settings_mod, "load_settings", lambda: defaults)
    return defaults


@pytest.fixture
def flag_off(monkeypatch):
    defaults = settings_mod.RuntimeSettings(skill_autosurface_enabled=False)
    monkeypatch.setattr(settings_mod, "load_settings", lambda: defaults)
    return defaults


def test_flag_defaults_off():
    assert settings_mod.load_settings().skill_autosurface_enabled is False


def test_empty_allowlist_by_default(isolated_store):
    assert sa.list_approved() == []


def test_approve_requires_owner(isolated_store, monkeypatch):
    monkeypatch.setattr(skill_engine, "skill_exists", lambda name: True)
    with pytest.raises(PermissionError):
        sa.approve_skill("tdd", role="user")
    assert sa.approve_skill("tdd", role="owner") is True
    assert sa.list_approved() == ["tdd"]


def test_approve_rejects_unknown_skill(isolated_store, monkeypatch):
    monkeypatch.setattr(skill_engine, "skill_exists", lambda name: False)
    assert sa.approve_skill("does-not-exist", role="owner") is False
    assert sa.list_approved() == []


def test_filter_allowlist_flag_off(isolated_store, monkeypatch, flag_off):
    monkeypatch.setattr(skill_engine, "skill_exists", lambda name: True)
    sa.approve_skill("tdd", role="owner")
    assert sa.filter_to_approved(["tdd", "brand"]) == []


def test_filter_allowlist_flag_on(isolated_store, monkeypatch, flag_on):
    monkeypatch.setattr(skill_engine, "skill_exists", lambda name: True)
    sa.approve_skill("tdd", role="owner")
    assert sa.filter_to_approved(["tdd", "brand"]) == ["tdd"]


def test_revoke(isolated_store, monkeypatch):
    monkeypatch.setattr(skill_engine, "skill_exists", lambda name: True)
    sa.approve_skill("tdd", role="owner")
    assert sa.list_approved() == ["tdd"]
    sa.revoke_skill("tdd", role="owner")
    assert sa.list_approved() == []
