from __future__ import annotations

import json

import pytest


def test_fetch_recent_top_motif_empty_when_no_data(monkeypatch):
    """When no recent motif rows exist, return empty.

    SQL-table integration is verified via production smoke probe (Task 7);
    we don't monkeypatch core.runtime.db.connect here because that polluted
    downstream tests using isolated_runtime.
    """
    from core.services.creative_journal_runtime import _fetch_recent_top_motif

    # Patch the connect-import inside the function via the runtime db module.
    # When the SELECT returns no rows, the function returns "".
    import core.runtime.db as runtime_db

    class _FakeConn:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def execute(self, sql, params=None):
            class _Result:
                def fetchone(self_inner):
                    return None
            return _Result()

    monkeypatch.setattr(runtime_db, "connect", lambda: _FakeConn())
    try:
        assert _fetch_recent_top_motif() == ""
    finally:
        # Defensive — ensure no lingering references
        pass


def test_fetch_recent_top_motif_returns_motif_when_row_present(monkeypatch):
    from core.services.creative_journal_runtime import _fetch_recent_top_motif
    import core.runtime.db as runtime_db

    class _Row:
        def __getitem__(self, key):
            assert key == "motif"
            return "clarity"

    class _FakeConn:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def execute(self, sql, params=None):
            class _Result:
                def fetchone(self_inner):
                    return _Row()
            return _Result()

    monkeypatch.setattr(runtime_db, "connect", lambda: _FakeConn())
    assert _fetch_recent_top_motif() == "clarity"


def test_fetch_dominant_taste_empty_when_no_profile(monkeypatch):
    from core.services import creative_journal_runtime as cjr
    import core.runtime.db as runtime_db
    monkeypatch.setattr(runtime_db, "get_latest_cognitive_taste_profile", lambda: None)
    assert cjr._fetch_dominant_taste() == ""


def test_fetch_dominant_taste_gated_on_evidence(monkeypatch):
    from core.services import creative_journal_runtime as cjr
    import core.runtime.db as runtime_db
    monkeypatch.setattr(
        runtime_db, "get_latest_cognitive_taste_profile",
        lambda: {
            "code_taste": json.dumps({"prefers_inline_styles": 0.9}),
            "design_taste": json.dumps({"compact_over_spacious": 0.5}),
            "communication_taste": json.dumps({"concise_over_verbose": 0.5}),
            "evidence_count": 3,
        },
    )
    assert cjr._fetch_dominant_taste() == ""


def test_fetch_dominant_taste_picks_largest_deviation(monkeypatch):
    from core.services import creative_journal_runtime as cjr
    import core.runtime.db as runtime_db
    monkeypatch.setattr(
        runtime_db, "get_latest_cognitive_taste_profile",
        lambda: {
            "code_taste": json.dumps({"prefers_inline_styles": 0.6}),
            "design_taste": json.dumps({"compact_over_spacious": 0.5}),
            "communication_taste": json.dumps({"concise_over_verbose": 0.85}),
            "evidence_count": 12,
        },
    )
    result = cjr._fetch_dominant_taste()
    assert "concise_over_verbose" in result
    assert "0.85" in result


def test_klangbraet_includes_aesthetic_subdict(monkeypatch):
    from core.services.creative_journal_runtime import _fetch_affective_klangbraet

    monkeypatch.setattr(
        "core.services.creative_journal_runtime._fetch_recent_top_motif",
        lambda: "clarity",
    )
    monkeypatch.setattr(
        "core.services.creative_journal_runtime._fetch_dominant_taste",
        lambda: "concise_over_verbose (0.78)",
    )
    out = _fetch_affective_klangbraet()
    assert "aesthetic" in out
    aesthetic = out["aesthetic"]
    assert aesthetic["top_motif"] == "clarity"
    assert aesthetic["dominant_taste"] == "concise_over_verbose (0.78)"


def test_klangbraet_aesthetic_empty_when_no_data(monkeypatch):
    from core.services.creative_journal_runtime import _fetch_affective_klangbraet

    monkeypatch.setattr(
        "core.services.creative_journal_runtime._fetch_recent_top_motif",
        lambda: "",
    )
    monkeypatch.setattr(
        "core.services.creative_journal_runtime._fetch_dominant_taste",
        lambda: "",
    )
    out = _fetch_affective_klangbraet()
    aesthetic = out["aesthetic"]
    assert aesthetic["top_motif"] == ""
    assert aesthetic["dominant_taste"] == ""


def test_build_prompt_renders_aesthetic_section():
    from core.services.creative_journal_runtime import _build_prompt

    klangbraet = {
        "dream_bias": "",
        "user_temperature": "",
        "current_pull": "",
        "finitude": {
            "age": "", "looming_end": "", "last_transition": "",
            "monthly_reflection": "",
        },
        "aesthetic": {
            "top_motif": "clarity",
            "dominant_taste": "concise_over_verbose (0.78)",
        },
    }
    prompt = _build_prompt(
        chronicle_entries=[],
        life_projects=[],
        broken_decisions=[],
        klangbraet=klangbraet,
        voice_anchor="",
    )
    assert "## Æstetik" in prompt
    assert "Seneste motif: clarity" in prompt
    assert "Dominant taste: concise_over_verbose (0.78)" in prompt


def test_build_prompt_aesthetic_fallback_when_all_empty():
    from core.services.creative_journal_runtime import _build_prompt

    klangbraet = {
        "dream_bias": "",
        "user_temperature": "",
        "current_pull": "",
        "finitude": {
            "age": "", "looming_end": "", "last_transition": "",
            "monthly_reflection": "",
        },
        "aesthetic": {"top_motif": "", "dominant_taste": ""},
    }
    prompt = _build_prompt(
        chronicle_entries=[],
        life_projects=[],
        broken_decisions=[],
        klangbraet=klangbraet,
        voice_anchor="",
    )
    assert "## Æstetik" in prompt
    assert "(intet æstetisk signal lige nu)" in prompt


def test_build_prompt_handles_legacy_klangbraet_without_aesthetic_key():
    """Backwards compat: stubs from older tests don't include aesthetic key."""
    from core.services.creative_journal_runtime import _build_prompt

    klangbraet = {
        "dream_bias": "",
        "user_temperature": "",
        "current_pull": "",
        "finitude": {
            "age": "", "looming_end": "", "last_transition": "",
            "monthly_reflection": "",
        },
    }
    prompt = _build_prompt(
        chronicle_entries=[],
        life_projects=[],
        broken_decisions=[],
        klangbraet=klangbraet,
        voice_anchor="",
    )
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_yaml_frontmatter_includes_aesthetic_booleans():
    from core.services.creative_journal_runtime import _format_yaml_frontmatter

    frontmatter = _format_yaml_frontmatter(
        created_at="2026-05-11T22:00:00+00:00",
        chronicle_count=1,
        broken_decisions_count=0,
        life_projects_count=0,
        klangbraet={
            "dream_bias": "",
            "user_temperature": "",
            "current_pull": "",
            "finitude": {
                "age": "24 dage", "looming_end": "",
                "last_transition": "", "monthly_reflection": "",
            },
            "aesthetic": {
                "top_motif": "clarity",
                "dominant_taste": "",
            },
        },
        trigger="heartbeat",
    )
    assert "aesthetic_top_motif: true" in frontmatter
    assert "aesthetic_dominant_taste: false" in frontmatter
