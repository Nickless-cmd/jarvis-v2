"""Calendar tools — Google Calendar with .ics fallback."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

_ICS_PATH = Path.home() / ".jarvis-v2" / "calendar.ics"


def _read_runtime_key(key: str) -> str:
    try:
        from core.runtime.config import SETTINGS_FILE
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return str(data.get(key) or "")
    except Exception:
        return ""


# ── Google Calendar helpers ────────────────────────────────────────────────

def _get_gcal_service():
    """Build Google Calendar service from credentials in runtime.json."""
    creds_json = _read_runtime_key("google_calendar_credentials")
    if not creds_json:
        return None
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        creds_data = json.loads(creds_json) if isinstance(creds_json, str) else creds_json
        creds = Credentials.from_authorized_user_info(creds_data)
        return build("calendar", "v3", credentials=creds)
    except Exception:
        return None


def _gcal_list_events(days_ahead: int) -> list[dict]:
    service = _get_gcal_service()
    if not service:
        return []
    now = datetime.utcnow().isoformat() + "Z"
    end = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + "Z"
    try:
        events_result = service.events().list(
            calendarId="primary",
            timeMin=now, timeMax=end,
            singleEvents=True, orderBy="startTime",
            maxResults=50,
        ).execute()
        items = events_result.get("items", [])
        return [
            {
                "id": e.get("id"),
                "title": e.get("summary", "(no title)"),
                "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
                "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
                "description": e.get("description", ""),
                "location": e.get("location", ""),
            }
            for e in items
        ]
    except Exception:
        return []


def _gcal_create_event(title: str, start_dt: datetime, end_dt: datetime) -> dict | None:
    service = _get_gcal_service()
    if not service:
        return None
    try:
        event = service.events().insert(
            calendarId="primary",
            body={
                "summary": title,
                "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
            },
        ).execute()
        return {"id": event.get("id"), "title": event.get("summary"), "start": event.get("start", {}).get("dateTime")}
    except Exception:
        return None


def _gcal_delete_event(event_id: str) -> bool:
    service = _get_gcal_service()
    if not service:
        return False
    try:
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return True
    except Exception:
        return False


# ── ICS fallback ──────────────────────────────────────────────────────────

def _ics_list_events(days_ahead: int) -> list[dict]:
    if not _ICS_PATH.exists():
        return []
    try:
        import icalendar
        cal = icalendar.Calendar.from_ical(_ICS_PATH.read_bytes())
        cutoff = date.today() + timedelta(days=days_ahead)
        events = []
        for component in cal.walk():
            if component.name != "VEVENT":
                continue
            dtstart = component.get("DTSTART")
            if not dtstart:
                continue
            start = dtstart.dt
            start_date = start.date() if hasattr(start, "date") else start
            if start_date < date.today() or start_date > cutoff:
                continue
            events.append({
                "id": str(component.get("UID", "")),
                "title": str(component.get("SUMMARY", "(no title)")),
                "start": str(start),
                "end": str(component.get("DTEND", {}).dt if component.get("DTEND") else ""),
                "description": str(component.get("DESCRIPTION", "")),
                "location": str(component.get("LOCATION", "")),
            })
        return sorted(events, key=lambda e: e["start"])
    except ImportError:
        return []
    except Exception:
        return []


def _ics_create_event(title: str, start_dt: datetime, end_dt: datetime) -> dict | None:
    try:
        import icalendar
        import uuid as _uuid
        cal = icalendar.Calendar()
        if _ICS_PATH.exists():
            cal = icalendar.Calendar.from_ical(_ICS_PATH.read_bytes())
        event = icalendar.Event()
        uid = str(_uuid.uuid4())
        event.add("UID", uid)
        event.add("SUMMARY", title)
        event.add("DTSTART", start_dt)
        event.add("DTEND", end_dt)
        event.add("DTSTAMP", datetime.utcnow())
        cal.add_component(event)
        _ICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        _ICS_PATH.write_bytes(cal.to_ical())
        return {"id": uid, "title": title, "start": start_dt.isoformat()}
    except ImportError:
        return None
    except Exception:
        return None


def _ics_delete_event(event_id: str) -> bool:
    if not _ICS_PATH.exists():
        return False
    try:
        import icalendar
        cal = icalendar.Calendar.from_ical(_ICS_PATH.read_bytes())
        new_cal = icalendar.Calendar()
        for attr in ("VERSION", "PRODID", "CALSCALE", "METHOD"):
            if cal.get(attr):
                new_cal.add(attr, cal[attr])
        removed = False
        for component in cal.walk():
            if component.name == "VEVENT" and str(component.get("UID", "")) == event_id:
                removed = True
                continue
            if component.name != "VCALENDAR":
                new_cal.add_component(component)
        _ICS_PATH.write_bytes(new_cal.to_ical())
        return removed
    except Exception:
        return False


# ── Public executors ──────────────────────────────────────────────────────

def _exec_list_events(args: dict[str, Any]) -> dict[str, Any]:
    days_ahead = max(1, min(int(args.get("days_ahead") or 7), 90))
    has_gcal = bool(_read_runtime_key("google_calendar_credentials"))

    if has_gcal:
        events = _gcal_list_events(days_ahead)
        source = "google_calendar"
    else:
        events = _ics_list_events(days_ahead)
        source = "ics_file"

    if not has_gcal and not _ICS_PATH.exists():
        return {
            "status": "ok",
            "events": [],
            "source": "none",
            "message": "No calendar configured. Set google_calendar_credentials in runtime.json or place a calendar.ics at ~/.jarvis-v2/calendar.ics",
        }

    return {"status": "ok", "events": events, "days_ahead": days_ahead, "source": source, "count": len(events)}


def _exec_create_event(args: dict[str, Any]) -> dict[str, Any]:
    title = str(args.get("title") or "").strip()
    date_str = str(args.get("date") or "").strip()
    time_str = str(args.get("time") or "10:00").strip()
    duration_min = int(args.get("duration_minutes") or 60)

    if not title:
        return {"status": "error", "error": "title is required"}
    if not date_str:
        return {"status": "error", "error": "date is required (YYYY-MM-DD)"}

    try:
        start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        return {"status": "error", "error": f"Invalid date/time format. Use date=YYYY-MM-DD time=HH:MM"}
    end_dt = start_dt + timedelta(minutes=duration_min)

    has_gcal = bool(_read_runtime_key("google_calendar_credentials"))
    if has_gcal:
        result = _gcal_create_event(title, start_dt, end_dt)
        source = "google_calendar"
    else:
        result = _ics_create_event(title, start_dt, end_dt)
        source = "ics_file"

    if not result:
        return {"status": "error", "error": f"Failed to create event via {source}"}
    return {"status": "ok", "event": result, "source": source}


def _exec_delete_event(args: dict[str, Any]) -> dict[str, Any]:
    event_id = str(args.get("event_id") or "").strip()
    if not event_id:
        return {"status": "error", "error": "event_id is required"}

    has_gcal = bool(_read_runtime_key("google_calendar_credentials"))
    if has_gcal:
        ok = _gcal_delete_event(event_id)
        source = "google_calendar"
    else:
        ok = _ics_delete_event(event_id)
        source = "ics_file"

    if not ok:
        return {"status": "error", "error": f"Event not found or could not be deleted (source: {source})"}
    return {"status": "ok", "deleted": event_id, "source": source}


CALENDAR_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_events",
            "description": "List upcoming calendar events. Uses Google Calendar if configured, otherwise reads ~/.jarvis-v2/calendar.ics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_ahead": {"type": "integer", "description": "How many days ahead to look (default 7, max 90)."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_event",
            "description": "Create a calendar event. Uses Google Calendar if configured, otherwise writes to ~/.jarvis-v2/calendar.ics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Event title/summary."},
                    "date": {"type": "string", "description": "Event date in YYYY-MM-DD format."},
                    "time": {"type": "string", "description": "Event start time in HH:MM format (default 10:00)."},
                    "duration_minutes": {"type": "integer", "description": "Duration in minutes (default 60)."},
                },
                "required": ["title", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_event",
            "description": "Delete a calendar event by its ID (obtained from list_events).",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "The event ID to delete."},
                },
                "required": ["event_id"],
            },
        },
    },
]
