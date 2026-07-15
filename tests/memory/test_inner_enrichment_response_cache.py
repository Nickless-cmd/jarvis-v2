"""FIX 2 tests — lossless prompt-hash response cache on the inner lane.

The `inner` lane hit only ~3% DeepSeek prefix cache. Prefix-sharing with the
visible lane is not viable (would balloon input tokens), so the lever is
call-count reduction. This cache skips the whole call when an identical
(system+user) prompt recurs within TTL — lossless by construction.

Covers:
  - identical prompt within TTL → cached, underlying call made only once
  - different prompt → not served from cache
  - flag off ('inner_enrichment_response_cache'=off) → no caching
"""
from __future__ import annotations

from unittest import mock

import core.memory.inner_llm_enrichment as ile


def _reset_cache():
    with ile._RESPONSE_CACHE_LOCK:
        ile._RESPONSE_CACHE.clear()


class TestResponseCache:
    def test_identical_prompt_hits_cache(self):
        _reset_cache()
        calls = {"n": 0}

        def fake_remote(**kw):
            calls["n"] += 1
            return "a reflection"

        with mock.patch.object(ile, "_response_cache_enabled", return_value=True), \
             mock.patch.object(
                 ile, "_resolve_enrichment_target",
                 return_value={"provider": "groq", "model": "m", "active": True},
             ), \
             mock.patch.object(ile, "_call_remote_chat", side_effect=fake_remote):
            r1 = ile._call_cheap_llm("sys", "user")
            r2 = ile._call_cheap_llm("sys", "user")

        assert r1 == "a reflection"
        assert r2 == "a reflection"
        assert calls["n"] == 1          # second call served from cache

    def test_different_prompt_misses_cache(self):
        _reset_cache()
        calls = {"n": 0}

        def fake_remote(**kw):
            calls["n"] += 1
            return f"reflection-{calls['n']}"

        with mock.patch.object(ile, "_response_cache_enabled", return_value=True), \
             mock.patch.object(
                 ile, "_resolve_enrichment_target",
                 return_value={"provider": "groq", "model": "m", "active": True},
             ), \
             mock.patch.object(ile, "_call_remote_chat", side_effect=fake_remote):
            ile._call_cheap_llm("sys", "user-A")
            ile._call_cheap_llm("sys", "user-B")

        assert calls["n"] == 2          # distinct prompts → two calls

    def test_flag_off_disables_cache(self):
        _reset_cache()
        calls = {"n": 0}

        def fake_remote(**kw):
            calls["n"] += 1
            return "a reflection"

        with mock.patch.object(ile, "_response_cache_enabled", return_value=False), \
             mock.patch.object(
                 ile, "_resolve_enrichment_target",
                 return_value={"provider": "groq", "model": "m", "active": True},
             ), \
             mock.patch.object(ile, "_call_remote_chat", side_effect=fake_remote):
            ile._call_cheap_llm("sys", "user")
            ile._call_cheap_llm("sys", "user")

        assert calls["n"] == 2          # no caching → two calls

    def test_cache_key_stable(self):
        k1 = ile._response_cache_key("s", "u")
        k2 = ile._response_cache_key("s", "u")
        k3 = ile._response_cache_key("s", "u2")
        assert k1 == k2
        assert k1 != k3
