"""Ingen læser af previews må levere chiffertekst videre.

Målt 25/11-2026: fire læsere hentede `visible_work_notes`/
`visible_work_units`/`visible_runs` med rå SQL og gav `enc:v1:…` videre
til operativ hukommelse, outreach-tekst og genstart-visning. Værnet er
`visible_preview_crypto.laesbaar_preview`: klartekst passerer uændret,
chiffer uden beviselig nøgle bliver `PLADSHOLDER_KRYPTERET`.

Rækkerne i `visible_runs`/`visible_work_units` er krypteret i hvile med
vilje — det er ikke fejlen. Fejlen er en læser der giver chifferen videre
som om den var svaret.

Fixturen bruger RIGTIGE tabeller og en RIGTIG forbindelse: en fake der
returnerer faste dicts kan ikke se at `_owner`-kolonnen overhovedet findes,
og ville bestå selv om join'et var forkert.
"""
from __future__ import annotations

import sqlite3

from core.services.visible_preview_crypto import PLADSHOLDER_KRYPTERET

CHIFFER = "enc:v1:" + "A" * 80
KLAR = "et helt almindeligt svar"


class _FakeConn:
    """Kun til læsere der tager en tuple-række (restart_self)."""

    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, *a, **k):
        rows = self._rows

        class _R:
            def fetchall(_s):
                return rows

        return _R()


def _visible_db(tmp_path, *, preview: str = CHIFFER, owner: str | None = "u-medlem"):
    sti = tmp_path / "vis.db"
    conn = sqlite3.connect(sti)
    conn.execute(
        "CREATE TABLE visible_runs (id INTEGER PRIMARY KEY, run_id TEXT, "
        "user_id TEXT NOT NULL DEFAULT '')"
    )
    conn.execute(
        "CREATE TABLE visible_work_notes (id INTEGER PRIMARY KEY, note_id TEXT, "
        "work_id TEXT, run_id TEXT, status TEXT, lane TEXT, provider TEXT, model TEXT, "
        "user_message_preview TEXT, capability_id TEXT, work_preview TEXT, "
        "projection_source TEXT, created_at TEXT, finished_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE visible_work_units (id INTEGER PRIMARY KEY, work_id TEXT, "
        "run_id TEXT, status TEXT, lane TEXT, provider TEXT, model TEXT, started_at TEXT, "
        "finished_at TEXT, user_message_preview TEXT, capability_id TEXT, work_preview TEXT)"
    )
    if owner is not None:
        conn.execute("INSERT INTO visible_runs (run_id, user_id) VALUES ('r1', ?)", (owner,))
    conn.execute(
        "INSERT INTO visible_work_notes (note_id, work_id, run_id, status, lane, provider, "
        "model, user_message_preview, capability_id, work_preview, projection_source, "
        "created_at, finished_at) VALUES ('n1','w1','r1','completed','visible','p','m',?,'',?,"
        "'x','','')",
        (preview, preview),
    )
    conn.execute(
        "INSERT INTO visible_work_units (work_id, run_id, status, lane, provider, model, "
        "started_at, finished_at, user_message_preview, capability_id, work_preview) "
        "VALUES ('w1','r1','completed','visible','p','m','','',?,'',?)",
        (preview, preview),
    )
    conn.commit()
    conn.close()
    return sti


def _connect_til(sti):
    def _c():
        conn = sqlite3.connect(sti)
        conn.row_factory = sqlite3.Row
        return conn

    return _c


def test_work_notes_leverer_ikke_chiffer(monkeypatch, tmp_path):
    import core.runtime.db_visible as dbv

    monkeypatch.setattr(dbv, "connect", _connect_til(_visible_db(tmp_path)))
    note = dbv.recent_visible_work_notes(limit=1)[0]
    assert note["work_preview"] == PLADSHOLDER_KRYPTERET
    assert note["user_message_preview"] == PLADSHOLDER_KRYPTERET
    assert "enc:" not in str(note)


def test_work_units_leverer_ikke_chiffer(monkeypatch, tmp_path):
    import core.runtime.db_visible as dbv

    monkeypatch.setattr(dbv, "connect", _connect_til(_visible_db(tmp_path)))
    unit = dbv.recent_visible_work_units(limit=1)[0]
    assert unit["work_preview"] == PLADSHOLDER_KRYPTERET
    assert unit["user_message_preview"] == PLADSHOLDER_KRYPTERET
    assert "enc:" not in str(unit)


def test_uden_ejer_giver_pladsholder_ikke_chiffer(monkeypatch, tmp_path):
    """Run'en findes ikke i visible_runs → ingen nøgle → pladsholder."""
    import core.runtime.db_visible as dbv

    monkeypatch.setattr(dbv, "connect", _connect_til(_visible_db(tmp_path, owner=None)))
    unit = dbv.recent_visible_work_units(limit=1)[0]
    assert unit["work_preview"] == PLADSHOLDER_KRYPTERET


def test_klartekst_passerer_uaendret(monkeypatch, tmp_path):
    """Værnet må ikke sløre et svar der aldrig var krypteret."""
    import core.runtime.db_visible as dbv

    monkeypatch.setattr(dbv, "connect", _connect_til(_visible_db(tmp_path, preview=KLAR)))
    unit = dbv.recent_visible_work_units(limit=1)[0]
    assert unit["work_preview"] == KLAR
    assert unit["user_message_preview"] == KLAR


def _work_units_db(tmp_path):
    sti = tmp_path / "rt.db"
    conn = sqlite3.connect(sti)
    conn.execute(
        "CREATE TABLE visible_work_units (id INTEGER PRIMARY KEY, "
        "user_message_preview TEXT, finished_at TEXT, capability_id TEXT)"
    )
    conn.execute(
        "INSERT INTO visible_work_units "
        "(user_message_preview, finished_at, capability_id) VALUES (?,?,?)",
        (CHIFFER, "2026-11-25T00:00:00+00:00", "webchat"),
    )
    conn.commit()
    conn.close()
    return sti


def test_outreach_preview_er_ikke_chiffer(monkeypatch, tmp_path):
    from core.services import outreach_composer as oc

    monkeypatch.setattr(oc, "_runtime_db_path", lambda: _work_units_db(tmp_path))
    ud = oc._last_user_message_context()
    assert ud["preview"] == PLADSHOLDER_KRYPTERET
    assert "enc:" not in str(ud)


def test_longing_emne_er_ikke_chiffer(monkeypatch, tmp_path):
    from core.services import longing_signal_daemon as ls

    monkeypatch.setattr(ls, "_runtime_db_path", lambda: _work_units_db(tmp_path))
    assert ls._last_user_topic() == PLADSHOLDER_KRYPTERET


def test_restart_self_visning_er_ikke_chiffer(monkeypatch):
    import core.runtime.db as db_mod
    from core.tools import restart_self_tools as rst

    monkeypatch.setattr(db_mod, "connect", lambda: _FakeConn([("r1", CHIFFER)]))
    monkeypatch.setattr(
        "core.services.visible_runs.is_visible_run_alive", lambda _rid: True)
    ud = rst._aktive_koersler(5)
    assert ud and ud[0]["preview"] == PLADSHOLDER_KRYPTERET
    assert "enc:" not in str(ud)


# --- relation_dynamics: profilen beskrev et blandet publikum som én relation ---
#
# Målt 25/11-2026: `_recent_runs()` kaldte `recent_visible_runs(limit=500)` UDEN
# `user_id`. Den returnerede derfor hele basen, hvoraf 30 rækker var medlems-
# kørsler hvis preview kommer tilbage som `PLADSHOLDER_KRYPTERET`. Pladsholderen
# er ~55 tegn og blev (a) talt med i længdestatistikken som et kort svar og
# (b) valgt som «nyeste kørsel» i stemnings-udledningen. Profilen sagde altså
# noget om ejerens relation ud fra medlemmernes kørsler — uden at nogen havde
# læst et ord af deres indhold.


def test_relation_dynamics_henter_kun_ejerens_koersler(monkeypatch):
    import core.runtime.db as db_mod
    from core.services import relation_dynamics as rd

    kaldt: dict = {}

    def _fake_recent(limit: int = 5, *, user_id=None, **kw):
        kaldt["user_id"] = user_id
        return []

    monkeypatch.setattr(db_mod, "recent_visible_runs", _fake_recent)
    monkeypatch.setattr(
        "core.identity.owner_resolver.owner_user_id", lambda: "u-ejer")
    rd._recent_runs()
    assert kaldt["user_id"] == "u-ejer", (
        "relation_dynamics hentede kørsler uden user_id — så tælles andre "
        f"brugeres kørsler med i ejerens relationsprofil (fik: {kaldt['user_id']!r})"
    )


def test_stemning_udledes_ikke_af_pladsholder():
    from datetime import UTC, datetime, timedelta

    from core.services.relation_dynamics import _vibe_from_recent

    nu = datetime.now(UTC)
    runs = [
        # Nyeste kørsel er en medlems-kørsel: indholdet kan ikke læses.
        {"text_preview": PLADSHOLDER_KRYPTERET, "_parsed_at": nu},
        # Ejerens egen, fem minutter ældre — den er den faktiske stemme.
        {"text_preview": "det var dejligt, tak for hjælpen", "_parsed_at": nu - timedelta(minutes=5)},
    ]
    assert _vibe_from_recent(runs) == "warm", (
        "stemningen blev udledt af den nyeste kørsel uanset om dens svar kunne "
        "læses — en pladsholder er ikke en stemme"
    )


def test_stemning_er_ukendt_naar_intet_kan_laeses():
    from datetime import UTC, datetime

    from core.services.relation_dynamics import _vibe_from_recent

    nu = datetime.now(UTC)
    runs = [{"text_preview": PLADSHOLDER_KRYPTERET, "_parsed_at": nu}]
    assert _vibe_from_recent(runs) is None, (
        "en pladsholder på 55 tegn blev klassificeret som «engaged» — den er "
        "hverken kort eller lang, den er ukendt"
    )


def test_laengdestatistik_springer_pladsholder_over():
    from core.services.relation_dynamics import _message_length_stats

    svar = "x" * 200
    runs = [
        {"text_preview": svar},
        {"text_preview": PLADSHOLDER_KRYPTERET},
        {"text_preview": PLADSHOLDER_KRYPTERET},
    ]
    stats = _message_length_stats(runs)
    assert stats["avg_preview_length"] == 200.0, (
        "pladsholdere blev talt med som korte svar og trak gennemsnittet ned "
        f"(fik {stats['avg_preview_length']})"
    )

