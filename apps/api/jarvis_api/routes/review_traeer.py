"""Hvilket arbejdstræ kigger vi i — serverens eller Bjørns egen maskine?

Udskilt fra review.py 16/9-2026, da /review/changes fik to nye krav på én gang.
Begge var huller man kun kunne se ved at vide hvad der IKKE stod i svaret:

``utrackede filer``
    ``git diff HEAD`` viser kun SPOREDE filer. En helt ny fil — den slags der
    opstår hver gang Jarvis skriver et nyt modul — talte ikke med. Panelet
    sagde «ingen ændringer» over et træ fuldt af nye filer. Samme fælde som
    ``+0 −0`` i miljø-feltet samme dag.

``hans egen maskine``
    Ruten kørte git på SERVERENS repo. Arbejder Jarvis i hans workspace, ligger
    ændringerne dér, og ruden stod tom uden at det var sandt.

Begge træer læses med ÉT kald: serverens som fire git-kommandoer i træk, hans
som én compound-kommando over broen. En tur pr. kommando ville være fire
netværksture for noget der skal kunne poll'es hvert fjerde sekund.
"""
from __future__ import annotations

import shlex
from typing import Any

# Skilletegn mellem segmenterne i compound-kommandoen. Vælgt frem for fx «---»
# fordi git-output selv indeholder «---» i hver eneste diff-header.
SKILLE = "@@@JARVIS@@@"


def kommando_for(rod: str) -> str:
    """Én kommando, fire svar: gren, numstat, status, diff.

    `shlex.quote` på roden: stien kommer fra klienten og havner i en shell på
    hans maskine. Uden den kunne en sti med et mellemrum — eller værre — brække
    kommandoen op.
    """
    r = shlex.quote(rod)
    return (
        f"cd {r} 2>/dev/null || exit 9; "
        f"git rev-parse --abbrev-ref HEAD 2>/dev/null; echo '{SKILLE}'; "
        f"git diff --numstat HEAD 2>/dev/null; echo '{SKILLE}'; "
        f"git status --porcelain 2>/dev/null; echo '{SKILLE}'; "
        f"git diff HEAD 2>/dev/null"
    )


def parse_segmenter(stdout: str) -> tuple[str, str, str, str]:
    """Del svaret op i (gren, numstat, status, diff).

    Mangler et segment, returneres tom streng for det — IKKE en undtagelse.
    Et halvt svar er stadig bedre end ingenting, og kalderen kan se forskel på
    «tomt træ» og «intet svar» på grenen.
    """
    dele = stdout.split(SKILLE)
    while len(dele) < 4:
        dele.append("")
    return dele[0].strip(), dele[1], dele[2], dele[3]


def _er_binaer(indhold: bytes) -> bool:
    return b"\0" in indhold[:8000]


def utrackede_fra_status(porcelain: str) -> list[str]:
    """Stierne bag `??` i `git status --porcelain`.

    Mapper (som porcelain melder med et afsluttende «/») springes over: de er
    ikke én fil, og at tælle linjer i en mappe giver ingen mening. Deres
    indhold kommer med, hvis man tilføjer dem — det er en bevidst afvejning
    frem for at gå rekursivt ned i noget der kan være enormt (node_modules).
    """
    ud: list[str] = []
    for linje in (porcelain or "").splitlines():
        if not linje.startswith("?? "):
            continue
        sti = linje[3:].strip().strip('"')
        if sti and not sti.endswith("/"):
            ud.append(sti)
    return ud


def numstat_til_filer(numstat: str) -> list[dict[str, Any]]:
    filer: list[dict[str, Any]] = []
    for ln in (numstat or "").splitlines():
        dele = ln.split("\t")
        if len(dele) < 3:
            continue
        tilf, fjern, sti = dele[0], dele[1], dele[2]
        filer.append({
            "path": sti,
            "added": int(tilf) if tilf.isdigit() else 0,
            "removed": int(fjern) if fjern.isdigit() else 0,
            "binary": not tilf.isdigit(),
            "ny": False,
        })
    return filer


def ny_fil_post(sti: str, indhold: bytes | None) -> dict[str, Any]:
    """En utracket fil som en fil-post.

    `added` er filens linjeantal: det ER hvad den tilføjer til træet. At sætte
    den til 0 (som `git diff HEAD` i praksis gør ved at udelade den) ville vise
    «+0» for en fil på 400 linjer.
    """
    if indhold is None:
        return {"path": sti, "added": 0, "removed": 0, "binary": False, "ny": True}
    if _er_binaer(indhold):
        return {"path": sti, "added": 0, "removed": 0, "binary": True, "ny": True}
    linjer = indhold.count(b"\n") + (0 if indhold.endswith(b"\n") or not indhold else 1)
    return {"path": sti, "added": linjer, "removed": 0, "binary": False, "ny": True}


def ny_fil_diff(sti: str, indhold: bytes | None) -> str:
    """En diff-blok for en ny fil, i samme form som git selv skriver den.

    Klienten deler den samlede diff op pr. fil ved at søge efter
    «diff --git a/<sti>». En ny fil uden den linje ville være usynlig i
    udfoldningen, selv om den stod i listen.
    """
    if indhold is None:
        return ""
    if _er_binaer(indhold):
        return (f"diff --git a/{sti} b/{sti}\nnew file mode 100644\n"
                f"Binary files /dev/null and b/{sti} differ\n")
    tekst = indhold.decode("utf-8", "replace")
    linjer = tekst.splitlines()
    hoved = (f"diff --git a/{sti} b/{sti}\nnew file mode 100644\n"
             f"--- /dev/null\n+++ b/{sti}\n@@ -0,0 +1,{len(linjer)} @@\n")
    return hoved + "".join(f"+{l}\n" for l in linjer)
