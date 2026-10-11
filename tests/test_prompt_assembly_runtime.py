from __future__ import annotations

from core.services import prompt_assembly_runtime as runtime
from core.services import prompt_assembly_turn_cache as cache


def test_db_fejl_deaktiverer_cachen_i_stedet_for_at_servere_stale(monkeypatch):
    monkeypatch.setattr(
        runtime, "_query_latest_user_msg_id",
        lambda _sid: (_ for _ in ()).throw(RuntimeError("db unavailable")),
    )
    assert runtime.latest_user_msg_id("s1") == 0


def test_samme_besked_id_genbruger_assembly_til_post_tool(monkeypatch):
    cache.clear()
    builds: list[str] = []
    events: list[dict] = []
    monkeypatch.setattr(
        "core.services.prompt_assembly_telemetri.rapporter_cache_lookup",
        lambda **kwargs: events.append(kwargs),
    )

    def builder(**kwargs):
        builds.append(kwargs["user_message"])
        return object()

    common = dict(
        builder=builder,
        latest_message_id=7,
        provider="deepseek",
        model="deepseek-flash",
        user_message="hej",
        session_id="s1",
        name="default",
        runtime_self_report_context=None,
    )
    first = runtime.build_with_turn_cache(**common, caller_phase="initial")
    second = runtime.build_with_turn_cache(**common, caller_phase="post_tool")

    assert first is second
    assert builds == ["hej"]
    assert [event["outcome"] for event in events] == ["miss", "hit"]
