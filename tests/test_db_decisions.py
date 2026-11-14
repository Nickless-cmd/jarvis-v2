"""Tests for core.runtime.db_decisions — focus on update_decision.

update_decision semantics (2026-09-07):
- None  → field unchanged
- ""    → field cleared to NULL (rationale/trigger_cue/trigger_name)
- value → field set

Uses a throwaway sqlite DB via monkeypatched connect — never the live DB.
"""
from __future__ import annotations

import sqlite3

import pytest


@pytest.fixture()
def tmp_db(monkeypatch, tmp_path):
    """Point db_decisions.connect at a fresh temp database."""
    from core.runtime import db_decisions as mod

    db_path = tmp_path / "decisions-test.db"
    monkeypatch.setattr(mod, "connect", lambda: _connect_row(str(db_path)))

    # ensure tables once through the module's own code path
    conn = sqlite3.connect(str(db_path))
    mod._ensure_tables(conn)
    conn.close()
    return mod


def _connect_row(db_path):
    """Production connect() sets row_factory=sqlite3.Row — mirror that."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _mk(tmp_db, **over):
    """Create a baseline decision row via the store's create path."""
    params = {
        "directive": "Pause before replying when unsure.",
        "rationale": "Cutting people off costs trust.",
        "trigger_cue": "when a message feels urgent",
        "priority": 60,
    }
    params.update(over)
    return tmp_db.create_decision(**params)


def test_update_directive_and_priority(tmp_db):
    d = _mk(tmp_db)
    did = d["decision_id"]

    u = tmp_db.update_decision(did, directive="New sharper rule.", priority=90)

    assert u["directive"] == "New sharper rule."
    assert u["priority"] == 90
    # untouched fields survive
    assert u["rationale"] == "Cutting people off costs trust."
    assert u["status"] == "active"
    assert u["updated_at"] >= d["updated_at"]


def test_update_clears_optional_fields_with_empty_string(tmp_db):
    d = _mk(tmp_db)
    did = d["decision_id"]

    u = tmp_db.update_decision(did, trigger_cue="", rationale="")

    assert u["trigger_cue"] is None
    assert u["rationale"] is None


def test_update_keeps_field_when_none_passed(tmp_db):
    d = _mk(tmp_db, trigger_cue="when X")
    did = d["decision_id"]

    u = tmp_db.update_decision(did, priority=80)  # trigger_cue not passed

    assert u["trigger_cue"] == "when X"
    assert u["priority"] == 80


def test_update_status(tmp_db):
    d = _mk(tmp_db)
    did = d["decision_id"]

    u = tmp_db.update_decision(did, status="fulfilled")

    assert u["status"] == "fulfilled"


def test_update_rejects_invalid_status(tmp_db):
    d = _mk(tmp_db)
    did = d["decision_id"]

    u = tmp_db.update_decision(did, status="not-a-status")

    assert u is None
    # unchanged in db
    assert tmp_db.get_decision(did)["status"] == "active"


def test_update_unknown_id_returns_none(tmp_db):
    assert tmp_db.update_decision("dec-unknown", directive="x") is None


def test_update_nothing_to_change_returns_row_unchanged(tmp_db):
    d = _mk(tmp_db)
    did = d["decision_id"]

    u = tmp_db.update_decision(did)

    assert u is not None
    assert u["decision_id"] == did
    assert u["directive"] == d["directive"]


# ---------------------------------------------------------------------------
# Det partielle indeks paa `source_record_id` (14/11-2026)
# ---------------------------------------------------------------------------
# Værnet skal staa der hvor raekken bliver til: `create_decision` dedupliker
# paa direktiv-TEKST med et SELECT foer INSERT, saa to samtidige kald med
# samme fund kunne begge indsaette hver sin beslutning. Maalt: to traade,
# samme fund-id -> to beslutninger, hvoraf den ene var foraeldroes.
#
# Indeksen er PARTIEL. Grunden blev foerst skrevet forkert: jeg paastod at en
# fuld unik indeks kun ville tillade ÉN raekke uden `source_record_id`. Det er
# ikke sandt — SQLite behandler NULL som distinkt, saa mange NULL gaar frit
# igennem. Det er den TOMME STRENG den kun tillader én af. Praecis dét er
# grunden: et kald der sender '' frem for NULL ville optage den ene plads og
# derefter afvise enhver senere beslutning uden fund. Testen her værner begge
# halvdele, saa kommentaren ikke kan blive sand igen uden at nogen ser det.


_RAW_TAELLER = iter(range(10_000))


def _indsæt_raw(conn, sr):
    conn.execute(
        "INSERT INTO behavioral_decisions "
        "(decision_id, directive, created_at, updated_at, source_record_id) "
        "VALUES (?,?,?,?,?)",
        (f"dec_raw_{next(_RAW_TAELLER)}", "x", "2026-11-14T00:00:00+00:00",
         "2026-11-14T00:00:00+00:00", sr),
    )


def test_mange_null_kan_indsættes_side_om_side(tmp_db, tmp_path):
    """En fuld unik indeks ville ogsaa tillade dette — saa det er ikke
    grunden til at indeksen er partiel. Men det skal stadig holde: de 397
    beslutninger uden fund i drift er NULL, ikke tomme strenge."""
    conn = _connect_row(str(tmp_path / "decisions-test.db"))
    for _ in range(3):
        _indsæt_raw(conn, None)
    conn.commit()
    n = conn.execute(
        "SELECT COUNT(*) FROM behavioral_decisions WHERE source_record_id IS NULL"
    ).fetchone()[0]
    assert n == 3


def test_tom_streng_optager_ikke_den_eneste_plads(tmp_db, tmp_path):
    """Det er HER det partielle indeks bærer. En fuld unik indeks ville
    afvise den anden tomme streng — og dermed ogsaa enhver senere kalder der
    sender '' i stedet for NULL, med en fejl der intet siger om hvorfor."""
    conn = _connect_row(str(tmp_path / "decisions-test.db"))
    _indsæt_raw(conn, "")
    _indsæt_raw(conn, "")
    conn.commit()
    n = conn.execute(
        "SELECT COUNT(*) FROM behavioral_decisions WHERE source_record_id = ''"
    ).fetchone()[0]
    assert n == 2, f"to tomme strenge skal begge kunne staa der: {n}"


def test_samme_fund_kun_én_beslutning(tmp_db, tmp_path):
    """Og den regel indeksen faktisk findes for: to beslutninger for samme
    fund er en foraeldroes forpligtelse — den overlever uden ejer."""
    conn = _connect_row(str(tmp_path / "decisions-test.db"))
    _indsæt_raw(conn, "fund-samme")
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        _indsæt_raw(conn, "fund-samme")
        conn.commit()
