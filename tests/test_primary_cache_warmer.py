"""Tests for scripts/primary_cache_warmer.py — primary lane cache warmer."""
from __future__ import annotations

import io
import json
import os
import sqlite3
import time
from pathlib import Path
from unittest import mock

import pytest
import urllib.error as urllib_error
import urllib.request as urllib_request


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _fake_home(monkeypatch, tmp_path):
    """Redirect ~/.jarvis-v2 to a temp dir so tests don't touch real state."""
    fake = tmp_path / ".jarvis-v2"
    fake.mkdir()
    monkeypatch.setattr("scripts.primary_cache_warmer.HOME_DIR", fake)
    monkeypatch.setattr("scripts.primary_cache_warmer.DB_PATH", fake / "state" / "jarvis.db")
    monkeypatch.setattr("scripts.primary_cache_warmer.LOG_PATH", fake / "logs" / "cache_warmer.jsonl")
    monkeypatch.setattr(
        "scripts.primary_cache_warmer.LAST_RUN_PATH",
        fake / "state" / "cache_warmer_last_run.txt",
    )
    monkeypatch.setattr("scripts.primary_cache_warmer.PROMPT_FILE", fake / "config" / "primary_system_prompt.txt")
    return fake


@pytest.fixture(autouse=True)
def _fake_env(monkeypatch):
    """Set fake API key so tests don't need real credentials."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-fake-key-12345")


@pytest.fixture(autouse=True)
def _patch_urllib(monkeypatch):
    """Mock urllib.request.urlopen to avoid real HTTP calls.

    Returns a helper so individual tests can set response data.
    """

    class FakeResponse:
        def __init__(self, data, status=200):
            self.data = data.encode("utf-8") if isinstance(data, str) else data
            self.status = status

        def read(self):
            return self.data

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class FakeUrlOpener:
        _responses: dict[str, tuple] = {}

        @classmethod
        def set_response(cls, response_data: str, status: int = 200):
            cls._responses["default"] = (response_data, status)

        @classmethod
        def set_error(cls, error_cls, error_args):
            cls._responses["default"] = ("error", error_cls, error_args)

    def _fake_urlopen(req, *args, **kwargs):
        entry = FakeUrlOpener._responses.get("default", ("{}", 200))
        if entry[0] == "error":
            _, error_cls, error_args = entry
            raise error_cls(*error_args)
        data, status = entry
        if status >= 400:
            raise urllib_error.HTTPError(
                url=req.full_url if hasattr(req, "full_url") else "",
                code=status,
                msg="Error",
                hdrs={},
                fp=io.BytesIO(data.encode("utf-8")),
            )
        return FakeResponse(data, status)

    monkeypatch.setattr("scripts.primary_cache_warmer.urllib_request.urlopen", _fake_urlopen)
    monkeypatch.setattr("scripts.primary_cache_warmer.urllib_error", urllib_error)

    return FakeUrlOpener


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_system_prompt() -> str:
    """A realistic-ish system prompt for testing."""
    return "Du er Jarvis. Du kører på deepseek-v4-flash. " * 200  # ~6K tokens


def _make_usage_overrides(
    cache_hit: int = 0,
    cache_miss: int = 80000,
    input_tokens: int = 80000,
    output_tokens: int = 10,
) -> dict:
    """Build a usage dict to merge into the API response."""
    return {
        "prompt_cache_hit_tokens": cache_hit,
        "prompt_cache_miss_tokens": cache_miss,
        "prompt_tokens": input_tokens,
        "completion_tokens": output_tokens,
    }


def _make_api_response(
    overrides: dict | None = None,
) -> str:
    """Build a realistic DeepSeek API response JSON string."""
    usage = {
        "prompt_tokens": 80000,
        "completion_tokens": 10,
        "prompt_cache_hit_tokens": 0,
        "prompt_cache_miss_tokens": 80000,
    }
    if overrides:
        usage.update(overrides)
    body = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "deepseek-chat",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "pong",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": usage,
    }
    return json.dumps(body)


def _create_db(fake_home: Path) -> None:
    """Create a minimal jarvis.db with the costs table."""
    db_path = fake_home / "state" / "jarvis.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.execute("""
        CREATE TABLE IF NOT EXISTS costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lane TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cost_usd REAL NOT NULL DEFAULT 0,
            cache_hit_tokens INTEGER NOT NULL DEFAULT 0,
            cache_miss_tokens INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()


def _write_prompt_file(fake_home: Path, content: str | None = None) -> Path:
    """Write the system prompt file so fallback works."""
    prompt_file = fake_home / "config" / "primary_system_prompt.txt"
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text(content or _sample_system_prompt(), encoding="utf-8")
    return prompt_file


# ---------------------------------------------------------------------------
# Tests — warm_primary_cache()
# ---------------------------------------------------------------------------


class TestWarmPrimaryCache:
    """Tests for warm_primary_cache() — the core function."""

    def test_happy_path_full_hit(self, _fake_home, _fake_env, _patch_urllib):
        """Normal successful call with 100% cache hit — DB + last_run."""
        _create_db(_fake_home)
        _write_prompt_file(_fake_home)
        TEST_PROMPT = "Du er Jarvis. Test prompt."

        from scripts.primary_cache_warmer import warm_primary_cache

        _patch_urllib.set_response(
            _make_api_response(_make_usage_overrides(cache_hit=80000, cache_miss=0))
        )

        result = warm_primary_cache(system_prompt=TEST_PROMPT)
        assert result["status"] == "ok"
        assert result["cache_hit_tokens"] == 80000
        assert result["cache_miss_tokens"] == 0
        assert result["hit_rate_pct"] == 100.0

        # Verify DB row
        con = sqlite3.connect(str(_fake_home / "state" / "jarvis.db"))
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM costs ORDER BY id DESC LIMIT 1").fetchone()
        assert int(row["cache_hit_tokens"]) == 80000
        assert int(row["cache_miss_tokens"]) == 0
        assert row["provider"] == "primary_cache_warmer"

        # Verify last_run file
        last_run = _fake_home / "state" / "cache_warmer_last_run.txt"
        assert last_run.exists()
        t = float(last_run.read_text(encoding="utf-8").strip())
        assert 0 < time.time() - t < 5  # skrevet for nylig

    def test_partial_hit(self, _fake_home, _fake_env, _patch_urllib):
        """Partial cache hit — 40K hit / 40K miss (50%)."""
        _create_db(_fake_home)
        _write_prompt_file(_fake_home)
        TEST_PROMPT = "Du er Jarvis. Test prompt."

        from scripts.primary_cache_warmer import warm_primary_cache

        _patch_urllib.set_response(
            _make_api_response(_make_usage_overrides(cache_hit=40000, cache_miss=40000))
        )

        result = warm_primary_cache(system_prompt=TEST_PROMPT)
        assert result["status"] == "ok"
        assert result["hit_rate_pct"] == 50.0

    def test_complete_miss(self, _fake_home, _fake_env, _patch_urllib):
        """Zero cache hit — 0% hit rate."""
        _create_db(_fake_home)
        _write_prompt_file(_fake_home)
        TEST_PROMPT = "Du er Jarvis. Test prompt."

        from scripts.primary_cache_warmer import warm_primary_cache

        _patch_urllib.set_response(
            _make_api_response(_make_usage_overrides(cache_hit=0, cache_miss=80000))
        )

        result = warm_primary_cache(system_prompt=TEST_PROMPT)
        assert result["status"] == "ok"
        assert result["cache_hit_tokens"] == 0
        assert result["hit_rate_pct"] == 0.0

    def test_rate_limit_429(self, _fake_home, _fake_env, _patch_urllib):
        """HTTP 429 → status='skipped', no crash."""
        _create_db(_fake_home)
        _write_prompt_file(_fake_home)
        TEST_PROMPT = "Du er Jarvis. Test prompt."

        from scripts.primary_cache_warmer import warm_primary_cache

        _patch_urllib.set_response("Rate limited", status=429)

        result = warm_primary_cache(system_prompt=TEST_PROMPT)
        assert result["status"] == "skipped"
        assert "rate limit" in result.get("reason", "").lower()

    def test_server_error_503(self, _fake_home, _fake_env, _patch_urllib):
        """HTTP 503 → status='skipped'."""
        _create_db(_fake_home)
        _write_prompt_file(_fake_home)
        TEST_PROMPT = "Du er Jarvis. Test prompt."

        from scripts.primary_cache_warmer import warm_primary_cache

        _patch_urllib.set_response("Service unavailable", status=503)

        result = warm_primary_cache(system_prompt=TEST_PROMPT)
        assert result["status"] == "skipped"

    def test_network_timeout(self, _fake_home, _fake_env, _patch_urllib):
        """Connection timeout → status='skipped'."""
        _create_db(_fake_home)
        _write_prompt_file(_fake_home)
        TEST_PROMPT = "Du er Jarvis. Test prompt."

        from scripts.primary_cache_warmer import warm_primary_cache

        _patch_urllib.set_error(TimeoutError, ("timed out",))

        result = warm_primary_cache(system_prompt=TEST_PROMPT)
        assert result["status"] == "skipped"

    def test_missing_api_key(self, _fake_home, _fake_env, monkeypatch):
        """No DEEPSEEK_API_KEY → status='error', reason mentions API key."""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        _create_db(_fake_home)
        _write_prompt_file(_fake_home)
        TEST_PROMPT = "Du er Jarvis. Test prompt."

        from scripts.primary_cache_warmer import warm_primary_cache

        result = warm_primary_cache(system_prompt=TEST_PROMPT)
        assert result["status"] == "error"
        assert "api key" in result.get("reason", "").lower()

    def test_dedup_skip(self, _fake_home, _fake_env, _patch_urllib):
        """Second call within dedup window returns 'dedup_skip'."""
        _create_db(_fake_home)
        _write_prompt_file(_fake_home)
        TEST_PROMPT = "Du er Jarvis. Test prompt."

        from scripts.primary_cache_warmer import warm_primary_cache

        _patch_urllib.set_response(
            _make_api_response(_make_usage_overrides(cache_hit=80000, cache_miss=0))
        )

        first = warm_primary_cache(system_prompt=TEST_PROMPT)
        assert first["status"] == "ok"

        second = warm_primary_cache(system_prompt=TEST_PROMPT)
        assert second["status"] == "dedup_skip"
        assert "too soon" in second.get("reason", "").lower()

    def test_no_system_prompt(self, _fake_home, _fake_env):
        """Empty system prompt → status='error'."""
        from scripts.primary_cache_warmer import warm_primary_cache

        result = warm_primary_cache(system_prompt="")
        assert result["status"] == "error"
        assert "system prompt" in result.get("reason", "").lower()


# ---------------------------------------------------------------------------
# Tests — main() CLI entry point
# ---------------------------------------------------------------------------


class TestMainEntryPoint:
    """Tests for main() — CLI entry point with log file."""

    @pytest.fixture(autouse=True)
    def _mock_prompt(self, monkeypatch):
        """Mock _fetch_system_prompt so main() doesn't try to import core (12s delay)."""
        monkeypatch.setattr(
            "scripts.primary_cache_warmer._fetch_system_prompt",
            # **kwargs: warmeren er multi-user → kalder med workspace_name=...
            lambda *a, **kw: "Du er Jarvis. Dette er en test prompt til cache warmer.",
        )

    def test_main_ok(self, _fake_home, _fake_env, _patch_urllib):
        """main() returns exit code 0 on success + writes log."""
        _create_db(_fake_home)
        from scripts.primary_cache_warmer import main

        _patch_urllib.set_response(
            _make_api_response(_make_usage_overrides(cache_hit=80000, cache_miss=0))
        )

        exit_code = main()
        assert exit_code == 0

        # Log file skrevet
        log_path = _fake_home / "logs" / "cache_warmer.jsonl"
        assert log_path.exists()
        entry = json.loads(log_path.read_text().strip().split("\n")[-1])
        assert entry["status"] == "ok"

    def test_main_dry_run(self, _fake_home, _fake_env):
        """main() with --dry-run returns 0 and logs dry_run status."""
        from scripts.primary_cache_warmer import main

        exit_code = main(["--dry-run"])
        assert exit_code == 0

        log_path = _fake_home / "logs" / "cache_warmer.jsonl"
        assert log_path.exists()
        entry = json.loads(log_path.read_text().strip().split("\n")[-1])
        assert entry["status"] == "dry_run"

    def test_main_error_missing_key(self, _fake_home, _fake_env, monkeypatch):
        """main() returns exit code 1 when API key is missing."""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        from scripts.primary_cache_warmer import main

        exit_code = main()
        assert exit_code == 1


def test_fetch_warmer_tools_are_normalized_with_type(monkeypatch):
    """REGRESSION (2026-06-30): warmeren sendte RÅ tools (uden {"type":"function"}
    wrapper) → DeepSeek 400'ede ("tools[N]: missing field `type`") og warming
    stoppede HELT (død siden 09:10). Den SKAL normalisere som live-lanen, både for
    at undgå 400 OG for byte-identisk cache-match."""
    import scripts.primary_cache_warmer as w
    # Rå (u-normaliserede) tool-defs som select_tools_for_visible kan returnere.
    raw = [{"name": "t1", "description": "d", "parameters": {}},
           {"function": {"name": "t2"}}]  # mangler 'type'
    monkeypatch.setattr(w, "_fetch_warmer_tools", w._fetch_warmer_tools)  # ensure real
    import core.tools.simple_tools as st
    import core.tools.copilot_tool_pruning as ctp
    monkeypatch.setattr(st, "get_tool_definitions", lambda: raw)
    monkeypatch.setattr(ctp, "select_tools_for_visible",
                        lambda tools, **kw: list(tools))
    out = w._fetch_warmer_tools()
    assert out, "warmer tools tomt"
    # ALLE tools skal nu have 'type' (ellers 400 på DeepSeek).
    assert all("type" in t for t in out), f"u-normaliseret: {[t for t in out if 'type' not in t]}"
    assert all(t.get("type") == "function" for t in out)
