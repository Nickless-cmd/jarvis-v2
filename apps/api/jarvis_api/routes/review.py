"""Review: hvad er der faktisk ændret, og hvad bør man kigge efter?

Egen fil frem for endnu et endpoint i chat.py (1615 linjer, split-graense 1200).

Risikoflagene er UDLEDT af repoets egne regler i CLAUDE.md — ikke en vurdering
jeg finder paa. En «risiko» uden en regel bag sig er en fornemmelse forklaedt
som en maaling, og den ville faa folk til at ignorere flagene.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException


def _kun_ejer() -> None:
    """Ruten laeser repoets arbejdstrae og filstoerrelser paa vaerten.

    Samme regel som projekt-ruterne og /mc/runs: ejer ser alt, andre kun det
    der vedroerer dem. Et diff af hans arbejdstrae vedroerer ingen andre.
    Tom rolle = ubundet lokal/CLI-kontekst, ikke en fremmed.
    """
    from core.identity.workspace_context import current_role

    if current_role() not in {"", "owner"}:
        raise HTTPException(status_code=403, detail="review is owner only")


router = APIRouter(prefix="/review", tags=["review"], dependencies=[Depends(_kun_ejer)])

# CLAUDE.md: ingen fil over 1500 linjer uden undtagelse; ingen core-runtime-fil
# over 2000; split ved 1200.
_SPLIT_GRAENSE = 1200
_HAARD_GRAENSE = 1500
_CORE_GRAENSE = 2000

_DIFF_MAX_BYTES = 200_000   # loft pr. svar; en review-visning skal kunne aabnes


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _kør(rod: Path, *args: str) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(rod), *args],
            capture_output=True, text=True, timeout=20, check=False,
        )
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def _linjer_i(sti: Path) -> int:
    try:
        with sti.open("rb") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def _risici(rod: Path, filer: list[dict[str, Any]], test_koert: bool) -> list[dict[str, str]]:
    """Flag udledt af repoets EGNE regler. Ingen regel → intet flag."""
    ud: list[dict[str, str]] = []
    for f in filer:
        sti = rod / f["path"]
        if not sti.suffix == ".py" and not sti.suffix in {".ts", ".tsx"}:
            continue
        n = _linjer_i(sti)
        f["lines"] = n
        if n == 0:
            continue
        er_core = f["path"].startswith("core/")
        graense = _CORE_GRAENSE if er_core else _HAARD_GRAENSE
        if n > graense:
            ud.append({
                "path": f["path"],
                "regel": f"over {graense} linjer",
                "note": (
                    f"{n} linjer. CLAUDE.md: Boy Scout-reglen siger udskil en "
                    f"naturlig enhed FØR du ændrer en fil over 2000."
                    if er_core else
                    f"{n} linjer. CLAUDE.md: ingen fil over {_HAARD_GRAENSE} uden "
                    f"eksplicit undtagelse."
                ),
            })
        elif n > _SPLIT_GRAENSE:
            ud.append({
                "path": f["path"],
                "regel": f"over {_SPLIT_GRAENSE} linjer",
                "note": f"{n} linjer. CLAUDE.md: split ved {_SPLIT_GRAENSE}.",
            })

    if filer and not test_koert:
        ud.append({
            "path": "",
            "regel": "ingen test kørt",
            "note": "Der er ændringer, men ingen testkørsel er set i denne tur.",
        })
    return ud


@router.get("/changes")
def review_changes(test_koert: bool = False, diff: bool = True) -> dict:
    """Hvad er ændret i arbejdstræet — pr. fil, med diff og regel-baserede flag.

    `test_koert` kommer fra klienten, som ved om turen indeholdt en testkørsel
    (tidslinjen udleder det af værktøjskaldene). Serveren kan ikke se det:
    tool.completed bærer ikke run_id, så en server-side kobling ville kræve
    tidsmatch.
    """
    rod = _repo_root()
    numstat = _kør(rod, "diff", "--numstat", "HEAD")
    filer: list[dict[str, Any]] = []
    for ln in numstat.splitlines():
        dele = ln.split("\t")
        if len(dele) < 3:
            continue
        tilf, fjern, sti = dele[0], dele[1], dele[2]
        filer.append({
            "path": sti,
            "added": int(tilf) if tilf.isdigit() else 0,
            "removed": int(fjern) if fjern.isdigit() else 0,
            "binary": not tilf.isdigit(),
        })

    tekst = ""
    afkortet = False
    if diff and filer:
        tekst = _kør(rod, "diff", "HEAD")
        if len(tekst.encode("utf-8", "ignore")) > _DIFF_MAX_BYTES:
            tekst = tekst[: _DIFF_MAX_BYTES // 2]
            afkortet = True

    return {
        "branch": (_kør(rod, "rev-parse", "--abbrev-ref", "HEAD") or "").strip(),
        "files": filer,
        "added": sum(f["added"] for f in filer),
        "removed": sum(f["removed"] for f in filer),
        "diff": tekst,
        "diff_truncated": afkortet,
        "risks": _risici(rod, filer, test_koert),
    }


@router.get("/lessons")
def review_lessons(limit: int = 20) -> dict:
    """Lektier der venter paa en dom — og dem der allerede er i brug.

    Loekken var halv: forslag blev skrevet, og `build_lessons_section` laeser
    `active` ind i prompten (prompt_contract.py:2923, ingen gate) — men intet
    kunne flytte en lektion fra det ene til det andet. Fire forslag stod fra
    4.-5. september uden at nogen kunne se dem.

    `evidence_count` og `repeated_count` sendes med, fordi de er forskellen paa
    en hypotese og et moenster: set en gang er en anelse, set tre gange er en
    regel. Den vurdering skal Bjoern kunne traeffe, ikke appen.
    """
    from core.runtime.db_lessons import list_lessons

    n = max(1, min(int(limit), 100))
    try:
        forslag = list_lessons(status="proposed", limit=n)
        aktive = list_lessons(status="active", limit=n)
    except Exception as exc:  # pragma: no cover - defensivt
        return {"proposed": [], "active": [], "error": str(exc)}
    return {"proposed": forslag, "active": aktive}


@router.post("/lessons/{lesson_id}")
def review_lesson_set(lesson_id: int, payload: dict | None = None) -> dict:
    """Godkend (`active`), afvis (`rejected`) eller send tilbage (`proposed`).

    Godkendelse har en reel virkning: aktive lektier gaar ind i prompten. Derfor
    er det en bevidst handling og ikke noget der sker automatisk.
    """
    from core.runtime.db_lessons import set_lesson_status

    status = str((payload or {}).get("status") or "").strip().lower()
    try:
        raekke = set_lesson_status(int(lesson_id), status)
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}
    if raekke is None:
        return {"status": "error", "error": f"lektion {lesson_id} findes ikke"}
    return {"status": "ok", "lesson": raekke}
