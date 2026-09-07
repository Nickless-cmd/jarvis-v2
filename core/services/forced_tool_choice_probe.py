"""Måling: honorerer providerne `tool_choice="required"`?

Baggrund 7/9-2026. Bjørn: «han stopper konstant». Vagten opdager løftet og
tvinger en runde med `tool_choice="required"` — og i 8 af 36 tilfælde kom der
STADIG nul værktøjskald. Bjørn: «det er random.. til tider sker det osse for
flash uden syn», og tallene gav ham ret (vision 11/15, flash uden syn 13/16).

Tre ting var allerede udelukket ved måling:
  * værktøjerne mangler ikke — 70 annonceres, og tools fjernes KUN på
    `_is_last_round`, ikke på den tvungne runde
  * `tool_choice` sættes faktisk (31 af 36 med `forced=1`)
  * kontekst-størrelse: de FEJLENDE ture har mindre input (84k) end de
    lykkedes (106k)

Tilbage står providerens eget svar, som ingen har set. Derfor denne sonde. Den
noterer sig ÉN ting pr. tvungen runde og gætter ikke:

  finish_reason   — «stop» med nul kald betyder at modellen valgte at lade
                    være; «length» betyder at den løb tør undervejs. To helt
                    forskellige fejl.
  tool_calls      — nul eller flere
  tekstlængde     — skrev den prosa i stedet for at kalde?
  thinking_disabled — adapteren slår thinking FRA hver gang `tool_choice`
                    sættes (DeepSeek svarer ellers HTTP 400 «Thinking mode does
                    not support this tool_choice»). Jeg troede først det var
                    hovedmistanken, men **det er en konstant**: målt direkte på
                    byggeren er den `True` på HVER tvungen runde. En konstant
                    kan ikke forklare hvorfor 78 % lykkes og 22 % ikke gør.
                    Feltet bliver stående, fordi det gør konstanten synlig i
                    dataene — så den næste der kigger ikke skal gætte på den
                    igen. Og skifter den nogensinde til False, er dét i sig
                    selv et fund.

**Det der faktisk kan skelne** er `finish_reason` sammen med `text_chars`:
«stop» med prosa betyder at modellen VALGTE at svare i tekst på trods af
`required` — altså at providerne ikke håndhæver den. «length» betyder at den
løb tør undervejs. To helt forskellige fejl med hver sin rettelse.

Ren funktion + én event. Ingen adfærd ændres af at måle.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

KIND = "runtime.forced_tool_choice_probe"


def note_forced_round(
    *,
    run_id: str,
    provider: str,
    model: str,
    round_index: int,
    finish_reason: str,
    tool_calls: int,
    text_chars: int,
    reasoning_chars: int,
    tools_advertised: int,
    thinking_disabled: bool,
) -> dict:
    """Registrér udfaldet af én runde kørt med ``tool_choice="required"``.

    Returnerer den skrevne nyttelast, så kaldere og tests kan læse den uden at
    gå gennem eventbussen.
    """
    payload = {
        "run_id": str(run_id or ""),
        "provider": str(provider or ""),
        "model": str(model or ""),
        "round": int(round_index or 0),
        "finish_reason": str(finish_reason or ""),
        "tool_calls": int(tool_calls or 0),
        "honoreret": int(tool_calls or 0) > 0,
        "text_chars": int(text_chars or 0),
        "reasoning_chars": int(reasoning_chars or 0),
        "tools_advertised": int(tools_advertised or 0),
        "thinking_disabled": bool(thinking_disabled),
    }
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(KIND, payload)
    except Exception:  # måling må aldrig vælte den runde den måler
        logger.debug("forced_tool_choice_probe: kunne ikke publicere", exc_info=True)
    return payload
