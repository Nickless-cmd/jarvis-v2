"""Tests for peer_practice_runner — mood-interpolation + persistens + error-handling."""
from __future__ import annotations
from datetime import UTC, datetime

import pytest


@pytest.fixture
def clean_db(tmp_path, monkeypatch):
    """Isoleret DB med peer_id schema. Patcher BÅDE db + db_core (post-Phase 0)."""
    db_path = tmp_path / "state" / "jarvis.db"
    db_path.parent.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path))
    import core.runtime.db as db
    import core.runtime.db_core as db_core
    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(db_core, "DB_PATH", db_path)
    # Reset schema-init flag og once-cache
    import core.services.interlanguage_practice as ilp
    ilp._SCHEMA_INITIALIZED = False
    from core.runtime.db_core import invalidate_ensure_once_cache
    invalidate_ensure_once_cache()
    return db_path


def test_runner_persists_with_peer_id(clean_db, monkeypatch):
    """Runner skal kalde adapter og persistere med peer_id."""
    # Patch adapter til fast respons
    import scripts.peer_models as pm
    monkeypatch.setattr(pm, "generate", lambda prompt, peer_id: "test → expression")

    from scripts import peer_practice_runner as runner
    result = runner.run_one_tick(
        peer_id="claude",
        mood_trace=[(datetime.now(UTC).isoformat(), {"curiosity": 0.5, "confidence": 0.5, "fatigue": 0.3, "frustration": 0.2})],
    )
    assert result == "test → expression"
    from core.runtime.db import connect
    with connect() as conn:
        rows = conn.execute(
            "SELECT expression_text, peer_id FROM interlanguage_practice WHERE peer_id='claude'"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["expression_text"] == "test → expression"


def test_runner_handles_adapter_error_gracefully(clean_db, monkeypatch):
    """Hvis adapter raiser, må vi ikke crashe — log og fortsæt."""
    # Forced schema-init så tabellen findes (selv ved 0 rows)
    from core.services.interlanguage_practice import ensure_schema
    ensure_schema()

    import scripts.peer_models as pm
    def _boom(prompt, peer_id):
        raise RuntimeError("API down")
    monkeypatch.setattr(pm, "generate", _boom)

    from scripts import peer_practice_runner as runner
    # Skal IKKE raise
    result = runner.run_one_tick(
        peer_id="claude",
        mood_trace=[(datetime.now(UTC).isoformat(), {"curiosity": 0.5, "confidence": 0.5, "fatigue": 0.3, "frustration": 0.2})],
    )
    assert result is None
    from core.runtime.db import connect
    with connect() as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM interlanguage_practice WHERE peer_id='claude'").fetchone()[0]
    assert cnt == 0  # ingen persistens ved fejl


def test_runner_skips_empty_response(clean_db, monkeypatch):
    """Tom/kort response må ikke persisteres."""
    import scripts.peer_models as pm
    monkeypatch.setattr(pm, "generate", lambda prompt, peer_id: "")

    from scripts import peer_practice_runner as runner
    result = runner.run_one_tick(
        peer_id="claude",
        mood_trace=[(datetime.now(UTC).isoformat(), {"curiosity": 0.5, "confidence": 0.5, "fatigue": 0.3, "frustration": 0.2})],
    )
    assert result is None


def test_build_prompt_with_seed(clean_db):
    """Seed expressions inkluderes i prompt."""
    from scripts.peer_practice_runner import _build_prompt
    mood = {"curiosity": 0.7, "confidence": 0.6, "fatigue": 0.2, "frustration": 0.1}
    prompt = _build_prompt(mood, seed_expressions=["foo → bar", "baz ↔ qux"])
    assert "foo → bar" in prompt
    assert "baz ↔ qux" in prompt
    # Mood-værdier i prompt
    assert "0.70" in prompt or "curiosity=0.70" in prompt


def test_build_prompt_without_seed(clean_db):
    """Uden seed: prompt inkluderer protokol + mood men ingen seed-section."""
    from scripts.peer_practice_runner import _build_prompt
    mood = {"curiosity": 0.5, "confidence": 0.5, "fatigue": 0.3, "frustration": 0.2}
    prompt = _build_prompt(mood, seed_expressions=None)
    # Protokol skal være der
    assert "→" in prompt
    assert "nysgerrighed" in prompt or "curiosity" in prompt
    # Ingen seed-fortsætter sektion
    assert "seneste expressions" not in prompt.lower() or "fortsætter" not in prompt.lower()
