"""Explicit code-answer boundary shared by the stream and persistence paths.

The marker is presentation intent, never a turn-completion or policy signal.
Only an unquoted line-start marker outside fenced code has this meaning.
"""
from __future__ import annotations

import re

_FENCE_LINE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")

ANSWER_MARKER = "[[jarvis:answer]]"
# Compatibility only: chat's existing heuristic is not code-mode authority.
ANSWER_START_CHARS = 350


class AnswerMarkerStream:
    """Incremental scanner: (text | answer_start, value), independent of chunks."""

    def __init__(self) -> None:
        self.pending = ""
        self.line_prefix = ""
        self.line_start = True
        self.fence = ""
        self.started = False

    def feed(self, text: str) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        literal: list[str] = []
        for char in text:
            if self.pending or (self.line_start and not self.fence and char == "["):
                self.pending += char
                if ANSWER_MARKER.startswith(self.pending):
                    if self.pending == ANSWER_MARKER:
                        if literal:
                            out.append(("text", "".join(literal)))
                            literal.clear()
                        self.pending = ""
                        self.line_start = False
                        if not self.started:
                            self.started = True
                            out.append(("answer_start", ""))
                    continue
                literal.append(self.pending)
                self.line_prefix = self.pending[:3]
                self.line_start = False
                self.pending = ""
            else:
                literal.append(char)
                if len(self.line_prefix) < 512 and char != "\n":
                    self.line_prefix += char
                self.line_start = False
            if char == "\n":
                fence = _FENCE_LINE.match(self.line_prefix)
                if fence:
                    run, suffix = fence.groups()
                    if not self.fence:
                        self.fence = run
                    elif run[0] == self.fence[0] and len(run) >= len(self.fence) and not suffix.strip():
                        self.fence = ""
                self.line_start = True
                self.line_prefix = ""
        if literal:
            out.append(("text", "".join(literal)))
        return out

    def flush(self) -> list[tuple[str, str]]:
        text, self.pending = self.pending, ""
        # A truncated, identifiable protocol token is never visible prose.
        if text.startswith("[[jarvis:"):
            return []
        return [("text", text)] if text else []


def strip_answer_markers(text: str) -> str:
    scanner = AnswerMarkerStream()
    return "".join(value for kind, value in scanner.feed(text) + scanner.flush() if kind == "text")


def mark_code_answer_start(blocks: list[dict]) -> None:
    """Persist the declared boundary, never infer it from answer length.

    On older/marker-free output, terminal fallback is the final text block.
    Legacy chat phases remain independent and are assigned by the caller.
    """
    texts = [b for b in blocks if b.get("type") == "text"]
    if not texts or any(b.get("code_answer_protocol") == 1 for b in texts):
        return
    result: list[dict] = []
    boundary: dict | None = None
    for block in blocks:
        if block.get("type") != "text":
            result.append(block)
            continue
        scanner = AnswerMarkerStream()
        parts = scanner.feed(str(block.get("text") or "")) + scanner.flush()
        current = {**block, "text": "", "code_answer_protocol": 1}
        for kind, value in parts:
            if kind == "answer_start" and boundary is None:
                if current["text"].strip():
                    result.append(current)
                    current = {**block, "text": "", "code_answer_protocol": 1}
                current["code_answer_start"] = True
                current["code_answer_source"] = "explicit"
                boundary = current
            elif kind == "text":
                current["text"] += value
        result.append(current)
    if boundary is None:
        texts = [b for b in result if b.get("type") == "text"]
        candidate = next((b for b in texts if b.get("code_answer_start") or b.get("phase") == "final_answer"), None)
        if candidate is None:
            candidate = texts[0] if not any(b.get("type") == "tool_use" for b in result) else texts[-1]
        candidate["code_answer_start"] = True
        candidate["code_answer_source"] = "terminal"
    blocks[:] = result
