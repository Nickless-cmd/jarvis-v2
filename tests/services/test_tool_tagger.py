import json
from pathlib import Path
import pytest

from core.services import tool_tagger


@pytest.fixture
def isolated_tags(tmp_path, monkeypatch):
    monkeypatch.setattr(tool_tagger, "_TAGS_PATH", tmp_path / "tool_tags.json")
    monkeypatch.setattr(tool_tagger, "_OVERRIDES_PATH", tmp_path / "tool_tags.overrides.json")
    monkeypatch.setattr(tool_tagger, "_PINNED_PATH", tmp_path / "tool_tags.pinned.json")
    monkeypatch.setattr(tool_tagger, "_REPO_OVERRIDES", tmp_path / "_repo_overrides.json")
    monkeypatch.setattr(tool_tagger, "_REPO_PINNED", tmp_path / "_repo_pinned.json")
    monkeypatch.setattr(tool_tagger, "_STATE_DIR", tmp_path)
    tool_tagger.invalidate_cache()
    return tmp_path


def test_get_tags_returns_empty_when_no_files(isolated_tags):
    assert tool_tagger.get_tags("read_file") == []


def test_overrides_win_over_auto(isolated_tags):
    (isolated_tags / "tool_tags.json").write_text(json.dumps({"tags": {"read_file": ["code"]}}))
    (isolated_tags / "tool_tags.overrides.json").write_text(
        json.dumps({"overrides": {"read_file": ["system", "code"]}})
    )
    tool_tagger.invalidate_cache()
    assert tool_tagger.get_tags("read_file") == ["system", "code"]


def test_pinned_set_loads(isolated_tags):
    (isolated_tags / "tool_tags.pinned.json").write_text(
        json.dumps({"pinned": ["read_file", "bash"]})
    )
    tool_tagger.invalidate_cache()
    pinned = tool_tagger.get_pinned_set()
    assert "read_file" in pinned
    assert "bash" in pinned


def test_unknown_tool_returns_empty(isolated_tags):
    (isolated_tags / "tool_tags.json").write_text(json.dumps({"tags": {"x": ["code"]}}))
    tool_tagger.invalidate_cache()
    assert tool_tagger.get_tags("nonexistent") == []


def test_bootstrap_filters_to_allowed_domains(isolated_tags, monkeypatch):
    fake_response = {"text": json.dumps({"tags": {
        "read_file": ["code", "system"],
        "bash": ["system", "INVALID_DOMAIN", "code"],
    }})}
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime.execute_cheap_lane_via_pool",
        lambda **kwargs: fake_response,
    )
    out = tool_tagger.bootstrap_tags()
    assert "INVALID_DOMAIN" not in out["bash"]
    assert "system" in out["bash"]
    assert "code" in out["read_file"]
