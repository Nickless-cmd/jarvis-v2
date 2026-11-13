"""The Mourning — fra enkeltdødsfald til læring.

Målt 13/11-2026: Mourning sørgede over 34.796 modsagte hypoteser som var de
spredte. De er ikke spredte. Et lille antal systemiske fejl gentages hundredvis
af gange — den hyppigste forudsigelse var modsagt 752 gange. En karakter der
kun mindes, lærer intet: den skrev en epitaf pr. død og nul regler.

Rettelsen: `_gentagne_moenstre()` finder de gentagne fejl, og `land_moenster()`
lader den værste blive en bindende forpligtelse — med sin måling og sin kilde.
"""

from __future__ import annotations

import sqlite3

import pytest

from core.services import central_mourning as cm


def _iso_db(tmp_path, rows: list[tuple[str, str]]) -> str:
    """Isoleret base med central_hypotheses — ingen produktionsdata røres."""
    sti = str(tmp_path / "mourning.db")
    with sqlite3.connect(sti) as c:
        c.execute(
            """CREATE TABLE central_hypotheses (
                   hyp_id TEXT PRIMARY KEY, statement TEXT, outcome TEXT,
                   resolved_at TEXT)"""
        )
        for i, (statement, outcome) in enumerate(rows):
            c.execute(
                "INSERT INTO central_hypotheses VALUES (?,?,?,?)",
                (f"h{i}", statement, outcome, "2026-11-13T00:00:00+00:00"),
            )
        c.commit()
    return sti


@pytest.fixture
def isoleret(tmp_path, monkeypatch):
    def _set(rows):
        sti = _iso_db(tmp_path, rows)

        def _connect():
            conn = sqlite3.connect(sti)
            conn.row_factory = sqlite3.Row
            return conn

        monkeypatch.setattr(cm, "connect", _connect)
        return sti

    return _set


class TestGentagneMoenstre:
    def test_finder_de_gentagne_fejl_sorteret_efter_hyppighed(self, isoleret):
        isoleret([
            ("Sekvens-modellen tog fejl: A -> B", "contradicted"),
            ("Sekvens-modellen tog fejl: A -> B", "contradicted"),
            ("Sekvens-modellen tog fejl: A -> B", "contradicted"),
            ("Sekvens-modellen tog fejl: C -> D", "contradicted"),
            ("Sekvens-modellen tog fejl: C -> D", "contradicted"),
            ("Sekvens-modellen tog fejl: C -> D", "contradicted"),
            ("Noget der faktisk holdt", "supported"),
        ])
        m = cm._gentagne_moenstre(limit=5)
        assert len(m) == 2, "kun de gentagne skal med"
        fundet = {x["sig"]: x["n"] for x in m}
        assert "Sekvens-modellen tog fejl: A -> B" in fundet
        assert "Sekvens-modellen tog fejl: C -> D" in fundet
        assert all(n == 3 for n in fundet.values())

    def test_to_forekomster_er_ikke_et_moenster(self, isoleret):
        """Tærsklen er n > 2 — målt: de ægte mønstre har 752, 664, 641 forekomster.

        To gange kan være et sammenfald. Tre gange begynder at være en vane, og
        det er vanen der kan bære en forpligtelse.
        """
        isoleret([
            ("A -> B", "contradicted"),
            ("A -> B", "contradicted"),
            ("C -> D", "contradicted"),
            ("C -> D", "contradicted"),
            ("C -> D", "contradicted"),
        ])
        m = cm._gentagne_moenstre(limit=5)
        assert len(m) == 1, f"kun C->D krydser tærsklen, fik {m}"
        assert m[0]["n"] == 3

    def test_bekraeftede_taelles_ikke_som_doede(self, isoleret):
        isoleret([
            ("A -> B", "supported"),
            ("A -> B", "supported"),
            ("A -> B", "supported"),
            ("A -> B", "supported"),
        ])
        assert cm._gentagne_moenstre() == [], "kun modsagte hypoteser er døde"

    def test_enkelttilfaelde_er_ikke_et_moenster(self, isoleret):
        isoleret([
            ("A -> B", "contradicted"),
            ("C -> D", "contradicted"),
            ("E -> F", "contradicted"),
        ])
        assert cm._gentagne_moenstre() == [], "tre forskellige fejl er ikke ét mønster"


class TestLandMoenster:
    def test_moensteret_lander_med_baade_evidens_og_kilde(self, isoleret, monkeypatch):
        isoleret([("A -> B", "contradicted")] * 4)
        kaldt: list[dict] = []
        monkeypatch.setattr(
            "core.services.central_consequence.land_decision",
            lambda *a, **kw: kaldt.append(kw) or {"applied": True, "decision_id": "dec_x"},
        )
        r = cm.land_moenster()
        assert r["applied"] is True
        assert kaldt, "land_decision blev slet ikke kaldt"
        kw = kaldt[0]
        assert kw["evidence"] == "modsagt 4 gange", kw["evidence"]
        assert kw["evidence_source"] == "central_hypotheses.outcome=contradicted"
        assert "4 gange" in kw["rationale"]

    def test_uden_moenster_landes_intet(self, isoleret):
        isoleret([("A -> B", "contradicted")])
        r = cm.land_moenster()
        assert r["applied"] is False
        assert "ingen gentaget" in r["reason"]


class TestLoggerFindes:
    """Ramt fire gange samme dag: `logger` brugt i et modul uden en logger.

    En `logger.warning` inde i en `except`-gren kaster `NameError` — så
    fejlhåndteringen fejler højere end fejlen den skulle håndtere.
    """

    def test_modulet_har_en_logger(self):
        import logging

        assert isinstance(cm.logger, logging.Logger)

    def test_loggeren_bruges_kun_hvor_den_findes(self):
        import pathlib
        import re

        rod = pathlib.Path(__file__).resolve().parent.parent / "core" / "services"
        for fil in rod.glob("central_*.py"):
            kilde = fil.read_text(encoding="utf-8")
            if re.search(r"\blogger\.", kilde):
                assert "logger = logging.getLogger" in kilde, \
                    f"{fil.name} kalder logger uden at definere den"
