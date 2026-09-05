"""Blindspot-modulet spurgte efter kolonner der ikke findes.

Målt 2026-09-05: `_load_recent_failed_runs()` returnerede 0 mod et krav om
mindst 3 — mens `visible_runs` havde 250 fejlede runs. Forespørgslen valgte
`outcome_summary` og `created_at`, som ikke er kolonner i den tabel. Hvert kald
kastede OperationalError, og `except Exception: return []` slugte den. Derfor
har `cognitive_blind_spots` aldrig haft en eneste række.
"""

from __future__ import annotations

from core.services import self_model_blind_spots as B


def test_forespoergslen_bruger_kolonner_der_findes():
    """Vagt mod at aliasene falder tilbage til de opdigtede navne."""
    import inspect

    kilde = inspect.getsource(B._load_recent_failed_runs)
    assert "FROM visible_runs" in kilde
    assert "error AS outcome_summary" in kilde, (
        "forespørgslen vælger ikke `error` — så er den tilbage ved den kolonne "
        "der ikke findes"
    )
    assert "started_at AS created_at" in kilde
    # De rå navne må ikke stå som selectede kolonner længere.
    assert "SELECT run_id, outcome_summary, status, created_at" not in kilde


def test_kolonnerne_findes_faktisk_i_tabellen():
    """Den kontrol der ville have fanget fejlen med det samme."""
    try:
        from core.runtime.db import connect

        with connect() as conn:
            kol = {r[1] for r in conn.execute("PRAGMA table_info(visible_runs)").fetchall()}
    except Exception:
        return  # ingen DB i dette miljø — intet at kontrollere
    if not kol:
        return
    for n in ("run_id", "status", "error", "started_at"):
        assert n in kol, "visible_runs mangler kolonnen %s" % n
    for opdigtet in ("outcome_summary", "created_at"):
        assert opdigtet not in kol, (
            "%s findes nu i visible_runs — så kan forespørgslen forenkles igen"
            % opdigtet
        )


def test_henter_faktisk_fejlede_runs():
    """Mekanismen skal levere noget, ikke bare undlade at kaste."""
    try:
        from core.runtime.db import connect

        with connect() as conn:
            antal = conn.execute(
                "SELECT COUNT(*) FROM visible_runs WHERE status IN "
                "('error','failed','aborted','incomplete')"
            ).fetchone()[0]
    except Exception:
        return
    if antal < 3:
        return  # for få fejlede runs i dette miljø til at sige noget
    fundet = B._load_recent_failed_runs(limit=10)
    assert fundet, (
        "der er %d fejlede runs i tabellen, men modulet finder ingen — "
        "forespørgslen fejler stille igen" % antal
    )
    assert "run_id" in fundet[0]


def test_taersklen_er_naabar():
    """Et krav der ligger over hvad kilden kan levere, er en lukket dør."""
    assert B._MIN_FAILED_RUNS_FOR_DISCOVERY <= 10, (
        "kravet til antal fejlede runs er højere end det vindue der hentes"
    )
