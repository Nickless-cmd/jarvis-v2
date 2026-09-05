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
