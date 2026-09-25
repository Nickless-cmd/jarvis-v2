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


# Vagten leder i HELE `core/`, ikke i to navngivne filer.
#
# Den stod før med `("core/services/visible_runs.py", {"_mark_run_started"})`.
# 25/9-2026 flyttede Boy Scout-reglen skrivningen til
# `core/services/visible_run_journal.py`, og vagten meldte «fandt ikke kaldene
# — er de flyttet?». Den havde ret i spørgsmålet: kaldet VAR flyttet, og
# skrivningen var intakt. Men en vagt der peger på en filsti holder kun til
# næste udskillelse, og den regel siger netop at filer skal splittes.
#
# Nu følger vagten kaldet. Flyttes det igen, flytter vagten med; SLETTES det,
# falder tællingen og vagten siger fra.


def _kald_med_omgivende_try(navn: str) -> list[tuple[str, int, list]]:
    """(fil, linje, handlers) for hvert kald til `navn` i `core/`.

    `handlers` er tom når kaldet ikke ligger i et `try`.
    """
    import ast
    import pathlib

    fundne: list[tuple[str, int, list]] = []
    for fil in sorted(pathlib.Path("core").rglob("*.py")):
        try:
            traeet = ast.parse(fil.read_text(encoding="utf-8"))
        except SyntaxError:  # en fil vi ikke kan parse er ikke vagtens aerinde
            continue
        # Hvert kald -> det naermeste omsluttende `try` (kun kroppen, ikke
        # handlerne: et kald inde i en handler er ikke daekket af den).
        i_try: dict[int, list] = {}
        for n in ast.walk(traeet):
            if not isinstance(n, ast.Try):
                continue
            for s in n.body:
                for c in ast.walk(s):
                    if isinstance(c, ast.Call):
                        i_try[id(c)] = n.handlers
        for n in ast.walk(traeet):
            if not isinstance(n, ast.Call):
                continue
            kaldt = getattr(n.func, "id", "") or getattr(n.func, "attr", "")
            if kaldt != navn:
                continue
            fundne.append((str(fil), n.lineno, i_try.get(id(n), [])))
    return fundne


def _tavs(handler) -> bool:
    import ast
    return all(isinstance(s, (ast.Pass, ast.Continue, ast.Break))
               for s in handler.body)


def test_hvert_mark_started_kald_siger_fra_naar_det_fejler():
    """`mark_started` skriver journal-posten. Fejler den i tavshed, kan
    boot-reconcilerens præcise ejer-regel aldrig se runnet."""
    kald = _kald_med_omgivende_try("mark_started")

    assert len(kald) >= 2, (
        f"fandt {len(kald)} kald til mark_started — der skal være mindst to: "
        "den autonome bane og den synlige. Er et spor faldet ud?"
    )
    for fil, linje, handlers in kald:
        assert handlers, f"{fil}:{linje}: mark_started ligger ikke i et try"
        for h in handlers:
            assert not _tavs(h), f"{fil}:{h.lineno} sluger fejlen i tavshed"


def test_start_raekken_er_selv_safe_og_skrives_fra_begge_baner():
    """`persist_visible_run_start` kaldes UDEN `try` — dens docstring siger
    «Self-safe: kaster aldrig». Vagten måler at påstanden holder, frem for at
    tro på den: værnet skal så ligge i funktionen selv."""
    import ast
    import pathlib

    kald = _kald_med_omgivende_try("persist_visible_run_start")
    assert len(kald) >= 2, (
        f"fandt {len(kald)} kald til persist_visible_run_start — der skal være "
        "mindst to: den autonome bane og den synlige."
    )

    kilde = pathlib.Path("core/services/visible_runs_outcomes.py")
    traeet = ast.parse(kilde.read_text(encoding="utf-8"))
    defs = [n for n in ast.walk(traeet)
            if isinstance(n, ast.FunctionDef)
            and n.name == "persist_visible_run_start"]
    assert defs, f"{kilde}: definitionen er flyttet — find den og ret vagten"

    handlers = [h for n in ast.walk(defs[0]) if isinstance(n, ast.Try)
                for h in n.handlers]
    assert handlers, "persist_visible_run_start har intet try — «self-safe» er falsk"
    for h in handlers:
        assert not _tavs(h), (
            f"{kilde}:{h.lineno} sluger fejlen i tavshed — så er «self-safe» "
            "kun sandt om kalderen, ikke om sporet"
        )


@pytest.mark.parametrize("navn", ["autonomous_stream_run", "visible_runs"])
def test_modulerne_har_en_logger(navn):
    """Uden en logger i modulet kan advarslen ikke skrives overhovedet."""
    m = __import__(f"core.services.{navn}", fromlist=["logger"])
    assert getattr(m, "logger", None) is not None
