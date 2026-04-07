"""Tests for body_memory.py"""

import pytest
from apps.api.jarvis_api.services.body_memory import (
    record_body_snapshot,
    describe_body_memory,
    format_body_for_prompt,
    reset_body_memory,
    build_body_memory_surface,
)


def setup_function():
    reset_body_memory()


def test_record_body_snapshot():
    record_body_snapshot("test_context", "varm", 0.5)
    surface = build_body_memory_surface()
    assert surface["snapshot_count"] == 1
    assert surface["active"] is True


def test_describe_body_memory():
    record_body_snapshot("test_context", "kold", 0.7)
    desc = describe_body_memory()
    assert "kold" in desc
    assert "test_context" in desc


def test_format_body_for_prompt():
    record_body_snapshot("test_context", "tryk", 0.6)
    result = format_body_for_prompt()
    assert "KROP:" in result


def test_build_body_memory_surface():
    record_body_snapshot("test_context", "prikken", 0.4)
    surface = build_body_memory_surface()
    assert surface["active"] is True
    assert surface["snapshot_count"] == 1
    assert surface["latest"] is not None


def test_reset_body_memory():
    record_body_snapshot("test_context", "varm", 0.5)
    reset_body_memory()
    surface = build_body_memory_surface()
    assert surface["snapshot_count"] == 0
    assert surface["active"] is False


def test_empty_body_memory():
    surface = build_body_memory_surface()
    assert surface["active"] is False
    assert surface["snapshot_count"] == 0
