# tests/test_db_runtime_initiatives.py
"""Skrivevejen for godkendelse af livsprojekter (7/11-2026).

## Hvorfor denne fil findes

Målt 7/11-2026: `endorse_long_term_intention` kaldte
`update_runtime_initiative(..., user_approved_at=..., outcome_note=...)` — men
ingen af de to parametre fandtes i signaturen. Hvert godkendelsesforsøg kastede
`TypeError`, og `user_approved_at` var tom i **alle** rækker. Bjørn havde
godkendt de samme tre livsprojekter mange gange uden at noget landede.

Kolonnerne har hele tiden stået i skemaet (`_ensure_runtime_initiatives_table`).
Det var kun skrivevejen der manglede — og ingen test rørte den.

Testen her måler ikke funktionen `endorse`; den måler det lag under den, hvor
fejlen faktisk sad: at `update_runtime_initiative` kan skrive de to felter.
"""

from __future__ import annotations


def _opret(initiative_id: str) -> dict[str, object]:
    from core.runtime import db

    return db.create_runtime_initiative(
        initiative_id=initiative_id,
        initiative_type="long_term_intention",
        focus="Testprojekt",
        why_text="fordi skrivevejen skal maales",
        status="pending",
        detected_at="2026-11-07T00:00:00+00:00",
        next_attempt_at="2026-11-07T00:00:00+00:00",
        updated_at="2026-11-07T00:00:00+00:00",
    )


def test_update_kan_skrive_user_approved_at(isolated_runtime) -> None:
    from core.runtime import db

    iid = "life-test000001"
    _opret(iid)

    opdateret = db.update_runtime_initiative(
        iid,
        user_approved_at="2026-11-07T12:00:00+00:00",
        updated_at="2026-11-07T12:00:00+00:00",
    )

    assert opdateret is not None
    assert str(opdateret.get("user_approved_at") or "") == "2026-11-07T12:00:00+00:00", (
        "user_approved_at kunne ikke skrives — saa fejler hver godkendelse af et "
        "livsprojekt med TypeError, praecis som maalt 7/11-2026"
    )


def test_update_kan_skrive_outcome_note(isolated_runtime) -> None:
    from core.runtime import db

    iid = "life-test000002"
    _opret(iid)

    opdateret = db.update_runtime_initiative(
        iid,
        outcome_note="go fra mennesket",
        updated_at="2026-11-07T12:00:00+00:00",
    )

    assert opdateret is not None
    assert str(opdateret.get("outcome_note") or "") == "go fra mennesket"


def test_update_roerer_ikke_status_naar_den_ikke_er_bedt_om_det(isolated_runtime) -> None:
    """En godkendelse maa ikke lukke projektet — modsat abandon."""
    from core.runtime import db

    iid = "life-test000003"
    _opret(iid)

    opdateret = db.update_runtime_initiative(
        iid,
        user_approved_at="2026-11-07T12:00:00+00:00",
        updated_at="2026-11-07T12:00:00+00:00",
    )

    assert opdateret is not None
    assert str(opdateret.get("status") or "") == "pending"
