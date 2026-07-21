"""Tests for core.services.session_prewarm — prewarm-on-return DeepSeek cache warming.

Guards the invariants that keep warming SAFE:
  - no session / non-deepseek / disabled → skip (no API call)
  - throttle: a second warm within the cooldown is skipped
  - a successful warm records cache-hit/miss stats without persisting anything
The deepseek POST + message builder are monkeypatched so no network/DB is touched.
"""
from __future__ import annotations

import core.services.session_prewarm as sp


def _reset_throttle():
    with sp._last_warm_lock:
        sp._last_warm.clear()


def test_skip_when_no_session(monkeypatch):
    monkeypatch.setattr(sp, "_deepseek_key", lambda: "k", raising=True)
    r = sp.warm_session_prefix("", force=True)
    assert r["status"] == "skipped" and r["reason"] == "no-session"


def test_skip_when_not_deepseek(monkeypatch):
    _reset_throttle()
    r = sp.warm_session_prefix("chat-x", provider="ollama", force=True)
    assert r["status"] == "skipped" and r["reason"] == "provider-not-deepseek"


def test_skip_when_disabled(monkeypatch):
    _reset_throttle()
    monkeypatch.setattr(sp, "session_prewarm_enabled", lambda: False, raising=True)
    r = sp.warm_session_prefix("chat-x", force=True)
    assert r["status"] == "skipped" and r["reason"] == "disabled"


def test_throttle_second_call_within_cooldown(monkeypatch):
    _reset_throttle()
    monkeypatch.setattr(sp, "session_prewarm_enabled", lambda: True, raising=True)
    # first (non-forced) call passes the throttle and stamps it
    assert sp._should_warm("chat-throttle") is True
    # second within cooldown is throttled
    assert sp._should_warm("chat-throttle") is False


def test_successful_warm_records_stats(monkeypatch):
    _reset_throttle()
    monkeypatch.setattr(sp, "session_prewarm_enabled", lambda: True, raising=True)
    monkeypatch.setattr(sp, "_deepseek_key", lambda: "key", raising=True)

    # message builder → deterministic messages (no assembly/DB)
    import core.services.visible_model as vm
    monkeypatch.setattr(
        vm, "_build_visible_chat_messages_for_github",
        lambda *a, **k: [{"role": "system", "content": "sys"}, {"role": "user", "content": "(prewarm)"}],
        raising=True,
    )
    # deepseek POST → fake usage with cache split
    monkeypatch.setattr(
        sp, "_post_deepseek",
        lambda *a, **k: {"usage": {"prompt_cache_hit_tokens": 900,
                                   "prompt_cache_miss_tokens": 100,
                                   "prompt_tokens": 1000, "completion_tokens": 1}},
        raising=True,
    )
    recorded: dict = {}
    import core.costing.ledger as ledger
    monkeypatch.setattr(ledger, "record_cost", lambda **kw: recorded.update(kw), raising=True)

    r = sp.warm_session_prefix("chat-ok", user_id="u1", force=True)
    assert r["status"] == "ok"
    assert r["cache_hit_tokens"] == 900 and r["cache_miss_tokens"] == 100
    # cost is recorded under the dedicated warmer label — never as real traffic
    assert recorded.get("provider") == "session_cache_warmer"
    assert recorded.get("cache_hit_tokens") == 900


def test_warm_never_raises_on_builder_error(monkeypatch):
    _reset_throttle()
    monkeypatch.setattr(sp, "session_prewarm_enabled", lambda: True, raising=True)
    monkeypatch.setattr(sp, "_deepseek_key", lambda: "key", raising=True)
    import core.services.visible_model as vm

    def _boom(*a, **k):
        raise RuntimeError("build failed")

    monkeypatch.setattr(vm, "_build_visible_chat_messages_for_github", _boom, raising=True)
    r = sp.warm_session_prefix("chat-err", force=True)
    assert r["status"] == "error"  # self-safe: returned, not raised
