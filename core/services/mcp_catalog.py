"""Kurateret katalog over vedligeholdte MCP-reference-servere.

Kataloget er kun metadata og installationsopskrifter. Registrering sker fortsat
gennem ``mcp_registry``; tillid styres fortsat separat af ``mcp_trust``.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "id": "filesystem",
        "name": "Filesystem",
        "description": (
            "Læs og søg filer i den aktuelle arbejdsmappe. Installeres read-only "
            "som en sikker standard."
        ),
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "--read-only", "."],
        "tools": [
            "read_text_file",
            "read_media_file",
            "list_directory",
            "directory_tree",
            "search_files",
            "get_file_info",
        ],
        "source_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem",
    },
    {
        "id": "git",
        "name": "Git",
        "description": "Læs status og historik, sammenlign og arbejd med Git-repositories.",
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-server-git"],
        "tools": [
            "git_status",
            "git_diff_unstaged",
            "git_diff_staged",
            "git_log",
            "git_show",
            "git_commit",
        ],
        "source_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/git",
    },
    {
        "id": "fetch",
        "name": "Fetch",
        "description": "Hent websider og konverter HTML-indhold til læsevenlig Markdown.",
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "tools": ["fetch"],
        "source_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/fetch",
    },
)


def list_mcp_catalog() -> list[dict[str, Any]]:
    """Returner katalogposter som kopier, så kaldere ikke kan ændre kataloget."""
    return deepcopy(list(_CATALOG))


def get_mcp_catalog_entry(catalog_id: str) -> dict[str, Any] | None:
    """Find én katalogpost på dens stabile id."""
    wanted = str(catalog_id or "").strip()
    for entry in _CATALOG:
        if entry["id"] == wanted:
            return deepcopy(entry)
    return None


def catalog_with_installation_status(
    installed_servers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Tilføj ``installed`` ud fra den registrerede transportkonfiguration."""
    catalog = list_mcp_catalog()
    for entry in catalog:
        entry["installed"] = any(
            _same_server(entry, installed) for installed in installed_servers
        )
    return catalog


def _same_server(catalog_entry: dict[str, Any], installed: dict[str, Any]) -> bool:
    if catalog_entry["transport"] != installed.get("transport"):
        return False
    if catalog_entry["transport"] == "http":
        return catalog_entry.get("url") == installed.get("url")
    return (
        catalog_entry.get("command") == installed.get("command")
        and catalog_entry.get("args", []) == installed.get("args", [])
    )
