"""En brugerafbrudt kørsel skal bære sin årsag ind i `visible_runs.error`.

MÅLT 18/11-2026: 12 af 12 kørsler med NULL i `visible_runs.error` havde
`provider_error_summary="user-cancelled"` i trace. Årsagen blev altså beregnet
(`_cancel_reason` i visible_runs.py:1784) og skrevet i trace — men aldrig sendt
videre til `set_last_visible_run_outcome`, som er den eneste vej til kolonnen.
Resultatet var at en brugerafbrudt tur var uskelnelig fra en klient der faldt
væk, og fra en tur der døde af ingenting.

Testen har to ben, fordi de måler hver sin halvdel af kæden:

1. `test_aarsagen_naar_visible_runs_error` — den ægte skrivevej: kalder
   funktionen med en årsag og læser kolonnen i databasen. Den beviser at
   rørføringen findes; den kan ikke se om kaldestederne bruger den.
2. `test_alle_cancel_kaldesteder_sender_aarsagen` — AST over de faktiske
   kaldesteder. En streng-grep ville matche sin egen kommentar og intet måle;
   AST'en ser præcis de `Call`-noder der kalder funktionen.

Ben 2 er det der fanger regressionen: et nyt cancelled-kaldested uden `error=`
er præcis den fejl der blev målt 12 gange.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
FUNKTION = "set_last_visible_run_outcome"


# ── Ben 1: den ægte skrivevej ──────────────────────────────────────────────


def _indsæt_koerende(run_id: str) -> None:
    from core.runtime.db import connect

    with connect() as conn:
        conn.execute(
            "INSERT INTO visible_runs (run_id, lane, provider, model, status,"
            " finished_at) VALUES (?,?,?,?,?,?)",
            (run_id, "visible", "deepseek", "deepseek-v4-flash", "running", ""),
        )
        conn.commit()


def _laes_error(run_id: str):
    from core.runtime.db import connect

    with connect() as conn:
        return conn.execute(
            "SELECT status, error FROM visible_runs WHERE run_id = ?", (run_id,)
        ).fetchone()


def _vis_run(run_id: str):
    import core.services.visible_runs as vr

    return vr.VisibleRun(
        run_id=run_id,
        lane="visible",
        provider="deepseek",
        model="deepseek-v4-flash",
        user_message="hej",
        session_id="chat-cancel",
    )


@pytest.fixture
def uden_traad(monkeypatch):
    """DB-projektionen kører i en daemon-tråd; her måler vi det synkrone UPDATE."""
    import core.services.visible_runs_outcomes as vro

    monkeypatch.setattr(vro, "_persist_visible_run_outcome", lambda *a, **kw: None)


def test_aarsagen_naar_visible_runs_error(isolated_runtime, uden_traad) -> None:
    from core.services.visible_runs_outcomes import set_last_visible_run_outcome

    _indsæt_koerende("visible-cancel-aarsag")
    set_last_visible_run_outcome(
        _vis_run("visible-cancel-aarsag"),
        status="cancelled",
        error="user-cancelled",
    )
    status, error = _laes_error("visible-cancel-aarsag")
    assert status == "cancelled"
    assert error == "user-cancelled", (
        "aarsagen forsvandt paa vejen til kolonnen — en afbrudt tur er nu "
        "uskelnelig fra en der faldt væk"
    )


# ── Ben 2: de faktiske kaldesteder ─────────────────────────────────────────


def _kald_i(sti: Path) -> list[ast.Call]:
    trae = ast.parse(sti.read_text(encoding="utf-8"), filename=str(sti))
    fund: list[ast.Call] = []
    for node in ast.walk(trae):
        if not isinstance(node, ast.Call):
            continue
        navn = None
        if isinstance(node.func, ast.Name):
            navn = node.func.id
        elif isinstance(node.func, ast.Attribute):
            navn = node.func.attr
        if navn == FUNKTION:
            fund.append(node)
    return fund


def _status_kw(call: ast.Call):
    for kw in call.keywords:
        if kw.arg == "status" and isinstance(kw.value, ast.Constant):
            return kw.value.value
    return None


def _error_kw(call: ast.Call):
    for kw in call.keywords:
        if kw.arg == "error":
            return kw.value
    return None


def test_alle_cancel_kaldesteder_sender_aarsagen() -> None:
    """Hvert `status="cancelled"`-kald skal bære en `error` der ikke er None.

    Vi kræver ikke en bestemt streng — kun at argumentet FINDES og ikke er
    `None`, så `_cancel_reason` (som allerede beregnes) bliver sendt videre.
    """
    filer = sorted((REPO / "core").rglob("*.py"))
    manglende: list[str] = []
    set_ialt = 0

    for sti in filer:
        for call in _kald_i(sti):
            if _status_kw(call) != "cancelled":
                continue
            set_ialt += 1
            error = _error_kw(call)
            if error is None or (isinstance(error, ast.Constant) and error.value is None):
                manglende.append(f"{sti.relative_to(REPO)}:{call.lineno}")

    assert set_ialt > 0, "fandt slet ingen cancelled-kald — vagten maaler ingenting"
    assert not manglende, (
        "cancelled-kald uden aarsag: " + ", ".join(manglende)
        + " — en afbrudt tur bliver uskelnelig fra en der faldt væk"
    )
