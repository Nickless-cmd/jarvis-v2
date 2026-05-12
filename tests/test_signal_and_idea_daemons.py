from __future__ import annotations

import sys
from types import ModuleType


def test_agent_skill_distiller_appends_principles(monkeypatch):
    from core.services import agent_skill_distiller as distiller

    observations = [
        {"role": "planner", "kind": "run", "summary": "ship small tests", "success": True, "recorded_at": "2026-05-12T10:00:00+00:00"},
        {"role": "planner", "kind": "run", "summary": "ship small tests", "success": True, "recorded_at": "2026-05-12T10:30:00+00:00"},
        {"role": "planner", "kind": "run", "summary": "split large diffs", "success": False, "recorded_at": "2026-05-12T11:00:00+00:00"},
    ]

    state_store = ModuleType("core.runtime.state_store")
    state_store.load_json = lambda key, default: observations if key == "agent_observations" else default
    monkeypatch.setitem(sys.modules, "core.runtime.state_store", state_store)

    daemon_llm = ModuleType("core.services.daemon_llm")
    daemon_llm.daemon_llm_call = lambda prompt, max_len=400, fallback="", daemon_name="": (
        "WORKFLOW: split large diffs first\nPITFALL: shipping without tests\nPATTERN: tests unlock merges"
    )
    monkeypatch.setitem(sys.modules, "core.services.daemon_llm", daemon_llm)

    appended: list[tuple[str, str, str]] = []
    skill_lib = ModuleType("core.services.agent_skill_library")
    skill_lib.append_skill_observation = lambda *, role, section, observation, proposer: appended.append((role, section, observation)) or {"status": "ok"}
    monkeypatch.setitem(sys.modules, "core.services.agent_skill_library", skill_lib)

    result = distiller.distill_skills_for_role("planner", days=7)

    assert result["status"] == "ok"
    assert result["appended"] == 3
    assert appended[0][1] == "Workflows"


def test_avoidance_detector_finds_stale_clusters(monkeypatch):
    from core.services import avoidance_detector as detector

    stale = "2026-04-20T00:00:00+00:00"
    db = ModuleType("core.runtime.db")
    db.list_runtime_goal_signals = lambda limit=500: [
        {"title": "self mutation lineage", "support_count": 2, "session_count": 1, "status": "active", "updated_at": stale},
        {"title": "self mutation learning", "support_count": 1, "session_count": 1, "status": "active", "updated_at": stale},
    ]
    db.list_runtime_dream_hypothesis_signals = lambda limit=500: []
    db.list_runtime_development_focuses = lambda limit=200: []
    monkeypatch.setitem(sys.modules, "core.runtime.db", db)

    findings = detector.detect_avoidances()
    surface = detector.build_avoidance_surface()
    prompt = detector.build_avoidance_prompt_section()

    assert findings and findings[0]["cluster"] == "self-mutation"
    assert surface["active"] is True
    assert prompt is not None
    assert "Undgåelses-mønster" in surface["summary"] or "undgåelses-mønster" in surface["summary"]


def test_creative_instinct_daemon_generates_seeds(monkeypatch, tmp_path):
    from core.services import creative_instinct_daemon as daemon

    state = {"seeds": [], "last_tick_at": "2026-05-12T07:00:00+00:00"}
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setattr(daemon, "_load", lambda: state)
    monkeypatch.setattr(daemon, "_save", lambda data: state.update(data))
    monkeypatch.setattr(daemon, "_recent_chat_topics", lambda limit=5: ["build a graph", "short tests first"])
    monkeypatch.setattr(daemon, "_recent_dream_hypotheses", lambda: ["persistent creative project"])
    monkeypatch.setattr(daemon, "_recent_avoidances", lambda: ["avoidance detector"])
    monkeypatch.setattr(daemon, "_current_mood_label", lambda: "content")
    monkeypatch.setattr(daemon, "_hours_since", lambda iso_str: 3.0)
    monkeypatch.setattr(daemon.random, "sample", lambda pool, k: list(pool)[:k])
    monkeypatch.setattr(daemon.random, "choice", lambda seq: seq[0])
    monkeypatch.setattr(daemon.random, "uniform", lambda a, b: 0.5)
    monkeypatch.setattr(daemon, "_write_incubator_md", lambda seeds: True)

    result = daemon.tick()

    assert result["active_seeds"] >= 1
    assert result["total_seeds"] >= 1
    assert state["seeds"]


def test_day_shape_memory_detects_anomaly(tmp_path, monkeypatch):
    from core.services import day_shape_memory as day

    monkeypatch.setattr(day, "_storage_path", lambda: tmp_path / "day_shapes.json")
    history = []
    for _ in range(5):
        history.append({
            "date": "2026-05-11",
            "tick_samples": 8,
            "hour_distribution": {"9": 2},
            "contact_hours": [9],
            "sound_categories": {"calm": 2},
            "cpu_mean": 10.0,
            "ram_mean": 20.0,
            "mood_mean": 0.1,
        })
    state = {
        "history": history,
        "current": {
            "date": "2026-05-12",
            "tick_samples": 6,
            "hour_distribution": {"14": 6},
            "contact_hours": [14],
            "sound_categories": {"alert": 3},
            "hardware_load_samples": [[90.0, 95.0]] * 6,
            "mood_samples": [-0.7] * 6,
        },
    }
    monkeypatch.setattr(day, "_load", lambda: state)
    monkeypatch.setattr(day, "_save", lambda data: state.update(data))

    anomaly = day.detect_today_anomaly()

    assert anomaly["has_signal"] is True
    assert anomaly["anomalies"]


def test_dream_motif_daemon_clusters_and_names(monkeypatch, tmp_path):
    from core.services import dream_motif_daemon as motif

    state = {}
    monkeypatch.setattr(motif, "set_runtime_state_value", lambda key, value: state.update(value))
    monkeypatch.setattr(motif, "get_runtime_state_value", lambda key: state)
    monkeypatch.setattr(motif, "_load_recent_fragments", lambda: [
        "forest green and memory drift",
        "forest green and signal texture",
        "memory drift with recurring pattern",
        "signal texture and recurring pattern",
        "forest green recurring pattern",
        "memory drift recurring pattern",
        "signal texture recurring pattern",
        "forest green memory drift signal texture",
    ])
    monkeypatch.setattr(motif, "_name_motifs_via_llm", lambda motifs, fragments: [
        {"word": "forest", "description": "color motif", "occurrences": 4},
        {"word": "memory", "description": "recurrence motif", "occurrences": 4},
    ])
    monkeypatch.setattr(motif, "_write_dream_language_file", lambda motifs, now, fragment_count: True)

    result = motif.tick_dream_motif_daemon()
    surface = motif.build_dream_motif_surface()

    assert result["generated"] is True
    assert result["motif_count"] == 2
    assert surface["motif_count"] == 2
    assert isinstance(surface["motifs"], list)
