"""Grænser for værktøjs-kørsel — ét sted, så de to bash-stier ikke driver fra hinanden.

`MAX_BASH_SECONDS` stod hardkodet som 15 i BÅDE `simple_tools.py` og
`simple_tools_web.py`. To kopier af samme tal driver fra hinanden før eller
siden, og der er ingen måde at justere dem uden en udrulning.

Hvorfor 15 var for lidt (Jarvis 4. sep): «~7 timeouts på grep/git status/ls-
agtige kommandoer der burde tage <1s, mens de samme kommandoer via
bash_session lykkedes med det samme». En grep over dette repo tager legitimt
flere sekunder, og når event-loopet er belastet bliver selv hurtige kommandoer
langsomme. Grænsen ramte altså arbejdet, ikke løbske kommandoer.

Den må heller ikke være væk: en runde har et loft på 300 s, og en ubundet
kommando ville æde det. 45 s er valgt så en repo-bred søgning kan nå at blive
færdig, mens en løbsk kommando stadig standses længe før runden dør.
"""
from __future__ import annotations

_DEFAULT_BASH_SECONDS = 45


def bash_timeout_s() -> int:
    """Sekunder en enkelt bash-kommando må tage. Overstyres i runtime.json som
    `bash_timeout_s`. Self-safe — falder tilbage til standarden."""
    try:
        from core.runtime.settings import load_settings
        v = int(load_settings().extra.get("bash_timeout_s", _DEFAULT_BASH_SECONDS))
        # Under 5 s ville gøre selv trivielle kommandoer upålidelige; over 240 s
        # æder en runde (loftet er 300 s) og ligner et hængt system.
        return max(5, min(v, 240))
    except Exception:
        return _DEFAULT_BASH_SECONDS


def timeout_note(seconds: int, command: str = "") -> str:
    """Besked når en kommando løber tør for tid.

    «Command timed out after 15s» siger hvad der skete, men ikke hvad man gør.
    Den der læser den skal kunne komme videre uden at gætte.
    """
    hint = "indsnævr søgningen (sti/glob), eller brug bash_session til lange kørsler"
    if command and any(k in command for k in ("grep", "rg ", "find ", "**")):
        hint = "søgningen er for bred — angiv en mappe eller et glob"
    return f"Kommandoen nåede ikke at blive færdig på {seconds}s. {hint}."
