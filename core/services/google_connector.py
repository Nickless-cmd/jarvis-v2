"""Google-pakke-connector — Calendar/Drive/Docs/Sheets/Slides (læse-tools).

Deler ÉN Google-OAuth med Gmail (token gemt under provider="google",
get_fresh_token → auto-refresh). Alle tools bruger BRUGERENS egen token.

v1: kun LÆSE-tools (sikre). Opret/rediger-tools (calendar_create, docs_write …)
kræver approval-flow og følger separat — derfor ikke registreret endnu.
Fejl: intet token → *_not_connected; 403 → *_scope_missing.
"""
from __future__ import annotations

from core.services.oauth_store import get_fresh_token

_PROVIDER = "google"

GOOGLE_CONNECTOR_TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "calendar_list_events",
            "description": (
                "List kommende begivenheder i brugerens primære Google Calendar via deres "
                "EGEN forbundne Google-konto. Kræver forbundet Google Calendar i Marketplace."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "max_results": {"type": "integer", "description": "Maks antal (1-25, standard 10)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "drive_search",
            "description": (
                "Søg/list filer i brugerens Google Drive via deres EGEN forbundne konto. "
                "Tom query = nyeste filer. Returnerer navn/type/link. Kræver forbundet Drive."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Fritekst-søgning i filnavne (valgfri)"},
                    "max_results": {"type": "integer", "description": "Maks antal (1-25, standard 10)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "drive_download",
            "description": (
                "Hent en fil fra brugerens Google Drive ned på maskinen og få et download-link. "
                "Google Docs/Sheets/Slides eksporteres automatisk til .docx/.xlsx/.pptx. "
                "Brug file_id fra drive_search. Kræver forbundet Drive."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {"type": "string", "description": "Drive-filens id (fra drive_search)"},
                    "export_as": {
                        "type": "string",
                        "description": "Valgfri: 'pdf', 'docx', 'xlsx' eller 'pptx' — tvinger format for Google-native filer",
                    },
                },
                "required": ["file_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "docs_read",
            "description": (
                "Læs tekstindholdet af et Google Docs-dokument via dets document_id "
                "(brugerens EGEN konto). Kræver forbundet Google Docs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "Docs document-id (fra Drive-link)"},
                },
                "required": ["document_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sheets_read",
            "description": (
                "Læs celler fra et Google Sheets-regneark via spreadsheet_id + A1-range "
                "(fx 'Ark1!A1:D20'). Brugerens EGEN konto. Kræver forbundet Google Sheets."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {"type": "string", "description": "Sheets spreadsheet-id"},
                    "range": {"type": "string", "description": "A1-range, fx 'Ark1!A1:D20'"},
                },
                "required": ["spreadsheet_id", "range"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "slides_read",
            "description": (
                "Læs titler og tekst fra et Google Slides-show via presentation_id "
                "(brugerens EGEN konto). Kræver forbundet Google Slides."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "presentation_id": {"type": "string", "description": "Slides presentation-id"},
                },
                "required": ["presentation_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calendar_create_event",
            "description": (
                "Opret en begivenhed i brugerens primære Google Calendar. KRÆVER brugerens "
                "godkendelse (approval-kort) — kald bare værktøjet direkte. start/end = ISO-8601 "
                "(fx '2026-06-18T09:00:00+02:00'); udelades end sættes den til start +1 time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Titel på aftalen"},
                    "start": {"type": "string", "description": "Start, ISO-8601 med tidszone"},
                    "end": {"type": "string", "description": "Slut, ISO-8601 (valgfri)"},
                    "description": {"type": "string", "description": "Beskrivelse (valgfri)"},
                    "location": {"type": "string", "description": "Sted (valgfri)"},
                },
                "required": ["summary", "start"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "docs_append",
            "description": (
                "Tilføj tekst i slutningen af et Google Docs-dokument (document_id). KRÆVER "
                "brugerens godkendelse (approval-kort) — kald bare værktøjet direkte."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "Docs document-id"},
                    "text": {"type": "string", "description": "Teksten der tilføjes"},
                },
                "required": ["document_id", "text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sheets_write",
            "description": (
                "Skriv celler i et Google Sheets-regneark (overskriver range). KRÆVER brugerens "
                "godkendelse (approval-kort) — kald bare værktøjet direkte. values = liste af rækker, "
                "fx [[\"Navn\",\"Beløb\"],[\"Leje\",\"8000\"]]."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {"type": "string", "description": "Sheets spreadsheet-id"},
                    "range": {"type": "string", "description": "A1-range, fx 'Ark1!A1:B2'"},
                    "values": {"type": "array", "description": "Liste af rækker (liste af lister)",
                               "items": {"type": "array", "items": {"type": "string"}}},
                },
                "required": ["spreadsheet_id", "range", "values"],
            },
        },
    },
]


def _get(user_id: str, url: str, params: dict | None, err_prefix: str) -> dict:
    """Fælles GET med brugerens Google-token. → {status, data} | {status:error,...}."""
    token = get_fresh_token(user_id, _PROVIDER)
    if not token or not token.get("access_token"):
        return {"status": "error", "error": f"{err_prefix}_not_connected"}
    try:
        import httpx
        r = httpx.get(url, headers={"Authorization": f"Bearer {token['access_token']}"},
                      params=params or {}, timeout=20)
        if r.status_code == 401:
            return {"status": "error", "error": f"{err_prefix}_not_connected"}
        if r.status_code == 403:
            return {"status": "error", "error": f"{err_prefix}_scope_missing"}
        if r.status_code != 200:
            return {"status": "error", "error": f"{err_prefix}_http_{r.status_code}"}
        return {"status": "ok", "data": r.json()}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": f"{err_prefix}_request_failed: {e}"}


def _send(user_id: str, method: str, url: str, *, json_body: dict | None = None,
          params: dict | None = None, err_prefix: str = "google") -> dict:
    """Skrive-kald (POST/PUT) med brugerens Google-token. Bruges af create/edit-tools."""
    token = get_fresh_token(user_id, _PROVIDER)
    if not token or not token.get("access_token"):
        return {"status": "error", "error": f"{err_prefix}_not_connected"}
    try:
        import httpx
        r = httpx.request(method, url, headers={"Authorization": f"Bearer {token['access_token']}"},
                          json=json_body, params=params or {}, timeout=20)
        if r.status_code == 401:
            return {"status": "error", "error": f"{err_prefix}_not_connected"}
        if r.status_code == 403:
            return {"status": "error", "error": f"{err_prefix}_scope_missing"}
        if r.status_code not in (200, 201):
            return {"status": "error", "error": f"{err_prefix}_http_{r.status_code}"}
        return {"status": "ok", "data": r.json()}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": f"{err_prefix}_request_failed: {e}"}


def _clamp(n, lo: int, hi: int, default: int) -> int:
    try:
        return max(lo, min(hi, int(n)))
    except (TypeError, ValueError):  # uden tal → standardvaerdien; en ugyldig graense er ikke en haendelse
        return default


def list_events(user_id: str, *, max_results: int = 10) -> dict:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    res = _get(user_id, "https://www.googleapis.com/calendar/v3/calendars/primary/events",
               {"maxResults": _clamp(max_results, 1, 25, 10), "singleEvents": "true",
                "orderBy": "startTime", "timeMin": now}, "calendar")
    if res["status"] != "ok":
        return res
    events = []
    for ev in (res["data"].get("items") or []):
        start = ev.get("start", {})
        events.append({
            "id": ev.get("id"),
            "summary": ev.get("summary", "(uden titel)"),
            "start": start.get("dateTime") or start.get("date", ""),
            "location": ev.get("location", ""),
            "link": ev.get("htmlLink", ""),
        })
    return {"status": "ok", "events": events, "count": len(events)}


def drive_search(user_id: str, *, query: str = "", max_results: int = 10) -> dict:
    params = {
        "pageSize": _clamp(max_results, 1, 25, 10),
        "fields": "files(id,name,mimeType,modifiedTime,webViewLink)",
        "orderBy": "modifiedTime desc",
    }
    q = (query or "").strip()
    if q:
        params["q"] = f"name contains '{q.replace(chr(39), '')}' and trashed = false"
    else:
        params["q"] = "trashed = false"
    res = _get(user_id, "https://www.googleapis.com/drive/v3/files", params, "drive")
    if res["status"] != "ok":
        return res
    files = [
        {"id": f.get("id"), "name": f.get("name"), "type": f.get("mimeType"),
         "modified": f.get("modifiedTime", ""), "link": f.get("webViewLink", "")}
        for f in (res["data"].get("files") or [])
    ]
    return {"status": "ok", "files": files, "count": len(files)}


#: Google-native filer kan ikke hentes som bytes — de skal EKSPORTERES til et
#: rigtigt format. Uden denne tabel ville `drive_download` på en Docs give
#: `drive_http_400` og se ud som en fejl i forbindelsen.
_EXPORT_AS: dict[str, tuple[str, str]] = {
    "application/vnd.google-apps.document": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
    "application/vnd.google-apps.presentation": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"),
    "application/vnd.google-apps.drawing": ("image/png", ".png"),
}


def drive_download(user_id: str, file_id: str, *, export_as: str = "") -> dict:
    """Hent en Drive-fil ned til brugerens EGEN filmappe og returnér et link.

    Hvorfor den gemmer i stedet for at returnere bytes
    -------------------------------------------------
    Et værktøjssvar er tekst. En PDF på 61 kB som base64 er 82 kB tekst i
    prompten — det æder konteksten og kan ikke bruges til noget. Filen lægges
    derfor i brugerens isolerede mappe (samme som `publish_file`) og svaret
    bærer et download-link. Det gør den samtidig synlig i desk som et
    fil-kort, fordi klienten kender `/files/…`-formen.

    Google-native filer (Docs/Sheets/Slides) har ingen bytes — de eksporteres
    til .docx/.xlsx/.pptx. `export_as` kan tvinge et andet format, fx
    `"pdf"` for alle tre.
    """
    fid = (file_id or "").strip()
    if not fid:
        return {"status": "error", "error": "file_id mangler"}

    meta = _get(user_id, f"https://www.googleapis.com/drive/v3/files/{fid}",
                {"fields": "id,name,mimeType,size", "supportsAllDrives": "true"},
                "drive")
    if meta["status"] != "ok":
        return meta
    data = meta.get("data") or {}
    navn = str(data.get("name") or fid).strip()
    mime = str(data.get("mimeType") or "")

    token = get_fresh_token(user_id, _PROVIDER)
    if not token or not token.get("access_token"):
        return {"status": "error", "error": "drive_not_connected"}

    valg = (export_as or "").strip().lower()
    if mime in _EXPORT_AS:
        ud_mime, endelse = _EXPORT_AS[mime]
        if valg == "pdf":
            ud_mime, endelse = "application/pdf", ".pdf"
        elif valg in ("docx", "xlsx", "pptx"):
            for m, (mm, ee) in _EXPORT_AS.items():
                if ee == "." + valg:
                    ud_mime, endelse = mm, ee
                    break
        url = f"https://www.googleapis.com/drive/v3/files/{fid}/export"
        params = {"mimeType": ud_mime}
    else:
        ud_mime, endelse = mime or "application/octet-stream", ""
        # En Drive-fil kan hedde «brev» uden endelse. Så kan modtageren ikke
        # åbne den, uanset at indholdet er en fuldgyldig PDF. Endelsen udledes
        # derfor af mime-typen når navnet ikke selv bærer den.
        if mime:
            import mimetypes
            gæt = mimetypes.guess_extension(mime.split(";")[0].strip()) or ""
            if gæt == ".jpe":
                gæt = ".jpg"
            endelse = gæt
        url = f"https://www.googleapis.com/drive/v3/files/{fid}"
        params = {"alt": "media", "supportsAllDrives": "true"}

    try:
        import httpx
        r = httpx.get(url, headers={"Authorization": f"Bearer {token['access_token']}"},
                      params=params, timeout=60, follow_redirects=True)
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": f"drive_request_failed: {e}"}
    if r.status_code == 401:
        return {"status": "error", "error": "drive_not_connected"}
    if r.status_code == 403:
        return {"status": "error", "error": "drive_scope_missing"}
    if r.status_code != 200:
        return {"status": "error", "error": f"drive_http_{r.status_code}"}

    # Endelsen følger INDHOLDET, ikke filnavnet: en Docs der eksporteres til
    # docx skal heddde .docx, ellers kan modtageren ikke åbne den.
    rent = navn if endelse and navn.lower().endswith(endelse) else f"{navn}{endelse}"
    from core.runtime.workspace_paths import NoUserContextError, published_file_path
    try:
        dest = published_file_path(rent, opret_mappe=True)
    except NoUserContextError:  # fail-closed: uden bruger maa filen ikke havne i en faelles mappe
        return {"status": "error", "error": "ingen bruger i konteksten — filen blev ikke hentet"}
    except ValueError as exc:  # et ugyldigt filnavn er kalderens fejl, ikke en haendelse
        return {"status": "error", "error": str(exc)}
    try:
        dest.write_bytes(r.content)
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}

    try:
        from core.runtime.secrets import read_runtime_key
        base = str(read_runtime_key("public_base_url", "JARVIS_PUBLIC_BASE_URL") or "").strip()
    except Exception:
        base = ""
    base = (base or "http://localhost:8080").rstrip("/")
    return {
        "status": "ok",
        "filename": dest.name,
        "url": f"{base}/files/{dest.name}",
        "mime_type": ud_mime,
        "size_bytes": len(r.content),
        "source_id": fid,
        "exported_from": mime if mime in _EXPORT_AS else "",
    }


def _doc_text(content: list) -> str:
    out = []
    for el in content or []:
        para = el.get("paragraph")
        if not para:
            continue
        for pe in para.get("elements") or []:
            tr = pe.get("textRun")
            if tr and tr.get("content"):
                out.append(tr["content"])
    return "".join(out).strip()


def docs_read(user_id: str, document_id: str) -> dict:
    if not (document_id or "").strip():
        return {"status": "error", "error": "document_id_required"}
    res = _get(user_id, f"https://docs.googleapis.com/v1/documents/{document_id}", None, "docs")
    if res["status"] != "ok":
        return res
    d = res["data"]
    text = _doc_text((d.get("body") or {}).get("content") or [])
    return {"status": "ok", "title": d.get("title", ""), "text": text[:20000]}


def sheets_read(user_id: str, spreadsheet_id: str, cell_range: str) -> dict:
    if not (spreadsheet_id or "").strip():
        return {"status": "error", "error": "spreadsheet_id_required"}
    if not (cell_range or "").strip():
        return {"status": "error", "error": "range_required"}
    res = _get(user_id,
               f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{cell_range}",
               None, "sheets")
    if res["status"] != "ok":
        return res
    return {"status": "ok", "range": res["data"].get("range", ""),
            "values": res["data"].get("values", [])}


def _slides_text(pres: dict) -> list[dict]:
    slides = []
    for i, slide in enumerate(pres.get("slides") or [], start=1):
        texts = []
        for pe in slide.get("pageElements") or []:
            shape = pe.get("shape") or {}
            for te in (shape.get("text") or {}).get("textElements") or []:
                tr = te.get("textRun")
                if tr and tr.get("content"):
                    texts.append(tr["content"].strip())
        slides.append({"slide": i, "text": " ".join(t for t in texts if t)})
    return slides


def slides_read(user_id: str, presentation_id: str) -> dict:
    if not (presentation_id or "").strip():
        return {"status": "error", "error": "presentation_id_required"}
    res = _get(user_id, f"https://slides.googleapis.com/v1/presentations/{presentation_id}",
               None, "slides")
    if res["status"] != "ok":
        return res
    d = res["data"]
    slides = _slides_text(d)
    return {"status": "ok", "title": d.get("title", ""), "slide_count": len(slides), "slides": slides}


# ── Skrive-tools (kaldes kun efter approval — gating sker i simple_tools) ──

def create_event(user_id: str, summary: str, start: str, *, end: str = "",
                 description: str = "", location: str = "") -> dict:
    """Opret en begivenhed i brugerens primære kalender. start/end = ISO-8601."""
    if not (summary or "").strip():
        return {"status": "error", "error": "summary_required"}
    if not (start or "").strip():
        return {"status": "error", "error": "start_required"}
    if not end:
        try:
            from datetime import datetime, timedelta
            end = (datetime.fromisoformat(start.replace("Z", "+00:00")) + timedelta(hours=1)).isoformat()
        except (ValueError, TypeError):
            end = start
    body = {
        "summary": summary,
        "start": {"dateTime": start},
        "end": {"dateTime": end},
    }
    if description:
        body["description"] = description
    if location:
        body["location"] = location
    res = _send(user_id, "POST",
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                json_body=body, err_prefix="calendar")
    if res["status"] != "ok":
        return res
    return {"status": "ok", "id": res["data"].get("id"), "link": res["data"].get("htmlLink", "")}


def append_doc(user_id: str, document_id: str, text: str) -> dict:
    """Tilføj tekst i slutningen af et Google Docs-dokument."""
    if not (document_id or "").strip():
        return {"status": "error", "error": "document_id_required"}
    if not (text or ""):
        return {"status": "error", "error": "text_required"}
    body = {"requests": [{"insertText": {"endOfSegmentLocation": {}, "text": text}}]}
    res = _send(user_id, "POST",
                f"https://docs.googleapis.com/v1/documents/{document_id}:batchUpdate",
                json_body=body, err_prefix="docs")
    if res["status"] != "ok":
        return res
    return {"status": "ok", "document_id": document_id}


def write_sheet(user_id: str, spreadsheet_id: str, cell_range: str, values: list) -> dict:
    """Skriv celler i et Google Sheets-regneark (overskriver range). values = liste af rækker."""
    if not (spreadsheet_id or "").strip():
        return {"status": "error", "error": "spreadsheet_id_required"}
    if not (cell_range or "").strip():
        return {"status": "error", "error": "range_required"}
    if not isinstance(values, list) or not values:
        return {"status": "error", "error": "values_required"}
    res = _send(user_id, "PUT",
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{cell_range}",
                json_body={"values": values},
                params={"valueInputOption": "USER_ENTERED"}, err_prefix="sheets")
    if res["status"] != "ok":
        return res
    return {"status": "ok", "updated": res["data"].get("updatedCells", 0)}
