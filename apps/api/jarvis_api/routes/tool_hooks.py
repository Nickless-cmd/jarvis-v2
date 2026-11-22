"""Owner-facing read/reload surface for configured shell hooks and their JSONL log."""
from __future__ import annotations

import json
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from core.services import tool_shell_hooks

router = APIRouter(prefix="/api/tool-hooks", tags=["tool-hooks"])


def _log_metadata() -> dict[str, Any]:
    path = tool_shell_hooks.LOG_STI
    rotated = path.with_name(f"{path.name}.1")
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    return {
        "path": str(path),
        "exists": path.is_file(),
        "size_bytes": size,
        "rotated": rotated.is_file(),
        "rotated_path": str(rotated),
    }


def _timestamp(entry: dict[str, Any]) -> datetime | None:
    raw = str(entry.get("time") or entry.get("timestamp") or entry.get("ts") or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        # en loglinje med ufuldstændigt tidsstempel skal tælles som uden tid,
        # ikke vælte hele log-visningen
        return None
    return parsed.replace(tzinfo=parsed.tzinfo or UTC).astimezone(UTC)


def _confinement(entry: dict[str, Any]) -> dict[str, Any]:
    direct = entry.get("confinement")
    if isinstance(direct, dict):
        return direct
    arguments = entry.get("arguments")
    if isinstance(arguments, dict):
        result = arguments.get("__result__")
        if isinstance(result, dict) and isinstance(result.get("confinement"), dict):
            return result["confinement"]
    return {}


def _normalise_entry(entry: dict[str, Any]) -> dict[str, Any]:
    arguments = entry.get("arguments")
    nested_result = arguments.get("__result__") if isinstance(arguments, dict) else None
    result = entry.get("result", entry.get("status"))
    if result is None and isinstance(nested_result, dict):
        result = nested_result.get("status")
    confinement = _confinement(entry)
    return {
        **entry,
        "time": str(entry.get("time") or entry.get("timestamp") or entry.get("ts") or ""),
        "tool": str(entry.get("tool") or entry.get("tool_name") or ""),
        "phase": str(entry.get("phase") or ""),
        "result": result if result is not None else "",
        "confinement": confinement,
    }


def _coverage(entries: list[dict[str, Any]]) -> dict[str, int]:
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    counts = {"confined": 0, "fail_open": 0, "non_shell": 0}
    for entry in entries:
        timestamp = _timestamp(entry)
        if timestamp is not None and timestamp < cutoff:
            continue
        if str(entry.get("tool") or entry.get("tool_name") or "") != "bash":
            counts["non_shell"] += 1
        elif _confinement(entry).get("actual") is True:
            counts["confined"] += 1
        else:
            counts["fail_open"] += 1
    return counts


def _read_entries() -> tuple[list[dict[str, Any]], int]:
    entries: list[dict[str, Any]] = []
    invalid = 0
    try:
        with tool_shell_hooks.LOG_STI.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    value = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    invalid += 1
                    continue
                if isinstance(value, dict):
                    entries.append(value)
                else:
                    invalid += 1
    except OSError:
        # logfilen kan mangle (ingen hooks har kørt endnu) eller være låst under
        # rotation — fladen skal vise tomt, ikke svare 500
        pass
    return entries, invalid


@router.get("")
def get_tool_hooks() -> dict[str, Any]:
    tool_shell_hooks.ensure_loaded()
    return {**tool_shell_hooks.status(), "log": _log_metadata()}


@router.post("/reload")
def reload_tool_hooks() -> dict[str, Any]:
    tool_shell_hooks.ensure_loaded(tving=True)
    return {**tool_shell_hooks.status(), "log": _log_metadata()}


@router.get("/log")
def get_tool_hook_log(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
    entries, invalid = _read_entries()
    tail = [_normalise_entry(entry) for entry in deque(entries, maxlen=limit)]
    return {
        "entries": tail,
        "coverage_24h": _coverage(entries),
        "invalid_lines": invalid,
        "log": _log_metadata(),
    }


@router.get("/config")
def get_tool_hook_config() -> dict[str, Any]:
    """Det rå dokument redigeringen arbejder på — med kommandoerne."""
    _kraev_ejer()
    return tool_shell_hooks.read_config()


def _kraev_ejer() -> str:
    """En hook-regel er en shell-kommando på hvert tool-kald — kun ejeren rører den."""
    from core.identity.workspace_context import current_user_id

    user_id = str(current_user_id() or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Ikke logget ind")
    from apps.api.jarvis_api.routes.account import _current_role

    if _current_role(user_id) != "owner":
        raise HTTPException(status_code=403, detail="owner_required")
    return user_id


class HookRule(BaseModel):
    name: str
    match: str
    before: str = ""
    after: str = ""
    timeout_s: float = 5.0
    cwd: str = ""


class HooksConfigBody(BaseModel):
    """Body for gem og tør-kørsel.

    ``extra="forbid"`` og et påkrævet ``hooks`` er ikke kosmetik. Målt
    22/11-2026: uden dem ignorede pydantic et ukendt feltnavn og brugte
    tomme defaults — så en klient der sendte ``{"config": {...}}`` i stedet
    for ``{"hooks": [...]}`` gemte en TOM konfiguration og afvæbnede hver
    regel uden en eneste fejlmeddelelse.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    hooks: list[HookRule]
    approved: bool = False


@router.put("")
def put_tool_hooks(body: HooksConfigBody) -> dict[str, Any]:
    """Erstat hook-konfigurationen. Validering sker før filen røres."""
    _kraev_ejer()
    if not body.approved:
        # Reglerne bestemmer hvad der kører shell på HVERT model-initieret
        # tool-kald. Et gem uden en bevidst bekræftelse ville være en ændring
        # af eksekveringsfladen gemt bag et enkelt klik.
        raise HTTPException(status_code=409, detail="explicit_approval_required")

    resultat = tool_shell_hooks.save_config(body.model_dump(exclude={"approved"}))
    if not resultat.get("ok"):
        # 422: input var forstået, men ugyldigt — brugeren skal se ALLE fejl
        raise HTTPException(status_code=422, detail={"fejl": resultat.get("fejl") or []})
    return {**resultat, "log": _log_metadata()}


@router.post("/validate")
def validate_tool_hooks(body: HooksConfigBody) -> dict[str, Any]:
    """Tør kørsel: svarer hvad der ville fejle, uden at skrive noget."""
    _kraev_ejer()
    fejl = tool_shell_hooks.validate_config(body.model_dump(exclude={"approved"}))
    return {"ok": not fejl, "fejl": fejl}
