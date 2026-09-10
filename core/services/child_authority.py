"""Et barn maa ikke laane foraeldrens autoritet — Fase 5.

«child authority/profile/tool scope is frozen before publication, cannot
import ambient parent authority.»

## Hvad der faktisk arves — maalt 10/9-2026

`spawn_agent_task` kalder `execute_agent_task` INLINE (linje 322): ingen traad,
ingen `contextvars.copy_context()`. Barnet koerer altsaa i foraeldrens kontekst
og ser alle fire ambiente ContextVars.

Kun ÉN af dem er en autoritet barnet ikke maa arve:

  `owner_approval`   ET MENNESKE sagde ja til DEN HER handling. Det ja gaelder
                     kaldet, ikke alt hvad kaldet maatte finde paa at starte.
                     Ryddes.
  `run_autonomy`     Et barn af en uovervaaget koersel ER uovervaaget. At rydde
                     det ville give barnet en frihed foraeldren ikke havde —
                     stik modsat af hensigten. Bevares.
  `workspace_trust`  Barnets vaerktoejs-scope hviler paa den; explore mod en
                     workstation ville holde op med at virke. Bevares.
  `tool_scoping`     Samme. Bevares.

## Er det udnytteligt i dag? Nej — og det er ikke pointen

`owner_approval` saettes kun under ét godkendt vaerktoejskald og nulstilles i
`finally`, og ingen af de nitten godkendelses-kraevende vaerktoejer spawner
agenter. Vinduet findes altsaa ikke lige nu.

Men invarianten skal holde naar det naeste vaerktoej tilfoejes, ikke kun i dag.
En arv der er utilsigtet men harmloes, bliver farlig i det oejeblik nogen
kobler de to ting sammen — og saa vil ingen huske at kigge her.
"""
from __future__ import annotations

import contextlib
from typing import Iterator


@contextlib.contextmanager
def uden_foraeldrens_godkendelse() -> Iterator[None]:
    """Koer barnets arbejde UDEN foraeldrens ejer-godkendelse.

    Nulstilles i `finally`, saa foraeldrens eget kald beholder sin godkendelse
    naar barnet er faerdigt. Kaster aldrig af sig selv.
    """
    token = None
    try:
        from core.tools.owner_approval import _ejer_godkendt
        token = _ejer_godkendt.set(False)
    except Exception:
        token = None
    try:
        yield
    finally:
        if token is not None:
            try:
                from core.tools.owner_approval import _ejer_godkendt
                _ejer_godkendt.reset(token)
            except Exception:
                pass
