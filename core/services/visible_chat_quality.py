"""Observe chat-response quality without rewriting the user's text.

These are diagnostic signals, not a prose linter.  A signal is evidence worth
measuring; it is never permission to insert line breaks, delete content, or
block an answer.  Code/cowork never enters this module's observer.
"""
from __future__ import annotations

import json
import re
from collections import Counter

_FENCE_RE = re.compile(r"```(?P<lang>[^\n`]*)\n(?P<body>.*?)```", re.DOTALL)
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)
_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\S", re.MULTILINE)

#: Et svar med så mange afsnit og nul hierarki er ikke "roligt" — det er en mur
#: af tekstøer uden landkort. Målt 25/10-2026: 90 % af mine prosa-afsnit var på
#: ≤3 sætninger, mens kun 5 % af svarene havde en overskrift og 5 % en liste.
#: Signalet er diagnostik, ikke en rettelse — det må aldrig ændre teksten.
_HIERARCHY_PARAGRAPH_FLOOR = 5
_MECHANICAL_CLOSE_RE = re.compile(
    r"^(?:sammenfattende|opsummeret|opsummering|afslutningsvis|(?:min\s+)?konklusion)\b",
    re.IGNORECASE,
)


def _hierarchy_signals(prose: str, paragraphs: list[str]) -> list[dict[str, object]]:
    """Mål om et langt svar har hierarki — ikke om det er pænt.

    Et svar med mange afsnit og hverken overskrift eller liste er svært at
    skimme, uanset hvor korte afsnittene er. Signalet peger på den mangel;
    det siger intet om hvorvidt strukturen burde have været der.
    """
    if len(paragraphs) < _HIERARCHY_PARAGRAPH_FLOOR:
        return []
    if _HEADING_RE.search(prose) or _BULLET_RE.search(prose):
        return []
    return [{"kind": "missing_hierarchy", "paragraphs": len(paragraphs)}]


def analyse_chat_response(text: str, *, wall_chars: int = 600) -> list[dict[str, object]]:
    """Return measurable quality signals for a final chat response."""
    raw = str(text or "").strip()
    if not raw:
        return []
    signals: list[dict[str, object]] = []
    native_specs: list[dict] = []
    for match in _FENCE_RE.finditer(raw):
        if match.group("lang").strip().lower() != "jarvis-ui":
            continue
        try:
            spec = json.loads(match.group("body"))
            if isinstance(spec, dict):
                native_specs.append(spec)
            else:
                raise ValueError("native payload is not an object")
        except Exception:
            signals.append({"kind": "invalid_native_surface"})

    prose = _FENCE_RE.sub("", raw).strip()
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", prose) if p.strip()]
    for signal in _hierarchy_signals(prose, paragraphs):
        signals.append(signal)
    try:
        from core.services.wall_guard import find_walls
        for wall in find_walls(prose):
            signals.append({"kind": "prose_wall", **wall})
    except Exception:  # kvalitetsmåling må aldrig ændre eller blokere svaret
        pass

    normalized = [re.sub(r"\s+", " ", p).strip().casefold() for p in paragraphs]
    repeated = [p for p, count in Counter(p for p in normalized if len(p) >= 80).items() if count > 1]
    if repeated:
        signals.append({"kind": "repeated_prose", "count": len(repeated)})

    native_types = {str(spec.get("type") or "") for spec in native_specs}
    has_table = any(_TABLE_ROW_RE.match(line) for line in raw.splitlines())
    if has_table and native_types.intersection({"comparison", "stats"}):
        signals.append({"kind": "competing_data_surfaces"})
    if native_specs and len(prose) < 80:
        signals.append({"kind": "surface_without_standalone_text"})
    if paragraphs and _MECHANICAL_CLOSE_RE.match(paragraphs[-1]):
        signals.append({"kind": "mechanical_closure"})
    if paragraphs and paragraphs[-1].rstrip().endswith("?"):
        signals.append({"kind": "closing_question"})
    return signals


def observe_chat_response(text: str, **context: object) -> list[dict[str, object]]:
    """Emit one metadata-only observation when, and only when, scope is chat."""
    try:
        from core.tools.tool_scoping import current_tool_scope
        if current_tool_scope() != "chat":
            return []
    except Exception:  # scope er valgfri metadata; manglende context betyder ingen observation
        return []
    signals = analyse_chat_response(text)
    if not signals:
        return []
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "chat", "nerve": "response_quality", "kind": "observe",
            "chars": len(str(text or "")), "signals": signals,
            **{k: v for k, v in context.items() if v not in (None, "")},
        })
    except Exception:  # diagnostik må aldrig blokere eller ændre et synligt svar
        pass
    return signals

