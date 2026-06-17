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


def _clamp(n, lo: int, hi: int, default: int) -> int:
    try:
        return max(lo, min(hi, int(n)))
    except (TypeError, ValueError):
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
