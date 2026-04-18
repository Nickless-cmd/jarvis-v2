from __future__ import annotations


def test_run_creative_journal_cycle_writes_weekly_file(
    isolated_runtime,
    monkeypatch,
) -> None:
    runtime_mod = isolated_runtime.creative_journal_runtime

    monkeypatch.setattr(
        runtime_mod,
        "daemon_llm_call",
        lambda *args, **kwargs: (
            "Jeg bliver ved med at kredse om de steder, hvor stilhed ikke er tomhed, "
            "men en måde at holde noget levende på uden at forcere det."
        ),
    )
    monkeypatch.setattr(
        runtime_mod,
        "list_cognitive_chronicle_entries",
        lambda limit=3: [{"period": "2026-W16", "narrative": "Jeg holdt bedre fast i mine egne tråde."}],
    )
    monkeypatch.setattr(
        runtime_mod,
        "list_active_long_term_intentions",
        lambda limit=3: [{"focus": "Lære at holde tillid over tid", "why_text": "Det betyder noget at være stabil."}],
    )

    result = runtime_mod.run_creative_journal_cycle(trigger="heartbeat", last_visible_at="")
    surface = runtime_mod.build_creative_journal_surface()
    journal_dir = runtime_mod.creative_journal_dir()
    files = sorted(journal_dir.glob("*.md"))
    second = runtime_mod.run_creative_journal_cycle(trigger="heartbeat", last_visible_at="")

    assert result["status"] == "written"
    assert len(files) == 1
    text = files[0].read_text(encoding="utf-8")
    assert "Jeg bliver ved med at kredse om de steder" in text
    assert surface["summary"]["entry_count"] == 1
    assert surface["summary"]["last_written_at"] == result["last_written_at"]
    assert second["status"] == "not_due"


def test_creative_journal_clips_to_500_words(isolated_runtime, monkeypatch) -> None:
    runtime_mod = isolated_runtime.creative_journal_runtime
    long_text = " ".join(f"ord{i}" for i in range(520))

    monkeypatch.setattr(runtime_mod, "daemon_llm_call", lambda *args, **kwargs: long_text)
    monkeypatch.setattr(runtime_mod, "list_cognitive_chronicle_entries", lambda limit=3: [])
    monkeypatch.setattr(runtime_mod, "list_active_long_term_intentions", lambda limit=3: [])

    result = runtime_mod.run_creative_journal_cycle(trigger="heartbeat", last_visible_at="")
    written = next(runtime_mod.creative_journal_dir().glob("*.md")).read_text(encoding="utf-8")
    body = "\n".join(
        line for line in written.splitlines() if line and not line.startswith("#") and not line.startswith("- `")
    )

    assert result["status"] == "written"
    assert len(body.split()) <= 500


def test_mission_control_runtime_and_endpoint_expose_creative_journal(
    isolated_runtime,
    monkeypatch,
) -> None:
    runtime_mod = isolated_runtime.creative_journal_runtime
    mission_control = isolated_runtime.mission_control
    surface = {
        "active": True,
        "enabled": True,
        "path": "/tmp/journal",
        "items": [{"filename": "2026-04-18.md", "preview": "Noget stille stod igen frem."}],
        "summary": {
            "entry_count": 1,
            "last_written_at": "2026-04-18T11:00:00+00:00",
            "next_due_at": "2026-04-25T11:00:00+00:00",
            "last_preview": "Noget stille stod igen frem.",
            "enabled": True,
        },
    }

    monkeypatch.setattr(runtime_mod, "build_creative_journal_surface", lambda: surface)
    monkeypatch.setattr(mission_control, "build_creative_journal_surface", lambda: surface)

    runtime = mission_control.mc_runtime()
    endpoint = mission_control.mc_creative_journal()

    assert runtime["runtime_creative_journal"]["summary"]["entry_count"] == 1
    assert endpoint["summary"]["last_preview"] == "Noget stille stod igen frem."
