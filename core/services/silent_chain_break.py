"""Detektor: en bash-kæde der brød tavst ved et ``&&``-led.

## Hvorfor (Bjørn 9/10-2026)

Klassen: en sammensat bash-kommando hvor ét led fejler (exit≠0), og et
SENERE led derfor aldrig producerede output — og Jarvis læser videre som om
hele kommandoen kørte. Målt tre gange på to dage. Den dyreste: ``grep -c``
returnerede 0 træf → exit 1 (grep's dokumenterede kontrakt) → ``&&``-kæden
brød → pytest kørte aldrig og ``cp``-gendannelsen skete ikke, så målingen
fortsatte mod en falsificeret fil.

## Hvorfor ikke en prompt-regel

Læren («brug ; mellem uafhængige led») er låst som beslutning, men en regel
afhænger af at Jarvis husker den i det øjeblik han skriver kommandoen.
Detektoren er mekanisk: den ser exit-koden og kæde-strukturen bagefter.

## Den skarpe regel

``&&`` kortslutter: kør næste led KUN hvis dette lykkedes. Fejler et led i en
REN ``&&``-kæde — ingen ``;`` der redder resten, ingen ``||`` der håndterer
fejlen — kørte alt efter brud-punktet ikke. Det er den eneste kæde-form hvor
exit≠0 beviser et tavst knæk.

``;`` kører alle led uanset · ``||`` kører højre side NETOP fordi venstre
fejlede · en blanding (``a && b || c``) håndterer fejlen med vilje. Ingen af
dem rejses.

## Hvorfor her og ikke i `central_agent_smith.py`

Smiths modul vurderer MØNSTRE over tid (gentagelser, klynger). Detektoren her
ser ÉN hændelse, i det øjeblik exit-koden findes, og føder fundet ind i
``lessons`` — den kilde Smiths egen fejl-detektor allerede læser. Så arver
den hele Smith-maskineriet gratis: en engangs-knæk støjer ikke, en gentaget
bliver til et Smith-fund.

## Self-safe

Enhver fejl → None. En detektor der vælter et tool-kald koster mere end den
fanger.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

#: Kun shell-kald bærer en kommando OG en exit-kode i sit resultat.
#:
#: `operator_bash` med fra 10/10-2026. Maalt: den var 96 % af alle shell-kald
#: (11.238 mod bash' 509 i doegnet), saa uden den saa detektoren 4 % af det
#: den skal fange. Indvendingen var at langt de fleste kald er desk-broens
#: job-poll — men den er nu flagget som internt kald (`_bro_svar` saetter
#: contextvar'et), saa `observe` kaldes slet ikke for den. Tilbage er de
#: aegte model-kald gennem broen, og de kan braekke en `&&`-kaede som alle andre.
_SHELL_TOOLS = frozenset({"bash", "bash_session_run", "operator_bash"})

#: Signaturen alle knæk samles på — så en gentagelse bliver ÉT fund hos Smith,
#: ikke én ny lesson pr. kommando. `repeated_count` kræver en stabil signatur.
_SIGNATURE = "silent_chain_break: bash: &&"


def _led(command: str) -> list[tuple[str, str]]:
    """Split i (operator, led) på top-niveau. Første led har operator ''.

    Respekterer quotes og backslash-escape, så et ``&&`` inde i en streng
    (``grep "a && b" fil``) ikke læses som en operator. Det er hele forskellen
    mellem at fange et rigtigt knæk og at rejse en falsk positiv på en
    kommando der blot nævner operatoren.
    """
    ud: list[tuple[str, str]] = []
    buf: list[str] = []
    op = ""
    i, n = 0, len(command)
    quote = ""
    while i < n:
        ch = command[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and i + 1 < n:
                buf.append(command[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = ""
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            buf.append(ch)
            buf.append(command[i + 1])
            i += 2
            continue
        to = command[i:i + 2]
        if to in ("&&", "||"):
            ud.append((op, "".join(buf)))
            buf = []
            op = to
            i += 2
            continue
        if ch == ";":
            ud.append((op, "".join(buf)))
            buf = []
            op = ";"
            i += 1
            continue
        buf.append(ch)
        i += 1
    ud.append((op, "".join(buf)))
    return ud


def silent_chain_break(command: object, exit_code: object) -> dict | None:
    """Ren detektor. Fund-dict hvis en REN ``&&``-kæde brød, ellers None.

    Ingen side-effekter, ingen DB, ingen logging — kun et svar. Det gør den
    falsificerbar: en test kan kalde den direkte og se den AFVISE.
    """
    cmd = str(command or "").strip()
    if not cmd:
        return None
    try:
        kode = int(exit_code)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None  # ingen exit-kode = ingen dom at fælde
    if kode == 0:
        return None
    led = _led(cmd)
    operatorer = [op for op, _ in led[1:]]
    # Kun en REN kortslutnings-kæde: mindst to led, og HVER operator er `&&`.
    # Et enkelt `;` eller `||` i kæden gør exit-koden tvetydig — så tier vi.
    if len(led) < 2 or not operatorer or any(op != "&&" for op in operatorer):
        return None
    return {
        "kind": "silent_chain_break",
        "command": cmd[:400],
        "exit_code": kode,
        "led": len(led),
        "reason": (
            f"ren `&&`-kæde med {len(led)} led fejlede (exit {kode}); "
            f"led efter brud-punktet kørte ikke"
        ),
    }


def _record(fund: dict) -> None:
    """Fød fundet ind i `lessons` — kilden Smiths fejl-detektor læser."""
    try:
        from core.runtime.db_lessons import SOURCE_TOOL_ERROR, upsert_lesson

        upsert_lesson(
            signature=_SIGNATURE,
            lesson=(
                f"En `&&`-kæde brød tavst: exit {fund['exit_code']} efter "
                f"{fund['led']} led — resten kørte ikke, og jeg læste videre som "
                f"om hele kommandoen kørte. Kommando: {fund['command']}"
            ),
            source=SOURCE_TOOL_ERROR,
        )
    except Exception:  # self-safe: en fejl her maa ikke vaelte tool-flow
        logger.debug("silent_chain_break: kunne ikke skrive lesson", exc_info=True)


def observe(tool_name: object, arguments: object, result: object) -> dict | None:
    """Kaldes fra `execute_tool` efter hvert kald. Self-safe → None.

    Returnerer fundet (så kalderen kan logge det) eller None. Skriver fundet
    til `lessons` som side-effekt — det er hele koblingen til Smith.

    Wrapperen er med vilje tynd: `try` har ÉN sætning, så den fanger netop
    det kald den skal og ikke en tastefejl længere nede.
    """
    try:
        return _observe_impl(tool_name, arguments, result)
    except Exception:  # self-safe: detektoren maa ikke vaelte et tool-kald
        return None


def _observe_impl(tool_name: object, arguments: object, result: object) -> dict | None:
    if str(tool_name) not in _SHELL_TOOLS or not isinstance(result, dict):
        return None
    fund = silent_chain_break(
        command=(arguments or {}).get("command") if isinstance(arguments, dict) else None,
        exit_code=result.get("exit_code"),
    )
    if fund is None:
        return None
    _record(fund)
    return fund
