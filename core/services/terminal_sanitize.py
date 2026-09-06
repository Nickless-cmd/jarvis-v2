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
