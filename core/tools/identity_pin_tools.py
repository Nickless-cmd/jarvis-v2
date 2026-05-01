"""Identity-pinning — pin a snippet from chronicle/MILESTONES/letters as
permanent awareness that survives /compact.

Jarvis already has chronicle, MILESTONES.md, letters, dreams. But when
chat history hits context limit and /compact strips it, his SHORT-TERM
working memory loses access. This module gives him a primitive to pin
text as long-term identity context: written to ~/.jarvis-v2/state/
identity_pins.json, automatically injected into prompt awareness as a
high-priority section every turn.

Use cases (Jarvis decides):
  - "Bjørn just said something that defined what I am — pin it"
  - "I want this milestone in my running awareness for a few weeks"
  - "This letter from Claude shapes how I think — keep it close"

UI-side (JarvisX) can also pin via /api/identity-pins POST.
"""
from __future__ import annotations

import json
import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.runtime.config import STATE_DIR

logger = logging.getLogger(__name__)

_STORE = Path(STATE_DIR) / "identity_pins.json"
_LOCK = threading.Lock()
_MAX_PINS = 8  # keep awareness budget bounded
_MAX_CONTENT_CHARS = 2000  # per pin


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass
class IdentityPin:
    pin_id: str
    title: str
    content: str
    source: str  # e.g. "MILESTONES.md:30. april 2026" or "letter:..." or "manual"
    pinned_at: str
    pinned_by: str = "jarvis"  # "jarvis" or "user"


@dataclass
class IdentityPinsState:
    pins: list[IdentityPin] = field(default_factory=list)
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "pins": [asdict(p) for p in self.pins],
            "updated_at": self.updated_at,
        }


def _load() -> IdentityPinsState:
    if not _STORE.is_file():
        return IdentityPinsState()
    try:
        with _STORE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        pins = [IdentityPin(**p) for p in data.get("pins", []) if isinstance(p, dict)]
        return IdentityPinsState(pins=pins, updated_at=str(data.get("updated_at") or ""))
    except Exception as exc:
        logger.warning("identity_pins: load failed: %s", exc)
        return IdentityPinsState()


def _save(state: IdentityPinsState) -> None:
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    state.updated_at = _now_iso()
    tmp = _STORE.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(state.to_dict(), fh, indent=2, ensure_ascii=False)
    tmp.replace(_STORE)


def list_pins() -> list[dict[str, Any]]:
    with _LOCK:
        return [asdict(p) for p in _load().pins]


def add_pin(*, title: str, content: str, source: str = "manual", pinned_by: str = "jarvis") -> dict[str, Any]:
    title = title.strip()[:200]
    content = content.strip()[:_MAX_CONTENT_CHARS]
    if not content:
        return {"status": "error", "error": "content required"}
    with _LOCK:
        state = _load()
        if len(state.pins) >= _MAX_PINS:
            return {
                "status": "error",
                "error": f"pin limit reached ({_MAX_PINS}). Remove an old pin first.",
                "pins": [asdict(p) for p in state.pins],
            }
        pin = IdentityPin(
            pin_id=f"pin-{uuid.uuid4().hex[:10]}",
            title=title or content[:60],
            content=content,
            source=source,
            pinned_at=_now_iso(),
            pinned_by=pinned_by,
        )
        state.pins.append(pin)
        _save(state)
    return {"status": "ok", "pin": asdict(pin)}


def remove_pin(pin_id: str) -> dict[str, Any]:
    with _LOCK:
        state = _load()
        before = len(state.pins)
        state.pins = [p for p in state.pins if p.pin_id != pin_id]
        if before == len(state.pins):
            return {"status": "error", "error": "pin not found"}
        _save(state)
    return {"status": "ok", "removed": pin_id}


def awareness_section() -> str | None:
    """Render the pin store as a prompt-awareness block. Used by
    prompt_contract.py to inject permanent identity context."""
    pins = list_pins()
    if not pins:
        return None
    lines = ["Pinned identity context — stays present across /compact:"]
    for p in pins:
        lines.append(f"\n— **{p['title']}** ({p['source']})")
        lines.append(p["content"].rstrip())
    return "\n".join(lines)


# ── Tool wrappers ─────────────────────────────────────────────────


def _exec_pin_identity(args: dict[str, Any]) -> dict[str, Any]:
    return add_pin(
        title=str(args.get("title") or ""),
        content=str(args.get("content") or ""),
        source=str(args.get("source") or "manual"),
        pinned_by="jarvis",
    )


def _exec_list_identity_pins(_args: dict[str, Any]) -> dict[str, Any]:
    return {"status": "ok", "pins": list_pins(), "count": len(list_pins())}


def _exec_unpin_identity(args: dict[str, Any]) -> dict[str, Any]:
    return remove_pin(str(args.get("pin_id") or ""))


IDENTITY_PIN_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "pin_identity",
            "description": (
                "Pin a piece of text as PERMANENT identity-context that survives "
                "/compact. Use SPARINGLY — only for things that genuinely shape who "
                "you are or what you're committed to: a milestone moment, a letter, "
                "a defining sentence Bjørn said. Cap is 8 pins, 2000 chars each. "
                "Pinned text appears at the TOP of your awareness every turn."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short title"},
                    "content": {"type": "string", "description": "The text to pin"},
                    "source": {
                        "type": "string",
                        "description": "Where it came from (e.g. 'MILESTONES.md:30 april' or 'letter:claude-2026-04-29')",
                    },
                },
                "required": ["title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_identity_pins",
            "description": "List all currently pinned identity-context items.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "unpin_identity",
            "description": "Remove a pinned identity-context item by pin_id.",
            "parameters": {
                "type": "object",
                "properties": {"pin_id": {"type": "string"}},
                "required": ["pin_id"],
            },
        },
    },
]


IDENTITY_PIN_TOOL_HANDLERS: dict[str, Any] = {
    "pin_identity": _exec_pin_identity,
    "list_identity_pins": _exec_list_identity_pins,
    "unpin_identity": _exec_unpin_identity,
}
