"""Hvem koerer denne agent — og lever den proces stadig?

BAGGRUND (maalt 10/9-2026). `jarvis-api` og `jarvis-runtime` koerer SAMME
app (`uvicorn apps.api.jarvis_api.app:app`), saa BEGGE processer eksekverer
opstarts-hooken — inklusive `recover_crashed_agents()`, som markerer enhver
agent i `starting/active/blocked` som styrtet.

Registret havde intet ejerskabs-maerke. En genstart af den ene proces kunne
derfor doemme en agent der levede i den ANDEN. Kun én agent er nogensinde
blevet fejet (af 198), fordi agenter er kortlivede — men mekanismen er der,
og et deploy genstarter begge.

VALGET NAAR VI IKKE KAN AFGOERE DET: lad vaere at feje. En aegte
forældreloes bliver samlet op af TTL-udloebet (verificeret levende, senest
5/9), mens en fejet LEVENDE agent mister sit arbejde uden spor. Af de to
fejl er den sidste vaerst, saa tvivl falder ud til agentens fordel.

Maerket er `<host>:<pid>:<starttid>`. Starttiden goer det immunt over for
pid-genbrug: en ny proces med samme pid har en anden starttid.
"""
from __future__ import annotations

import os
import socket


def _starttid(pid: int) -> str:
    """Procesens starttid i clock ticks (felt 22 i /proc/<pid>/stat).

    Kommandonavnet i felt 2 kan indeholde mellemrum og parenteser, saa der
    splittes EFTER den sidste `)` — ellers forskubbes felterne.
    """
    try:
        with open(f"/proc/{pid}/stat", "rb") as fh:
            raw = fh.read().decode("utf-8", "replace")
        hale = raw[raw.rindex(")") + 1:].split()
        return hale[19]                       # felt 22, 0-indekseret efter comm
    except Exception:
        return ""


def denne_proces() -> str:
    """Maerket for den proces der kalder. Tom streng hvis vi ikke kan danne et."""
    try:
        pid = os.getpid()
        st = _starttid(pid)
        if not st:
            return ""
        return f"{socket.gethostname()}:{pid}:{st}"
    except Exception:
        return ""


def lever(maerke: str) -> bool | None:
    """Lever processen bag maerket?

    `True`  — samme host, pid findes, starttid matcher.
    `False` — samme host, og processen er beviseligt vaek.
    `None`  — kan ikke afgoeres (tomt maerke, anden host, ulaesbar form).
              Kalderen skal behandle `None` som «roer den ikke».
    """
    if not maerke:
        return None
    dele = maerke.rsplit(":", 2)
    if len(dele) != 3:
        return None
    host, pid_s, start = dele
    try:
        if host != socket.gethostname():
            return None                       # en anden maskine — ikke vores kald
        pid = int(pid_s)
    except Exception:
        return None
    if not os.path.exists(f"/proc/{pid}"):
        return False
    nu = _starttid(pid)
    if not nu:
        return None
    return nu == start
