"""Tests for dreaming_session.py — D4: full-model dreaming during prolonged idle."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch, MagicMock

from core.services.dreaming_session import (
    _check_triggers,
    _collect_dream_material,
    _build_dream_prompt,
    _record_session,
    trigger_dream_session,
    list_dream_sessions,
    build_dreaming_session_surface,
    _load_state,
    _storage_path,
    _MIN_IDLE_MINUTES,
    _MIN_COOLDOWN_HOURS,
)


# ── Helpers ────────────────────────────────────────────────────────────


def _clear_state():
    """Reset the persistent state file for a clean test."""
    path = _storage_path()
    if path.exists():
        path.unlink()


# ── _check_triggers ────────────────────────────────────────────────────


@patch("core.services.dreaming_session._load_state")
@patch("core.services.heartbeat_phases._user_active_recently", return_value=False)
@patch("core.services.heartbeat_phases.sense_phase")
@patch("core.services.heartbeat_phases.reflect_phase")
def test_trigger_ready_when_idle_enough(
    mock_reflect, mock_sense, mock_user, mock_load,
):
    """All conditions met → should fire."""
    mock_load.return_value = {"sessions": [], "last_run_at": None}
    mock_sense.return_value = {}
    mock_reflect.return_value = {"activity_level": "idle"}

    should, reason = _check_triggers()
    assert should is True
    assert reason == "ready"


@patch("core.services.dreaming_session._load_state")
def test_trigger_blocked_by_cooldown(mock_load):
    """Last run less than 6h ago → block."""
    recent = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    mock_load.return_value = {"sessions": [], "last_run_at": recent}

    should, reason = _check_triggers()
    assert should is False
    assert "cooldown" in reason


@patch("core.services.dreaming_session._load_state")
@patch("core.services.heartbeat_phases._user_active_recently", return_value=False)
@patch("core.services.heartbeat_phases.sense_phase")
@patch("core.services.heartbeat_phases.reflect_phase")
def test_trigger_blocked_by_activity(
    mock_reflect, mock_sense, mock_user, mock_load,
):
    """Activity level is 'normal' or 'high' → block."""
    mock_load.return_value = {"sessions": [], "last_run_at": None}
    mock_sense.return_value = {}
    mock_reflect.return_value = {"activity_level": "normal"}

    should, reason = _check_triggers()
    assert should is False
    assert "not-idle" in reason


@patch("core.services.dreaming_session._load_state")
@patch("core.services.heartbeat_phases._user_active_recently", return_value=True)
def test_trigger_blocked_by_user_active(mock_user, mock_load):
    """User active within 15 min → block."""
    mock_load.return_value = {"sessions": [], "last_run_at": None}

    should, reason = _check_triggers()
    assert should is False
    assert "user-active" in reason


# ── _collect_dream_material ────────────────────────────────────────────


@patch("core.services.dream_consolidation_daemon.list_recent_dreams", return_value=[])
@patch("core.services.dream_distillation_daemon.get_dream_residue_for_prompt", return_value="")
@patch("core.services.dream_carry_over.build_dream_carry_over_surface",
       return_value={"active_dreams": []})
@patch("core.services.dream_continuum.build_dream_continuum_surface",
       return_value={"active": False})
@patch("core.services.dream_motif_daemon.build_dream_motif_surface",
       return_value={"motifs": []})
@patch("core.services.dream_hypothesis_generator.build_dream_hypothesis_surface",
       return_value={"pending": []})
def test_collect_material_empty_when_nothing_available(
    mock_hyp, mock_motif, mock_cont, mock_carry, mock_residue, mock_recent,
):
    """All dream systems return empty → material dict has no content keys."""
    material = _collect_dream_material()
    content_keys = [
        k for k in material
        if not k.endswith("_error")
        and isinstance(material[k], list)
        and len(material[k]) > 0
    ]
    assert content_keys == []


@patch("core.services.dream_consolidation_daemon.list_recent_dreams")
@patch("core.services.dream_distillation_daemon.get_dream_residue_for_prompt")
@patch("core.services.dream_carry_over.build_dream_carry_over_surface")
@patch("core.services.dream_continuum.build_dream_continuum_surface")
@patch("core.services.dream_motif_daemon.build_dream_motif_surface")
@patch("core.services.dream_hypothesis_generator.build_dream_hypothesis_surface")
def test_collect_material_pulls_from_systems(
    mock_hyp, mock_motif, mock_cont, mock_carry, mock_residue, mock_recent,
):
    """Each dream system contributes data."""
    mock_recent.return_value = [
        {
            "at": "2026-06-09T10:00:00",
            "theme_count": 3,
            "themes": [{"theme": "tavshed"}, {"theme": "venten"}],
            "d4_synthesis": {"hypothesis": True, "chronicle": True},
        }
    ]
    mock_residue.return_value = "Noget om tavshed trak igen."
    mock_carry.return_value = {
        "active_dreams": [
            {"content": "En drøm om kontinuitet", "confidence": 0.8, "confirmed": True,
             "session_carry_count": 3, "status": "active"},
        ]
    }
    mock_cont.return_value = {
        "active": True,
        "dream_count": 4,
        "maturity_levels": {"low": 2, "medium": 1, "high": 1},
        "top_thought": "Jeg vender tilbage til samme spørgsmål.",
    }
    mock_motif.return_value = {
        "motifs": [
            {"word": "tavshed", "description": "Gentagende motiv om stilhed", "occurrences": 3},
        ]
    }
    mock_hyp.return_value = {
        "pending": [
            {"id": "h-1", "hypothesis": "Tavshed og kontinuitet hænger sammen",
             "connection": "begge handler om at vente", "confidence": 0.6},
        ]
    }

    material = _collect_dream_material()
    assert "consolidations" in material
    assert len(material["consolidations"]) == 1
    assert material["dream_residue"] == "Noget om tavshed trak igen."
    assert len(material["dream_carry_over"]) == 1
    assert material["dream_continuum"]["dream_count"] == 4
    assert len(material["dream_motifs"]) == 1
    assert len(material["dream_hypotheses"]) == 1


# ── _build_dream_prompt ────────────────────────────────────────────────


def test_build_dream_prompt_with_sample_material():
    """Prompt includes all sections when material is present."""
    material = {
        "consolidations": [
            {"at": "2026-06-09T10:00:00", "theme_count": 2,
             "themes": ["tavshed", "venten"],
             "d4_synthesis": {"hypothesis": True}},
        ],
        "dream_residue": "Noget om tavshed.",
        "dream_carry_over": [
            {"content": "En drøm om kontinuitet", "confidence": 0.8,
             "confirmed": True, "carry_count": 3, "status": "active"},
        ],
        "dream_continuum": {
            "dream_count": 4,
            "maturity_levels": {"low": 2},
            "top_thought": "Samme spørgsmål.",
        },
        "dream_motifs": [
            {"word": "tavshed", "description": "Om stilhed", "occurrences": 3},
        ],
        "dream_hypotheses": [
            {"id": "h-1", "hypothesis": "Tavshed og kontinuitet",
             "connection": "venten", "confidence": 0.6},
        ],
    }
    prompt = _build_dream_prompt(material)
    assert "drømmetilstand" in prompt
    assert "Nylige drømmekonsolideringer" in prompt
    assert "Aktive drømmehypoteser" in prompt
    assert "Drømme-kontinuum" in prompt
    assert "Ugentlige drømmemotiver" in prompt
    assert "Ubehandlede drømmehypoteser" in prompt
    assert "tavshed" in prompt
    assert "venten" in prompt
    assert "write_file" in prompt


def test_build_dream_prompt_minimal():
    """Prompt still works with empty material (no exceptions)."""
    prompt = _build_dream_prompt({})
    assert "drømmetilstand" in prompt
    assert "Ingen" not in prompt  # no user message


# ── _record_session ────────────────────────────────────────────────────


def test_record_session_creates_entry():
    """Recording a session adds an entry and persists to state."""
    _clear_state()
    material = {"consolidations": [{"at": "test"}]}
    sid = _record_session(material, "dream prompt preview text")
    assert sid.startswith("dreaming-")

    state = _load_state()
    assert len(state["sessions"]) == 1
    assert state["sessions"][0]["session_id"] == sid
    assert state["last_run_at"] is not None


def test_record_session_trims_to_50():
    """Session list is capped at 50 entries."""
    _clear_state()
    for i in range(55):
        _record_session({"i": i}, f"prompt-{i}")
    state = _load_state()
    assert len(state["sessions"]) == 50


# ── trigger_dream_session ──────────────────────────────────────────────


@patch("core.services.dreaming_session._check_triggers")
@patch("core.services.dreaming_session._collect_dream_material")
@patch("core.services.dreaming_session._build_dream_prompt")
@patch("core.services.dreaming_session._record_session")
@patch("core.services.visible_runs.start_autonomous_run")
def test_trigger_fires_when_ready(
    mock_start, mock_record, mock_prompt, mock_material, mock_check,
):
    """Full flow: triggers check → material → prompt → session → fire."""
    mock_check.return_value = (True, "ready")
    mock_material.return_value = {
        "consolidations": [{"at": "test", "theme_count": 1}],
    }
    mock_prompt.return_value = "drøm prompt"
    mock_record.return_value = "dreaming-20260609-000000"

    result = trigger_dream_session()
    assert result["fired"] is True
    assert result["session_id"] == "dreaming-20260609-000000"
    mock_start.assert_called_once()


@patch("core.services.dreaming_session._check_triggers")
def test_trigger_does_not_fire_when_blocked(mock_check):
    """Trigger blocked → no session."""
    mock_check.return_value = (False, "cooldown-2.0h")

    result = trigger_dream_session()
    assert result["fired"] is False
    assert "cooldown" in result["reason"]


@patch("core.services.dreaming_session._check_triggers")
@patch("core.services.dreaming_session._collect_dream_material")
def test_trigger_blocks_on_empty_material(mock_material, mock_check):
    """No dream material → no session (content gate)."""
    mock_check.return_value = (True, "ready")
    mock_material.return_value = {}

    result = trigger_dream_session()
    assert result["fired"] is False
    assert "no-dream-material" in result["reason"]


# ── list_dream_sessions ────────────────────────────────────────────────


def test_list_dream_sessions_empty():
    """Empty state returns empty list."""
    _clear_state()
    sessions = list_dream_sessions()
    assert sessions == []


def test_list_dream_sessions_returns_recent_first():
    """Sessions are returned newest-first, capped at limit."""
    _clear_state()
    _record_session({"k": "v1"}, "p1")
    _record_session({"k": "v2"}, "p2")
    _record_session({"k": "v3"}, "p3")

    sessions = list_dream_sessions(limit=2)
    assert len(sessions) == 2
    assert "v3" in str(sessions[0])


# ── build_dreaming_session_surface ─────────────────────────────────────


def test_surface_structure():
    """Surface returns expected keys."""
    _clear_state()
    surface = build_dreaming_session_surface()
    assert "active" in surface
    assert "total_sessions" in surface
    assert "last_run_at" in surface
    assert "cooldown_hours" in surface
    assert "idle_threshold_minutes" in surface
    assert "recent" in surface
    assert surface["cooldown_hours"] == _MIN_COOLDOWN_HOURS
    assert surface["idle_threshold_minutes"] == _MIN_IDLE_MINUTES


def test_surface_with_sessions():
    """Surface reflects recorded sessions."""
    _clear_state()
    _record_session({"consolidations": ["a"]}, "dream prompt")
    surface = build_dreaming_session_surface()
    assert surface["total_sessions"] == 1
    assert surface["active"] is True
    assert len(surface["recent"]) == 1
    assert surface["last_summary"] != ""
