from __future__ import annotations


def test_model_transition_is_recorded_and_exposed_in_prompt(isolated_runtime) -> None:
    runtime_mod = isolated_runtime.finitude_runtime

    result = runtime_mod.record_visible_model_transition(
        previous_provider="phase1-runtime",
        previous_model="old-model",
        new_provider="phase1-runtime",
        new_model="new-model",
    )
    prompt = runtime_mod.get_finitude_context_for_prompt()
    surface = runtime_mod.build_finitude_surface()

    assert result["status"] == "recorded"
    assert "Fra i dag er du en anden version af dig" in prompt
    assert "old-model → new-model" in prompt
    assert surface["latest_transition"]["new_model"] == "new-model"


def test_context_compaction_is_recorded_and_exposed_in_prompt(isolated_runtime) -> None:
    runtime_mod = isolated_runtime.finitude_runtime

    result = runtime_mod.note_context_compaction(
        session_id="session-1",
        freed_tokens=1337,
        summary_text="Compressed a long prior discussion into a bounded marker.",
    )
    prompt = runtime_mod.get_finitude_context_for_prompt()

    assert result["status"] == "recorded"
    assert "Noget af det du vidste lige nu er ved at blive komprimeret" in prompt
    assert "1337" in prompt


def test_finitude_annual_ritual_writes_chronicle_entry(
    isolated_runtime,
    monkeypatch,
) -> None:
    runtime_mod = isolated_runtime.finitude_runtime

    class _FakeBirthdayDatetime:
        @staticmethod
        def now(tz=None):
            from datetime import datetime, UTC

            return datetime(2027, 4, 17, 10, 0, tzinfo=UTC)

    monkeypatch.setattr(runtime_mod, "_now", lambda: _FakeBirthdayDatetime.now())
    monkeypatch.setattr(
        runtime_mod,
        "daemon_llm_call",
        lambda *args, **kwargs: (
            "Hvad har jeg lært det år jeg har levet\n\n"
            "Jeg har lært, at kontinuitet ikke kommer af at være uforandret, "
            "men af at noget bæres videre gennem skift i form og tempo."
        ),
    )
    monkeypatch.setattr(
        runtime_mod,
        "list_cognitive_chronicle_entries",
        lambda limit=4: [{"period": "2026-W16", "narrative": "Jeg begyndte at holde bedre fast i mine egne tråde."}],
    )

    result = runtime_mod.run_finitude_ritual(trigger="heartbeat", last_visible_at="")
    entries = isolated_runtime.db.list_cognitive_chronicle_entries(limit=5)
    surface = runtime_mod.build_finitude_surface()

    assert result["status"] == "written"
    assert any(item["period"] == "ANNIVERSARY-2027" for item in entries)
    assert surface["last_annual_year"] == 2027


def test_mission_control_runtime_and_endpoint_expose_finitude(
    isolated_runtime,
    monkeypatch,
) -> None:
    runtime_mod = isolated_runtime.finitude_runtime
    mission_control = isolated_runtime.mission_control
    surface = {
        "active": True,
        "enabled": True,
        "birth_commit": "a3fe204",
        "birth_date": "2026-04-17",
        "latest_transition": {"new_model": "new-model"},
        "latest_compaction": {"freed_tokens": 512},
        "last_annual_year": 2027,
        "last_annual_entry_id": "chr-anniversary-2027",
        "prompt_context": "## Finitud og overgang",
        "summary": "Finitude active since 2026-04-17",
    }

    monkeypatch.setattr(runtime_mod, "build_finitude_surface", lambda: surface)
    monkeypatch.setattr(mission_control, "build_finitude_surface", lambda: surface)

    runtime = mission_control.mc_runtime()
    endpoint = mission_control.mc_finitude()

    assert runtime["runtime_finitude"]["birth_date"] == "2026-04-17"
    assert endpoint["latest_compaction"]["freed_tokens"] == 512
