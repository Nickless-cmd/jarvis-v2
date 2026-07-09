"""Rene content-blok-funktioner: tekst-projektion + serve-on-read rekonstruktion.

Kanonisk blok-format er dokumenteret i
docs/superpowers/specs/2026-07-09-structured-content-blocks-design.md §4.
Ingen DB-adgang her — rekonstruktion får en ``load_result``-callback injiceret,
så modulet er rent og enhedstestbart.
"""
from __future__ import annotations

from typing import Callable, Optional

from core.services.tool_result_store import parse_tool_result_reference

LoadResult = Callable[[str], Optional[dict]]


def content_blocks_to_text(blocks: list[dict]) -> str:
    """Flad en content-blok-array til markdown-tekst-projektionen. KUN text-blokke
    bidrager — tool_use/tool_result er ikke prosa. Deterministisk og stabil."""
    parts = [str(b.get("text") or "") for b in (blocks or []) if b.get("type") == "text"]
    return "\n\n".join(p for p in parts if p)


def reconstruct_blocks_from_legacy(
    role: str, content: str, *, load_result: LoadResult
) -> list[dict]:
    """Serve-on-read: byg blok-array for en GAMMEL besked (uden content_json).
    role="tool" m. "[tool_result:...]" → tool_result-blok; alt andet → text-blok.
    Ukendt/uopslåelig ref → degradér til text (fejler aldrig)."""
    text = str(content or "")
    if role == "tool":
        ref = parse_tool_result_reference(text)
        if ref:
            result_id = str(ref.get("result_id") or "")
            if result_id:
                loaded = None
                try:
                    loaded = load_result(result_id)
                except Exception:
                    loaded = None
                if loaded:
                    return [{
                        "type": "tool_result",
                        "tool_use_id": "",
                        "status": "done",
                        "content": str(loaded.get("content") or ""),
                        "is_error": False,
                        "name": str(loaded.get("tool_name") or ""),
                    }]
    return [{"type": "text", "text": text}]
