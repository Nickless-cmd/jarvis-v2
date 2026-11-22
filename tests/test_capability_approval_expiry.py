"""Et capability-kort der aldrig kan eksekveres skal have sin terminale tilstand.

Målt 22/11-2026: 22 poster stod ``pending`` og 8 stod ``approved`` uden at være
kørt, de ældste syv måneder gamle. ``capability_approval_request_is_stale``
nægtede at eksekvere dem hele tiden — men intet skrev tilstanden, så tabellen
løj om sin egen tilstand: «venter på dig» og «glemt» så ens.

Det er samme fejlform som ``db_approval_bridge.expire_stale`` havde: mekanismen
fandtes, den var testet, og den havde nul kaldere. Derfor måler de sidste tests
her KALDET fra daemonen — ikke kun fejningen. En mekanisme uden kalder er ingen
mekanisme.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.runtime import db_capability_approval as CA
from core.services import approval_expiry_daemon as D


def _tid(offset_s: int) -> str:
    """Relativt tidsstempel — en hardkodet dato bliver forældet i morgen."""
    return (datetime.now(UTC) + timedelta(seconds=offset_s)).isoformat()


def _indsæt(
    db,
    request_id: str,
    *,
    requested_at: str,
    status: str = "pending",
    executed: int = 0,
) -> None:
    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO capability_approval_requests (
                request_id, capability_id, execution_mode, requested_at, status,
                executed, scheduled_for_user_id
            ) VALUES (?, 'tool:test', 'workspace-file-write', ?, ?, ?, 'u1')
            """,
            (request_id, requested_at, status, executed),
        )
        conn.commit()


def _status(db, request_id: str) -> str:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT status FROM capability_approval_requests WHERE request_id = ?",
            (request_id,),
        ).fetchone()
    return str(row["status"]) if row else ""


# ── fejningen selv ───────────────────────────────────────────────────────

def test_foraeldet_kort_faar_terminal_tilstand(isolated_runtime) -> None:
    db = isolated_runtime.db
    _indsæt(db, "cap-gammel", requested_at=_tid(-25 * 3600))
    assert CA.expire_stale_capability_approval_requests() == 1
    assert _status(db, "cap-gammel") == "expired"


def test_friskt_kort_roeres_ikke(isolated_runtime) -> None:
    db = isolated_runtime.db
    _indsæt(db, "cap-frisk", requested_at=_tid(-60))
    assert CA.expire_stale_capability_approval_requests() == 0
    assert _status(db, "cap-frisk") == "pending"


def test_igangvaerende_eksekvering_skrives_aldrig_bagud(isolated_runtime) -> None:
    """Samme regel som ``dispatching`` i broen: et ukendt udfald udløber ikke."""
    db = isolated_runtime.db
    _indsæt(db, "cap-koerer", requested_at=_tid(-25 * 3600), status="executing")
    assert CA.expire_stale_capability_approval_requests() == 0
    assert _status(db, "cap-koerer") == "executing"


def test_koert_kort_roeres_ikke(isolated_runtime) -> None:
    db = isolated_runtime.db
    _indsæt(db, "cap-koert", requested_at=_tid(-25 * 3600),
            status="approved", executed=1)
    assert CA.expire_stale_capability_approval_requests() == 0
    assert _status(db, "cap-koert") == "approved"


def test_foraeldet_approved_uden_koersel_udloeber(isolated_runtime) -> None:
    """Godkendt er ikke kørt: de 8 poster fra målingen var `approved` + executed=0."""
    db = isolated_runtime.db
    _indsæt(db, "cap-godkendt", requested_at=_tid(-25 * 3600), status="approved")
    assert CA.expire_stale_capability_approval_requests() == 1
    assert _status(db, "cap-godkendt") == "expired"


# ── koblingen: den fejl der faktisk skete ────────────────────────────────

def test_daemonen_kalder_fejeren(isolated_runtime, monkeypatch) -> None:
    """DEN afgørende prøve: en fejer der aldrig kaldes retter ingenting."""
    D._nulstil_for_tests()
    kaldt: list[bool] = []

    def _falsk(*, now=None, limit: int = 500) -> int:
        kaldt.append(True)
        return 0

    # Patch på MODULET: daemonen importerer navnet inde i kaldet, så det er
    # modul-attributten der slås op — ikke en kopi bundet ved import.
    monkeypatch.setattr(
        "core.runtime.db_capability_approval."
        "expire_stale_capability_approval_requests",
        _falsk,
    )
    D.tick_approval_expiry_daemon(now=datetime.now(UTC))
    assert kaldt == [True], "capability-fejeren blev ikke kaldt af daemonen"


def test_daemonen_fejeR_ende_til_ende(isolated_runtime) -> None:
    db = isolated_runtime.db
    _indsæt(db, "cap-e2e", requested_at=_tid(-25 * 3600))
    D._nulstil_for_tests()
    res = D.tick_approval_expiry_daemon(now=datetime.now(UTC))
    assert res["udloebne_capability_kort"] == 1
    assert _status(db, "cap-e2e") == "expired"


def test_doed_fejer_ser_ikke_ud_som_ingenting_at_feje(isolated_runtime, monkeypatch) -> None:
    """«Kunne ikke køre» og «intet at feje» må ikke give samme tal."""
    D._nulstil_for_tests()

    def _braek(*, now=None, limit: int = 500) -> int:
        raise RuntimeError("nede")

    monkeypatch.setattr(
        "core.runtime.db_capability_approval."
        "expire_stale_capability_approval_requests",
        _braek,
    )
    res = D.tick_approval_expiry_daemon(now=datetime.now(UTC))
    assert res["udloebne_capability_kort"] == -1
    # De øvrige fejere skal have kørt — et fælles fejlpunkt ville gøre ét
    # subsystems fejl til det andets.
    assert res.get("fejet") is True
