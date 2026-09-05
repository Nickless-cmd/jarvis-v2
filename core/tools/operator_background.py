"""Baggrunds-shells paa operatoerens maskine — paritet med jarvis-code.

`run_in_background` / `bash_output` / `kill_shell` fandtes hverken i runtimen
eller i operator-saettet. De var tre af de fire huller i «det samme paa min
maskine»: server-loopet kendte dem ikke, OG der var ingen vej til Bjoerns
maskine. Selv en loop-integration ville derfor kun have virket i containeren.

**Hvorfor tilstandsloes.** jarvis-code holder et in-process `Popen`-register.
Det kan runtimen ikke: processen lever paa en ANDEN maskine, og et
modul-globalt register ville alligevel ikke krydse api/runtime-grænsen — den
grænse har vaeret aarsag til en stribe fejl (se hukommelsen om
felt-overflader og prompt-sektioner).

I stedet ligger HELE tilstanden som filer paa operatoerens maskine, og
`shell_id` er noeglen:

    <rod>/<id>.log   samlet stdout+stderr
    <rod>/<id>.pid   processens pid
    <rod>/<id>.rc    exit-kode, skrevet naar den er faerdig

Det goer opslag idempotente, overlever genstart af begge processer, og lader to
forskellige processer laese den samme shell uden at dele hukommelse.
"""
from __future__ import annotations

import re
import shlex
import uuid
from typing import Any

_ROOT = "/tmp/jarvis-bg"
_ID_RE = re.compile(r"^bg_[0-9a-f]{12}$")


def _new_id() -> str:
    return f"bg_{uuid.uuid4().hex[:12]}"


def _valid(shell_id: str) -> bool:
    """Kun vores egne id'er. Uden det kunne et id smugle sti-fragmenter ind i
    de kommandoer vi bygger nedenfor."""
    return bool(_ID_RE.match(str(shell_id or "")))


async def start_async(*, command: str, user_id: str, cwd: str = "",
                      timeout_s: float = 20.0) -> dict[str, Any]:
    """Start en loesrevet baggrunds-shell. Returnerer {shell_id, pid}.

    `setsid` + omdirigering betyder at processen overlever baade bro-kaldet og
    en genstart af runtimen — den er ikke bundet til den socket der startede
    den. Det er praecis den binding der har kostet afbrudte runs i dag.
    """
    from core.tools.operator_tools import operator_bash_async

    sid = _new_id()
    cd = f"cd {shlex.quote(cwd)} && " if cwd else ""
    boot = (
        f"mkdir -p {_ROOT} && {cd}"
        f"setsid sh -c {shlex.quote(command)} > {_ROOT}/{sid}.log 2>&1 "
        f"& echo $! > {_ROOT}/{sid}.pid; cat {_ROOT}/{sid}.pid"
    )
    res = await operator_bash_async(command=boot, user_id=user_id,
                                    timeout_s=timeout_s)
    pid = str((res or {}).get("stdout") or "").strip().splitlines()
    return {"shell_id": sid, "pid": (pid[-1] if pid else ""), "log": f"{_ROOT}/{sid}.log"}


async def read_async(*, shell_id: str, user_id: str, since: int = 0,
                     timeout_s: float = 20.0) -> dict[str, Any]:
    """Laes NYT output siden byte-offset `since`.

    Returnerer {output, offset, running, exit_code}. `offset` gives tilbage i
    naeste kald — saa er laesningen inkrementel og turen kan foelge en lang
    kommando uden at gentage det den allerede har set.
    """
    from core.tools.operator_tools import operator_bash_async

    if not _valid(shell_id):
        return {"error": f"ukendt shell_id: {shell_id}", "output": "",
                "offset": int(since or 0), "running": False}
    off = max(int(since or 0), 0)
    cmd = (
        f"L={_ROOT}/{shlex.quote(shell_id)}.log; "
        f"P=$(cat {_ROOT}/{shlex.quote(shell_id)}.pid 2>/dev/null); "
        f"SZ=$(wc -c < \"$L\" 2>/dev/null || echo 0); "
        f"if kill -0 \"$P\" 2>/dev/null; then R=1; else R=0; fi; "
        f"echo \"__JBG__ $SZ $R\"; "
        f"tail -c +{off + 1} \"$L\" 2>/dev/null"
    )
    res = await operator_bash_async(command=cmd, user_id=user_id,
                                    timeout_s=timeout_s)
    raw = str((res or {}).get("stdout") or "")
    stoerrelse, koerer, tekst = off, False, ""
    for i, linje in enumerate(raw.splitlines(keepends=True)):
        if linje.startswith("__JBG__"):
            dele = linje.split()
            if len(dele) >= 3:
                try:
                    stoerrelse, koerer = int(dele[1]), dele[2] == "1"
                except ValueError:
                    pass
            tekst = "".join(raw.splitlines(keepends=True)[i + 1:])
            break
    return {"output": tekst, "offset": stoerrelse, "running": koerer,
            "shell_id": shell_id}


async def kill_async(*, shell_id: str, user_id: str,
                     timeout_s: float = 20.0) -> dict[str, Any]:
    """Draeb en baggrunds-shell. Idempotent: en allerede doed shell er ikke en fejl."""
    from core.tools.operator_tools import operator_bash_async

    if not _valid(shell_id):
        return {"error": f"ukendt shell_id: {shell_id}", "killed": False}
    q = shlex.quote(shell_id)
    cmd = (f"P=$(cat {_ROOT}/{q}.pid 2>/dev/null); "
           f"[ -n \"$P\" ] && kill \"$P\" 2>/dev/null; echo draebt")
    await operator_bash_async(command=cmd, user_id=user_id, timeout_s=timeout_s)
    return {"killed": True, "shell_id": shell_id}
