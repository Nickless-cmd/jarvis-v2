"""Streaming tool-echo backstop, extracted from the v2 translator."""
import re

# Echo-mønstre for tool-leak backstop (Del A2 i Phase 2-spec):
#  - _ECHO_BUILDING: en partiel linje der STADIG kan blive til "[tool]:"
#    (vi holder den tilbage indtil den enten fuldføres eller diverger).
#  - _ECHO_FULL: en bekræftet "[tool]:"-præfiks — droppes hvis <tool> er et
#    kendt registreret toolnavn.
_ECHO_BUILDING_RE = re.compile(r"^\s*\[[a-z0-9_]*\]?\s*:?\s*$")
_ECHO_FULL_RE = re.compile(r"^\s*\[([a-z0-9_]+)\]\s*:")


class ToolEchoFilter:
    """Streaming-backstop mod at modellen ekkoer rå tool-output i sit svar.

    Dropper hele linjer der starter med ``[<kendt_tool>]:`` (fx
    ``[read_file]: <fil-dump>``) men lader al anden tekst flyde igennem
    token-for-token (minimal latency — vi holder kun tilbage når en linje
    ved line-start *kunne* blive til en tool-echo).

    Brug: ``feed(text)`` pr. delta, ``flush()`` ved stream-slut.
    """

    def __init__(self, tool_names=None) -> None:
        if tool_names is None:
            try:
                from core.tools.simple_tools import _TOOL_HANDLERS
                tool_names = list(_TOOL_HANDLERS.keys())
            except Exception:
                tool_names = []
        self._names = {str(n).lower() for n in tool_names}
        self._held = ""             # holdt partiel linje (mulig echo)
        self._at_line_start = True  # er vi ved starten af en ny linje?
        self._dropping = False      # dropper vi resten af en bekræftet echo-linje?

    def _is_echo_line(self, line: str) -> bool:
        m = _ECHO_FULL_RE.match(line)
        return bool(m and m.group(1).lower() in self._names)

    def feed(self, text: str) -> str:
        if not text:
            return ""
        out: list[str] = []
        buf = self._held + text
        self._held = ""
        while buf:
            if self._dropping:
                nl = buf.find("\n")
                if nl == -1:
                    buf = ""
                else:
                    buf = buf[nl + 1:]
                    self._dropping = False
                    self._at_line_start = True
                continue
            if not self._at_line_start:
                nl = buf.find("\n")
                if nl == -1:
                    out.append(buf)
                    buf = ""
                else:
                    out.append(buf[:nl + 1])
                    buf = buf[nl + 1:]
                    self._at_line_start = True
                continue
            # Ved line-start.
            nl = buf.find("\n")
            if nl != -1:
                line = buf[:nl + 1]
                buf = buf[nl + 1:]
                if not self._is_echo_line(line):
                    out.append(line)
                # echo-linje droppes
                self._at_line_start = True
                continue
            # Partiel linje uden newline endnu.
            line = buf
            buf = ""
            if _ECHO_BUILDING_RE.match(line):
                self._held = line          # endnu uafklaret — hold tilbage
            elif self._is_echo_line(line):
                self._dropping = True      # bekræftet echo, drop resten af linjen
            else:
                out.append(line)
                self._at_line_start = False
            break
        return "".join(out)

    def flush(self) -> str:
        held = self._held
        self._held = ""
        if not held:
            return ""
        if self._is_echo_line(held):
            return ""
        return held


