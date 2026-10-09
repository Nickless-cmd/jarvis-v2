"""Hvem kaldte hvilket vaerktoej — gjort taelleligt.

## Hvorfor modulet findes

`tool_router._always_core_set()` bygger den faste vaerktoejskerne som «top-N
efter kald de sidste 7 dage». Den har ingen bruger- og ingen rolle-dimension:
én global liste betjener hele husstanden. Bjoern 29/9-2026: «andre brugere har
andre tool saet.. vores maaling holder stadig ikke.»

Han har ret, og det er vaerre end et maaleproblem. Rangeringen KAN ikke skelne,
for identiteten laa inde i `arguments`:

    json_extract(payload_json, '$._runtime_user_id')  ->  None for alle 59.778

Maalt samme dag: 20.408 kald fra ét bruger-id, 3.033 uden id (Jarvis' egne
autonome runs), nul fra nogen anden. Men 63 % af `tool.invoked` manglede
feltet helt, saa selv med den rigtige sti ville taellingen vaere halv.

Derfor loeftes identiteten op i payloadens ROD her, og et manglende id skrives
som ``UKENDT`` i stedet for at blive udeladt: en taelling hvor 63 % falder ud
lyder som et resultat, mens den er et haul. Feltet i ``arguments`` bliver
staaende — elleve steder i kodebasen laeser det derfra.

## Boy Scout

Udskilt fra `simple_tools.py` (2.256 linjer) 29/9-2026 foer aendringen, jf.
reglen i CLAUDE.md. Udgivelsen af `tool.invoked` er en naturlig enhed: den har
ét ansvar, ét kald, og er nu testbar uden at koere et vaerktoej.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

#: Skrives naar identiteten ikke kan fastslaas. En taelling skal kunne vise
#: hvor stort hullet er — ikke skjule det ved at springe raekken over.
UKENDT = "UKENDT"

#: Argumenterne afkortes i eventet. 100 tegn har vaeret grænsen siden
#: begyndelsen; den er BEVARET her med vilje, saa udskillelsen ikke aendrer
#: adfaerd. (Den er for kort til at diagnosticere en lang kommando — en
#: `commit_with_attribution.py`-linje staar afkortet ved «--repo» — men det er
#: en separat beslutning med en lagerpris, ikke noget der hoerer til her.)
ARG_GRAENSE = 100


def _fra_args(arguments: dict[str, Any], navn: str) -> str:
    return str(arguments.get(navn) or "").strip()


def identitet(arguments: dict[str, Any]) -> dict[str, str]:
    """Bruger, samtale og run — fra argumenterne, ellers fra konteksten.

    Bro-kald (desk' `operator_bash`) gaar uden om `simple_tool_executor`, som
    er den der normalt haefter `_runtime_user_id` paa. Derfor spoerges
    contextvar'en ogsaa: er den sat, er svaret rigtigt, og ellers staar der
    ``UKENDT`` — ikke ingenting.
    """
    uid = _fra_args(arguments, "_runtime_user_id")
    if not uid:
        try:
            from core.identity.workspace_context import current_user_id
            uid = str(current_user_id() or "").strip()
        except Exception as exc:  # ImportError/LookupError — kontekst mangler
            logger.debug("tool_call_telemetry: ingen bruger i konteksten: %s", exc)
            uid = ""
    return {
        "user_id": uid or UKENDT,
        "session_id": _fra_args(arguments, "_runtime_session_id") or UKENDT,
        "run_id": _fra_args(arguments, "_runtime_turn_id") or UKENDT,
    }


def byg_payload(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Selve eventet. Adskilt fra udgivelsen, saa formen kan testes alene."""
    return {
        "tool": str(name),
        **identitet(arguments or {}),
        "arguments": {k: str(v)[:ARG_GRAENSE] for k, v in (arguments or {}).items()},
    }


def udgiv_tool_invoked(name: str, arguments: dict[str, Any]) -> None:
    """Udgiv `tool.invoked`. Maa ALDRIG braekke et vaerktoejskald."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("tool.invoked", byg_payload(name, arguments))
    except Exception as exc:  # bussen nede / payload userialiserbar
        logger.warning("tool_call_telemetry: kunne ikke udgive tool.invoked for %s: %s",
                       name, exc)


#: Shell-vaerktoejer — kun de baerer baade en kommando OG en exit-kode i
#: resultatet. Det er den raa substans bagud-maalingen kraever: detektoren
#: `silent_chain_break` er en REN funktion af (kommando, exit-kode).
SHELL_TOOLS = frozenset({"bash", "bash_session_run", "operator_bash"})

#: Kommandoen gemmes i completed-eventet op til denne graense. `tool.invoked`
#: klipper ved 100 tegn — for kort til at afgoere kaede-strukturen i en rigtig
#: kommando. Detektoren klipper selv ved 400.
COMMAND_GRAENSE = 400


def byg_completed_payload(
    name: str,
    status: str,
    arguments: dict[str, Any],
    result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """`tool.completed` — nu med de to felter der goer parringen mulig.

    Frem til 3/10-2026 bar eventet kun ``{tool, status, mutating}``. Et
    ``tool.invoked`` kunne derfor ikke parres med sit svar, og et panel der
    ville vise «hvad koerer lige nu» kunne ikke se forskel paa et kald der var
    i gang og et der var faerdigt — uden at gaette ud fra raekkefoelgen, hvilket
    netop fejler naar to kald gaar i samme runde.

    ``run_id`` og ``tool_use_id`` ligger begge i ``arguments`` allerede
    (``simple_tool_executor`` haefter dem), saa det er en loeftning, ikke en ny
    maaling. Et UI-kald gennem ``execute_tool`` uden om executoren har dem ikke —
    og faar dermed tomme felter, hvilket er den aerlige beskrivelse af et kald
    der ikke hoerer til et model-run.
    """
    args = arguments or {}
    payload = {
        "tool": str(name),
        "status": str(status),
        "run_id": _fra_args(args, "_runtime_turn_id"),
        "tool_use_id": _fra_args(args, "_runtime_tool_use_id"),
    }
    # Exit-koden (10/10-2026). `tool.completed` bar den ikke, saa Smiths
    # tavse-kaede-detektor kunne kun maales i NUET: exit-koden findes kun i
    # `result` og blev smidt vaek ved udgivelsen. Uden den kan «hvor ofte
    # knækker mine kaeder?» ikke besvares bagud. Kommandoen gemmes med, fordi
    # detektoren er en ren funktion af (kommando, exit-kode) — med begge dele
    # kan historikken afspilles gennem den aegte funktion i stedet for et gæt.
    if str(name) in SHELL_TOOLS and isinstance(result, dict):
        kode = result.get("exit_code")
        if kode is not None:
            payload["exit_code"] = kode
        kommando = _fra_args(args, "command")
        if kommando:
            payload["command"] = kommando[:COMMAND_GRAENSE]
    return payload
