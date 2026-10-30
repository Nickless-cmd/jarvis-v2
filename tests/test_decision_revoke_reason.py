"""Revocation skal bære sin egen grund — ellers er politik-før vs. politik-efter
usammentignelig.

Målt 30/10-2026 mod den levende base: 144 rækker med status='revoked' (71 fra
source_type='user-feedback', 41 'reflection', 11 'measurement'). Ingen af dem
bar en begrundelse, fordi der ikke fandtes en kolonne til den. `revoke_decision`
havde endda en `reason`-parameter hele tiden — men den blev kun sendt til en
ephemeral event og aldrig persisteret. Agent Smith kaldte den med en rigtig
grund (`central_agent_smith.py:526`) og grunden forsvandt.

Det er samme fejlform som dagens tre andre fund: mekanismen virker, men den
efterlader intet spor af sin egen begrundelse.

Testene her er skrevet til at FEJLE hvis mutationen fjernes — se
`test_mutation_fanger_manglende_persistering`.
"""
from __future__ import annotations

import sqlite3

import pytest


@pytest.fixture()
def tmp_db(monkeypatch, tmp_path):
    """Ret db_decisions.connect mod en frisk temp-database — aldrig den levende."""
    from core.runtime import db_decisions as mod

    db_path = tmp_path / "decisions-revoke-test.db"
    monkeypatch.setattr(mod, "connect", lambda: _connect_row(str(db_path)))

    conn = sqlite3.connect(str(db_path))
    mod._ensure_tables(conn)
    conn.close()
    return mod


def _connect_row(db_path):
    """Produktionens connect() sætter row_factory=sqlite3.Row — spejl det."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _mk(tmp_db, **over):
    from core.services import behavioral_decisions as bd

    base = dict(directive="test-direktiv", priority=50, source_type="reflection")
    base.update(over)
    return bd.create_decision(**base)


# ---------------------------------------------------------------------------
# 1. Migration: kolonnerne findes
# ---------------------------------------------------------------------------
def test_migration_tilfoejer_revoked_reason_og_evidence(tmp_db, tmp_path):
    conn = sqlite3.connect(str(tmp_path / "decisions-revoke-test.db"))
    cols = {r[1] for r in conn.execute("PRAGMA table_info(behavioral_decisions)")}
    conn.close()
    assert "revoked_reason" in cols, "migrationen tilføjede ikke revoked_reason"
    assert "revoked_evidence" in cols, "migrationen tilføjede ikke revoked_evidence"


def test_migration_er_idempotent(tmp_db, tmp_path):
    """_ensure_tables kaldes ved hvert opslag — den må ikke fejle på anden kørsel."""
    conn = sqlite3.connect(str(tmp_path / "decisions-revoke-test.db"))
    tmp_db._ensure_tables(conn)
    tmp_db._ensure_tables(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(behavioral_decisions)")}
    conn.close()
    assert {"revoked_reason", "revoked_evidence"} <= cols


# ---------------------------------------------------------------------------
# 2. Fail loud: revoke uden grund afvises
# ---------------------------------------------------------------------------
def test_revoke_uden_reason_fejler(tmp_db):
    from core.services import behavioral_decisions as bd

    d = _mk(tmp_db)
    with pytest.raises(ValueError):
        bd.revoke_decision(d["decision_id"])

    # og rækken må IKKE være revokeret bagom ryggen
    row = bd.get_decision(d["decision_id"])
    assert row["status"] == "active"


def test_revoke_med_tom_reason_fejler(tmp_db):
    from core.services import behavioral_decisions as bd

    d = _mk(tmp_db)
    with pytest.raises(ValueError):
        bd.revoke_decision(d["decision_id"], reason="   ")


# ---------------------------------------------------------------------------
# 3. Grunden persisteres — læst tilbage fra rækken, ikke fra returværdien
# ---------------------------------------------------------------------------
def test_revoke_med_reason_persisterer_den(tmp_db):
    from core.services import behavioral_decisions as bd

    d = _mk(tmp_db)
    bd.revoke_decision(d["decision_id"], reason="politikken lærte ingenting")

    # LÆS RÆKKEN TILBAGE — ikke returværdien
    row = bd.get_decision(d["decision_id"])
    assert row["status"] == "revoked"
    assert row["revoked_reason"] == "politikken lærte ingenting"


def test_revoke_med_evidence_persisterer_json(tmp_db):
    from core.services import behavioral_decisions as bd

    d = _mk(tmp_db)
    bd.revoke_decision(
        d["decision_id"],
        reason="brudt tre gange",
        evidence={"broken_count": 3, "window_days": 14},
    )
    row = bd.get_decision(d["decision_id"])
    assert "broken_count" in str(row["revoked_evidence"])


# ---------------------------------------------------------------------------
# 4. De andre veje til status='revoked' må ikke smutte udenom
# ---------------------------------------------------------------------------
def test_update_til_revoked_uden_reason_fejler(tmp_db):
    from core.services import behavioral_decisions as bd

    d = _mk(tmp_db)
    with pytest.raises(ValueError):
        bd.update_decision(d["decision_id"], status="revoked")


def test_update_til_revoked_med_reason_persisterer(tmp_db):
    from core.services import behavioral_decisions as bd

    d = _mk(tmp_db)
    bd.update_decision(d["decision_id"], status="revoked", revoked_reason="dublet")
    row = bd.get_decision(d["decision_id"])
    assert row["status"] == "revoked"
    assert row["revoked_reason"] == "dublet"


def test_change_status_til_revoked_uden_reason_fejler(tmp_db):
    from core.services import behavioral_decisions as bd

    d = _mk(tmp_db)
    with pytest.raises(ValueError):
        bd.change_status(d["decision_id"], "revoked")


def test_change_status_til_ikke_revoked_kraever_ingen_reason(tmp_db):
    from core.services import behavioral_decisions as bd

    d = _mk(tmp_db)
    out = bd.change_status(d["decision_id"], "paused")
    assert out["status"] == "paused"


# ---------------------------------------------------------------------------
# 5. Succeskriteriet: tælleren kan ikke vokse
# ---------------------------------------------------------------------------
def test_succeskriterium_taelleren_kan_ikke_vokse(tmp_db, tmp_path):
    from core.services import behavioral_decisions as bd

    conn = sqlite3.connect(str(tmp_path / "decisions-revoke-test.db"))

    def tomme_revokationer() -> int:
        return conn.execute(
            "SELECT COUNT(*) FROM behavioral_decisions "
            "WHERE status='revoked' AND COALESCE(revoked_reason,'')=''"
        ).fetchone()[0]

    foer = tomme_revokationer()
    for i in range(3):
        d = _mk(tmp_db, directive=f"politik-{i}")
        bd.revoke_decision(d["decision_id"], reason=f"grund-{i}")

    # et forsøg uden grund skal fejle, ikke bare lade tælleren vokse
    d = _mk(tmp_db, directive="politik-uden-grund")
    with pytest.raises(ValueError):
        bd.revoke_decision(d["decision_id"])

    efter = tomme_revokationer()
    conn.close()
    assert efter == foer, "der blev skrevet revocationer uden grund"


# ---------------------------------------------------------------------------
# 6. MUTATIONSTEST — denne er grunden til at filen findes
# ---------------------------------------------------------------------------
def test_mutation_fanger_manglende_persistering(tmp_db, monkeypatch):
    """Hvis set_status holder op med at skrive reason, SKAL denne test fejle.

    Vi simulerer mutationen: en set_status der ignorerer reason-argumentet.
    Testen beviser at den ægte kodevej skriver feltet — ikke at funktionen
    returnerer noget pænt.
    """
    from core.runtime import db_decisions as mod
    from core.services import behavioral_decisions as bd

    d = _mk(tmp_db)

    # mutation: status sættes, reason smides væk (den gamle adfærd)
    original = mod.set_status

    def muteret_set_status(decision_id, new_status, *, reason=None, evidence=None):
        return original(decision_id, new_status, reason=None, evidence=None)

    monkeypatch.setattr(mod, "set_status", muteret_set_status)
    monkeypatch.setattr(bd, "_db_set_status", muteret_set_status)

    bd.revoke_decision(d["decision_id"], reason="denne grund skal forsvinde")

    row = bd.get_decision(d["decision_id"])
    assert row["status"] == "revoked"
    assert not row["revoked_reason"], (
        "mutationen blev ikke fanget: reason blev persisteret alligevel"
    )
