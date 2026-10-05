"""Tests for D1 — Selective Consolidation Daemon.

Tests use isolated DB and sensory tables so they never touch real data.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest


@pytest.fixture
def isolated_db(monkeypatch, tmp_path):
    """Point DB_PATH at a clean temp file."""
    from core.runtime import db_core
    db_file = tmp_path / "test_consolidation.db"
    monkeypatch.setattr(db_core, "DB_PATH", db_file)
    from core.runtime.db_core import invalidate_ensure_once_cache
    invalidate_ensure_once_cache()
    # Throttle-tilstanden persisteres nu til state/ (fix 5/10-2026), saa testen
    # skal ogsaa isolere DEN. Uden dette skriver testen til den aegte
    # state-mappe, og en tidligere tests koersel faar naeste test til at svare
    # cadence_not_reached — praecis den fejl testen selv blev ramt af.
    from core.runtime import state_store
    state_dir = tmp_path / "state"
    state_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(state_store, "_STATE_DIR", state_dir)
    return db_file


def _insert_sensory(conn, content: str, mood_tone: str | None = None, days_ago: int = 0):
    """Insert a sensory memory row directly."""
    from core.runtime.db_sensory import _ensure_sensory_memories_table, _scope
    _ensure_sensory_memories_table(conn)
    ts = datetime.now(UTC).isoformat()
    if days_ago > 0:
        # For testing with "today" timestamps
        pass
    # Per-user scope (#154): count_sensory_memories() filters by scope_uid(),
    # so rows must carry the scoped user_id or they are invisible to the count.
    conn.execute(
        "INSERT INTO sensory_memories (id, timestamp, modality, content, mood_tone, metadata_json, user_id) "
        "VALUES (?, ?, ?, ?, ?, '{}', ?)",
        (uuid4().hex, ts, "visual", content, mood_tone, _scope()),
    )
    conn.commit()


def _insert_private_record(conn, summary: str, detail: str = "", salience: float = 1.0,
                           days_ago: int = 0):
    """Insert a private brain record directly."""
    from core.runtime.db import _ensure_private_brain_records_table
    _ensure_private_brain_records_table(conn)
    now = datetime.now(UTC)
    ts = now.isoformat()
    record_id = uuid4().hex
    conn.execute(
        "INSERT INTO private_brain_records "
        "(record_id, record_type, layer, summary, detail, salience, status, "
        "created_at, updated_at) "
        "VALUES (?, 'reflection', 'private_brain', ?, ?, ?, 'active', ?, ?)",
        (record_id, summary, detail, salience, ts, ts),
    )
    conn.commit()
    return record_id


# ── længde er ikke et signal ─────────────────────────────────────────


def test_sensory_layer_has_no_scorer():
    """Vaern: genindfoeres en scorer for sensory, fejler denne.

    Maalt 5/10-2026: `_score_sensory` gav `len/500` + mood-bonus. Median-
    laengden er IDENTISK for aegte indtryk og prompt-ekkoer (301 tegn for
    begge), saa den skelnede ikke — men den spredte scorerne, og det var
    nok til at udpege 1.362 af 2.725 aegte poster som «bund-50%».
    """
    import core.services.selective_consolidation_daemon as mod

    assert not hasattr(mod, "_score_sensory")
    assert not hasattr(mod, "_MAX_CONTENT_FACTOR")
    assert not hasattr(mod, "_MIN_CONTENT_LENGTH")


def test_no_scorer_reads_content_length():
    """Vaern: en scorer maa ikke laese indhold eller laengde. Det var fejlen.

    Testen laeser KILDEKODEN, ikke et resultat. En scorer der genindfoerer
    `len(content)` som led slipper ellers igennem alle andre tests, fordi
    de maaler rangering — ikke hvad rangeringen bygger paa.
    """
    import inspect

    import core.services.selective_consolidation_daemon as mod

    for navn in ("_score_brain", "_score_private"):
        src = inspect.getsource(getattr(mod, navn))
        assert "len(" not in src, f"{navn} laeser laengde igen"
        for felt in ("content", "detail", "summary"):
            assert f'"{felt}"' not in src, f"{navn} laeser {felt} — kun salience maa rangere"


# ── _score_private ────────────────────────────────────────────────────


def test_score_private_is_salience_only():
    """Scoren ER salience — hverken mere eller mindre.

    Foer gav den `salience + len/500`. Testen laaser at et langt indhold
    med lav salience IKKE kan overhale et kort med hoej: laengde maa ikke
    flytte tallet.
    """
    from core.services.selective_consolidation_daemon import _score_private

    assert _score_private({"detail": "x" * 5000, "salience": 0.3}) == 0.3
    assert _score_private({"detail": "kort", "salience": 0.9}) == 0.9
    assert _score_private({"salience": 0.5}) == 0.5
    assert _score_private({}) == 0.0


# ── _consolidate_sensory ──────────────────────────────────────────────


def test_consolidate_sensory_ranks_nothing_and_deletes_nothing(isolated_db):
    """Laget RANGERER ikke laengere — og sletter i hvert fald ikke.

    Maalt 5/10-2026: rangeringen byggede paa content-laengde, og
    median-laengden er IDENTISK for aegte indtryk og prompt-ekkoer (301
    tegn for begge). Den skelnede altsaa ikke, men udpegede 1.362 af 2.725
    aegte poster som «bund-50%».

    Testen beviser at der hverken udpeges eller fjernes noget: 10 ind,
    10 tilbage, intet `would_archive`.
    """
    from core.runtime.db import connect
    from core.services.selective_consolidation_daemon import _consolidate_sensory

    today_start = datetime.now(UTC).strftime("%Y-%m-%dT00:00:00")

    with connect() as conn:
        # 5 korte + 5 lange. Under den gamle scorer var det netop denne
        # forskel der afgjorde hvem der roeg.
        for i in range(5):
            _insert_sensory(conn, "short", mood_tone=None)
        for i in range(5):
            _insert_sensory(conn, "x" * 500, mood_tone="calm")

    result = _consolidate_sensory(today_start)
    assert result["scored"] == 10
    assert result["archived"] == 0  # intet slettet
    assert result["ranked"] is False  # og intet udpeget
    assert "would_archive" not in result

    # Beviset: ALLE 10 er der endnu.
    from core.runtime.db_sensory import count_sensory_memories
    assert count_sensory_memories() == 10


def test_sensory_layer_has_no_delete():
    """Vaern: genindfoeres en DELETE mod sensory_memories, fejler denne test.

    Uden dette vaern kan nogen (ogsaa jeg) genopstaa sletningen uden at nogen
    af de andre tests opdager det — de maaler rangering, ikke datatab.
    """
    import inspect

    import core.services.selective_consolidation_daemon as mod

    src = inspect.getsource(mod)
    assert "DELETE FROM sensory_memories" not in src


def test_consolidate_sensory_no_today_records(isolated_db):
    """No records today = nothing archived."""
    from core.services.selective_consolidation_daemon import _consolidate_sensory
    future_start = "2099-01-01T00:00:00"
    result = _consolidate_sensory(future_start)
    assert result["scored"] == 0
    assert result["archived"] == 0


# ── _consolidate_private ──────────────────────────────────────────────


def test_consolidate_private_archives_bottom_half(isolated_db):
    """With 6 private records, bottom 50% must be archived."""
    from core.runtime.db import connect
    from core.services.selective_consolidation_daemon import _consolidate_private

    today_start = datetime.now(UTC).strftime("%Y-%m-%dT00:00:00")

    with connect() as conn:
        # 3 low-quality (short, low salience)
        for i in range(3):
            _insert_private_record(conn, "short", detail="x", salience=0.1)
        # 3 high-quality (long, high salience)
        for i in range(3):
            _insert_private_record(conn, "Long summary here", detail="x" * 500, salience=0.8)

    result = _consolidate_private(today_start)
    assert result["scored"] == 6
    assert result["archived"] >= 2  # bottom 50% → at least 2 archived (rounding)

    # Verify archived status
    from core.runtime.db import connect
    with connect() as conn:
        from core.runtime.db import _ensure_private_brain_records_table
        _ensure_private_brain_records_table(conn)
        active = conn.execute(
            "SELECT COUNT(*) as n FROM private_brain_records WHERE status = 'active'"
        ).fetchone()
        archived = conn.execute(
            "SELECT COUNT(*) as n FROM private_brain_records WHERE status = 'archived'"
        ).fetchone()
    assert active["n"] <= 4  # at most 4 remain (to-keep = ceil(6*0.5) = 3)
    assert archived["n"] >= 2


def test_no_spread_means_no_archiving(isolated_db):
    """Er alle scorer ens, arkiveres der INTET — ikke en vilkaarlig halvdel.

    Uden dette vaern ville 6 poster med identisk salience blive delt i en
    «top-3» og en «bund-3» uden grundlag. Det er samme fejlform som
    laengde-rangeringen: et tal der ser ud som et kvalitetsvalg uden at
    vaere det.
    """
    from core.runtime.db import connect
    from core.services.selective_consolidation_daemon import _consolidate_private

    today_start = datetime.now(UTC).strftime("%Y-%m-%dT00:00:00")

    with connect() as conn:
        for i in range(6):
            _insert_private_record(conn, f"ens {i}", detail="x" * 100, salience=0.5)

    result = _consolidate_private(today_start)
    assert result["scored"] == 6
    assert result["archived"] == 0
    assert result["skipped"] == "no_score_spread"


# ── tick (integration smoke) ──────────────────────────────────────────


def test_tick_no_data_returns_empty(isolated_db):
    """Running the daemon tick with no data must return empty layers."""
    from core.services.selective_consolidation_daemon import (
        tick_selective_consolidation_daemon,
    )

    # Temporarily lower cadence for testing
    import core.services.selective_consolidation_daemon as scd
    original = scd._last_tick_at
    scd._last_tick_at = None  # force tick to fire

    try:
        result = tick_selective_consolidation_daemon()
        assert result["consolidated"] is True
        for layer in result["layers"]:
            assert "error" not in layer, f"layer error: {layer.get('error')}"
            assert layer.get("scored", 0) == 0
    finally:
        scd._last_tick_at = original


def test_tick_respects_cadence(isolated_db):
    """Running tick twice rapidly must skip second run."""
    import core.services.selective_consolidation_daemon as scd
    from core.services.selective_consolidation_daemon import (
        tick_selective_consolidation_daemon,
    )

    # Cadence state lives in a module-level global, not the DB — reset it so a
    # prior tick (e.g. from another test/file) doesn't make the first run here
    # return cadence_not_reached.
    scd._last_tick_at = None

    first = tick_selective_consolidation_daemon()
    assert first["consolidated"] is True

    second = tick_selective_consolidation_daemon()
    assert second["consolidated"] is False
    assert second["reason"] == "cadence_not_reached"


def test_surface_returns_metadata(isolated_db):
    """build_selective_consolidation_surface must return config."""
    from core.services.selective_consolidation_daemon import (
        build_selective_consolidation_surface,
    )
    surface = build_selective_consolidation_surface()
    assert "cadence_hours" in surface
    assert "top_k_percent" in surface
    assert surface["top_k_percent"] == 50
