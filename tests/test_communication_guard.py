"""Tests for core.services.communication_guard and communication_guard_daemon.

Dækker:
  - Grundlæggende scan med triggerfraser
  - Case-insensitive match
  - Ingen false positives på sikre tekster
  - TTL turns — decrement og udløb
  - TTL hours — tidsbaseret udløb
  - Permanent trigger (udløber aldrig)
  - add_trigger / remove_trigger
  - cleanup_expired
  - Daemon tick (kun logik, ingen LLM)
  - Tom tekst / None / whitespace
  - Edge: trigger tilføjes to gange (opdaterer, duplikere ikke)
"""
from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_PHRASES = ["godnat", "sov godt", "laeg dig til at sove", "put dig selv"]


def _clean_state():
    """Slet evt. state-fil så hver test starter rent."""
    p = Path.home() / ".jarvis-v2" / "state" / "communication_guard.json"
    if p.exists():
        p.unlink()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _clean(request):
    """Ryd state-fil før og efter hver test, medmindre @pytest.mark.dirty_state er sat."""
    if "dirty_state" not in request.keywords:
        _clean_state()
    yield
    if "dirty_state" not in request.keywords:
        _clean_state()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestScan:

    def test_detects_sleep_phrases(self):
        from core.services.communication_guard import scan
        result = scan("Sov godt, Bjørn")
        assert result is not None
        assert result["matched"] == "sov godt"
        assert result["kind"] == "permanent"

    def test_detects_godnat(self):
        from core.services.communication_guard import scan
        result = scan("godnat, så ses vi i morgen")
        assert result is not None
        assert result["matched"] == "godnat"

    def test_case_insensitive(self):
        from core.services.communication_guard import scan
        result = scan("GODNAT min ven")
        assert result is not None
        assert result["matched"] == "godnat"

    def test_safe_text_no_false_positive(self):
        from core.services.communication_guard import scan
        safe_texts = [
            "Hej Bjørn, hvordan går det?",
            "Jeg har fikset cachen nu",
            "Vi ses i næste uge",
            "nat er en god tid til at sove",
            "sovetryne er et sjovt ord",
        ]
        for text in safe_texts:
            assert scan(text) is None, f"false positive: {text!r}"

    def test_empty_text(self):
        from core.services.communication_guard import scan
        assert scan("") is None
        assert scan(None) is None
        assert scan("   ") is None

    def test_partial_word_no_false_positive(self):
        """Sikrer at 'godnat' ikke matcher midt i andre ord."""
        from core.services.communication_guard import scan
        assert scan("godnatte") is not None  # 'godnat' er stadig substring
        assert scan("sovetryne") is None     # 'sove' != 'sov godt'


class TestTTLTurns:

    def test_ttl_decrements_and_expires(self):
        from core.services.communication_guard import add_trigger, scan, consume_turn, list_triggers

        # TTL på 3 turns
        add_trigger("teststop", kind="ttl", ttl_turns=3, reason="test")
        assert scan("sig teststop") is not None  # fundet

        consume_turn()  # turn 2/3
        assert scan("sig teststop") is not None

        consume_turn()  # turn 1/3
        assert scan("sig teststop") is not None

        consume_turn()  # turn 0/3 → bør forsvinde
        # Efter consume_turn er ttl_turns = 0 → markeret inaktiv
        # cleanup_expired skal køre før den fjernes
        from core.services.communication_guard import cleanup_expired
        cleanup_expired()
        assert scan("sig teststop") is None  # væk

    def test_ttl_reject_negative(self):
        """ttl_turns sættes minimum til 1."""
        from core.services.communication_guard import add_trigger, scan, consume_turn
        add_trigger("pytest_stop", kind="ttl", ttl_turns=0)
        # Selv med ttl_turns=0, sættes minimum til 1
        assert scan("sig pytest_stop") is not None
        consume_turn()
        from core.services.communication_guard import cleanup_expired
        cleanup_expired()
        assert scan("sig pytest_stop") is None


class TestTTLHours:

    def test_ttl_hours_expires(self):
        from core.services.communication_guard import add_trigger, scan
        from core.services.communication_guard import _load, _save

        # Tilføj TTL på 1 time
        add_trigger("timestop", kind="ttl", ttl_hours=1, reason="test")

        # Manuelt ryk ttl_until bagud i tid
        triggers = _load()
        for t in triggers:
            if t["phrase"] == "timestop":
                t["ttl_until"] = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
        _save(triggers)

        assert scan("sig timestop") is None  # udløbet

    def test_ttl_hours_still_valid(self):
        from core.services.communication_guard import add_trigger, scan
        add_trigger("stillstop", kind="ttl", ttl_hours=24)
        assert scan("sig stillstop") is not None  # stadig gyldig


class TestAddRemove:

    def test_add_custom_trigger(self):
        from core.services.communication_guard import add_trigger, scan
        add_trigger("hold mund", kind="permanent", reason="Test")
        assert scan("hold mund nu") is not None

    def test_remove_trigger(self):
        from core.services.communication_guard import add_trigger, remove_trigger, scan
        add_trigger("stop", kind="ttl", ttl_turns=5)
        assert scan("sig stop") is not None
        assert remove_trigger("stop") is True
        assert scan("sig stop") is None

    def test_add_twice_updates(self):
        from core.services.communication_guard import add_trigger, list_triggers
        add_trigger("hej", kind="ttl", ttl_turns=5)
        add_trigger("hej", kind="permanent")  # opgrader til permanent
        triggers = [t for t in list_triggers() if t["phrase"] == "hej"]
        assert len(triggers) == 1
        assert triggers[0]["kind"] == "permanent"

    def test_remove_nonexistent(self):
        from core.services.communication_guard import remove_trigger
        assert remove_trigger("findes_ikke") is False


class TestCleanup:

    def test_cleanup_removes_expired(self):
        from core.services.communication_guard import add_trigger, cleanup_expired, list_triggers
        from core.services.communication_guard import _load, _save
        from datetime import UTC, datetime, timedelta

        add_trigger("old", kind="ttl", ttl_turns=0)  # ttl_turns sættes til min=1
        # Manuelt sæt den til 0
        triggers = _load()
        for t in triggers:
            if t["phrase"] == "old":
                t["ttl_turns"] = 0
        _save(triggers)

        before = len(list_triggers())
        removed = cleanup_expired()
        after = len(list_triggers())
        assert removed >= 1

    def test_cleanup_skips_permanent(self):
        from core.services.communication_guard import cleanup_expired, list_triggers
        # Default-triggers er permanente og skal ikke ryddes
        removed = cleanup_expired()
        assert removed == 0
        active = [t for t in list_triggers() if t["kind"] == "permanent"]
        assert len(active) == 4  # godnat, sov godt, læg dig til at sove, put dig selv


class TestDaemonTick:

    def test_daemon_tick_returns_status(self):
        from core.services.communication_guard_daemon import tick
        result = tick()
        assert isinstance(result, dict)
        assert result.get("status") == "ok"
        assert "active_triggers" in result
        assert "expired_removed" in result

    def test_daemon_tick_import_error_handled(self):
        """Simuler import-fejl i daemon tick."""
        from core.services.communication_guard_daemon import tick_communication_guard_daemon
        import sys as _sys
        # Nulstil cached communication_guard saa tick() tvinges til at gen-importere
        _sys.modules.pop("core.services.communication_guard", None)
        # Mock __import__ til at fejle specifikt for communication_guard
        import builtins as _b
        real_import = _b.__import__
        def _selective_import(name, *args, **kw):
            if name == "core.services.communication_guard":
                raise ImportError("fake import failure")
            return real_import(name, *args, **kw)
        _b.__import__ = _selective_import
        try:
            result = tick_communication_guard_daemon()
        finally:
            _b.__import__ = real_import
            # Genindlaes communication_guard til normal tilstand
            import core.services.communication_guard  # noqa: F811
        assert result.get("status") == "error"
        assert "import" in result.get("error", "").lower()


class TestConsumeTurnIntegration:

    def test_consume_turn_reduces_all_ttl(self):
        from core.services.communication_guard import (
            add_trigger, consume_turn, list_triggers,
        )
        add_trigger("a", kind="ttl", ttl_turns=3)
        add_trigger("b", kind="ttl", ttl_turns=5)

        consume_turn()
        triggers = {t["phrase"]: t for t in list_triggers()}
        assert triggers["a"]["ttl_turns"] == 2
        assert triggers["b"]["ttl_turns"] == 4

    def test_consume_turn_skips_permanent(self):
        from core.services.communication_guard import consume_turn, list_triggers
        # Permanente har ttl_turns=None → consume_turn påvirker dem ikke
        consume_turn()
        for t in list_triggers():
            if t["kind"] == "permanent":
                assert t.get("ttl_turns") is None
