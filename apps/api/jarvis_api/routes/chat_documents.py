"""Chat-artefakter: dokumenter med version og et delbart link.

Tynd adapter. Al logik ligger i ``core.services.artifact_document`` — ruten
tilføjer kun det servicen ikke kan vide: HVEM der spørger, og om samtalen er
hans.

## Hvorfor ejer-tjekket ligger her og ikke i servicen

``artifact_document`` er session-baseret og har intet ejer-felt (målt
22/11-2026: `create_document`/`get_document`/`list_documents`/
`update_document` tager kun `session_id` og `document_id`). Et gættet
``session_id`` eller ``document_id`` ville derfor være nok til at læse en
andens dokument. Ejer-beviset kommer fra ``chat_sessions.owner_user_id`` via
``get_session_owner`` — samme kilde som projekt-ruten bruger.

**404, ikke 403**, når dokumentet ikke er dit: et 403 ville bekræfte at det
FINDES hos en anden. Samme regel som ``files.py``.

## Publicering

Et dokument lever i tråden. ``POST /chat/documents/{id}/publish`` skriver det
til kalderens EGEN filmappe (``files/u/<workspace>/``) og udsteder et
kortlivet signeret link gennem ``file_links.signer``. Det er den samme vej
``POST /files/link`` bruger — ikke en ny mekanisme, så afgrænsningen og
signaturen over ``workspace|filnavn|udløb`` gælder uændret.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.api.jarvis_api.routes.chat_projects import _bruger, _kraev_session
from core.services import artifact_document

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat-documents"])


class OpretDokumentBody(BaseModel):
    title: str = ""
    content: str = ""
    content_type: str = "text/markdown"


class OpdaterDokumentBody(BaseModel):
    content: str
    expected_version: int
    title: str | None = None
    content_type: str | None = None


class PublicerBody(BaseModel):
    #: Filnavn uden sti. Tomt = afledt af dokumentets titel.
    filename: str = ""
    levetid_s: int = 0


def _doc_ud(dokument: dict[str, Any]) -> dict[str, Any]:
    """Service-form → Desk-kontrakt. Felterne er dem klienten læser."""
    return {
        "id": str(dokument.get("document_id") or ""),
        "session_id": str(dokument.get("session_id") or ""),
        "title": str(dokument.get("title") or ""),
        "content": str(dokument.get("content") or ""),
        "content_type": str(dokument.get("content_type") or ""),
        "version": int(dokument.get("version") or 1),
        "created_at": str(dokument.get("created_at") or ""),
        "updated_at": str(dokument.get("updated_at") or ""),
    }


def _kraev_dokument(document_id: str, uid: str) -> dict[str, Any]:
    """Dokumentet skal findes OG tilhøre kalderen. Ellers 404 i begge tilfælde."""
    dokument = artifact_document.get_document(document_id)
    if dokument is None:
        raise HTTPException(status_code=404, detail="Dokumentet findes ikke")
    _kraev_session(str(dokument.get("session_id") or ""), uid)
    return dokument


def _sikkert_filnavn(oenske: str, titel: str) -> str:
    """Et filnavn uden sti. Et navn med ``/`` eller ``..`` ville skrive uden
    for brugerens mappe — ``Path(...).name`` fjerner stien, og et tomt
    resultat falder tilbage til titlen."""
    raa = str(oenske or "").strip()
    if raa:
        navn = Path(raa).name
        if navn and navn == raa:
            return navn
    base = Path(str(titel or "").strip()).name or "dokument"
    base = base.replace("/", "-").replace("\x00", "").strip() or "dokument"
    if not base.lower().endswith((".md", ".txt", ".markdown")):
        base = f"{base}.md"
    return base


@router.get("/chat/sessions/{session_id}/documents")
def list_dokumenter(session_id: str) -> dict[str, Any]:
    uid = _bruger()
    sid = _kraev_session(session_id, uid)
    return {"documents": [_doc_ud(d) for d in artifact_document.list_documents(sid)]}


@router.post("/chat/sessions/{session_id}/documents")
def opret_dokument(session_id: str, body: OpretDokumentBody) -> dict[str, Any]:
    uid = _bruger()
    sid = _kraev_session(session_id, uid)
    dokument = artifact_document.create_document(
        session_id=sid,
        title=body.title,
        content=body.content,
        content_type=body.content_type,
    )
    return {"document": _doc_ud(dokument)}


@router.get("/chat/documents/{document_id}")
def laes_dokument(document_id: str) -> dict[str, Any]:
    uid = _bruger()
    return {"document": _doc_ud(_kraev_dokument(document_id, uid))}


@router.put("/chat/documents/{document_id}")
def opdater_dokument(document_id: str, body: OpdaterDokumentBody) -> dict[str, Any]:
    uid = _bruger()
    _kraev_dokument(document_id, uid)
    try:
        dokument = artifact_document.update_document(
            document_id,
            content=body.content,
            expected_version=body.expected_version,
            title=body.title,
            content_type=body.content_type,
        )
    except artifact_document.DocumentNotFound:
        raise HTTPException(status_code=404, detail="Dokumentet findes ikke")
    except artifact_document.VersionConflict:
        # 409, ikke 400: klienten skal hente den nye version og prøve igen.
        raise HTTPException(status_code=409, detail="Dokumentet er ændret siden")
    return {"document": _doc_ud(dokument)}


@router.post("/chat/documents/{document_id}/suggest")
def foreslaa_fortsaettelse(document_id: str) -> dict[str, str]:
    """Et tilbud på den næste sætning — ikke en afbrydelse.

    Bjørn 17/9-2026 afviste den klassiske ghost-text med sine egne ord: «det
    kommer dumpende mens jeg skriver, det er virkelig træls». Formen her er
    derfor et forslag der hentes når HAN beder om det, og som først bliver
    tekst hvis han tager imod. Der findes ingen automatisk hentning under
    tastning — det er hele forskellen mellem et tilbud og en afbrydelse.

    Kilden er ``daemon_llm_call``, husets egen model-indgang. Den lokale
    4b-model blev droppet i komponisten 28/9-2026, fordi dens forslag blev
    valgt 2,9 % af gangene mod Jarvis' egne 23,5 % — et dårligt forslag er
    værre end intet.

    Svarer altid 200 med en tom streng ved enhver fejl: et forslag er en
    bekvemmelighed, og et manglende forslag må ikke ligne en ødelagt editor.
    """
    uid = _bruger()
    dokument = _kraev_dokument(document_id, uid)
    tekst = str(dokument.get("content") or "").strip()
    if len(tekst) < 40:
        # Intet at fortsætte. Et gæt på et næsten tomt dokument er ikke et
        # forslag, og det ville koste et model-kald at finde ud af.
        return {"forslag": ""}
    try:
        from core.services.daemon_llm import daemon_llm_call
        hale = tekst[-2000:]
        prompt = (
            "Du fortsætter et dokument skrevet på dansk. Skriv KUN den næste "
            "sætning eller det næste korte afsnit — højst 40 ord. Ingen "
            "indledning, ingen forklaring, ingen anførselstegn. Matér tonen.\n\n"
            f"Dokumentet indtil nu:\n{hale}\n\nFortsættelse:"
        )
        forslag = daemon_llm_call(
            prompt, max_len=400, fallback="", daemon_name="canvas_forslag",
        )
        return {"forslag": str(forslag or "").strip()}
    except Exception:
        logger.debug("canvas-forslag fejlede", exc_info=True)
        return {"forslag": ""}


@router.post("/chat/documents/{document_id}/publish")
def publicer_dokument(document_id: str, body: PublicerBody) -> dict[str, Any]:
    """Skriv dokumentet til kalderens filmappe og udsted et kortlivet link."""
    from core.runtime.workspace_paths import NoUserContextError, published_files_dir
    from core.services.file_links import STANDARD_LEVETID_S, signer

    uid = _bruger()
    dokument = _kraev_dokument(document_id, uid)

    try:
        mappe = published_files_dir(opret=True)
    except NoUserContextError:
        raise HTTPException(status_code=401, detail="ingen autentificeret bruger")

    navn = _sikkert_filnavn(body.filename, str(dokument.get("title") or ""))
    try:
        (mappe / navn).write_text(str(dokument.get("content") or ""), encoding="utf-8")
    except OSError as exc:
        logger.warning("chat-documents: kunne ikke skrive %s: %s", navn, exc)
        raise HTTPException(status_code=500, detail="kunne ikke udgive dokumentet")

    resultat = signer(
        navn,
        workspace=mappe.name,
        levetid_s=int(body.levetid_s or STANDARD_LEVETID_S),
    )
    if resultat.get("status") != "ok":
        raise HTTPException(
            status_code=503, detail=str(resultat.get("error") or "kan ikke signere")
        )
    return {
        "status": "ok",
        "filename": navn,
        "url": (
            f"/files/{quote(navn)}?ws={quote(str(mappe.name))}"
            f"&udloeb={resultat['udloeb']}&sig={resultat['sig']}"
        ),
        "udloeb": resultat["udloeb"],
        "levetid_s": resultat["levetid_s"],
        "version": int(dokument.get("version") or 1),
    }
