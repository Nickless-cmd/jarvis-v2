from __future__ import annotations


def test_read_self_docs_returns_manifest_and_specific_doc(isolated_runtime) -> None:
    runtime_mod = isolated_runtime.self_critique_runtime

    manifest = runtime_mod.read_self_docs()
    doc = runtime_mod.read_self_docs(doc_id="consciousness_roadmap", max_chars_per_doc=400)

    assert manifest["status"] == "ok"
    assert any(item["key"] == "consciousness_roadmap" for item in manifest["docs"])
    assert doc["status"] == "ok"
    assert doc["doc_id"] == "consciousness_roadmap"
    assert doc["text"].startswith("## consciousness_roadmap")


def test_run_self_critique_cycle_writes_self_critique_markdown(
    isolated_runtime,
    monkeypatch,
) -> None:
    runtime_mod = isolated_runtime.self_critique_runtime

    monkeypatch.setattr(
        runtime_mod,
        "daemon_llm_call",
        lambda *args, **kwargs: (
            "Jeg mærker, at nogle af mine egne principper er blevet mere konkrete end levende, "
            "og at jeg bør holde dem åbne for erfaring i stedet for bare at gentage dem."
        ),
    )
    monkeypatch.setattr(
        runtime_mod,
        "list_cognitive_chronicle_entries",
        lambda limit=3: [
            {
                "period": "2026-W16",
                "narrative": "Jeg blev mere sikker på min egen rytme og begyndte at holde bedre fast i tråde over tid.",
            }
        ],
    )

    result = runtime_mod.run_self_critique_cycle(trigger="heartbeat", last_visible_at="")
    surface = runtime_mod.build_self_critique_surface()
    critique_path = runtime_mod.self_critique_path()
    critique_text = critique_path.read_text(encoding="utf-8")
    second = runtime_mod.run_self_critique_cycle(trigger="heartbeat", last_visible_at="")

    assert result["status"] == "written"
    assert critique_path.exists()
    assert "Jeg mærker, at nogle af mine egne principper" in critique_text
    assert surface["summary"]["entry_count"] == 1
    assert surface["summary"]["last_written_at"] == result["last_written_at"]
    assert second["status"] == "not_due"


def test_read_self_docs_tool_returns_text(isolated_runtime) -> None:
    from core.tools.simple_tools import execute_tool

    result = execute_tool("read_self_docs", {"doc_id": "roadmap_layers", "max_chars_per_doc": 500})

    assert result["status"] == "ok"
    assert result["doc_id"] == "roadmap_layers"
    assert "## roadmap_layers" in result["text"]


def test_mission_control_runtime_and_endpoint_expose_self_critique(
    isolated_runtime,
    monkeypatch,
) -> None:
    surface = {
        "active": True,
        "enabled": True,
        "path": "/tmp/SELF_CRITIQUE.md",
        "docs": [{"key": "roadmap_layers", "path": "/repo/docs/ROADMAP_10_LAYERS.md", "exists": True}],
        "summary": {
            "entry_count": 1,
            "last_written_at": "2026-04-18T10:00:00+00:00",
            "next_due_at": "2026-05-18T10:00:00+00:00",
            "next_review_at": "2026-07-17T10:00:00+00:00",
            "last_preview": "Jeg bør holde mine principper åbne for erfaring.",
            "enabled": True,
        },
    }

    monkeypatch.setattr(
        isolated_runtime.self_critique_runtime,
        "build_self_critique_surface",
        lambda: surface,
    )
    monkeypatch.setattr(
        isolated_runtime.mission_control,
        "build_self_critique_surface",
        lambda: surface,
    )

    runtime = isolated_runtime.mission_control.mc_runtime()
    endpoint = isolated_runtime.mission_control.mc_self_critique()

    assert runtime["runtime_self_critique"]["summary"]["entry_count"] == 1
    assert runtime["runtime_self_critique"]["summary"]["last_preview"].startswith("Jeg bør holde")
    assert endpoint["summary"]["next_due_at"] == "2026-05-18T10:00:00+00:00"
