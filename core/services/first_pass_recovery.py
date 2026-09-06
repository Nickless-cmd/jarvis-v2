"""Hvad gør vi når FØRSTE pas kom tilbage ubrugelig?

To måder et første pas kan svigte, og de har hver sin kur:

1. **Tomt** — intet indhold, ingen tools. DeepSeeks #1453 på thinking-modeller,
   og den er STICKY: spørger man samme model igen, bliver den tom igen. Kuren er
   at gen-spørge en NON-thinking model. `resend_target()` vælger hvilken.

2. **Et tomt løfte** — der ER tekst, den annoncerer en handling, og der blev
   ikke kaldt ét eneste værktøj. Runtimen så det aldrig: hele followup-loopet
   ligger inde i `if _collected_native_tool_calls:`, så et første pas UDEN
   tool-kald sprang loopet over — og værnet mod tomme løfter bor inde i det
   loop. Værnet kunne altså kun nogensinde se løfter der kom EFTER mindst ét
   værktøjskald.

   Det er præcis den klasse Bjørn ramte hele 5/9: «Lad mig bekræfte config'en»
   → turen slut, intet kaldt. Målt samme dag lovede vision-modellen og undlod i
   55 % af sine ture, flash i 15 %; værnet greb 12 af 31.

Udskilt fra `visible_runs.py` (7.152 linjer) efter Boy Scout-reglen, før
første-pas-kuren blev tilføjet.
"""
from __future__ import annotations

# Thinking-modeller deler den STICKY tom-completion-bug: gen-spørg SAMME model
# → tom igen. deepseek har et non-thinking alias vi kan skifte til; andre
# providere har ikke, og faldt derfor tilbage til samme sticky model → cutoff
# (provider-agnostisk, set 3. jul på kimi-k2.7-code:cloud).
_THINK_HINTS = ("kimi", "-code", "deepseek-v", "qwen3", "glm-5", "minimax",
                "gpt-oss", "nemotron", "-r1", "o1-", "think", "reason")

_FALLBACK = ("deepseek", "deepseek-v4-flash", "fast")


def resend_target(provider: str, model: str) -> tuple[str, str, str | None]:
    """(provider, model, thinking_mode) til ét gen-spørg efter et TOMT første pas.

    deepseek beholder sin egen model men får thinking slået fra. Andre
    thinking-modeller falder tilbage til en pålidelig non-thinking formulator, så
    turen får et ÆGTE svar frem for en fallback-stub. Alt andet: uændret.
    Self-safe — enhver tvivl giver det uændrede par.
    """
    try:
        p = (provider or "").strip().lower()
        m = (model or "").strip().lower()
        if p == "deepseek":
            # execute_visible_model normaliserer modellen og slår thinking fra
            # via thinking_mode="fast" (intet deprecated alias).
            return provider, model, "fast"
        if any(t in m for t in _THINK_HINTS):
            return _FALLBACK
        return provider, model, None
    except Exception:
        return provider, model, None


def first_pass_is_hollow(text: str, tool_calls: int) -> bool:
    """Lovede første pas en handling uden at kalde ét eneste værktøj?

    Samme dom som det inline-værn bruger — genbrugt bevidst, så de to steder
    ikke kan komme til at være uenige om hvad et løfte er.
    Self-safe: tvivl → False (turen får lov at stå som den er).
    """
    try:
        if int(tool_calls or 0) != 0:
            return False
        if not (text or "").strip():
            return False        # tomt håndteres af resend-kuren ovenfor
        from core.services.hollow_promise_guard import (
            hollow_promise_guard_enabled, is_promise_of_action,
        )
        if not hollow_promise_guard_enabled():
            return False
        return is_promise_of_action(text)
    except Exception:
        return False


def nudge_for_tool_calls(*, message: str, provider: str, model: str,
                         session_id: str | None, thinking_mode: str,
                         tool_scope: str = "", local_exec: bool = False) -> list[dict]:
    """Spoerg ÉN gang mere, med nudget, ad en vej der ANNONCERER vaerktoejer.

    Foerste forsoeg paa den her kur brugte `execute_visible_model`. Den vej har
    ingen tools-parameter — det er en ren tekst-completion — saa `tool_calls` var
    tom pr. konstruktion og kuren kunne aldrig lykkes. Maalt: 3 forsoeg, 0 loest.

    `stream_visible_model` er derimod netop den vej foerste pas selv bruger, og
    den bygger tool-definitionerne. Vi kalder den igen med nudget haeftet paa, og
    beholder KUN tool-kaldene — teksten kastes vaek. Brugeren har allerede set
    loeftet; det de mangler er at det bliver indfriet, ikke at det bliver sagt
    igen. Falder der kald ud, overtager det eksisterende maskineri dem.

    ContextVar-faelden gaelder her: `get_tool_definitions()` laeser
    `current_tool_scope()`, og scope TABES over traad-graensen. Uden
    re-assertion ser den DEFAULT og bygger alle 126 vaerktoejer i stedet for
    scopets faa. Se reference_tool_scope_ctxvar_lost.

    Self-safe: enhver fejl → tom liste (turen staar som den var, aldrig vaerre).
    """
    try:
        from core.services.hollow_promise_guard import HOLLOW_PROMISE_NUDGE
        from core.services.visible_model import stream_visible_model
        from core.services.visible_model_types import VisibleModelToolCalls
    except Exception:
        return []
    try:
        from core.tools.tool_scoping import set_local_exec, set_tool_scope
        if tool_scope:
            set_tool_scope(tool_scope)
        set_local_exec(bool(local_exec))
    except Exception:
        pass
    try:
        calls: list[dict] = []
        for item in stream_visible_model(
            message=f"{message}\n\n{HOLLOW_PROMISE_NUDGE}",
            provider=provider, model=model, session_id=session_id,
            thinking_mode=thinking_mode,
        ):
            if isinstance(item, VisibleModelToolCalls):
                calls = list(item.tool_calls or [])
        return calls
    except Exception:
        return []
