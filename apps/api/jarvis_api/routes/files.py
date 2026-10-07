"""Udgivne filer — per bruger.

## Afgrænsningen (Bjørn 4/10-2026: «filer skal være per bruger»)

Indtil i dag lå alt i én flad `~/.jarvis-v2/files/`: 151 filer, som enhver
autentificeret husstandsbruger kunne hente med sit eget token. Ruten slog op
direkte i mappen uden at spørge hvem der spurgte.

Nu bor en fil i `files/u/<workspace>/`, og ruten regner mappen ud af den
AUTENTIFICEREDE bruger. Der er ingen fallback til den gamle fælles mappe:
et fald dertil ville være nøjagtig den lækage afgrænsningen lukker, og det
ville ske tavst. Kan brugeren ikke afgøres, svarer ruten 401.

**404, ikke 403**, når filen ikke er din: et 403 ville fortælle at filen
FINDES hos en anden. En liste over naboens filnavne er også en lækage.

## Det signerede link

`GET /{filename}` kræver som alt andet et bearer-token. Men desk åbner
markdown-links i brugerens EGEN browser, som ikke kan bære en header, så
`POST /files/link` udsteder et kortlivet signeret link.

Signaturen bærer nu `workspace|filnavn|udløb`. Workspacet er NØDVENDIGT her,
og det var det ikke før: da alle filer lå i én mappe, kunne et filnavn kun
betyde én fil. Nu kan `rapport.pdf` findes hos to brugere, og uden workspacet
i signaturen ville det ene links signatur passe på den andens fil.

Verifikationen står i middlewaren, ikke her — beslutningen om at slippe forbi
auth hører på det ene sted hvor auth afgøres.
"""
from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.runtime.config import JARVIS_HOME

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])

#: Den GAMLE fælles mappe. Står her fordi migreringen og dens test refererer
#: den — ruten læser den ALDRIG. Se `scripts/migrer_filer_per_bruger.py`.
LEGACY_FILES_DIR = JARVIS_HOME / "files"


def _min_mappe(*, opret: bool = False) -> Path:
    """Den autentificerede brugers filmappe, eller 401.

    Oversætter `NoUserContextError` til 401 frem for at lade den blive en 500:
    «vi ved ikke hvem du er» er et autentifikations-svar, ikke et nedbrud.
    """
    from core.runtime.workspace_paths import NoUserContextError, published_files_dir
    try:
        return published_files_dir(opret=opret)
    except NoUserContextError:
        raise HTTPException(status_code=401, detail="ingen autentificeret bruger")
    except Exception as exc:  # noqa: BLE001
        # En ukendt bruger eller et uloeseligt workspace. Fail-closed, og
        # synligt — ellers staar en bruger med en tom filliste uden grund.
        logger.warning("files: kunne ikke oploese brugerens filmappe: %s", exc)
        raise HTTPException(status_code=401, detail="ingen autentificeret bruger")


def ensure_files_dir() -> Path:
    """Den autentificerede brugers mappe, oprettet. Bevarer det gamle navn,
    fordi `published_files` og testene importerer det."""
    return _min_mappe(opret=True)


class LinkOenske(BaseModel):
    """Hvilken fil, og hvor længe.

    Ingen bruger i kroppen. Hvem der spørger står i tokenet middlewaren
    allerede har verificeret — et felt kalderen vælger er en påstand.
    """
    filename: str = ""
    #: Sekunder. Loftet håndhæves i `file_links`, ikke her.
    levetid_s: int = 0


@router.post("/link")
def udsted_link(req: LinkOenske) -> dict:
    """Et kortlivet signeret link til én af MINE filer.

    Filen slås op i kalderens EGEN mappe. Gjorde den ikke det, kunne ruten
    bruges til at udstede links til naboens filer — og så ville signeringen
    være vejen udenom afgrænsningen frem for en del af den.
    """
    from core.runtime.workspace_paths import published_files_dir
    from core.services.file_links import STANDARD_LEVETID_S, signer

    raa = str(req.filename or "").strip()
    safe_name = Path(raa).name
    if not safe_name or safe_name != raa:
        raise HTTPException(status_code=400, detail="Invalid filename")

    mappe = _min_mappe()
    if not (mappe / safe_name).is_file():
        # 404 ogsaa naar filen findes hos en ANDEN: et andet svar ville
        # roebe at den eksisterer.
        raise HTTPException(status_code=404, detail="File not found")

    r = signer(safe_name, workspace=mappe.name,
               levetid_s=int(req.levetid_s or STANDARD_LEVETID_S))
    if r.get("status") != "ok":
        raise HTTPException(status_code=503, detail=str(r.get("error") or "kan ikke signere"))
    from urllib.parse import quote
    return {
        "status": "ok",
        "url": (f"/files/{quote(safe_name)}?ws={quote(str(mappe.name))}"
                f"&udloeb={r['udloeb']}&sig={r['sig']}"),
        "udloeb": r["udloeb"],
        "levetid_s": r["levetid_s"],
    }


@router.get("/{filename}")
def download_file(filename: str, ws: str = "") -> FileResponse:
    """Hent én fil — min egen, eller en andens via et gyldigt signeret link.

    `ws` kommer KUN fra et signeret link, og middlewaren har allerede
    verificeret signaturen over netop `ws|filnavn|udløb` før requesten nåede
    hertil. Uden den verifikation ville parameteren være en fri valgmulighed
    for enhver — altså ingen afgrænsning overhovedet.

    Derfor er `ws` kun i spil når der INTET token er: har kalderen et token,
    er det kalderens egen mappe der gælder, så en autentificeret bruger ikke
    kan sætte `ws=nabo` og læse med.
    """
    from core.runtime.workspace_paths import NoUserContextError, published_files_dir

    safe_name = Path(filename).name
    if not safe_name or safe_name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    try:
        mappe = published_files_dir()
    except NoUserContextError:
        # Ingen bruger i konteksten ⇒ det MAA vaere et signeret link, og
        # signaturen er allerede verificeret af middlewaren.
        from core.runtime.workspace_paths import (
            _jarvis_home,
            rent_mappe_eller_filnavn,
        )
        navn = rent_mappe_eller_filnavn(ws)
        if not navn:
            raise HTTPException(status_code=401, detail="ingen autentificeret bruger")
        # `_jarvis_home()` laeser env ved KALDET. Modul-konstanten `JARVIS_HOME`
        # bindes ved import, saa den overlever ikke en test der flytter hjemmet
        # — og en rute der laeser et andet hjem end resten maaler ikke det
        # samme sted.
        mappe = _jarvis_home() / "files" / "u" / navn

    file_path = mappe / safe_name
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    mime, _ = mimetypes.guess_type(safe_name)
    return FileResponse(
        path=file_path,
        filename=safe_name,
        media_type=mime or "application/octet-stream",
    )


@router.get("/")
def list_files() -> dict:
    """MINE filer. Aldrig nogen andens, og aldrig de gamle faelles."""
    mappe = _min_mappe(opret=True)
    files = [
        {"name": f.name, "size_bytes": f.stat().st_size, "url": f"/files/{f.name}"}
        for f in sorted(mappe.iterdir())
        if f.is_file()
    ]
    return {"files": files, "count": len(files)}
