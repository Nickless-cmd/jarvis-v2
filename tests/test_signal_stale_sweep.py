"""Stale-mekanismen: fra top-40-scan til SQL-mængdeoperation.

Målt 3/11-2026: ``refresh_statuses`` scannede ``list_fn(limit=refresh_scan_limit)``.
``list_fn`` sorterer ``ORDER BY id DESC`` — de NYESTE rækker, som pr. definition
er friske. Stale-grenen kunne derfor aldrig nås i en tabel større end limit.

Konsekvensen var målt på tværs af 25 signal-tabeller (~180.000 rækker): 24 moduler
satte ``refresh_scan_limit=40`` og havde **nul** stale-rækker, mens
``runtime_metabolism_state_signals`` (34.210 rækker), ``runtime_self_review_signals``
(24.663), ``runtime_self_narrative_continuity_signals`` (24.649) og
``runtime_release_marker_signals`` (23.307) hver havde 19.000–28.000 aktive der var
over 30 dage gamle. Mekanismen fandtes, var konfigureret — og nåede aldrig sit mål.

Testene her kalder den ÆGTE ``refresh_statuses`` mod en rigtig SQLite-tabel. Ingen
mock af DB-laget: en fake-forbindelse der returnerer samme rækker uanset SQL kan
pr. konstruktion ikke se forskel på en top-40-scan og en mængdeoperation.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from core.services import signal_tracking_framework as stf

TABLE = "runtime_test_sweep_signals"

_SCHEMA = f"""
CREATE TABLE {TABLE} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT NOT NULL,
    signal_type TEXT NOT NULL DEFAULT '',
    canonical_key TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    title TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    rationale TEXT NOT NULL DEFAULT '',
    source_kind TEXT NOT NULL DEFAULT '',
    confidence TEXT NOT NULL DEFAULT 'low',
    evidence_summary TEXT NOT NULL DEFAULT '',
    support_summary TEXT NOT NULL DEFAULT '',
    status_reason TEXT NOT NULL DEFAULT '',
    run_id TEXT NOT NULL DEFAULT '',
    session_id TEXT NOT NULL DEFAULT '',
    support_count INTEGER NOT NULL DEFAULT 1,
    session_count INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT ''
)
"""


def _opsæt_db(tmp_path, monkeypatch, *, gamle: int, friske: int, alder_dage: int = 40) -> None:
    """Rigtig DB med ``gamle`` forældede rækker FØRST og ``friske`` bagefter.

    Rækkefølgen er pointen: ``list_fn`` er ``ORDER BY id DESC``, så de friske
    ligger i toppen og skubber de gamle ud af ethvert vindue på 40.
    """
    db = tmp_path / "jarvis.db"
    conn = sqlite3.connect(db)
    conn.execute(_SCHEMA)
    nu = datetime.now(UTC)
    gammel = (nu - timedelta(days=alder_dage)).isoformat()
    frisk = nu.isoformat()
    rows = [
        (f"sig-gammel-{i}", "active", gammel, gammel) for i in range(gamle)
    ] + [(f"sig-frisk-{i}", "active", frisk, frisk) for i in range(friske)]
    conn.executemany(
        f"INSERT INTO {TABLE} (signal_id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()

    import core.runtime.db_core as db_core

    monkeypatch.setattr(db_core, "DB_PATH", db)


def _spec(*, list_fn=None, update_status_fn=None, **overrides) -> stf.SignalTrackingSpec:
    """Spec peget på testtabellen.

    ``list_fn`` og ``update_status_fn`` er bevidst inerte som udgangspunkt: hvis
    sweep'en faldt tilbage til scan-formen, ville den markere NUL — så en grøn
    test er samtidig beviset for at SQL-vejen blev brugt.
    """
    kwargs: dict[str, object] = {
        "name": "test-sweep",
        "slug": "test-sweep-signal",
        "list_fn": list_fn if list_fn is not None else (lambda limit=20, status=None: []),
        "upsert_fn": lambda **kw: {},
        "update_status_fn": update_status_fn if update_status_fn is not None else (lambda *a, **kw: None),
        "extract_fn": lambda spec, ctx: [],
    }
    kwargs.update(overrides)
    return stf.SignalTrackingSpec(**kwargs)  # type: ignore[arg-type]


def _status_fordeling(db_path) -> dict[str, int]:
    conn = sqlite3.connect(db_path)
    try:
        return dict(conn.execute(f"SELECT status, count(*) FROM {TABLE} GROUP BY status"))
    finally:
        conn.close()


def _db_sti() -> object:
    import core.runtime.db_core as db_core

    return db_core.DB_PATH


def test_gamle_signaler_uden_for_de_nyeste_40_bliver_markeret_stale(tmp_path, monkeypatch):
    """Kernepåstanden: sweep'en rammer rækker som top-40-scannen aldrig ser."""
    _opsæt_db(tmp_path, monkeypatch, gamle=3000, friske=200)

    resultat = stf.refresh_statuses(_spec(stale_sweep_batch=5000))

    assert resultat["stale_marked"] == 3000
    fordeling = _status_fordeling(_db_sti())
    assert fordeling.get("stale") == 3000
    assert fordeling.get("active") == 200


def test_scan_formen_kan_ikke_se_dem_negativ_tvilling(tmp_path, monkeypatch):
    """Uden denne kunne testen ovenfor bestå af den forkerte grund.

    Viser at den GAMLE form — som stadig bruges af early-retire-modulerne — ikke
    markerer noget som helst på præcis samme data. Det er beviset for at fejlen
    var ægte og ikke en indbildt.
    """
    _opsæt_db(tmp_path, monkeypatch, gamle=3000, friske=200)

    def _list_nyeste(limit: int = 40, status=None):
        conn = sqlite3.connect(_db_sti())
        try:
            cur = conn.execute(
                f"SELECT * FROM {TABLE} ORDER BY id DESC LIMIT ?", (limit,)
            )
            navne = [d[0] for d in cur.description]
            return [dict(zip(navne, r)) for r in cur.fetchall()]
        finally:
            conn.close()

    kaldt: list[str] = []
    resultat = stf._refresh_via_scan(
        _spec(
            list_fn=_list_nyeste,
            update_status_fn=lambda signal_id, **kw: kaldt.append(signal_id) or {"signal_id": signal_id},
            refresh_scan_limit=40,
        )
    )

    assert resultat["stale_marked"] == 0
    assert kaldt == []
    assert _status_fordeling(_db_sti()).get("active") == 3200


def test_friske_signaler_bliver_ikke_markeret(tmp_path, monkeypatch):
    """Grænsen skal ramme de gamle — ikke alt."""
    _opsæt_db(tmp_path, monkeypatch, gamle=100, friske=100, alder_dage=40)

    stf.refresh_statuses(_spec(stale_sweep_batch=5000))

    fordeling = _status_fordeling(_db_sti())
    assert fordeling.get("stale") == 100
    assert fordeling.get("active") == 100


def test_sweep_er_bounded_pr_kald(tmp_path, monkeypatch):
    """Oprydningen er gradvis: ét kald rører højst ``stale_sweep_batch`` rækker."""
    _opsæt_db(tmp_path, monkeypatch, gamle=3000, friske=10)

    foerste = stf.refresh_statuses(_spec(stale_sweep_batch=500))
    assert foerste["stale_marked"] == 500
    assert _status_fordeling(_db_sti()).get("stale") == 500

    andet = stf.refresh_statuses(_spec(stale_sweep_batch=500))
    assert andet["stale_marked"] == 500
    assert _status_fordeling(_db_sti()).get("stale") == 1000


def test_gentagne_kald_toemmer_ikke_tomt_men_naar_alt(tmp_path, monkeypatch):
    """Fremdriften er monoton: gentagne kald når til sidst alle gamle."""
    _opsæt_db(tmp_path, monkeypatch, gamle=1200, friske=5)

    for _ in range(10):
        stf.refresh_statuses(_spec(stale_sweep_batch=500))

    fordeling = _status_fordeling(_db_sti())
    assert fordeling.get("stale") == 1200
    assert fordeling.get("active") == 5


def test_ukendt_tidsformat_bliver_ikke_markeret(tmp_path, monkeypatch):
    """En række vi ikke kan læse tiden på må ikke få en gættet dom.

    ``datetime()`` giver NULL for et ulæseligt tidsstempel; NULL < x er falsk, så
    rækken forbliver urørt. Sikret retning: vi markerer ikke det vi ikke forstår.
    """
    _opsæt_db(tmp_path, monkeypatch, gamle=10, friske=0)
    conn = sqlite3.connect(_db_sti())
    conn.execute(
        f"INSERT INTO {TABLE} (signal_id, status, created_at, updated_at) VALUES (?, 'active', ?, ?)",
        ("sig-uforstaaet", "i gaar klokken tre", "i gaar klokken tre"),
    )
    conn.commit()
    conn.close()

    stf.refresh_statuses(_spec(stale_sweep_batch=5000))

    fordeling = _status_fordeling(_db_sti())
    assert fordeling.get("stale") == 10
    assert fordeling.get("active") == 1


def _opdater_i_db(signal_id, **kw):
    """Ægte status-opdatering mod testtabellen (bruges af early-retire-grenen)."""
    conn = sqlite3.connect(_db_sti())
    try:
        conn.execute(
            f"UPDATE {TABLE} SET status = ?, status_reason = ?, updated_at = ? WHERE signal_id = ?",
            (kw.get("status"), kw.get("status_reason", ""), kw.get("updated_at", ""), signal_id),
        )
        conn.commit()
        row = conn.execute(
            f"SELECT signal_id, signal_type, status, summary FROM {TABLE} WHERE signal_id = ?",
            (signal_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return dict(zip(("signal_id", "signal_type", "status", "summary"), row))


def test_early_retire_praedikat_virker_i_vinduet(tmp_path, monkeypatch):
    """Reflection/dream/goal pensionerer tidligt via et per-item prædikat.

    Rækker i vinduet mellem ``early_retire_days`` og ``stale_after_days`` må ikke
    være usynlige: de læses bounded og prædikatet afgør.
    """
    _opsæt_db(tmp_path, monkeypatch, gamle=100, friske=100, alder_dage=10)
    conn = sqlite3.connect(_db_sti())
    i_vinduet = (datetime.now(UTC) - timedelta(days=5)).isoformat()
    conn.executemany(
        f"INSERT INTO {TABLE} (signal_id, status, created_at, updated_at) VALUES (?, 'active', ?, ?)",
        [(f"sig-vindue-{i}", i_vinduet, i_vinduet) for i in range(100)],
    )
    conn.commit()
    conn.close()

    resultat = stf.refresh_statuses(
        _spec(
            early_retire_days=3,
            early_retire_predicate=lambda item: True,
            update_status_fn=_opdater_i_db,
        )
    )

    assert resultat["stale_marked"] == 200
    fordeling = _status_fordeling(_db_sti())
    assert fordeling.get("stale") == 200
    assert fordeling.get("active") == 100


def test_early_retire_praedikat_falsk_roerer_ikke_vinduet(tmp_path, monkeypatch):
    """Modvægten: uden prædikat-match må vinduet ikke tømmes.

    Uden denne kunne testen ovenfor bestå af den forkerte grund — at alt i
    vinduet altid markeres.
    """
    _opsæt_db(tmp_path, monkeypatch, gamle=100, friske=100, alder_dage=10)
    conn = sqlite3.connect(_db_sti())
    i_vinduet = (datetime.now(UTC) - timedelta(days=5)).isoformat()
    conn.executemany(
        f"INSERT INTO {TABLE} (signal_id, status, created_at, updated_at) VALUES (?, 'active', ?, ?)",
        [(f"sig-vindue-{i}", i_vinduet, i_vinduet) for i in range(100)],
    )
    conn.commit()
    conn.close()

    resultat = stf.refresh_statuses(
        _spec(
            early_retire_days=3,
            early_retire_predicate=lambda item: False,
            update_status_fn=_opdater_i_db,
        )
    )

    assert resultat["stale_marked"] == 100, "kun de 10 dage gamle må rammes"
    fordeling = _status_fordeling(_db_sti())
    assert fordeling.get("stale") == 100
    assert fordeling.get("active") == 200


def test_raekker_yngre_end_early_retire_roeres_ikke(tmp_path, monkeypatch):
    """En række fra i går er ikke pensionsmoden, uanset prædikatet."""
    _opsæt_db(tmp_path, monkeypatch, gamle=0, friske=50, alder_dage=0)

    stf.refresh_statuses(
        _spec(
            early_retire_days=3,
            early_retire_predicate=lambda item: True,
            update_status_fn=_opdater_i_db,
        )
    )

    assert _status_fordeling(_db_sti()).get("active") == 50


def test_sweep_falder_tilbage_naar_tabellen_mangler(tmp_path, monkeypatch):
    """En spec uden tabel må ikke kaste ind i den synlige tur."""
    _opsæt_db(tmp_path, monkeypatch, gamle=10, friske=0)

    spec = stf.SignalTrackingSpec(
        name="findes-ikke",
        slug="findes-ikke-signal",
        list_fn=lambda limit=20, status=None: [],
        upsert_fn=lambda **kw: {},
        update_status_fn=lambda *a, **kw: None,
        extract_fn=lambda spec, ctx: [],
    )

    resultat = stf.refresh_statuses(spec)

    assert resultat == {"stale_marked": 0}
    assert _status_fordeling(_db_sti()).get("active") == 10
