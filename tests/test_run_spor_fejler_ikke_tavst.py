"""Begge spor efter en kørsel skal skrives — og fejler et, skal nogen få det at vide.

20/9-2026: to autonome kørsler fra kl. 20:43 stod `running` i `visible_runs`
men fandtes IKKE i `in_flight_runs`. Det er den kombination der gør dem
usynlige for boot-reconcilerens PRÆCISE regel: `list_running_orphans` spørger
om ejerens pid, og den kan kun spørge om poster der findes. Tilbage er kun den
svage «fravær»-regel, som først slår til efter seks timer — og containeren var
ikke genstartet, så rækkerne lå og løj om at være i live i al den tid.

Hvorfor skrivningen fejlede, er en formodning: journalen var vokset til 521 KB,
hver mutation skriver HELE filen under en flock, og kl. 20:43 lå iowait på 51 %
fordi der blev installeret 5,9 GB pakker. Det eneste vi VED er at ingen fik det
at vide — begge kald stod med `except Exception: pass`.
"""
from __future__ import annotations

import pytest


# Den første udgave af denne fil havde en test der SPILLEDE koden efter: den
# rejste selv en OSError og loggede selv advarslen, og påstod så at logningen
# virkede. Den beviste ingenting — den målte sit eget opspil, ikke kilden. Den
# er væk. Tilbage står den der faktisk kan sige nej: et AST-opslag i de to
# filer. En kilde-vagt der greper efter en streng måler næsten ingenting, så
# træet parses.


def test_kilden_har_ingen_tavse_except_omkring_de_to_spor():
    """Vagten mod tavse undtagelser, men målt PRÆCIST på de to kald.

    En kilde-vagt der greper efter en streng måler næsten ingenting, så her
    parses træet: begge `mark_started`/`persist_visible_run_start`-kald skal
    ligge i et `try` hvis handler siger NOGET.
    """
    import ast
    import pathlib

    for fil, navne in (
        ("core/services/autonomous_stream_run.py",
         {"mark_started", "persist_visible_run_start"}),
        ("core/services/visible_runs.py", {"_mark_run_started"}),
    ):
        traeet = ast.parse(pathlib.Path(fil).read_text(encoding="utf-8"))
        fundet = 0
        for n in ast.walk(traeet):
            if not isinstance(n, ast.Try):
                continue
            kaldte = {getattr(c.func, "id", "") or getattr(c.func, "attr", "")
                      for c in ast.walk(n) if isinstance(c, ast.Call)}
            if not (kaldte & navne):
                continue
            fundet += 1
            for h in n.handlers:
                tavs = all(isinstance(s, (ast.Pass, ast.Continue, ast.Break))
                           for s in h.body)
                assert not tavs, f"{fil}:{h.lineno} sluger fejlen i tavshed"
        assert fundet, f"{fil}: fandt ikke kaldene — er de flyttet?"


@pytest.mark.parametrize("navn", ["autonomous_stream_run", "visible_runs"])
def test_modulerne_har_en_logger(navn):
    """Uden en logger i modulet kan advarslen ikke skrives overhovedet."""
    m = __import__(f"core.services.{navn}", fromlist=["logger"])
    assert getattr(m, "logger", None) is not None
