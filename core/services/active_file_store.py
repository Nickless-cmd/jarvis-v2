"""Live "aktiv fil" — den sti Jarvis senest læste/skrev (file-tree-control-spec).

Lader desk-appens fil-træ markere filen Jarvis netop nu rører, så brugeren kan
følge med live (ligesom preview-panelet). DB-backed (runtime_state_kv), cross-
proces (runtime skriver via tool-handlere, api læser via poll-endpoint). Pr.
bruger så ingen ser en andens aktivitet.
"""
from __future__ import annotations

from core.runtime.db import get_runtime_state_value, set_runtime_state_value

_KEY = "active_file_by_user"


def _load() -> dict:
    raw = get_runtime_state_value(_KEY, {})
    return raw if isinstance(raw, dict) else {}


def set_active_file(user_id: str, path: str, op: str, *, ts: float | None = None) -> None:
    """Registrér at brugeren (Jarvis i deres kontekst) rører `path` (op=read/write).

    ts gives ind udefra (Date.now/time.time) for at undgå tids-kald her — holder
    funktionen ren/testbar og resume-sikker. Fejler stille (må aldrig vælte et
    tool-kald)."""
    try:
        path = str(path or "").strip()
        if not path:
            return
        data = _load()
        data[str(user_id or "owner")] = {"path": path, "op": str(op or "read"), "ts": ts}
        set_runtime_state_value(_KEY, data)
    except Exception:
        pass


def get_active_file(user_id: str) -> dict | None:
    """Seneste aktiv-fil for brugeren, eller None."""
    rec = _load().get(str(user_id or "owner"))
    return rec if isinstance(rec, dict) and rec.get("path") else None


def clear_active_file(user_id: str) -> None:
    try:
        data = _load()
        if str(user_id or "owner") in data:
            del data[str(user_id or "owner")]
            set_runtime_state_value(_KEY, data)
    except Exception:
        pass
