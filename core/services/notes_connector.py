"""Huskesedler-connector (lokal) — simple per-bruger notater.

Lokalt værktøj, ingen OAuth. Per-bruger isoleret i runtime_state under
`user_notes` = {uid: [{id, text, ts}]}. Privatlivs-først: en brugers sedler er
aldrig synlige for andre.
"""
from __future__ import annotations

import time

import core.runtime.db_core as dbc

_KEY = "user_notes"
_MAX_NOTES = 500

NOTES_CONNECTOR_TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "note_add",
            "description": "Gem en huskeseddel for brugeren (per-bruger, privat). Returnerer note-id.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string", "description": "Sedlens indhold"}},
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "note_list",
            "description": "List brugerens huskesedler (nyeste først).",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "description": "Maks antal (standard 20)"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "note_search",
            "description": "Søg i brugerens huskesedler (fritekst, ikke-versalfølsom).",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Søgeord"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "note_delete",
            "description": "Slet en huskeseddel via dens id.",
            "parameters": {
                "type": "object",
                "properties": {"id": {"type": "string", "description": "Note-id fra note_list/note_add"}},
                "required": ["id"],
            },
        },
    },
]


def _store() -> dict:
    s = dbc.get_runtime_state_value(_KEY, {}) or {}
    return s if isinstance(s, dict) else {}


def _bucket(user_id: str) -> list[dict]:
    b = _store().get((user_id or "").strip())
    return list(b) if isinstance(b, list) else []


def _save(user_id: str, notes: list[dict]) -> None:
    store = _store()
    store[(user_id or "").strip()] = notes[-_MAX_NOTES:]
    dbc.set_runtime_state_value(_KEY, store)


def add_note(user_id: str, text: str, *, now: float | None = None) -> dict:
    text = (text or "").strip()
    if not text:
        return {"status": "error", "error": "text_required"}
    notes = _bucket(user_id)
    ts = now if now is not None else time.time()
    note = {"id": f"n{int(ts * 1000)}", "text": text, "ts": ts}
    notes.append(note)
    _save(user_id, notes)
    return {"status": "ok", "id": note["id"]}


def list_notes(user_id: str, *, limit: int = 20) -> dict:
    try:
        lim = max(1, min(100, int(limit)))
    except (TypeError, ValueError):
        lim = 20
    notes = sorted(_bucket(user_id), key=lambda n: n.get("ts", 0), reverse=True)[:lim]
    return {"status": "ok", "notes": notes, "count": len(notes)}


def search_notes(user_id: str, query: str) -> dict:
    q = (query or "").strip().lower()
    if not q:
        return {"status": "error", "error": "query_required"}
    hits = [n for n in _bucket(user_id) if q in str(n.get("text", "")).lower()]
    hits.sort(key=lambda n: n.get("ts", 0), reverse=True)
    return {"status": "ok", "notes": hits, "count": len(hits)}


def delete_note(user_id: str, note_id: str) -> dict:
    note_id = (note_id or "").strip()
    notes = _bucket(user_id)
    kept = [n for n in notes if n.get("id") != note_id]
    if len(kept) == len(notes):
        return {"status": "error", "error": "not_found"}
    _save(user_id, kept)
    return {"status": "ok", "deleted": note_id}
