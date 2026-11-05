"""MCP Apps host-bro: `ui://` resource -> sikker widget i samtalen.

MCP Apps er TO ting: et almindeligt tool-resultat og en HTML-resource peget
ud af tool-definitionens ``_meta.ui.resourceUri``. Dette modul holder dem
adskilt. Resultatet går fortsat gennem MCP-klientens untrusted-hegn til
modellen; HTML'en bliver en genereret attachment som kun rendereren læser.

Første version er med vilje netværkslukket. MCP Apps kan deklarere CSP-domæner,
men at honorere dem uden en særskilt brugerbeslutning ville gøre en godkendt
MCP-server til en generel browser-proxy. Bundled apps virker; eksterne scripts,
fetches og frames gør ikke.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MCP_APP_MIME = "text/html;profile=mcp-app"
MAX_HTML_BYTES = 512 * 1024
MAX_RESULT_BYTES = 256 * 1024

_CSP = (
    "default-src 'none'; "
    "script-src 'unsafe-inline' 'unsafe-eval' blob:; "
    "style-src 'unsafe-inline'; "
    "img-src data: blob:; font-src data:; media-src data: blob:; "
    "connect-src 'none'; frame-src 'none'; object-src 'none'; "
    "base-uri 'none'; form-action 'none'"
)


def resource_uri(tool: dict[str, Any] | None) -> str:
    """Foretræk den endelige nested form; behold legacy-interoperabilitet."""
    meta = (tool or {}).get("_meta")
    if not isinstance(meta, dict):
        return ""
    ui = meta.get("ui")
    nested = ui.get("resourceUri") if isinstance(ui, dict) else ""
    uri = str(nested or meta.get("ui/resourceUri") or "").strip()
    return uri if uri.startswith("ui://") else ""


def tool_visible_to(tool: dict[str, Any] | None, audience: str) -> bool:
    """Håndhæv MCP Apps' model/app-skel; manglende metadata betyder begge."""
    if audience not in {"model", "app"}:
        return False
    meta = (tool or {}).get("_meta")
    ui = meta.get("ui") if isinstance(meta, dict) else None
    visibility = ui.get("visibility") if isinstance(ui, dict) else None
    if visibility is None:
        return True
    if not isinstance(visibility, list):
        return False
    return audience in {str(item) for item in visibility}


def extract_html(resource: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Hent den første HTML-tekstblok fra et `resources/read`-resultat."""
    for item in list(resource.get("contents") or []):
        if not isinstance(item, dict) or not isinstance(item.get("text"), str):
            continue
        mime = str(item.get("mimeType") or "").lower()
        if mime and not (mime.startswith("text/html") or "mcp-app" in mime):
            continue
        html = item["text"]
        if not html.strip():
            continue
        if len(html.encode("utf-8")) > MAX_HTML_BYTES:
            raise ValueError("MCP App-resource er større end 512 KiB")
        return html, dict(item.get("_meta") or {})
    raise ValueError("MCP App-resource indeholder ingen HTML-tekst")


def harden_html(html: str) -> str:
    """Indsæt en fail-closed CSP uden at omskrive appens dokument."""
    meta = f'<meta http-equiv="Content-Security-Policy" content="{_CSP}">'
    head = re.search(r"<head(?:\s[^>]*)?>", html, flags=re.IGNORECASE)
    if head:
        return html[:head.end()] + meta + html[head.end():]
    return meta + html


def _result_for_block(result: dict[str, Any]) -> dict[str, Any]:
    """Bevar MCP-resultatet til View'et, men aldrig ubegrænset."""
    raw = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    if len(raw.encode("utf-8")) <= MAX_RESULT_BYTES:
        return result
    return {
        "content": [{"type": "text", "text": "Resultatet var for stort til MCP App-fladen."}],
        "isError": True,
    }


def publish(*, server: str, tool_name: str, arguments: dict[str, Any],
            result: dict[str, Any], html: str, run_id: str,
            tool_use_id: str) -> dict[str, Any]:
    """Gem HTML'en og hæft en MCP App-blok på det synlige run."""
    from core.runtime.workspace_paths import shared_dir
    from core.services.attachment_service import register_generated_media
    from core.services.published_files import note

    safe = harden_html(html)
    raw = safe.encode("utf-8")
    folder: Path = shared_dir() / "generated" / "mcp-apps"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    path = folder / f"mcp-app-{stamp}.html"
    path.write_bytes(raw)
    attachment_id = register_generated_media(local_path=str(path), mime_type=MCP_APP_MIME)
    if not attachment_id:
        raise RuntimeError("MCP App-resource kunne ikke registreres som attachment")

    note(
        run_id,
        filename=path.name,
        mime_type=MCP_APP_MIME,
        size_bytes=len(raw),
        attachment_id=attachment_id,
        tool_use_id=tool_use_id,
        metadata={"mcp_app": {
            "server": str(server),
            "tool": str(tool_name),
            "arguments": dict(arguments or {}),
            "result": _result_for_block(result),
        }},
    )
    return {"attachment_id": attachment_id, "path": str(path), "bytes": len(raw)}

