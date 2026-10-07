"""`publish_file` — udskilt enhed, og nu per bruger.

## Hvorfor den bor her

Boy Scout-reglen: `simple_tools_native.py` stod på 3.240 linjer, og dette
værktøj skulle have ændret LOGIK — ikke en tilføjelse. Den nærmeste
sammenhængende enhed er værktøjet selv: én funktion, ét ansvar, og den eneste
skriver ind i filmappen. `simple_tools_native` re-eksporterer navnet, så
ingen import brækker.

## Ændringen (Bjørn 4/10-2026: «filer skal være per bruger»)

Den skrev til `~/.jarvis-v2/files/` — én flad mappe, 151 filer, som enhver
autentificeret husstandsbruger kunne hente med sit eget token. Den skriver nu
til `files/u/<workspace>/` gennem `workspace_paths.published_file_path`, som
er det ene sted der kender layoutet.

Uden en bruger i konteksten skriver den INTET. Det er en opstramning:
før havde en ubundet kalder — et script, en daemon — en mappe at skrive i, og
den mappe var alles. Nu er svaret en typet fejl. Et autonomt run binder
ejeren (`visible_runs` gør det eksplicit), så Jarvis' egne udgivelser er
upåvirkede; det er kun de virkelig kontekstløse der stoppes, og dem skal man
kunne se.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

logger = logging.getLogger(__name__)


def _exec_publish_file(args: dict[str, Any]) -> dict[str, Any]:
    """Copy or create a file in ~/.jarvis-v2/files/ and return a download URL."""
    import mimetypes
    import shutil

    source_path = str(args.get("source_path") or "").strip()
    filename = str(args.get("filename") or "").strip()
    content = args.get("content")

    if not filename:
        return {"status": "error", "error": "filename is required"}
    # Prevent path traversal
    safe_name = Path(filename).name
    if not safe_name:
        return {"status": "error", "error": "invalid filename"}

    # ÉN definition af layoutet, i `workspace_paths`. En egen sammensætning
    # her ville være den fjerde kopi af samme regel — ruten, signeringen og
    # migreringen bruger alle den samme.
    from core.runtime.workspace_paths import (
        NoUserContextError,
        published_file_path,
    )
    try:
        dest = published_file_path(safe_name, opret_mappe=True)
    except NoUserContextError:
        # Fail-closed, og typet. Et fald til en faelles mappe er praecis den
        # laekage afgraensningen lukker — og det ville ske tavst.
        return {"status": "error",
                "error": "ingen bruger i konteksten — filen blev ikke udgivet"}
    except ValueError as exc:  # et ugyldigt filnavn er kalderens fejl, ikke en hændelse
        return {"status": "error", "error": str(exc)}

    try:
        if content is not None:
            # Write inline content (text or bytes)
            mode = "wb" if isinstance(content, bytes) else "w"
            dest.open(mode).write(content)
        elif source_path:
            src = Path(source_path)
            if not src.exists():
                return {"status": "error", "error": f"source_path not found: {source_path}"}
            shutil.copy2(src, dest)
        else:
            return {"status": "error", "error": "provide source_path or content"}
    except Exception as exc:  # disk/rettigheder — beskeden ER svaret til kalderen
        return {"status": "error", "error": str(exc)}

    # ADRESSEN SKAL VIRKE DÉR HVOR BRUGEREN ER. Indtil 12/9-2026 stod her
    # `http://localhost:8080/...`. Filen blev udgivet helt korrekt — og
    # brugeren fik en adresse der kun virker på den maskine Jarvis selv kører
    # på. Paa en telefon er `localhost` telefonen. Derfor kunne Bjoern ikke se
    # en HTML Jarvis lige havde lavet, naar han ikke sad ved computeren.
    #
    # Vaerre: hallucinations-vagten nedenfor hentede netop den localhost-URL
    # FRA SERVEREN, hvor den svarer 200. Vagten var sand om sin form og tavs
    # om at adressen kun virkede ét sted.
    _lokal = "http://localhost:8080"
    try:
        from core.runtime.secrets import read_runtime_key
        _base = str(read_runtime_key("public_base_url", "JARVIS_PUBLIC_BASE_URL") or "").strip()
    except Exception:
        _base = ""
    _base = (_base or _lokal).rstrip("/")
    url = f"{_base}/files/{safe_name}"

    # Hallucination guard: virker ruten?
    #
    # 401 OG 403 ER SUCCES HER. Ruten kraever godkendelse — maalt 12/9-2026
    # giver baade localhost og den udadvendte adresse 401 uden token. Vagten
    # hentede uden Authorization, fik 401, satte url_verified=False og skrev
    # «Praesenter IKKE URL'en for brugeren — den virker ikke».
    #
    # Resultatet: hver eneste gang en fil blev udgivet, fik Jarvis besked paa
    # at LADE VAERE med at vise linket. Funktionen virkede; vagten maalte et
    # ubeskyttet kald mod en beskyttet rute og kaldte det et nedbrud.
    #
    # Det vagten skal kunne skelne er «ruten findes og serverer» fra «filen er
    # ikke der» (404) eller «serveren er nede» (forbindelsesfejl). En 401 svarer
    # praecis paa det foerste: noget lytter, og det beskytter filen.
    url_verified = False
    url_error = ""
    try:
        req = urllib_request.Request(url, method="GET")
        with urllib_request.urlopen(req, timeout=5) as resp:
            url_verified = 200 <= resp.status < 300
            if not url_verified:
                url_error = f"HTTP {resp.status}"
    except urllib_error.HTTPError as exc:
        if exc.code in (401, 403):
            url_verified = True          # ruten lever og beskytter filen
            url_error = ""
        else:
            url_verified = False
            url_error = f"HTTP {exc.code}"
    except Exception as exc:
        url_verified = False
        url_error = str(exc)

    result: dict[str, Any] = {
        "status": "ok",
        "filename": safe_name,
        "url": url,
        "markdown_link": f"[{safe_name}]({url})",
        "size_bytes": dest.stat().st_size,
        "url_verified": url_verified,
    }
    if url_error:
        result["url_verify_error"] = url_error
    if not url_verified:
        result["warning"] = (
            f"URL'en {url} returnerede ikke 200 ({url_error or 'unknown'}). "
            "Præsenter IKKE URL'en for brugeren — den virker ikke."
        )
    # HAEFT DEN PAA TUREN. Uden dette bar svaret ikke filen: maalt 12/9-2026
    # havde NUL assistent-beskeder en image/file-blok, saa klienten - der
    # renderer efter blokke - kunne ikke vise den. Samme hul som taenkningen
    # havde, og samme loesning: laeg fra dig her, tag imod ved persistering.
    try:
        from core.services.published_files import note as _note_udgivet
        # NØGLENAVNET ER `_runtime_turn_id` — ikke `_runtime_run_id`. Executoren
        # (simple_tool_executor._prepare_call) stamper `_runtime_turn_id`, så den
        # gamle læsning gav ALTID tom run_id og `note()` returnerede straks.
        # Målt 13/9-2026: `published_files` havde derfor aldrig haeftet noget —
        # nul assistent-beskeder bar en image/file-blok. Fallback'et beholdes saa
        # en fremtidig kilde med det andet navn ikke tavst falder ud igen.
        _note_udgivet(
            str(args.get("_runtime_turn_id") or args.get("_runtime_run_id") or ""),
            filename=safe_name,
            url=url,
            mime_type=str(mimetypes.guess_type(safe_name)[0] or ""),
            size_bytes=int(result.get("size_bytes") or 0),
        )
    except Exception:
        pass  # en visning maa aldrig braekke selve udgivelsen

    if _base == _lokal:
        # SIG DET. En localhost-adresse er ikke en fejl her paa maskinen, men
        # den kan ikke deles. Uden denne linje ville svaret se fuldt gyldigt ud
        # og vaere ubrugeligt for enhver anden end serveren selv.
        result["kun_lokal"] = True
        result["warning"] = (
            f"{result.get('warning', '')} Adressen er en LOKAL adresse "
            "({_lokal}) og virker ikke fra telefon eller anden maskine. "
            "Saet `public_base_url` i runtime.json til den adresse klienterne "
            "bruger, hvis filen skal kunne deles."
        ).strip().replace("{_lokal}", _lokal)
    return result


