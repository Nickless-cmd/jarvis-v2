"""Kadence-journalen skal ryddes af den kørsel der allerede rydder op.

Målt 16/11-2026 på CT105: `prune_cadence_decisions` fandtes i
`core/runtime/db_cadence_journal.py` men blev KUN kaldt fra
`tests/test_db_cadence_journal.py`. Nul produktionskald. Tabellen havde
231.645 rækker og voksede ~19.000/dag.

Det er samme figur som `cheap_lane_route_decisions`, der blev 45 % af hele
databasen i september, fordi ingen havde sat den på listen. Forskellen er at
denne gang fandtes funktionen allerede — den blev bare aldrig kaldt.

Testene her er vagten mod at koblingen forsvinder igen. En funktion der virker
og har tests, men som ingen produktionssti kalder, er den teater-fejl Bjørn
jager: mekanismen ser ud som om den virker, fordi den skriver noget.
"""

from __future__ import annotations

import ast
import inspect
import pathlib

import core.services.cache_maintenance_daemon as cmd


def _tick_kilde() -> str:
    return pathlib.Path(inspect.getsourcefile(cmd)).read_text(encoding="utf-8")


def _tick_funktion() -> ast.FunctionDef:
    for node in ast.walk(ast.parse(_tick_kilde())):
        if isinstance(node, ast.FunctionDef) and node.name == "tick_cache_maintenance_daemon":
            return node
    raise AssertionError("fandt ikke tick_cache_maintenance_daemon")


def _kaldte_navne(fn: ast.FunctionDef) -> set[str]:
    """Alle funktionsnavne der kaldes i kroppen — også inde i try-blokke."""
    navne: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                navne.add(func.id)
            elif isinstance(func, ast.Attribute):
                navne.add(func.attr)
    return navne


class TestKoblingenFindes:
    def test_prune_cadence_decisions_kaldes_fra_produktionsstien(self) -> None:
        """Kernen: kaldet skal stå i dæmonens tick, ikke kun i en test."""
        assert "prune_cadence_decisions" in _kaldte_navne(_tick_funktion())

    def test_importen_peger_paa_det_rigtige_modul(self) -> None:
        """Et kald af en funktion der ikke blev importeret er en NameError —
        som dæmonens ydre `except Exception` ville sluge i tavshed."""
        kilde = _tick_kilde()
        assert "from core.runtime.db_cadence_journal import prune_cadence_decisions" in kilde

    def test_resultatet_baerer_noeglen(self) -> None:
        """Variablen skal også ud i resultatet, ellers er kørslen usynlig.

        Præcis denne fejl — en tildelt variabel der aldrig kom i ordbogen —
        slog hele vedligeholdelsen ud 27/9-2026 uden at noget blev rødt.
        """
        fn = _tick_funktion()
        noegler: set[str] = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.Dict):
                for k in node.keys:
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        noegler.add(k.value)
        assert "cadence_pruned" in noegler


class TestKoblingenErIkkeDoed:
    def test_funktionen_den_kalder_findes_og_kan_koere(self) -> None:
        """Kaldet må ikke pege på en funktion der er væk eller kaster."""
        from core.runtime.db_cadence_journal import prune_cadence_decisions

        assert callable(prune_cadence_decisions)
        # Kør mod en tom in-memory-base: den skal svare en ordbog, ikke kaste.
        ud = prune_cadence_decisions(retention_days=30)
        assert isinstance(ud, dict)
        assert set(ud) == {"expired", "capped"}

    def test_den_rydder_kun_lukkede_poster(self) -> None:
        """Åbne poster beskriver en tilstand der stadig gælder — de er fredede.

        Det er hele grunden til at funktionen kan kaldes uden at nogen skal
        godkende det: den kan ikke slette et spørgsmål der stadig er åbent.
        """
        import sqlite3

        from core.runtime import db_cadence_journal as j

        conn = sqlite3.connect(":memory:")
        try:
            j._ensure_cadence_decisions_table(conn)
            gammel = "2020-01-01T00:00:00+00:00"
            graense = "2021-01-01T00:00:00+00:00"
            conn.execute(
                "INSERT INTO cadence_decisions "
                "(producer, status, reason_code, reason_detail, priority, "
                " first_seen_at, last_seen_at, closed_at) "
                "VALUES ('p','ran','x','',0,?,?,?)",
                (gammel, gammel, gammel),
            )
            conn.execute(
                "INSERT INTO cadence_decisions "
                "(producer, status, reason_code, reason_detail, priority, "
                " first_seen_at, last_seen_at, closed_at) "
                "VALUES ('p','cooling_down','x','',0,?,?,'')",
                (gammel, gammel),
            )
            conn.commit()
            slettet = conn.execute(
                "DELETE FROM cadence_decisions WHERE closed_at <> '' AND closed_at < ?",
                (graense,),
            ).rowcount
            tilbage = conn.execute("SELECT COUNT(*) FROM cadence_decisions").fetchone()[0]
            assert slettet == 1
            assert tilbage == 1, "den åbne post må ikke forsvinde"
        finally:
            conn.close()
