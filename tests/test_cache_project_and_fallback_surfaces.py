from __future__ import annotations

import json
import sys
from types import ModuleType


def test_agentic_tool_cache_roundtrips_read_file(tmp_path, monkeypatch):
    from core.services import agentic_tool_cache as cache

    state: dict[str, dict[str, object]] = {}

    def load_json(_key, default):
        return dict(state) if state else dict(default)

    def save_json(_key, records):
        state.clear()
        state.update(records)

    monkeypatch.setattr(cache, "load_json", load_json)
    monkeypatch.setattr(cache, "save_json", save_json)

    target = tmp_path / "sample.txt"
    target.write_text("hello\n", encoding="utf-8")

    cache.store_result(
        tool_name="read_file",
        arguments={"path": str(target), "_runtime_session": "s1"},
        result_text="hello",
        status="ok",
    )
    cached = cache.get_cached_result("read_file", {"path": str(target)})

    assert cached is not None
    assert cached["result_text"] == "hello"
    assert cache.get_cached_result("search_memory", {"query": "x"}) is None


def test_memory_consolidation_nudge_is_unconditional():
    from core.services import memory_consolidation_nudge as nudge

    section = nudge.memory_consolidation_nudge_section()

    assert "MEMORY.md" in section
    assert "Aldrig bare skrive" in section


def test_creative_projects_surface_tracks_created_projects(tmp_path, monkeypatch):
    from core.services import creative_projects as projects

    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))

    created = projects.create_project(title="Build something", intent="ship a thing")
    note_added = projects.add_progress_note(created["project_id"], "first note")
    surface = projects.build_creative_projects_surface()
    prompt = projects.build_creative_projects_prompt_section()

    assert note_added is True
    assert surface["total"] == 1
    assert surface["active_count"] == 0
    assert surface["dreaming_count"] == 1
    assert prompt is not None
    assert "Drømme-projekter" in prompt


def test_mood_dialer_reads_current_mood(monkeypatch):
    from core.services import mood_dialer as dialer

    mood_module = ModuleType("core.services.mood_oscillator")
    mood_module.get_current_mood = lambda: "content"
    mood_module.get_mood_intensity = lambda: 0.9
    monkeypatch.setitem(sys.modules, "core.services.mood_oscillator", mood_module)

    params = dialer.derive_from_v2_mood()
    surface = dialer.build_mood_dialer_surface()

    assert params.mood_level == 4
    assert params.style_preset == "agentic"
    assert surface["active"] is True
    assert "level=4" in surface["summary"]


def test_heartbeat_provider_fallback_executes_openai_compat(monkeypatch):
    from core.services import heartbeat_provider_fallback as fallback

    monkeypatch.setattr(
        "core.services.heartbeat_runtime._load_provider_api_key",
        lambda provider, profile: "api-key",
    )
    monkeypatch.setattr(
        "core.services.heartbeat_runtime._estimate_tokens",
        lambda text: max(1, len(text) // 4),
    )

    response_payload = {
        "choices": [{"message": {"content": "heartbeat ok"}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 3},
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(response_payload).encode("utf-8")

    monkeypatch.setattr(
        fallback.urllib_request,
        "urlopen",
        lambda req, timeout=0: FakeResponse(),
    )

    result = fallback.execute_openai_compat_heartbeat_prompt(
        prompt="ping",
        target={"provider": "mistral", "model": "small", "auth_profile": "default"},
    )

    assert result["text"] == "heartbeat ok"
    assert result["execution_status"] == "success"
