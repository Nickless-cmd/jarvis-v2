"""Runde-resultater → `ToolResult` til modellens naeste runde og til den gemte tur.

Udskilt fra `visible_runs.py` (7.770 linjer) 18/9-2026 efter Boy Scout-reglen,
foer logikken blev aendret. Funktionen var en indlejret closure, men den brugte
intet fra sit omsluttende scope — kun sine argumenter.

## Aendringen

Kaldets udfald foelger nu med (`ToolResult.status`). Foer blev det kastet vaek
her, og den gemte tur (`visible_turn_accumulator`) kunne kun gaette. Den
gaettede «done» for alt: 4.885 af 4.885 gemte resultater paa CT105 var
succeser, ogsaa dem der fejlede. Live stod en fejl alene i traaden, fordi
stroemmen bar den rigtige status; efter genindlaesning var den foldet ind i
gruppen som en succes.
"""
from __future__ import annotations

from core.services import visible_followup_events as _vf

# #2 Per-runde-nudge (ReAct «Observation → Thought»): en KORT statisk instruks
# paa det SIDSTE tool-resultat, saa modellen moeder den lige foer den beslutter
# naeste runde. Statisk + append-only → cache-sikker; delt af first-pass og
# alle agentiske runder, saa den rammer alle providers ens.
#
# Den ligger i `med_react_nudge` — PROMPT-laget — og ikke i `to_followup_results`,
# fordi den ellers blev persisteret ind i den gemte turs `tool_result.content`
# (maalt 16/10-2026: besked 198525). Data-laget skal vaere rent.
_NUDGE = (
    "\n\n(⟳ Før du fortsætter: skriv én kort sætning om hvad disse resultater "
    "betyder og hvad du gør nu.)"
)


def _billede(result: object) -> str:
    # Et resultat er ikke altid et dict; foer ville en streng her kaste.
    return str(result.get("image_data_url") or "") if isinstance(result, dict) else ""


def to_followup_results(
    tool_calls: list[dict],
    round_results: list[dict[str, object]],
    resolved_texts: dict[int, str],
) -> list[_vf.ToolResult]:
    out: list[_vf.ToolResult] = []
    for idx, tc in enumerate(tool_calls):
        sr = round_results[idx] if idx < len(round_results) else {}
        sr = sr or {}
        content = str(resolved_texts.get(idx, sr.get("result_text", "")) or "").strip()
        tc_name = str(
            sr.get("tool_name")
            or ((tc.get("function") or {}).get("name") or tc.get("name") or "tool")
        )
        status = str(sr.get("status") or "")
        if not content:
            if idx >= len(round_results):
                content = (
                    f"[{tc_name}]: Tool call was not executed in this round "
                    "(bounded tool-execution limit reached)."
                )
                # Et kald der ALDRIG blev koert er ikke lykkedes. Uden status
                # her ville det blive gemt som en succes.
                status = status or "error"
            else:
                content = f"[{tc_name}]: Tool call completed with no output."
        out.append(
            _vf.ToolResult(
                tool_call_id=str(tc.get("id") or ""),
                tool_name=tc_name,
                content=content,
                image_data_url=_billede(sr.get("result")),
                status=status,
            )
        )
    return out


def med_react_nudge(results: list[_vf.ToolResult]) -> list[_vf.ToolResult]:
    """PROMPT-kopien: samme resultater, men det sidste baerer ReAct-nudgen.

    Nudgen er en INSTRUKS til modellen — ikke en del af vaerktoejets svar. Den
    maa derfor kun ligge i den kopi der gaar til naeste runde, aldrig i den
    gemte tur (16/10-2026).

    Foer laa den i `to_followup_results`, og SAMME liste gik baade til
    `_turn.add_tools` (persistens) og til `ToolExchange` (prompt). Nudgen blev
    derfor skrevet ind i `tool_result.content` i den gemte historik — maalt:
    besked 198525, position 2630. En JSON-streng med nudgen haeftet paa er
    UGYLDIG JSON, saa enhver laeser der parser blokken fejlede: mobilens
    spoergsmaals-kort døde, og tre klienter kompenserede hver for sig med
    samme regex. Nu er kilden ren, og kun prompten baerer instruksen.
    """
    if not results:
        return results
    last = results[-1]
    ud = list(results)
    ud[-1] = _vf.ToolResult(
        tool_call_id=last.tool_call_id,
        tool_name=last.tool_name,
        image_data_url=last.image_data_url,
        status=last.status,
        content=last.content.rstrip() + _NUDGE,
    )
    return ud
