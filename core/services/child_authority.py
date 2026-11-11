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
def uden_foraeldrens_vaerktoejsscope() -> Iterator[None]:
    """Koer barnet uden foraeldrens INTERAKTIVE vaerktoejsscope.

    MAALT 11/11-2026 — og det retter en fejl i denne fils egen tabel.

    Tabellen ovenfor siger «tool_scoping ... Bevares», med begrundelsen at
    barnets vaerktoejsscope hviler paa den. Det er forkert for kontraktagenter:
    deres vaerktoejer kommer fra `allowed_tools_json` (agentens EGEN politik),
    og scopet er en FLADE-begreb — `chat` og `code` beskriver hvilken fane
    mennesket sidder i, ikke hvad agenten maa.

    Maalt konsekvens foer rettelsen: `_build_agent_tools_payload()` med en
    researcher-politik gav

        scope=''      10 vaerktoejer (inkl. web_search)
        scope='chat'   6
        scope='code'   4  — praecis read_file, search, find_files, agent_note

    En agent dispatchet fra code mode fik altsaa fire laese-vaerktoejer i
    stedet for sine ti, kunne ikke soege paa nettet, meldte det aerligt — og
    blev bogfoert som `AGENT_INCOMPLETE`. 31 af 38 agentfejl laa i
    `delivery`-fasen. Agenten havde ret; vi tog fejl.

    Nulstilles til "" (owner/unbound = ingen flade-filtrering). Det er ikke en
    udvidelse af barnets rettigheder: `_build_agent_tools_payload(allowed)`
    skaerer stadig mod politikkens liste, saa barnet kan aldrig faa mere end
    sin egen politik giver det. Invarianten er at barnets autoritet kommer fra
    POLITIKKEN, ikke fra den flade der tilfaeldigt dispatchede det.
    """
    from core.tools.tool_scoping import reset_tool_scope, set_tool_scope
    token = set_tool_scope("")
    try:
        yield
    finally:
        reset_tool_scope(token)


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
