"""Capability markup parsing — udskilt fra visible_runs.py (Boy Scout).

Constants og rene parse-funktioner til `<capability-call …/>` markup.
Ingen side effects, ingen runtime-afhængigheder ud over `re` og `json`.

Re-eksporteres fra visible_runs.py så eksisterende imports + monkeypatches
i tests ikke knækker.
"""
from __future__ import annotations

import json
import re

# ── Regex patterns ──────────────────────────────────────────────────────
# Full capability-call tag: <capability-call attrs /> (self-closing)
CAPABILITY_CALL_PATTERN = re.compile(
    r"^<capability-call\s+(?P<attrs>[^<>]*?)\s*/>$"
)
# Scan pattern (partial match within larger text) — same pattern,
# but not anchored to fullmatch.
CAPABILITY_CALL_SCAN_PATTERN = re.compile(
    r"<capability-call\s+(?P<attrs>[^<>]*?)\s*/>"
)
# Block (non-self-closing) capability tag: <capability-call ...>...</capability-call>
CAPABILITY_BLOCK_PATTERN = re.compile(
    r'<capability-call\s+(?P<attrs>[^<>]*?)(?<!/)>\s*\n(?P<content>.*?)\n\s*</capability-call>',
    re.DOTALL,
)
# Attribute extraction inside a tag: key="value"
CAPABILITY_ATTR_PATTERN = re.compile(
    r'(?P<name>[a-z_]+)="(?P<value>[^"]*)"'
)

CAPABILITY_CALL_PREFIX = '<capability-call id="'
CAPABILITY_CALL_SUFFIX = '" />'
VISIBLE_CAPABILITY_ARG_NAMES = {"command_text", "target_path", "write_content"}

# Some models (notably big-pickle/MiniMax and deepseek-v4-flash) emit a
# preview of their tool call as plain text before the actual response, e.g.
#   ([deep_analyze]: { "summary": "...", "findings": [...] })
#   ([read_file]: /home/bs/.jarvis-v2/shared/SOUL.md)
#   ([list_recurring]): {" recurring ": [...]}
# The structured tool_call is already in the response's tool_calls field —
# this text is purely decorative and looks like garbage in the chat. Strip
# both shapes here.
_TOOL_TEXT_MARKUP_OPEN = "(["


def _extract_capability_call(text: str) -> str | None:
    parsed = _parse_capability_call_markup((text or "").strip())
    if not parsed:
        return None
    return str(parsed.get("capability_id") or "")


def _parse_capability_call_markup(text: str) -> dict[str, object] | None:
    match = CAPABILITY_CALL_PATTERN.fullmatch(str(text or "").strip())
    if not match:
        return None
    attrs = _parse_capability_attrs(match.group("attrs"))
    capability_id = str(attrs.pop("id", "")).strip()
    if not capability_id or not re.fullmatch(r"[a-z0-9:-]+", capability_id):
        return None
    arguments = {
        key: value
        for key, value in attrs.items()
        if key in VISIBLE_CAPABILITY_ARG_NAMES and str(value).strip()
    }
    return {
        "capability_id": capability_id,
        "arguments": arguments,
    }


def _extract_content_after_capability_tag(raw: str, capability_id: str) -> str | None:
    """Extract markdown/text content after a self-closing capability tag.

    When LLMs use <capability-call id="..." /> (self-closing) and then write
    the intended content below the tag, this function extracts that content.
    Only used for memory-write capabilities where write_content is expected.
    """
    # Find the self-closing tag
    pattern = re.compile(
        rf'<capability-call\s[^>]*id="{re.escape(capability_id)}"[^>]*/>\s*\n',
        re.IGNORECASE,
    )
    match = pattern.search(raw)
    if not match:
        return None

    after = raw[match.end():].strip()
    if not after:
        return None

    # Look for markdown content (starting with # or containing structured text)
    # Stop at the next capability-call tag or end of text
    next_tag = re.search(r'<capability-call\s', after)
    if next_tag:
        after = after[:next_tag.start()].strip()

    # Only accept if it looks like memory content (has a heading or substantial text)
    if len(after) < 20:
        return None
    if after.startswith("#") or after.startswith("- ") or "\n" in after:
        return after

    return None


def _parse_capability_attrs(attrs_text: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in CAPABILITY_ATTR_PATTERN.finditer(str(attrs_text or "")):
        attrs[str(match.group("name") or "")] = str(match.group("value") or "")
    return attrs


def _capability_call_state(text: str) -> str:
    candidate = (text or "").strip()
    if not candidate:
        return "invalid"
    if len(candidate) <= len(CAPABILITY_CALL_PREFIX):
        return "prefix" if CAPABILITY_CALL_PREFIX.startswith(candidate) else "invalid"
    if not candidate.startswith(CAPABILITY_CALL_PREFIX):
        return "invalid"

    remainder = candidate[len(CAPABILITY_CALL_PREFIX):]
    capability_id = ""
    index = 0
    while index < len(remainder) and re.fullmatch(r"[a-z0-9:-]", remainder[index]):
        capability_id += remainder[index]
        index += 1

    tail = remainder[index:]
    if not tail:
        return "prefix"
    if not capability_id:
        return "invalid"
    if CAPABILITY_CALL_SUFFIX.startswith(tail):
        return "exact" if tail == CAPABILITY_CALL_SUFFIX else "prefix"
    return "invalid"


def _strip_capability_markup(text: str) -> str:
    out = CAPABILITY_CALL_SCAN_PATTERN.sub("", str(text or ""))
    out = _strip_tool_call_text_markup(out)
    return out


def _try_match_tool_text_markup(text: str) -> int:
    """Return length of a leading tool-text-markup block, or 0 if no match,
    or -1 if it looks like the start of one but is still incomplete (the
    caller should keep buffering).

    Recognized shapes:
      ([word]: <anything until matching outer )>
      ([word]):\\s*{<balanced json>}
      ([word]):\\s*<text up to newline>
    """
    if not text.startswith(_TOOL_TEXT_MARKUP_OPEN):
        return 0
    m = re.match(r"\(\[([\w._-]+)\](\))?:\s*", text)
    if m is None:
        # Could still become a match while we're streaming — buffer it
        # unless we've already accumulated enough to know it never will.
        return -1 if len(text) < 80 else 0
    end = m.end()

    # Shape B: ([word]):  → expect JSON or until-newline
    if m.group(2):
        if end >= len(text):
            return -1
        if text[end] == "{":
            depth = 0
            i = end
            while i < len(text):
                c = text[i]
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        return i + 1
                i += 1
            return -1  # incomplete JSON
        nl = text.find("\n", end)
        return nl if nl != -1 else (-1 if len(text) < 800 else len(text))

    # Shape A: ([word]: <stuff> ) — scan to matching closing paren.
    # Outer "(" already at position 0 → depth starts at 1.
    depth = 1
    i = end
    while i < len(text):
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1  # incomplete, keep buffering


def _strip_tool_call_text_markup(text: str) -> str:
    """Non-streaming variant: strip all occurrences from a finished string.

    If stripping would leave the result empty (i.e. the entire input was
    tool-text-markup like "([write_file]: …)" with no real prose), fall
    back to returning the original text unchanged. Background:

      - The model emits markup-form tool calls when its real structured
        tool_calls slot was empty for that turn (a known hallucination
        mode for big-pickle/MiniMax and occasionally deepseek-v4-flash).
      - Stripping the markup AND silently dropping the empty turn made
        Jarvis appear to "lose" messages — user sees nothing, model
        believes its action succeeded, file was never written.
      - Keeping the markup visible is uglier in the rare case it slips
        through, but it surfaces the failure honestly so the user can
        notice and correct course. Strict tool-call rules in
        VISIBLE_CHAT_RULES.md should make this rare.
    """
    if not text or _TOOL_TEXT_MARKUP_OPEN not in text:
        return text
    out_parts: list[str] = []
    i = 0
    while i < len(text):
        idx = text.find(_TOOL_TEXT_MARKUP_OPEN, i)
        if idx == -1:
            out_parts.append(text[i:])
            break
        out_parts.append(text[i:idx])
        consumed = _try_match_tool_text_markup(text[idx:])
        if consumed > 0:
            i = idx + consumed
        else:
            out_parts.append(text[idx:idx + len(_TOOL_TEXT_MARKUP_OPEN)])
            i = idx + len(_TOOL_TEXT_MARKUP_OPEN)
    stripped = "".join(out_parts)
    if not stripped.strip():
        return text  # Preserve original markup rather than silently drop the turn.
    return stripped


class _CapabilityMarkupBuffer:
    """Buffer that holds back streaming deltas that may be capability-call markup.

    Tokens are fed in via ``feed()``.  The buffer accumulates text while it
    looks like the start of a ``<capability-call …/>`` or block tag.  When
    the accumulated text can no longer be a prefix of a capability tag, the
    buffered content is flushed (returned to the caller for sending).  When
    a complete tag is detected, it is swallowed (not returned).
    """

    _OPEN = "<capability-call"

    def __init__(self) -> None:
        self._buf = ""

    def feed(self, text: str) -> str:
        """Accept new text; return any content safe to send to the client."""
        self._buf += text
        return self._drain()

    def flush(self) -> str:
        """Return any remaining buffered content (call at end-of-stream)."""
        out = self._buf
        self._buf = ""
        return _strip_capability_markup(out)

    # ------------------------------------------------------------------

    def _drain(self) -> str:
        """Return sendable prefix, keeping potential markup buffered."""
        out_parts: list[str] = []
        while self._buf:
            lt = self._buf.find("<")
            paren = self._buf.find("(")
            candidates = [c for c in (lt, paren) if c != -1]
            if not candidates:
                out_parts.append(self._buf)
                self._buf = ""
                break
            tag_start = min(candidates)
            if tag_start > 0:
                out_parts.append(self._buf[:tag_start])
                self._buf = self._buf[tag_start:]

            if self._buf.startswith("<"):
                if self._is_capability_prefix(self._buf):
                    m = CAPABILITY_CALL_SCAN_PATTERN.match(self._buf)
                    if m:
                        self._buf = self._buf[m.end():]
                        continue
                    bm = CAPABILITY_BLOCK_PATTERN.match(self._buf)
                    if bm:
                        self._buf = self._buf[bm.end():]
                        continue
                    break
                else:
                    out_parts.append(self._buf[0])
                    self._buf = self._buf[1:]
                    continue

            if self._buf.startswith(_TOOL_TEXT_MARKUP_OPEN):
                consumed = _try_match_tool_text_markup(self._buf)
                if consumed > 0:
                    self._buf = self._buf[consumed:]
                    continue
                if consumed < 0:
                    break
                out_parts.append(self._buf[0])
                self._buf = self._buf[1:]
                continue

            out_parts.append(self._buf[0])
            self._buf = self._buf[1:]
        return "".join(out_parts)

    @staticmethod
    def _is_capability_prefix(text: str) -> bool:
        opening = _CapabilityMarkupBuffer._OPEN
        check_len = min(len(text), len(opening))
        return text[:check_len] == opening[:check_len]


def _visible_text_without_capability_markup(text: str, *, had_markup: bool) -> str:
    stripped = _strip_capability_markup(text)
    lines = stripped.split("\n")
    lines = [" ".join(line.split()) for line in lines]
    cleaned = "\n".join(lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    if cleaned:
        return cleaned
    if had_markup:
        return "Capability request was consumed by the visible lane."
    return ""
