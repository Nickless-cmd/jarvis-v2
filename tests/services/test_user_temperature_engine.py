"""Tests for user_temperature_engine — pure logic."""
from __future__ import annotations

import pytest


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    db_path = tmp_path / "jarvis.db"
    from core.runtime import db as db_mod
    from core.runtime import db_core
    # Post-2026-05-15 split: patch begge facade + db_core (kilden).
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    monkeypatch.setattr(db_core, "DB_PATH", db_path)
    db_mod.init_db()
    return db_path


# ── Signal computation ────────────────────────────────────────────────


def test_punct_density_basic():
    from core.services.user_temperature_engine import _punct_density
    assert _punct_density("hello!") == pytest.approx(1 / 6, abs=0.01)
    assert _punct_density("just text") == 0.0
    assert _punct_density("") == 0.0


def test_caps_density_basic():
    from core.services.user_temperature_engine import _caps_density
    assert _caps_density("HELLO") == 1.0
    assert _caps_density("hello") == 0.0
    assert _caps_density("Hello") == pytest.approx(1 / 5, abs=0.01)
    assert _caps_density("") == 0.0
    assert _caps_density("123!?") == 0.0


# ── Field mapping ──────────────────────────────────────────────────────


def test_map_signals_to_field_neutral_input():
    from core.services.user_temperature_engine import map_signals_to_field
    signals = {
        "length_z_score": 0.0, "response_delay_z_score": 0.0,
        "punctuation_density": 0.0, "caps_density": 0.0,
        "hour_of_day_offset": 0.0, "burst_density": 0.0,
    }
    out = map_signals_to_field(signals)
    assert out["valens"] == 0.0
    assert out["arousal"] == 0.0
    assert out["texture"] == "cool"


def test_map_signals_high_energy_negative_valens():
    """Strong arousal signals + negative valens → frustrated texture."""
    from core.services.user_temperature_engine import map_signals_to_field
    signals = {
        "length_z_score": -1.0,         # very short messages → strong negative valens
        "response_delay_z_score": 0.5,  # slow response → negative valens
        "punctuation_density": 0.8,     # very high → high arousal
        "caps_density": 0.5,            # high → high arousal
        "hour_of_day_offset": 0.5,      # off-hours → negative valens
        "burst_density": 1.0,           # max → high arousal
    }
    out = map_signals_to_field(signals)
    # valens: -1.0*0.4 - 0.5*0.3 - 0.5*0.3 = -0.4 - 0.15 - 0.15 = -0.70
    # arousal: 0.8*0.3 + 0.5*0.2 + 1.0*0.3 - 0.5*0.2 = 0.24+0.10+0.30-0.10 = 0.54
    assert out["valens"] < -0.3
    assert out["arousal"] > 0.4
    assert out["texture"] == "frustrated"


def test_texture_from_circumplex_quadrants():
    from core.services.user_temperature_engine import _texture_from_circumplex
    assert _texture_from_circumplex(0.5, 0.6) == "playful"
    assert _texture_from_circumplex(-0.5, 0.6) == "frustrated"
    assert _texture_from_circumplex(0.0, 0.6) == "alert"
    assert _texture_from_circumplex(0.5, 0.0) == "warm"
    assert _texture_from_circumplex(-0.5, 0.0) == "tender"
    assert _texture_from_circumplex(-0.7, -0.5) == "withdrawn"
    assert _texture_from_circumplex(0.0, -0.4) == "cool"


# ── LLM validation ─────────────────────────────────────────────────────


def test_validate_llm_output_accepts_clean():
    from core.services.user_temperature_engine import _validate_llm_output
    out = _validate_llm_output({
        "valens": 0.3, "arousal": 0.5, "texture": "playful",
        "confidence": 0.7, "rationale": "Bjørn er i flow",
    })
    assert out is not None
    assert out["valens"] == 0.3
    assert out["texture"] == "playful"


def test_validate_llm_output_drops_unknown_texture():
    from core.services.user_temperature_engine import _validate_llm_output
    out = _validate_llm_output({
        "valens": 0.3, "arousal": 0.5, "texture": "totally_made_up",
        "confidence": 0.7,
    })
    assert out is None


def test_validate_llm_output_clamps_values():
    from core.services.user_temperature_engine import _validate_llm_output
    out = _validate_llm_output({
        "valens": 5.0, "arousal": -3.0, "texture": "warm",
        "confidence": 2.0,
    })
    assert out["valens"] == 1.0
    assert out["arousal"] == -1.0
    assert out["confidence"] == 0.5


def test_validate_llm_output_rejects_missing_valens():
    from core.services.user_temperature_engine import _validate_llm_output
    out = _validate_llm_output({
        "arousal": 0.5, "texture": "warm", "confidence": 0.5,
    })
    assert out is None


# ── Combine ────────────────────────────────────────────────────────────


def test_combine_streams_no_llm_returns_struct():
    from core.services.user_temperature_engine import combine_streams
    struct = {"valens": 0.3, "arousal": 0.4, "texture": "warm", "confidence": 0.5}
    out = combine_streams(struct=struct, llm=None)
    assert out["field_valens"] == 0.3
    assert out["field_texture"] == "warm"
    assert out["field_conflict"] is False


def test_combine_streams_low_llm_confidence_returns_struct():
    from core.services.user_temperature_engine import combine_streams
    struct = {"valens": 0.3, "arousal": 0.4, "texture": "warm", "confidence": 0.5}
    llm = {"valens": -0.8, "arousal": 0.6, "texture": "frustrated",
           "confidence": 0.1, "rationale": "x"}
    out = combine_streams(struct=struct, llm=llm)
    assert out["field_texture"] == "warm"
    assert out["field_conflict"] is False


def test_combine_streams_agreement_averages_valens_arousal():
    from core.services.user_temperature_engine import combine_streams
    struct = {"valens": 0.3, "arousal": 0.4, "texture": "warm", "confidence": 0.5}
    llm = {"valens": 0.5, "arousal": 0.4, "texture": "warm",
           "confidence": 0.7, "rationale": "x"}
    out = combine_streams(struct=struct, llm=llm)
    assert out["field_valens"] == pytest.approx(0.4, abs=0.01)
    assert out["field_texture"] == "warm"
    assert out["field_conflict"] is False


def test_combine_streams_conflict_weighted_average_favours_higher_confidence():
    # 2026-06-11 (commit 1669f17b): on conflict the merge no longer keeps the
    # structural stream primary — it takes a confidence-weighted average of
    # valens/arousal and adopts the texture of whichever stream has the higher
    # confidence weight. Here llm confidence (0.7) > struct (0.5), so llm wins
    # the texture and pulls the weighted valens negative.
    from core.services.user_temperature_engine import combine_streams
    struct = {"valens": 0.3, "arousal": 0.4, "texture": "warm", "confidence": 0.5}
    llm = {"valens": -0.5, "arousal": 0.4, "texture": "frustrated",
           "confidence": 0.7, "rationale": "x"}
    out = combine_streams(struct=struct, llm=llm)
    # w_s = 0.5/1.2, w_l = 0.7/1.2 → fv = 0.3*w_s + (-0.5)*w_l
    assert out["field_valens"] == pytest.approx(-0.1667, abs=0.001)
    assert out["field_texture"] == "frustrated"  # llm has higher confidence weight
    assert out["field_conflict"] is True


def test_combine_streams_texture_mismatch_is_conflict():
    from core.services.user_temperature_engine import combine_streams
    struct = {"valens": 0.3, "arousal": 0.4, "texture": "warm", "confidence": 0.5}
    llm = {"valens": 0.4, "arousal": 0.4, "texture": "playful",
           "confidence": 0.7, "rationale": "x"}
    out = combine_streams(struct=struct, llm=llm)
    assert out["field_conflict"] is True
    # Texture mismatch is a conflict; texture follows the higher-confidence
    # stream (llm at 0.7 > struct at 0.5) per the 2026-06-11 weighted merge.
    assert out["field_texture"] == "playful"


# ── Shift detection ────────────────────────────────────────────────────


def test_significant_shift_no_prior_returns_false():
    from core.services.user_temperature_engine import _is_significant_shift
    new = {"valens": 0.5, "arousal": 0.5, "texture": "warm"}
    assert _is_significant_shift(None, new) is False


def test_significant_shift_valens_above_threshold():
    from core.services.user_temperature_engine import _is_significant_shift
    prior = {"struct_valens": 0.0, "struct_arousal": 0.0, "struct_texture": "cool"}
    new = {"valens": 0.5, "arousal": 0.0, "texture": "cool"}
    assert _is_significant_shift(prior, new) is True


def test_significant_shift_texture_change():
    from core.services.user_temperature_engine import _is_significant_shift
    prior = {"struct_valens": 0.1, "struct_arousal": 0.1, "struct_texture": "cool"}
    new = {"valens": 0.1, "arousal": 0.1, "texture": "warm"}
    assert _is_significant_shift(prior, new) is True


def test_significant_shift_below_threshold():
    from core.services.user_temperature_engine import _is_significant_shift
    prior = {"struct_valens": 0.1, "struct_arousal": 0.1, "struct_texture": "cool"}
    new = {"valens": 0.3, "arousal": 0.2, "texture": "cool"}
    assert _is_significant_shift(prior, new) is False


# ── Public read ────────────────────────────────────────────────────────


def test_get_active_field_returns_none_when_disabled(fresh_db, monkeypatch):
    from core.runtime.db_user_temperature import upsert_active_field
    from core.services.user_temperature_engine import get_active_field

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

    class _FakeSettings:
        user_temperature_enabled = False

    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )

    assert get_active_field(workspace_id="default") is None


def test_get_active_field_returns_data_when_enabled(fresh_db, monkeypatch):
    from core.runtime.db_user_temperature import upsert_active_field
    from core.services.user_temperature_engine import get_active_field

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

    class _FakeSettings:
        user_temperature_enabled = True

    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )

    field = get_active_field(workspace_id="default")
    assert field is not None
    assert field["field_valens"] == 0.3
    assert field["field_texture"] == "warm"


# ── Heartbeat formatter ────────────────────────────────────────────────


def test_heartbeat_formatter_returns_empty_when_no_field(fresh_db, monkeypatch):
    class _FakeSettings:
        user_temperature_enabled = True
    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )
    from core.services.user_temperature_engine import format_temperature_field_for_heartbeat
    assert format_temperature_field_for_heartbeat(workspace_id="default") == ""


def test_heartbeat_formatter_skips_low_intensity(fresh_db, monkeypatch):
    from core.runtime.db_user_temperature import upsert_active_field
    from core.services.user_temperature_engine import format_temperature_field_for_heartbeat

    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.05, "arousal": 0.05, "texture": "cool", "confidence": 0.05},
        struct_signals={},
        llm=None,
        combined={
            "field_valens": 0.05, "field_arousal": 0.05, "field_texture": "cool",
            "field_intensity": 0.10, "field_conflict": False,
        },
        baseline={"message_count": 50, "built_at": "now", "ready": True},
    )

    class _FakeSettings:
        user_temperature_enabled = True
    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )

    assert format_temperature_field_for_heartbeat(workspace_id="default") == ""


def test_heartbeat_formatter_renders_active_field(fresh_db, monkeypatch):
    from core.runtime.db_user_temperature import upsert_active_field
    from core.services.user_temperature_engine import format_temperature_field_for_heartbeat

    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.4, "arousal": 0.5, "texture": "warm", "confidence": 0.6},
        struct_signals={},
        llm={"valens": 0.4, "arousal": 0.5, "texture": "warm",
             "confidence": 0.7, "rationale": "Bjørn er engageret"},
        combined={
            "field_valens": 0.4, "field_arousal": 0.5, "field_texture": "warm",
            "field_intensity": 0.9, "field_conflict": False,
        },
        baseline={"message_count": 50, "built_at": "now", "ready": True},
    )

    class _FakeSettings:
        user_temperature_enabled = True
    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )

    out = format_temperature_field_for_heartbeat(workspace_id="default")
    assert "user_temperature_field" in out
    assert "warm" in out
    assert "engageret" in out


def test_heartbeat_formatter_shows_conflict(fresh_db, monkeypatch):
    from core.runtime.db_user_temperature import upsert_active_field
    from core.services.user_temperature_engine import format_temperature_field_for_heartbeat

    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.3, "arousal": 0.4, "texture": "warm", "confidence": 0.5},
        struct_signals={},
        llm={"valens": -0.5, "arousal": 0.4, "texture": "frustrated",
             "confidence": 0.7, "rationale": "x"},
        combined={
            "field_valens": 0.3, "field_arousal": 0.4, "field_texture": "warm",
            "field_intensity": 0.7, "field_conflict": True,
        },
        baseline={"message_count": 50, "built_at": "now", "ready": True},
    )

    class _FakeSettings:
        user_temperature_enabled = True
    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )

    out = format_temperature_field_for_heartbeat(workspace_id="default")
    assert "field_conflict" in out
    assert "frustrated" in out


# ── Response-style modifiers ────────────────────────────────────────────


def test_response_style_returns_default_when_no_field(fresh_db, monkeypatch):
    class _FakeSettings:
        user_temperature_enabled = True
    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )
    from core.services.user_temperature_engine import get_response_style_modifiers
    mods = get_response_style_modifiers(workspace_id="default")
    assert mods == {
        "preferred_length": "normal",
        "warmth": "neutral",
        "pace": "normal",
    }


def test_response_style_tender_field_yields_short_gentle_patient(fresh_db, monkeypatch):
    from core.runtime.db_user_temperature import upsert_active_field
    from core.services.user_temperature_engine import get_response_style_modifiers

    upsert_active_field(
        workspace_id="default",
        struct={"valens": -0.4, "arousal": -0.2, "texture": "tender", "confidence": 0.6},
        struct_signals={},
        llm=None,
        combined={
            "field_valens": -0.4, "field_arousal": -0.2, "field_texture": "tender",
            "field_intensity": 0.6, "field_conflict": False,
        },
        baseline={"message_count": 50, "built_at": "now", "ready": True},
    )

    class _FakeSettings:
        user_temperature_enabled = True
    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )

    mods = get_response_style_modifiers(workspace_id="default")
    assert mods["preferred_length"] == "short"
    assert mods["warmth"] == "gentle"
    assert mods["pace"] == "patient"


def test_response_style_playful_field_yields_warm_quick(fresh_db, monkeypatch):
    from core.runtime.db_user_temperature import upsert_active_field
    from core.services.user_temperature_engine import get_response_style_modifiers

    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.6, "arousal": 0.6, "texture": "playful", "confidence": 0.7},
        struct_signals={},
        llm=None,
        combined={
            "field_valens": 0.6, "field_arousal": 0.6, "field_texture": "playful",
            "field_intensity": 0.9, "field_conflict": False,
        },
        baseline={"message_count": 50, "built_at": "now", "ready": True},
    )

    class _FakeSettings:
        user_temperature_enabled = True
    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )

    mods = get_response_style_modifiers(workspace_id="default")
    assert mods["warmth"] == "warm"
    assert mods["pace"] == "quick"


def test_response_style_low_intensity_returns_default(fresh_db, monkeypatch):
    from core.runtime.db_user_temperature import upsert_active_field
    from core.services.user_temperature_engine import get_response_style_modifiers

    upsert_active_field(
        workspace_id="default",
        struct={"valens": 0.05, "arousal": 0.05, "texture": "cool", "confidence": 0.05},
        struct_signals={},
        llm=None,
        combined={
            "field_valens": 0.05, "field_arousal": 0.05, "field_texture": "cool",
            "field_intensity": 0.1, "field_conflict": False,
        },
        baseline={"message_count": 50, "built_at": "now", "ready": True},
    )

    class _FakeSettings:
        user_temperature_enabled = True
    monkeypatch.setattr(
        "core.services.user_temperature_engine.load_settings",
        lambda: _FakeSettings(),
    )

    mods = get_response_style_modifiers(workspace_id="default")
    assert mods["warmth"] == "neutral"
    assert mods["pace"] == "normal"


# ── workspace-afgrænsning (lækket lukket 26/9-2026) ────────────────────
#
# Motoren læste `chat_messages` på tværs af ALLE brugeres samtaler: fire
# queries uden `workspace_name`-filter. Corpus-query'en sendte dem til
# deepseek under overskriften «Bjørns sidste 24 timer» — så Michelle,
# Mikkel og Lottes beskeder gik ud af huset som om de var Bjørns.
#
# Vagterne pinner både STRUKTUREN (ingen query uden filter, også fremtidige)
# og ADFÆRDEN (A ser ikke B), plus fail-closed.


def _indsæt(db_path, *, workspace, role, content, created_at, i):
    import sqlite3
    with sqlite3.connect(db_path) as c:
        c.execute(
            "INSERT INTO chat_messages "
            "(message_id, session_id, role, content, created_at, user_id, workspace_name) "
            "VALUES (?,?,?,?,?,?,?)",
            (f"m{i}", "s1", role, content, created_at, workspace, workspace),
        )
        c.commit()


def test_ingen_query_uden_workspace_filter():
    """Strukturel vagt: enhver `FROM chat_messages` skal bære workspace_name.

    Uden den kan en fremtidig tilføjelse gentage lækket uden at nogen test
    fanger det — præcis fejlen fra 26/9.
    """
    import pathlib as _pl
    import re as _re
    src = _pl.Path("core/services/user_temperature_engine.py").read_text(encoding="utf-8")
    ramte = 0
    for m in _re.finditer(r"FROM chat_messages", src):
        ramte += 1
        blok = src[m.start(): m.start() + 260]
        assert "workspace_name" in blok, (
            f"chat_messages-query uden workspace_name-filter ved tegn "
            f"{m.start()}: {blok[:120]!r}"
        )
    assert ramte == 4, f"forventede 4 queries, fandt {ramte} — opdatér vagten"


def test_baseline_ser_kun_egen_workspace(fresh_db):
    """Baselinen ser 30 dage tilbage, så rækkerne skal stemples RELATIVT.

    Fundet 26/9-2026 ved at køre hele suiten under `faketime '+30 days'`:
    med faste stempler (`2026-09-26T10:0i:00Z`) falder rækkerne ud af
    `days=30`-vinduet en måned efter at vagten blev skrevet, og så bliver
    den rød uden at noget er i stykker. Præcis samme fælde som
    `test_decision_evidence.test_fremmed_workspace_laekker_ikke_ind`, der
    var rød allerede en time efter.

    En vagt der fejler af sig selv er værre end ingen vagt: den lærer folk
    at se bort fra suiten, og næste gang filteret FAKTISK knækker, ligner
    det bare den røde vi allerede kender.
    """
    from datetime import UTC, datetime, timedelta

    from core.services.user_temperature_engine import _compute_baseline

    def _for(minutter: int) -> str:
        return (datetime.now(UTC) - timedelta(minutes=minutter)).isoformat()

    for i in range(3):
        _indsæt(fresh_db, workspace="bjorn", role="user",
                content="x" * 20, created_at=_for(60 - i), i=i)
    for i in range(2):
        _indsæt(fresh_db, workspace="michelle", role="user",
                content="y" * 20, created_at=_for(30 - i), i=10 + i)

    assert _compute_baseline(days=30, workspace="bjorn")["message_count"] == 3, (
        "baselinen må ikke se Michelles beskeder"
    )
    assert _compute_baseline(days=30, workspace="michelle")["message_count"] == 2


def test_burst_taeller_kun_egen_workspace(fresh_db):
    from core.services.user_temperature_engine import _burst_density
    for i in range(2):
        _indsæt(fresh_db, workspace="bjorn", role="user",
                content="a", created_at=f"2026-09-26T10:00:0{i}Z", i=i)
    for i in range(3):
        _indsæt(fresh_db, workspace="michelle", role="user",
                content="b", created_at=f"2026-09-26T10:00:0{i}Z", i=10 + i)

    d = _burst_density("2026-09-26T10:00:05Z", workspace="bjorn")
    assert d == pytest.approx(2 / 5, abs=0.01), "må ikke tælle Michelles burst med"


def test_delay_ser_kun_egen_workspace(fresh_db):
    from core.services.user_temperature_engine import _delay_since_last_jarvis
    _indsæt(fresh_db, workspace="michelle", role="assistant",
            content="hej", created_at="2026-09-26T09:59:50Z", i=99)
    assert _delay_since_last_jarvis("2026-09-26T10:00:00Z", workspace="bjorn") is None


def test_fail_closed_uden_workspace(fresh_db):
    """Kan workspace ikke bestemmes, hentes INTET — aldrig 'alt'."""
    from core.services.user_temperature_engine import (
        _burst_density, _compute_baseline, _delay_since_last_jarvis,
    )
    _indsæt(fresh_db, workspace="bjorn", role="user",
            content="z" * 20, created_at="2026-09-26T10:00:00Z", i=1)

    ud = _compute_baseline(days=30, workspace="")
    assert ud["ready"] is False
    # `message_count` er den skarpe del: `ready=False` alene kan også komme af
    # «for få rækker», så den skelner ikke «intet hentet» fra «lidt hentet».
    # Målt 26/9: uden denne linje bestod vagten en mutation der faldt tilbage
    # til workspace 'bjorn' — altså præcis den adfærd den skulle forbyde.
    assert ud["message_count"] == 0, "fail-closed: ingen rækker må hentes"
    assert _burst_density("2026-09-26T10:00:00Z", workspace="") == 0.0
    assert _delay_since_last_jarvis("2026-09-26T10:00:00Z", workspace=None) is None
