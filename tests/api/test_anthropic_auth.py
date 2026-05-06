"""Verify x-api-key resolution for Anthropic endpoint."""
import json
import pytest
from pathlib import Path

from apps.api.jarvis_api.middleware import anthropic_auth as ah


@pytest.fixture
def isolated_keys(tmp_path, monkeypatch):
    keys_path = tmp_path / "anthropic_api_keys.json"
    keys_path.write_text(json.dumps({
        "keys": {
            "jvs-bjorn-test-key": {"user": "bjorn", "workspace": "default"},
            "jvs-mikkel-test-key": {"user": "mikkel", "workspace": "mikkel"},
        }
    }))
    monkeypatch.setattr(ah, "_KEYS_PATH", keys_path)
    monkeypatch.setattr(ah, "_REPO_KEYS_PATH", keys_path)
    ah.invalidate_cache()
    return keys_path


def test_resolve_valid_key(isolated_keys):
    out = ah.resolve_api_key("jvs-bjorn-test-key")
    assert out == {"user": "bjorn", "workspace": "default"}


def test_resolve_invalid_key_returns_none(isolated_keys):
    assert ah.resolve_api_key("nonexistent") is None


def test_resolve_empty_key_returns_none(isolated_keys):
    assert ah.resolve_api_key("") is None
    assert ah.resolve_api_key(None) is None


def test_resolve_strips_whitespace(isolated_keys):
    out = ah.resolve_api_key("  jvs-bjorn-test-key  ")
    assert out is not None
    assert out["user"] == "bjorn"


def test_dev_mode_open_returns_default(monkeypatch, isolated_keys):
    out = ah.resolve_api_key("anything", dev_mode_open=True)
    assert out == {"user": "dev", "workspace": "default"}


def test_dev_mode_off_no_match(isolated_keys):
    assert ah.resolve_api_key("anything", dev_mode_open=False) is None
