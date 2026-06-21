"""Parser for prosa-emitterede tool-kald (cluster: tool-leak-fix 2026-06-21).

Nogle modeller (fx deepseek-v4-flash) skriver tool-kald som prosa i deres tekst
i stedet for strukturerede tool_calls, fx:

    ([bash_session_run]: { "session_id": "bsh-1", "command": "ls" })
    [read_file]: {"path": "/x"}

Disse lækker som prosa → presentation_invariant blokerer svaret. Denne parser
konverterer dem til ægte OpenAI-format-tool-kald så de eksekverer.

KONSERVATIV: konverterer KUN `[navn]: {json-objekt}` hvor `navn` er et REGISTRERET
tool OG args parser som et JSON-objekt. Det undgår falske positiver på markdown-
reference-links (`[ref]: https://...`), citationer og narrerede resultater
(`[search]: [no matches]` — ikke et objekt → ignoreret)."""
from __future__ import annotations

import json
import re
from typing import Any, Iterable

# `[navn]: ` evt. omsluttet af `(` eller `[`. Navn = tool-id-agtigt.
_CALL_HEAD = re.compile(r"[\(\[]?\s*\[([a-z_][a-z0-9_]*)\]\s*:\s*", re.IGNORECASE)


def _match_json_object(s: str, start: int) -> tuple[str | None, int]:
    """s[start] skal være '{'. Returnér (objekt-streng, slut-index) via brace-matching
    (respekterer strenge/escapes), ellers (None, start)."""
    if start >= len(s) or s[start] != "{":
        return None, start
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[start : i + 1], i + 1
    return None, start


def extract_prose_tool_calls(
    text: str, valid_tool_names: Iterable[str]
) -> tuple[str, list[dict[str, Any]]]:
    """Find `[navn]: {json}`-prosa-kald hvor navn er et kendt tool og args er et
    JSON-objekt. Returnér (renset_tekst, kald). Kald er OpenAI-format:
    {"id": "", "type": "function", "function": {"name", "arguments": json-str}}.
    Hvis intet findes returneres (text, [])."""
    valid = {str(n) for n in (valid_tool_names or ())}
    if not text or not valid:
        return text, []
    calls: list[dict[str, Any]] = []
    spans: list[tuple[int, int]] = []
    for m in _CALL_HEAD.finditer(text):
        name = m.group(1)
        if name not in valid:
            continue
        j = m.end()
        if j >= len(text) or text[j] != "{":
            continue
        obj, end = _match_json_object(text, j)
        if obj is None:
            continue
        try:
            parsed = json.loads(obj)
        except Exception:
            continue
        if not isinstance(parsed, dict):
            continue
        calls.append({
            # KRITISK: id MÅ være ikke-tom. Tom tool_call_id får ALLE providers til at
            # afvise followup-runden ("invalid request body") — og den persisteres i
            # historikken, så hele session'en bliver ved at fejle. (Regression 2026-06-21.)
            "id": f"prose_{len(calls)}_{name}"[:60],
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(parsed, ensure_ascii=False)},
        })
        strip_end = end
        if strip_end < len(text) and text[strip_end] == ")":
            strip_end += 1   # spis afsluttende ')' hvis kaldet var `(...)`-omsluttet
        spans.append((m.start(), strip_end))
    if not spans:
        return text, []
    out: list[str] = []
    last = 0
    for s, e in spans:
        out.append(text[last:s])
        last = e
    out.append(text[last:])
    return "".join(out).strip(), calls
