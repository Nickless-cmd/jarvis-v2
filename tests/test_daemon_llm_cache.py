"""Tests for daemon LLM response cache."""
from __future__ import annotations

import time

import pytest


class TestResponseCacheHit:
    def test_second_call_returns_cached(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import core.services.daemon_llm as mod

        mod._response_cache.clear()
        call_count = 0

        def fake_cheap_lane(message: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"text": "LLM result", "provider": "groq"}

        monkeypatch.setattr(
            "core.services.non_visible_lane_execution.execute_cheap_lane",
            fake_cheap_lane,
        )

        result1 = mod.daemon_llm_call("test prompt", daemon_name="somatic")
        result2 = mod.daemon_llm_call("test prompt", daemon_name="somatic")

        assert result1 == result2
        assert call_count == 1  # only one LLM call

    def test_different_prompt_is_cache_miss(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import core.services.daemon_llm as mod

        mod._response_cache.clear()
        call_count = 0

        def fake_cheap_lane(message: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"text": f"Result {call_count}", "provider": "groq"}

        monkeypatch.setattr(
            "core.services.non_visible_lane_execution.execute_cheap_lane",
            fake_cheap_lane,
        )

        result1 = mod.daemon_llm_call("prompt A", daemon_name="somatic")
        result2 = mod.daemon_llm_call("prompt B", daemon_name="somatic")

        assert result1 != result2
        assert call_count == 2


class TestResponseCacheTTL:
    def test_expired_entry_is_cache_miss(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import core.services.daemon_llm as mod

        mod._response_cache.clear()
        call_count = 0

        def fake_cheap_lane(message: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"text": f"Result {call_count}", "provider": "groq"}

        monkeypatch.setattr(
            "core.services.non_visible_lane_execution.execute_cheap_lane",
            fake_cheap_lane,
        )

        # First call
        mod.daemon_llm_call("test prompt", daemon_name="somatic")

        # Expire the entry manually
        for key in mod._response_cache:
            text, _ = mod._response_cache[key]
            mod._response_cache[key] = (text, time.time() - 1)

        # Second call should be a miss
        mod.daemon_llm_call("test prompt", daemon_name="somatic")
        assert call_count == 2

    def test_ttl_varies_by_daemon_name(self) -> None:
        from core.services.daemon_llm import _get_cache_ttl

        assert _get_cache_ttl("somatic") == 90
        assert _get_cache_ttl("thought_stream") == 90
        assert _get_cache_ttl("curiosity") == 180
        assert _get_cache_ttl("meta_reflection") == 600
        assert _get_cache_ttl("session_summary") == 0
        assert _get_cache_ttl("unknown_daemon") == 120


class TestResponseCacheRules:
    def test_empty_response_not_cached(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import core.services.daemon_llm as mod

        mod._response_cache.clear()

        def fake_cheap_lane(message: str) -> dict:
            return {"text": "", "provider": "groq"}

        def fake_heartbeat_model(**kwargs: object) -> dict:
            return {"text": ""}

        monkeypatch.setattr(
            "core.services.non_visible_lane_execution.execute_cheap_lane",
            fake_cheap_lane,
        )
        monkeypatch.setattr(
            "core.services.heartbeat_runtime._execute_heartbeat_model",
            fake_heartbeat_model,
        )

        mod.daemon_llm_call("test", fallback="fallback text", daemon_name="somatic")
        assert len(mod._response_cache) == 0

    def test_no_cache_when_daemon_name_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import core.services.daemon_llm as mod

        mod._response_cache.clear()

        def fake_cheap_lane(message: str) -> dict:
            return {"text": "Result", "provider": "groq"}

        monkeypatch.setattr(
            "core.services.non_visible_lane_execution.execute_cheap_lane",
            fake_cheap_lane,
        )

        mod.daemon_llm_call("test", daemon_name="")
        assert len(mod._response_cache) == 0

    def test_no_cache_for_session_summary(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import core.services.daemon_llm as mod

        mod._response_cache.clear()

        def fake_cheap_lane(message: str) -> dict:
            return {"text": "Summary text", "provider": "groq"}

        monkeypatch.setattr(
            "core.services.non_visible_lane_execution.execute_cheap_lane",
            fake_cheap_lane,
        )

        mod.daemon_llm_call("test", daemon_name="session_summary")
        assert len(mod._response_cache) == 0


class TestCacheHitLogging:
    def test_cache_hit_logs_with_provider_cache(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import core.services.daemon_llm as mod

        mod._response_cache.clear()
        logged: list[dict] = []

        def fake_cheap_lane(message: str) -> dict:
            return {"text": "Result", "provider": "groq"}

        def fake_log(**kwargs: object) -> None:
            logged.append(dict(kwargs))

        monkeypatch.setattr(
            "core.services.non_visible_lane_execution.execute_cheap_lane",
            fake_cheap_lane,
        )
        monkeypatch.setattr(
            "core.runtime.db.daemon_output_log_insert",
            fake_log,
        )

        mod.daemon_llm_call("test", daemon_name="somatic")
        mod.daemon_llm_call("test", daemon_name="somatic")  # cache hit

        cache_logs = [l for l in logged if l.get("provider") == "cache"]
        assert len(cache_logs) == 1
        assert cache_logs[0]["daemon_name"] == "somatic"
        assert cache_logs[0]["success"] is True
