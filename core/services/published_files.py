"""Filer Jarvis har udgivet i en tur — så de kan hæfte sig på svaret.

## Hvorfor den findes

`publish_file` lagde filen i `~/.jarvis-v2/files/` og returnerede en URL. Men
turen bar den aldrig: målt 12/9-2026 over 3.653 beskeder med `content_json`
havde **nul** assistent-beskeder en `image`- eller `file`-blok (mod fire
bruger-beskeder). Klienten renderer efter blokke, så en fil Jarvis lavede
kunne ikke vises i tråden — kun nævnes i prosa, med en adresse man selv skulle
skrive af.

Det er samme hul som tænkningen havde: gemt ét sted, men ikke dér hvor nogen
kigger. Løsningen er den samme og med vilje: `visible_thinking_trace` lægger
sin måling fra sig under turen, og `visible_runs_outcomes` tager den når svaret
persisteres. Denne gør præcis det for filer.

## Hvorfor «læg og tag» og ikke en parsning af værktøjssvaret

Blokkene indeholder allerede `tool_result` med publish_file's JSON, så man
KUNNE læse URL'en ud derfra. Men så ville visningen afhænge af at et svar
bliver ved med at se ud på en bestemt måde — en streng-aftale ingen har skrevet
ned. Her siger værktøjet det selv, én gang, og persisteringen tager imod.

## Grænsen

Kun det turen faktisk udgav. Poster tages ÉN gang (`take`) og ryddes, så en
efterfølgende tur ikke arver en fil fra den forrige. Og der er et loft: en tur
der udgiver hundredvis af filer er en fejl i sig selv, og blok-arrayet skal
ikke vokse ubegrænset fordi den fejl findes.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)

#: Flere filer end dette i én tur er ikke en visning, det er støj.
MAKS_PR_TUR = 12

_laas = threading.Lock()
_pr_run: dict[str, list[dict[str, Any]]] = {}


def _nulstil_for_tests() -> None:
    with _laas:
        _pr_run.clear()


def note(run_id: str, *, filename: str, url: str = "", mime_type: str = "",
         size_bytes: int = 0, attachment_id: str = "",
         tool_use_id: str = "") -> None:
    """Registrér at turen udgav en fil eller et billede. Kaster aldrig.

    `run_id` tom → gør ingenting. En post uden tur kan ikke hæftes på noget,
    og at gemme den ville bare lade den ligge til den forkerte tur.

    To slags kilder, to slags referencer:
    - **publiceret fil** (`publish_file`): ligger i `files/`, hentes over
      `/files/{navn}` → `url` bæres.
    - **genereret billede** (`openrouter_image`, `pollinations_image`): ligger
      i `memory/generated/`, hentes over det user-scopede
      `/attachments/image/{id}` → `attachment_id` bæres.

    Referencen SKAL være den rigtige af slagsen: en genereret fil har ingen
    `/files/`-adresse, og et attachment-id kan ikke hentes fra `/files/`.
    Klienten renderer begge som `image`/`file`-blokke — den kender formen fra
    brugerbeskeder — men adressen den henter på er forskellig.
    """
    rid = str(run_id or "").strip()
    navn = str(filename or "").strip()
    aid = str(attachment_id or "").strip()
    if not rid or not navn:
        return
    # En post uden nogen hentbar reference er en blok klienten ikke kan fylde.
    if not aid and not str(url or "").strip():
        return
    try:
        with _laas:
            liste = _pr_run.setdefault(rid, [])
            if len(liste) >= MAKS_PR_TUR:
                return
            liste.append({
                "filename": navn,
                "url": str(url or ""),
                "mime_type": str(mime_type or ""),
                "size_bytes": int(size_bytes or 0),
                "attachment_id": aid,
                # Ankeret. Blokken indsaettes efter den `progress`-blok med
                # samme id, saa billedet staar DÉR hvor det blev lavet — ikke
                # bagerst efter fyrre andre blokke.
                "tool_use_id": str(tool_use_id or ""),
            })
    except Exception:
        logger.warning("published_files: kunne ikke notere %s", navn, exc_info=True)


def take(run_id: str) -> list[dict[str, Any]]:
    """Hent og RYD turens udgivne filer. Tom liste hvis ingen."""
    rid = str(run_id or "").strip()
    if not rid:
        return []
    with _laas:
        return _pr_run.pop(rid, [])


def as_blocks(poster: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Oversæt til content_json-blokke i samme form som vedhæftninger.

    Klienten kender allerede `image`/`file` fra brugerbeskeder, så en udgivet
    fil kan genbruge den renderer i stedet for at kræve en ny bloktype.

    `attachment_id` frem for `url` når billedet er GENERERET: en genereret fil
    ligger i `memory/generated/` og hentes over det user-scopede
    `/attachments/image/{id}` — den har ingen `/files/`-adresse. En publiceret
    fil har omvendt ingen attachment-række. Klienten skal kunne se forskel,
    for de to har hver sin adresse; derfor bærer blokken `kilde`.
    """
    ud: list[dict[str, Any]] = []
    for p in poster or []:
        navn = str(p.get("filename") or "").strip()
        if not navn:
            continue
        mime = str(p.get("mime_type") or "")
        blok: dict[str, Any] = {
            "type": "image" if mime.startswith("image/") else "file",
            "filename": navn,
            "mime_type": mime or "application/octet-stream",
        }
        if p.get("tool_use_id"):
            blok["tool_use_id"] = str(p["tool_use_id"])
        aid = str(p.get("attachment_id") or "").strip()
        if aid:
            blok["attachment_id"] = aid
            blok["kilde"] = "generated"
        else:
            blok["url"] = str(p.get("url") or "")
            blok["kilde"] = "published"
        stoerrelse = p.get("size_bytes")
        if isinstance(stoerrelse, int) and stoerrelse > 0:
            blok["size_bytes"] = stoerrelse
        ud.append(blok)
    return ud
