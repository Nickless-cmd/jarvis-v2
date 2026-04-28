"""Internal loopback endpoint for cross-process Discord dispatch.

The Discord gateway lives in the runtime process (jarvis-runtime, port 8011).
Tools that run in the api process (jarvis-api, port 80) can't reach the
gateway's in-memory queue directly, so they POST their send intent here.

Loopback-only — binds on 127.0.0.1 already, but we also sanity-check the
client host and refuse to forward if the gateway isn't local to this
process (prevents dispatch loops).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core.services.discord_gateway import (
    _is_gateway_owner,
    send_discord_file,
    send_discord_message,
    send_dm_to_owner,
    send_dm_to_user,
)

router = APIRouter(prefix="/api/internal/discord", tags=["internal"])


class DispatchRequest(BaseModel):
    action: str
    args: dict = {}


@router.post("/dispatch")
def dispatch(req: DispatchRequest, request: Request) -> dict:
    client_host = request.client.host if request.client else ""
    if client_host not in {"127.0.0.1", "::1", "localhost"}:
        raise HTTPException(status_code=403, detail="loopback-only")

    if not _is_gateway_owner():
        raise HTTPException(
            status_code=503,
            detail="gateway not owned by this process — refusing to forward",
        )

    action = req.action
    args = req.args or {}

    if action == "send_message":
        send_discord_message(int(args["channel_id"]), str(args["text"]))
        return {"status": "queued"}
    if action == "send_file":
        return send_discord_file(
            int(args["channel_id"]),
            str(args["text"]),
            str(args["file_path"]),
        )
    if action == "send_dm_to_owner":
        return send_dm_to_owner(str(args["text"]), float(args.get("timeout", 10.0)))
    if action == "send_dm_to_user":
        return send_dm_to_user(
            str(args["recipient_discord_id"]),
            str(args["text"]),
            float(args.get("timeout", 10.0)),
        )
    if action == "discord_channel":
        # Re-invoke the tool here, where _is_gateway_owner() is True so the
        # local search/fetch/send path runs against the in-memory _client.
        from core.tools.simple_tools import _exec_discord_channel
        return {"result": _exec_discord_channel(args)}

    raise HTTPException(status_code=400, detail=f"unknown action: {action}")
