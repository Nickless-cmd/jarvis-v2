"""Visning — serverer et lokalt billede til desk' rækkevisning.

## Hvorfor den findes

Rækkevisningen viser billedet bag et værktøjskald (`analyze_image`,
`operator_screenshot`). Desk'ens renderer har ingen disk-adgang, så den læser
lokale filer gennem en IPC-bro i main-processen (`electron/billede.ts`).

Det virker når filen ligger på SAMME maskine som appen. Men Jarvis' egne
skærmbilleder lægges i temp-mappen på SERVEREN (se `core/tools/operator_tools.py`
— `jarvisx-screenshot-`, `jarvisx-window-`, `jarvisx-browser-`). Så findes
stien ikke hos brugeren, og rækken viste navnet og intet billede: man kunne
ikke se det samme som Jarvis.

Denne rute er broens modstykke på serveren. Samme regel som `billede.ts`
(kun billed-endelser, loft på størrelsen), men stien skal desuden ligge under
en hvidlistet rod — så den ikke bliver en fil-browser.

## Grænsen

To rødder, og ikke flere:

  - `JARVIS_HOME` — uploads, publicerede filer, workspaces
  - temp-mappen, men KUN filer med Jarvis' egne skærmbilled-prefikser

Auth er den samme som `/files` og `/attachments`: Bearer-token gennem
middleware'en, så ruten svarer 401 uden.

Bevidst ingen `jarvis-`-prefix-regel: `jarvis-mic-` er en mappe, og et bredt
prefix ville åbne for mere end skærmbilleder. Listen holdes i takt med
`core/tools/operator_tools.py`.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from core.runtime.config import JARVIS_HOME

router = APIRouter(prefix="/visning", tags=["visning"])

# Samme liste som desk'ens `electron/billede.ts`. To steder med samme regel er
# ét sted for meget — men den ene kan ikke importere den anden (TS mod Python),
# og reglen er lille nok til at kunne holdes i hånden.
_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".avif": "image/avif",
}

# 12 MB. Et fuldt skærmbillede er ~2 MB — resten er ikke noget vi viser.
_LOFT = 12 * 1024 * 1024

_TEMP_PREFIKSER = (
    "jarvisx-screenshot-",
    "jarvisx-window-",
    "jarvisx-browser-",
    "jarvis-browser-",
    "jarvisx-vision-",
)


def _ligger_under(sti: Path, rod: Path) -> bool:
    try:
        sti.relative_to(rod)
    except ValueError:  # uden for roden — det ER svaret, ikke en fejl
        return False
    return True


def tilladt_sti(sti: str) -> Path | None:
    """Den opløste sti hvis den må vises — ellers None.

    Ren funktion uden I/O ud over `resolve()`, så reglen kan testes for sig.
    """
    if not sti or not sti.startswith("/"):
        return None
    raa = Path(sti)
    if raa.suffix.lower() not in _MIME:
        return None
    try:
        fuld = raa.resolve()
    except OSError:  # kan stien ikke opløses (fx for lang), må den ikke vises
        return None

    if _ligger_under(fuld, JARVIS_HOME.resolve()):
        return fuld

    # Jarvis' egne skærmbilleder: direkte i temp-roden, med et kendt prefix.
    tmp = Path(tempfile.gettempdir()).resolve()
    if fuld.parent == tmp and fuld.name.startswith(_TEMP_PREFIKSER):
        return fuld

    return None


@router.get("/billede")
def vis_billede(sti: str) -> FileResponse:
    fuld = tilladt_sti(sti)
    if fuld is None:
        raise HTTPException(status_code=403, detail="Stien maa ikke vises")
    if not fuld.is_file():
        raise HTTPException(status_code=404, detail="Billedet findes ikke")
    if fuld.stat().st_size > _LOFT:
        raise HTTPException(status_code=413, detail="Billedet er for stort")
    return FileResponse(
        path=fuld,
        media_type=_MIME[fuld.suffix.lower()],
        filename=fuld.name,
    )
