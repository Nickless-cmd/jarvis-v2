"""File download route — serves files Jarvis has published to ~/.jarvis-v2/files/.

## Det signerede link (4/10-2026)

`GET /{filename}` kraever som alt andet et bearer-token, baaret af
middlewaren. Men desk aabner markdown-links i Bjoerns EGEN browser
(`MarkdownRenderer.tsx:36` → `openExternal`), og en ekstern browser kan ikke
saettes en header paa. Filen findes, den er hans egen, og linket gav 401.

`POST /files/link` udsteder derfor et kortlivet signeret link. Selve
verifikationen staar i middlewaren, ikke her: beslutningen om at slippe en
request forbi auth skal ligge paa det ene sted hvor auth afgoeres, ellers er
der to steder der kan vaere uenige om hvad der er autentificeret.

Praecedensen er OAuth-callbacken, som er fritaget af samme grund:
«State-parameteren er signeret + binder bruger-id, saa callback'en kan ikke
forfalskes for en anden bruger.»
"""
from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.runtime.config import JARVIS_HOME

router = APIRouter(prefix="/files", tags=["files"])

FILES_DIR = JARVIS_HOME / "files"


def ensure_files_dir() -> Path:
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    return FILES_DIR


@router.get("/{filename}")
def download_file(filename: str) -> FileResponse:
    ensure_files_dir()
    # Strip any path traversal attempts
    safe_name = Path(filename).name
    if not safe_name or safe_name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = FILES_DIR / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    mime, _ = mimetypes.guess_type(safe_name)
    return FileResponse(
        path=file_path,
        filename=safe_name,
        media_type=mime or "application/octet-stream",
    )


@router.get("/")
def list_files() -> dict:
    ensure_files_dir()
    files = [
        {"name": f.name, "size_bytes": f.stat().st_size, "url": f"/files/{f.name}"}
        for f in sorted(FILES_DIR.iterdir())
        if f.is_file()
    ]
    return {"files": files, "count": len(files)}


class LinkOenske(BaseModel):
    """Hvilken fil, og hvor laenge.

    Ingen bruger i kroppen. Hvem der spoerger staar i tokenet middlewaren
    allerede har verificeret — et felt kalderen vaelger er en paastand.
    """
    filename: str = ""
    #: Sekunder. Loftet haandhaeves i `file_links`, ikke her.
    levetid_s: int = 0


@router.post("/link")
def udsted_link(req: LinkOenske) -> dict:
    """Et kortlivet signeret link til én fil.

    Kraever auth som enhver anden rute — det er KUN den faerdige adresse der
    kan bruges uden token, i 60 sekunder, til netop den fil.

    Filen skal findes FOER der udstedes. Ellers kunne ruten bruges til at
    gaette filnavne: et gyldigt link til noget der ikke findes er et svar om
    at det ikke findes.
    """
    from core.services.file_links import STANDARD_LEVETID_S, signer

    safe_name = Path(req.filename or "").name
    if not safe_name or safe_name != (req.filename or "").strip():
        raise HTTPException(status_code=400, detail="Invalid filename")
    ensure_files_dir()
    if not (FILES_DIR / safe_name).is_file():
        raise HTTPException(status_code=404, detail="File not found")

    r = signer(safe_name, levetid_s=int(req.levetid_s or STANDARD_LEVETID_S))
    if r.get("status") != "ok":
        # 503, ikke 500: ruten virker, signeringen er ikke konfigureret.
        raise HTTPException(status_code=503, detail=str(r.get("error") or "kan ikke signere"))
    from urllib.parse import quote
    return {
        "status": "ok",
        "url": f"/files/{quote(safe_name)}?udloeb={r['udloeb']}&sig={r['sig']}",
        "udloeb": r["udloeb"],
        "levetid_s": r["levetid_s"],
    }
