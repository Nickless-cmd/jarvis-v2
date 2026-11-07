"""Surface-test (dark-edges batch 1) — se tests/test_tool_infra_surfaces.py for moensteret."""
from __future__ import annotations

import json
import sqlite3

import pytest


def _ok(s, mode):
    assert s["mode"] == mode
    assert isinstance(s["signals"], dict)
    assert isinstance(s["summary"], str) and s["summary"]
    return s


def _inactive(s, mode, why):
    _ok(s, mode)
    assert s["active"] is False
    assert why in s["reason"], s["reason"]
    return s



# ── 4. tool_tagger ───────────────────────────────────────────────────────────

def test_tool_tagger_surface(monkeypatch, tmp_path):
    import core.services.tool_tagger as t
    monkeypatch.setattr(t, "_TAGS_PATH", tmp_path / "tags.json")
    monkeypatch.setattr(t, "_OVERRIDES_PATH", tmp_path / "ov.json")
    monkeypatch.setattr(t, "_PINNED_PATH", tmp_path / "pin.json")
    monkeypatch.setattr(t, "_REPO_OVERRIDES", tmp_path / "nope1.json")
    monkeypatch.setattr(t, "_REPO_PINNED", tmp_path / "nope2.json")
    _inactive(t.build_tool_tagger_surface(), "tool-tagger", "hverken tags")
    (tmp_path / "tags.json").write_text(json.dumps({"tags": {"a": ["code"], "b": ["code", "web"]}}))
    (tmp_path / "ov.json").write_text(json.dumps({"overrides": {"b": ["memory"], "c": ["system"]}}))
    (tmp_path / "pin.json").write_text(json.dumps({"pinned": ["a"]}))
    s = _ok(t.build_tool_tagger_surface(), "tool-tagger")
    assert s["active"] is True
    assert s["signals"] == {"auto_tagged": 2, "overrides": 2, "tagged_total": 3, "pinned": 1,
                            "domains": {"code": 2, "web": 1}, "cache_loaded": s["signals"]["cache_loaded"]}
    (tmp_path / "pin.json").write_text(json.dumps({"pinned": ["a", "b", "c"]}))
    assert t.build_tool_tagger_surface()["signals"]["pinned"] == 3  # frisk, ikke proces-cache
    (tmp_path / "tags.json").write_text("{ikke json")
    _inactive(t.build_tool_tagger_surface(), "tool-tagger", "tags.json")
