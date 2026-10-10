"""Fjern terminal-styrekoder fra tool-output før det når modellen.

Porteret fra jarvis-code 2026-09-06 (`sanitize.py`). Runtime havde INGEN
håndtering — målt: `printf "\\033[31mROED\\033[0m"` gennem bash nåede modellen
som `\\x1b[31mROED\\x1b[0m`, ordret.

To grunde til at det er værd at fjerne, og den anden vejer tungest.

**Tokens uden mening.** `git diff --color`, pytest, npm og `ls --color`
producerer escape-sekvenser i hobetal. Modellen betaler for hvert eneste af
dem og kan intet bruge dem til — de siger noget om en skærm der ikke findes.

**Skjult tekst.** Backspace kan overtype, og OSC-sekvenser kan saette en
vinduestitel. Det betyder at det modellen LAESER kan afvige fra det et
menneske SAA i en terminal. Derfor ryger de bare kontroltegn med, ikke kun
farverne.

Tre tegn bevares med vilje: `\n` og `\t` baerer struktur, og `\r` roeres
IKKE. Det sidste er et valg, ikke en forglemmelse: `\r\n` er almindelige
linjeskift i filer og HTTP, og en fremdriftslinje ville uden `\r` smelte
sammen til én ulaeselig streng. jarvis-codes udgave opfoerer sig ens, men har
en kommentar der paastaar den fjerner `\r` — den udelader ogsaa `\x0d`.
"""
from __future__ import annotations

import re

# CSI: ESC [ … slutbyte — farver, markør-flytning, skærmrydning.
_CSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
# OSC: ESC ] … BEL eller ESC \ — vinduestitel, hyperlinks.
_OSC = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
# Enkeltstående escapes som CSI/OSC ikke dækker (ESC c = reset, ESC M m.fl.).
_OVRIGE_ESC = re.compile(r"\x1b[0-9A-Za-z=><cDEHM78]")
# Bare kontroltegn ud over \n og \t: \r-overskrivning, bell, backspace-overtyping.
_KONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def strip_terminal_codes(text: str) -> str:
    """Fjern styrekoder. Bevarer tekst, linjeskift og tabulator."""
    if not text or "\x1b" not in text and not _KONTROL.search(text):
        return text  # hurtig vej: langt de fleste resultater er rene
    ud = _CSI.sub("", text)
    ud = _OSC.sub("", ud)
    ud = _OVRIGE_ESC.sub("", ud)
    return _KONTROL.sub("", ud)


class TerminalStreamSanitizer:
    """Stateful sanitizer that does not leak escape fragments across chunks."""

    def __init__(self, *, max_pending_chars: int = 8192) -> None:
        self._pending = ""
        self._max_pending_chars = max(16, int(max_pending_chars))
        self._discarding_osc = False
        self._discarding_osc_esc = False

    @staticmethod
    def _incomplete_escape_start(text: str) -> int | None:
        cursor = 0
        while True:
            start = text.find("\x1b", cursor)
            if start < 0:
                return None
            if start + 1 >= len(text):
                return start
            kind = text[start + 1]
            if kind == "]":
                bel = text.find("\x07", start + 2)
                st = text.find("\x1b\\", start + 2)
                ends = [end for end in (bel, st) if end >= 0]
                if not ends:
                    return start
                end = min(ends)
                cursor = end + (2 if text.startswith("\x1b\\", end) else 1)
                continue
            if kind == "[":
                final = next((idx for idx in range(start + 2, len(text))
                              if "@" <= text[idx] <= "~"), None)
                if final is None:
                    return start
                cursor = final + 1
                continue
            cursor = start + 2
        return None

    def _finish_discarded_osc(self, text: str) -> str:
        if not self._discarding_osc:
            return text
        prefix = "\x1b" if self._discarding_osc_esc else ""
        combined = prefix + text
        bel = combined.find("\x07")
        st = combined.find("\x1b\\")
        ends = [(bel, 1), (st, 2)]
        ends = [(idx, width) for idx, width in ends if idx >= 0]
        if not ends:
            self._discarding_osc_esc = combined.endswith("\x1b")
            return ""
        idx, width = min(ends)
        self._discarding_osc = False
        self._discarding_osc_esc = False
        return combined[idx + width:]

    def feed(self, chunk: str) -> str:
        text = self._finish_discarded_osc(str(chunk or ""))
        if self._discarding_osc:
            return ""
        text = self._pending + text
        self._pending = ""
        incomplete = self._incomplete_escape_start(text)
        if incomplete is not None:
            self._pending = text[incomplete:]
            text = text[:incomplete]
            if (self._pending.startswith("\x1b]")
                    and len(self._pending) > self._max_pending_chars):
                self._pending = ""
                self._discarding_osc = True
                self._discarding_osc_esc = False
            elif len(self._pending) > self._max_pending_chars:
                self._pending = self._pending[-self._max_pending_chars:]
        return strip_terminal_codes(text)

    def flush(self) -> str:
        # An unfinished control sequence is control data, not visible text.
        self._pending = ""
        self._discarding_osc = False
        self._discarding_osc_esc = False
        return ""
