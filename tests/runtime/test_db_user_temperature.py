"""Tests for db_user_temperature helpers."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    """Steer connect() at a fresh on-disk DB for each test."""
    db_path = tmp_path / "jarvis.db"
    from core.runtime import db as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    db_mod.init_db()
    return db_path


def test_upsert_active_field_creates_new(fresh_db):
    from core.runtime.db_user_temperature import upsert_active_field, get_active_field_raw

    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.3, "arousal": 0.4, "texture": "warm", "confidence": 0.5},
        struct_signals={"length_z_score": 0.1, "burst_density": 0.2},
        llm=None,
        combined={
            "field_valens": 0.3, "field_arousal": 0.4, "field_texture": "warm",
            "field_intensity": 0.7, "field_conflict": False,
        },
        baseline={"message_count": 50, "built_at": "2026-05-10T00:00:00Z", "ready": True},
    )
    row = get_active_field_raw(workspace_id="default")
    assert row is not None
    assert row["struct_texture"] == "warm"
    assert row["field_valens"] == 0.3


def test_upsert_active_field_updates_existing(fresh_db):
    from core.runtime.db_user_temperature import upsert_active_field, get_active_field_raw

    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.3, "arousal": 0.4, "texture": "warm", "confidence": 0.5},
        struct_signals={},
        llm=None,
        combined={
            "field_valens": 0.3, "field_arousal": 0.4, "field_texture": "warm",
            "field_intensity": 0.7, "field_conflict": False,
        },
        baseline={"message_count": 50, "built_at": "now", "ready": True},
    )
    upsert_active_field(
        workspace_id="default",
        struct={"valens": -0.5, "arousal": 0.7, "texture": "frustrated", "confidence": 0.8},
        struct_signals={},
        llm={"valens": -0.4, "arousal": 0.6, "texture": "frustrated",
             "confidence": 0.7, "rationale": "abrupt"},
        combined={
            "field_valens": -0.45, "field_arousal": 0.65, "field_texture": "frustrated",
            "field_intensity": 0.95, "field_conflict": False,
        },
        baseline={"message_count": 51, "built_at": "now", "ready": True},
    )
    row = get_active_field_raw(workspace_id="default")
    assert row["struct_texture"] == "frustrated"
    assert row["field_valens"] == -0.45
    assert row["llm_rationale"] == "abrupt"


def test_get_active_field_raw_returns_none_for_unknown(fresh_db):
    from core.runtime.db_user_temperature import get_active_field_raw
    assert get_active_field_raw(workspace_id="nonexistent") is None


def test_set_and_consume_trigger_pending(fresh_db):
    from core.runtime.db_user_temperature import (
        upsert_active_field, set_llm_trigger_pending, consume_llm_trigger_pending,
    )

    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.0, "arousal": 0.0, "texture": "cool", "confidence": 0.0},
        struct_signals={},
        llm=None,
        combined={
            "field_valens": 0.0, "field_arousal": 0.0, "field_texture": "cool",
            "field_intensity": 0.0, "field_conflict": False,
        },
        baseline={"message_count": 0, "built_at": "", "ready": False},
    )
    assert consume_llm_trigger_pending(workspace_id="default") is False
    set_llm_trigger_pending(workspace_id="default")
    assert consume_llm_trigger_pending(workspace_id="default") is True
    assert consume_llm_trigger_pending(workspace_id="default") is False


def test_signals_json_round_trips(fresh_db):
    from core.runtime.db_user_temperature import upsert_active_field, get_active_field_raw

    signals = {
        "length_z_score": 0.5,
        "response_delay_z_score": -0.3,
        "punctuation_density": 0.1,
        "caps_density": 0.0,
        "hour_of_day_offset": 0.2,
        "burst_density": 0.4,
    }
    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.0, "arousal": 0.0, "texture": "cool", "confidence": 0.0},
        struct_signals=signals,
        llm=None,
        combined={
            "field_valens": 0.0, "field_arousal": 0.0, "field_texture": "cool",
            "field_intensity": 0.0, "field_conflict": False,
        },
        baseline={"message_count": 0, "built_at": "", "ready": False},
    )
    row = get_active_field_raw(workspace_id="default")
    assert row["struct_signals"] == signals
