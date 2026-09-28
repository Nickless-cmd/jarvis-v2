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
  - temp-mappen: Jarvis' skærmbilled-prefikser, eller et ældre billede hvis
    et gemt `analyze_image`-kald i en samtale brugeren må åbne angiver PRÆCIS
    den sti og det værktøjs-id.

Auth er den samme som `/files` og `/attachments`: Bearer-token gennem
middleware'en, så ruten svarer 401 uden.

Bevidst ingen `jarvis-`-prefix-regel: `jarvis-mic-` er en mappe, og et bredt
prefix ville åbne for mere end skærmbilleder. Listen holdes i takt med
`core/tools/operator_tools.py`.
"""
from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/visning", tags=["visning"])
logger = logging.getLogger(__name__)

# Reglen selv bor i `core/services/vision_preview` — vaerktoejslaget skal kunne
# spoerge «maa klienten hente det her?» FOER det svarer, og `core/` kan ikke
# importere en API-rute. Ruten er stadig den eneste der serverer filen; den
# laaner bare reglen i stedet for at eje sin egen kopi af den.
#
# Navnene herunder er gen-eksporteret fordi testen og ruten bruger dem. BEMAERK
# at `tilladt_sti` laeser `JARVIS_HOME` og `tempfile` fra vision_preview — en
# monkeypatch skal ramme DET modul, ikke dette.
from core.services.vision_preview import (  # noqa: E402
    LOFT as _LOFT,
    MIME as _MIME,
    TEMP_PREFIKSER as _TEMP_PREFIKSER,
    maa_vises as tilladt_sti,
)

__all__ = ["router", "tilladt_sti", "vis_billede"]


def _gammelt_analysebillede(sti: str, besked_id: str, tool_use_id: str) -> Path | None:
    """Allow one old temp image only when the stored tool call names that path."""
    if not sti or not besked_id or not tool_use_id or len(sti) > 4096:
        return None
    path = Path(sti)
    temp = Path(tempfile.gettempdir()).resolve()
    if (not path.is_absolute() or path.suffix.lower() not in _MIME
            or path.is_symlink() or path.parent.resolve() != temp or path.resolve() != path):
        return None

    from core.runtime.db import connect
    from apps.api.jarvis_api.routes.chat_session_view import kraev_adgang
    with connect() as conn:
        row = conn.execute(
            "SELECT session_id, content_json FROM chat_messages WHERE message_id = ?",
            (besked_id,),
        ).fetchone()
    if not row:
        return None
    kraev_adgang(str(row["session_id"]))
    try:
        blocks = json.loads(str(row["content_json"] or ""))
    except (TypeError, ValueError) as exc:
        logger.debug("stored image message cannot be decoded: %s", exc)
        return None
    if not isinstance(blocks, list):
        return None
    for block in blocks:
        if (isinstance(block, dict) and block.get("type") == "tool_use"
                and block.get("id") == tool_use_id and block.get("name") == "analyze_image"):
            input_data = block.get("input")
            image_path = input_data.get("image_path") if isinstance(input_data, dict) else None
            if image_path == sti:
                return path
    return None


@router.get("/billede")
def vis_billede(sti: str, besked_id: str = "", tool_use_id: str = "") -> FileResponse:
    fuld = tilladt_sti(sti) or _gammelt_analysebillede(sti, besked_id, tool_use_id)
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
