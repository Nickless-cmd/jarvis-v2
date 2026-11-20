"""database-skema opslag skal MÅLES, ikke gættes (20/11-2026).

Målt før rettelsen: domænet stod på 0,40 i 1.002 vektorer med én enkelt
selvrapporteret flytning (0,44). Ingen mekanisk måling bag — og planen gjorde
det derfor til et mål der hverken kunne arbejdes med eller lukkes.

Testene her dækker tre ting, og den midterste er den vigtige: at måleren kan
sige NEJ. En måler der kun kan sige «alt stemmer», måler ingenting.
"""

from __future__ import annotations

import sqlite3

from core.services import db_schema_capability as dsc


def test_maaleren_ser_den_levende_base() -> None:
    """Den ægte base, ikke en stub: to uafhængige veje skal give samme svar."""
    result = dsc.measure()
    assert result["measured"] is True, result
    assert result["ok"] is True, result
    assert result["tables_checked"] > 10, result
    assert result["negative_control_ok"] is True, result
    assert result["confidence"] == dsc._CAP


def test_uenige_laesninger_giver_ikke_groen() -> None:
    """Sømmens test: PRAGMA og SELECT-beskrivelsen er uenige om én kolonne.

    Uden denne gren ville måleren kun kunne bekræfte sig selv — også når den
    ene vej løj. Det er præcis den fejl `costs.timestamp` var: jeg læste et
    kolonnenavn der ikke findes, fordi jeg ikke spurgte skemaet.
    """

    class _Cur:
        def __init__(self, description: list[tuple[str]]) -> None:
            self.description = description

    class Uenig:
        def execute(self, sql: str, *a: object):
            if sql.startswith("SELECT name FROM sqlite_master"):
                return [("t1",)]
            if sql.startswith("PRAGMA"):
                return [(0, "a", "TEXT"), (1, "b", "TEXT")]
            if dsc._FALSK_KOLONNE in sql:
                raise sqlite3.OperationalError("no such column")
            return _Cur([("a",), ("b",), ("c",)])

        def close(self) -> None:
            pass

    result = dsc.measure(conn=Uenig())
    assert result["measured"] is True, result
    assert result["ok"] is False, result
    assert result["mismatches"], result
    assert result["confidence"] < dsc._CAP


def test_negativ_kontrollen_skal_kunne_fejle() -> None:
    """Findes den falske kolonne alligevel, fanger opslaget intet.

    Så skal målingen ikke bare være rød — den skal være bundet, ellers kunne
    en fremmed SQLite-dialekt gøre et dødt opslag grønt.
    """

    class _Cur:
        description = [("a",)]

    class Slap:
        def execute(self, sql: str, *a: object):
            if sql.startswith("SELECT name FROM sqlite_master"):
                return [("t1",)]
            if sql.startswith("PRAGMA"):
                return [(0, "a", "TEXT")]
            return _Cur()

        def close(self) -> None:
            pass

    result = dsc.measure(conn=Slap())
    assert result["measured"] is True, result
    assert result["negative_control_ok"] is False, result
    assert result["ok"] is False, result
    assert result["confidence"] <= 0.5, result


def test_intet_maal_skriver_intet() -> None:
    """Tavshed er ikke 0,40. Kan basen ikke læses, skrives der ingen værdi."""

    class Doed:
        def execute(self, sql: str, *a: object):
            raise sqlite3.OperationalError("no such table")

        def close(self) -> None:
            pass

    result = dsc.record(conn=Doed())
    assert result["measured"] is False, result
    assert "record" not in result, result


def test_domaenenavnet_er_stavet_som_vektoren() -> None:
    """Et nyt domæne ved siden af det gamle ville gøre målingen usynlig.

    `set_domain_confidence` matcher stort/lille og mellemrum, men ikke en
    anden ordstilling. Stavningen er derfor pinnet her.
    """
    assert dsc.DOMAIN == "database-skema opslag"
