from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

from core.services import prompt_assembly_turn_cache as cache


def test_hit_miss_expired_and_unsafe_key_are_distinct():
    cache.clear()
    assert cache.lookup(None, now=1).outcome == "unsafe_no_key"
    key = ("s", 7, "deepseek", "m", "default")
    assert cache.lookup(key, now=1).outcome == "miss"
    cache.store(key, "value", now=1)

    hit = cache.lookup(key, now=2)
    assert hit.outcome == "hit"
    assert hit.value == "value"
    assert hit.age_ms == 1000

    expired = cache.lookup(key, now=182)
    assert expired.outcome == "expired"
    assert expired.value is None
    assert expired.age_ms == 181_000


def test_pruning_preserves_the_existing_clear_then_store_policy():
    cache.clear()
    for i in range(66):
        cache.store(("s", i), i, now=float(i))

    assert cache.lookup(("s", 0), now=66).outcome == "miss"
    assert cache.lookup(("s", 65), now=66).value == 65


def test_concurrent_misses_are_measured_without_singleflight(monkeypatch):
    from core.services import prompt_contract

    cache.clear()
    barrier = threading.Barrier(2)
    builds: list[str] = []
    events: list[tuple[str, dict]] = []

    def slow_builder(**_kwargs):
        builds.append(threading.current_thread().name)
        barrier.wait(timeout=2)
        return object()

    monkeypatch.setattr(prompt_contract, "_latest_user_msg_id", lambda _sid: 77)
    monkeypatch.setattr(prompt_contract, "_build_visible_chat_prompt_assembly_impl", slow_builder)
    monkeypatch.setattr("core.services.central_xproc.process_role", lambda: "api")
    monkeypatch.setattr(
        "core.eventbus.bus.event_bus.publish",
        lambda kind, payload: events.append((kind, payload)),
    )

    def build():
        return prompt_contract.build_visible_chat_prompt_assembly(
            provider="deepseek",
            model="m",
            user_message="secret message",
            session_id="secret-session",
            caller_phase="post_tool",
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _n: build(), range(2)))

    cache_events = [payload for kind, payload in events if kind == "prompt.assembly_cache"]
    assert len(builds) == 2
    assert len(results) == 2
    assert [event["cache_outcome"] for event in cache_events] == ["miss", "miss"]
    assert len({event["key_hash"] for event in cache_events}) == 1
    assert {event["caller_phase"] for event in cache_events} == {"post_tool"}
    assert {event["process_role"] for event in cache_events} == {"api"}
    assert all(isinstance(event["pid"], int) for event in cache_events)
    assert all("secret" not in str(event) for event in cache_events)
