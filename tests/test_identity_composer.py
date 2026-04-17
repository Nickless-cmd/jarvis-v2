"""Tests for identity_composer — name lookup and preamble construction."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock


def _reset_cache():
    """Reset module-level name cache between tests."""
    import core.services.identity_composer as ic
    ic._name_cache = None


def test_get_entity_name_reads_identity_md(tmp_path):
    identity = tmp_path / "IDENTITY.md"
    identity.write_text("# IDENTITY\n\nName: TestEntity\nMode: test\n")
    _reset_cache()
    import core.services.identity_composer as ic
    with patch.object(ic, "_IDENTITY_FILE", identity):
        name = ic.get_entity_name()
    assert name == "TestEntity"


def test_get_entity_name_caches_result(tmp_path):
    identity = tmp_path / "IDENTITY.md"
    identity.write_text("Name: CachedName\n")
    _reset_cache()
    import core.services.identity_composer as ic
    with patch.object(ic, "_IDENTITY_FILE", identity):
        name1 = ic.get_entity_name()
        # Delete the file — second call must use cache
        identity.unlink()
        name2 = ic.get_entity_name()
    assert name1 == "CachedName"
    assert name2 == "CachedName"


def test_get_entity_name_fallback_on_missing_file(tmp_path):
    _reset_cache()
    import core.services.identity_composer as ic
    with patch.object(ic, "_IDENTITY_FILE", tmp_path / "NONEXISTENT.md"):
        name = ic.get_entity_name()
    assert name == "the entity"


def test_get_entity_name_fallback_when_name_line_absent(tmp_path):
    identity = tmp_path / "IDENTITY.md"
    identity.write_text("# IDENTITY\n\nMode: persistent\n")
    _reset_cache()
    import core.services.identity_composer as ic
    with patch.object(ic, "_IDENTITY_FILE", identity):
        name = ic.get_entity_name()
    assert name == "the entity"


def test_build_identity_preamble_contains_name(tmp_path):
    identity = tmp_path / "IDENTITY.md"
    identity.write_text("Name: Jarvis\n")
    _reset_cache()
    import core.services.identity_composer as ic
    with patch.object(ic, "_IDENTITY_FILE", identity):
        with patch("core.services.identity_composer._read_bearing", return_value="Analytisk"):
            with patch("core.services.identity_composer._read_energy", return_value="middel"):
                preamble = ic.build_identity_preamble()
    assert "Jarvis" in preamble
    assert "Analytisk" in preamble
    assert "middel" in preamble


def test_build_identity_preamble_works_without_signals(tmp_path):
    identity = tmp_path / "IDENTITY.md"
    identity.write_text("Name: Jarvis\n")
    _reset_cache()
    import core.services.identity_composer as ic
    with patch.object(ic, "_IDENTITY_FILE", identity):
        with patch("core.services.identity_composer._read_bearing", return_value=""):
            with patch("core.services.identity_composer._read_energy", return_value=""):
                preamble = ic.build_identity_preamble()
    assert preamble == "Jarvis."
