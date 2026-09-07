"""Ejer-godkendelse — «Bjørn har set PRÆCIS denne kommando og sagt ja».

Det er en anden ting end trust, og forskellen er hele pointen.

## Fejlen den findes for

`_exec_bash` afviser destruktive kommandoer ubetinget:

    # DESTRUKTIVT springes ALDRIG over.
    #
    # Naar Bjoern selv har klikket Godkend paa praecis den kommando, kommer
    # kaldet gennem resolve_pending_approval med sin egen godkendelse i
    # ryggen — ikke gennem det her flag.
    if _ec.classification == "destructive":
        return {"status": "approval_needed", ...}

Antagelsen i den sidste sætning holdt ikke. `resolve_pending_approval` kalder
`execute_tool_force` → `_force_bash` → `_exec_bash(_runtime_trust_all=True)`,
altså **præcis dét flag**. En godkendt `rm -rf` ramte derfor gaten igen og fik
`approval_needed` tilbage — i ring. Målt hos Bjørn 7/9: kortet kom, han
godkendte, og runnet ventede videre til det timede ud.

## Hvorfor det ikke bare kan være et argument

`_runtime_trust_all` kan ikke bruges: autonome runs sætter det også
(`simple_tool_executor`, `force=True`), og de har ingen bag sig der har sagt
ja. Bruger man det, kan Jarvis køre `rm -rf` uden et menneske — netop hullet
kommentaren ovenfor lukkede.

Og markøren kan ikke ligge i tool-argumenterne: **modellen skriver selv
argumenterne**. Den kunne så sende sin egen godkendelse med og lukke gaten op
indefra.

Derfor en ContextVar, sat af `execute_tool_force` og KUN når kalderen
udtrykkeligt siger at et menneske har godkendt. Den kan ikke forfalskes fra en
tool-payload, og den nulstilles altid — også hvis værktøjet kaster.
"""

from __future__ import annotations

import contextlib
import contextvars
from typing import Iterator

_ejer_godkendt: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "jarvis_owner_approved", default=False,
)


@contextlib.contextmanager
def ejer_godkendt_kald() -> Iterator[None]:
    """Marker at DETTE kald bærer en menneskelig godkendelse.

    Sættes kun af ``execute_tool_force(..., owner_approved=True)``, som kun
    ``resolve_pending_approval`` kalder sådan. Nulstilles i ``finally``, så en
    fejlende kommando ikke efterlader porten åben for det næste kald i samme
    tråd.
    """
    token = _ejer_godkendt.set(True)
    try:
        yield
    finally:
        _ejer_godkendt.reset(token)


def er_ejer_godkendt() -> bool:
    """Har et menneske godkendt præcis dette kald?

    Læses af de gates der ALDRIG må åbnes af trust alene — først og fremmest
    den destruktive.
    """
    return bool(_ejer_godkendt.get())
