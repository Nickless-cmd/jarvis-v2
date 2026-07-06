from __future__ import annotations

from types import SimpleNamespace


def test_conflict_memory_prompts_from_recent_lessons(monkeypatch):
    from core.services import conflict_prompt_service as conflict

    monkeypatch.setattr(
        conflict,
        "list_cognitive_conflict_memories",
        lambda limit=4: [
            {"topic": "mail", "lesson": "ask for evidence", "resolution": "user_correct"},
            {"topic": "scope", "lesson": "avoid guessing", "resolution": "jarvis_holds"},
        ],
    )

    section = conflict.build_conflict_memory_prompt_section()
    surface = conflict.build_conflict_memory_surface()

    assert section is not None
    assert "Konflikthukommelse" in section
    assert "bruger havde ret" in section
    assert surface["active"] is True
    assert surface["count"] == 2


def test_life_milestones_reads_workspace_files(tmp_path, monkeypatch):
    from core.services import life_milestones as milestones

    milestones_file = tmp_path / "MILESTONES.md"
    milestones_file.write_text("## 2026-05-12\nFirst milestone\n", encoding="utf-8")
    manifest_file = tmp_path / "MANIFEST.md"
    manifest_file.write_text("Manifest text", encoding="utf-8")

    monkeypatch.setattr(milestones, "_milestones_file", lambda: milestones_file)
    monkeypatch.setattr(milestones, "_manifest_file", lambda: manifest_file)

    section = milestones.build_life_history_prompt_section()
    surface = milestones.build_life_milestones_surface()

    assert section == "## 2026-05-12\nFirst milestone"
    assert surface["active"] is True
    assert surface["has_manifest"] is True


def test_priors_feedback_uses_internal_priors(monkeypatch):
    from core.services import priors_feedback as priors

    monkeypatch.setattr(priors, "_recent_crisis_summary", lambda days=30: ["- crisis prior"])
    monkeypatch.setattr(priors, "_decision_priors", lambda: ["- decision prior"])
    monkeypatch.setattr(priors, "_quality_outlier_priors", lambda days=14: ["- quality prior"])

    bullets = priors.build_priors_feedback()
    section = priors.priors_feedback_section()

    assert bullets == ["- crisis prior", "- decision prior", "- quality prior"]
    assert "Mønstre fra dit eget data" in section


def test_session_wakeup_surfaces_notable_events(monkeypatch):
    from core.services import session_wakeup as wakeup

    events = [
        {
            "id": 11,
            "kind": "runtime.error",
            "created_at": "2026-05-12T09:00:00+00:00",
            "payload": {"error": "boom"},
        },
        {
            "id": 12,
            "kind": "tool.invoked",
            "created_at": "2026-05-12T09:01:00+00:00",
            "payload": {"tool": "noop"},
        },
        {
            "id": 13,
            "kind": "approval.pending",
            "created_at": "2026-05-12T09:02:00+00:00",
            "payload": {"summary": "waiting"},
        },
    ]
    seen: list[int] = []

    monkeypatch.setattr(wakeup, "last_seen_event_id", lambda session_id: 10)
    monkeypatch.setattr(wakeup, "mark_seen", lambda session_id, event_id: seen.append(event_id))
    monkeypatch.setattr(
        "core.eventbus.bus.event_bus",
        SimpleNamespace(
            recent_since_id=lambda last_id, limit=200: events,
            recent=lambda limit=30: events,
        ),
    )

    digest = wakeup.wakeup_digest("sess-3")

    assert digest is not None
    assert "runtime.error" in digest
    assert "approval.pending" in digest
    assert seen == [13]


def test_clarification_classifier_scores_vague_requests():
    from core.services import clarification_classifier as classifier

    result = classifier.score_message("fix it")
    prompt = classifier.clarification_prompt_section("fix it")

    assert result["verdict"] == "ask_first"
    assert result["score"] >= 50
    assert prompt is not None
    assert "Ambiguity-classifier: brugerbesked scored" in prompt
