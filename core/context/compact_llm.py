"""Thin wrapper for compact summarisation.

Routing priority (2026-08-19, Bjørn: "cheap lane er forkert værktøj til
kompaktering" — et compact-resumé ER Jarvis' hukommelse om et helt forløb,
og modelfilosofien siger at billige modeller må STØTTE ham, ikke definere
ham. Målt: cheap-lane-resuméer tog 2-30s pr. kald og faldt jævnligt til
mekanisk fallback):
  1. Primær-lane (visible provider/model, typisk deepseek) — hurtig, stabil,
     betalt-men-billig; kill-switch `compact_summary_primary` (runtime state).
  2. Cheap lane excluding Groq (sambanova, mistral, openrouter, nvidia-nim, cloudflare)
  3. Heartbeat model (Groq) as last resort

Callers use call_compact_llm(prompt) — never call heartbeat_runtime directly
from compact modules to keep the dependency one-way.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_FALLBACK_SUMMARY = "[Kontekst komprimeret — detaljer ikke tilgængelige]"
_SKIP_GROQ: frozenset[str] = frozenset({"groq"})


def _in_pytest() -> bool:
    """Testværn: et betalt provider-kald må ALDRIG fyre fra en test. Fundet
    19. aug 2026: test_context_compact → update_identity_sketch →
    call_compact_llm → ægte deepseek-HTTPS (40s + penge). Samme mønster som
    prompt_section_reevaluation._review_enabled. Patchbar for compact_llm's
    egne tests."""
    import sys as _sys
    return "pytest" in _sys.modules


def _call_primary(prompt: str, *, max_tokens: int) -> str | None:
    """Summarise via the PRIMARY (visible) lane — the model that defines Jarvis.

    Uses the existing openai-compat one-shot helper (deepseek m.fl.).
    Returns text or None (caller falls through to the cheap lane).
    Kill-switch: runtime state `compact_summary_primary` (default ON).
    """
    if _in_pytest():
        return None
    try:
        from core.runtime.db_core import get_runtime_state_bool
        if not get_runtime_state_bool("compact_summary_primary", default=True):
            return None
    except Exception:
        pass
    try:
        from core.runtime.settings import load_settings
        from core.services.heartbeat_provider_fallback import (
            _OPENAI_COMPAT_PROVIDERS,
            execute_openai_compat_heartbeat_prompt,
        )
        s = load_settings()
        provider = str(getattr(s, "visible_model_provider", "") or "").strip()
        model = str(getattr(s, "visible_model_name", "") or "").strip()
        auth_profile = str(getattr(s, "visible_auth_profile", "") or "").strip() or "default"
        if not provider or not model or provider not in _OPENAI_COMPAT_PROVIDERS:
            return None
        result = execute_openai_compat_heartbeat_prompt(
            prompt=prompt,
            target={"provider": provider, "model": model, "auth_profile": auth_profile},
            max_tokens=max_tokens,
            temperature=0.3,  # resumé, ikke kreativitet
        )
        text = str(result.get("text") or "").strip()
        return text or None
    except Exception as exc:
        logger.warning("compact_llm: primary-lane summary failed (%s) — cheap fallback", exc)
        return None


def _er_hans_tur() -> bool:
    """Sker det her INDE i en af Bjørns egne kørsler?

    ## Hvorfor ejerskab og ikke en liste

    `call_compact_llm` har femten kaldere, og standarden var den betalte lane.
    `daily_journal`, `session_milestones`, `cognitive_state_narrativizer`,
    `identity_sketch`, `auto_remember_subscriber`, `semantic_search_tools`,
    `memory_tools` — næsten alt sammen baggrundsarbejde på Bjørns betalte nøgle,
    mod hans gentagne regel.

    At sætte `tillad_betalt=False` femten steder ville være præcis den fejl den
    gamle betalt-lane-vagt lavede: at vedligeholde en liste over navne. Lister
    forfalder, og kalder nummer seksten ville arve den forkerte standard.

    Reglen siger det selv: DeepSeek kun i visible lane AF HAM. Er der ingen
    synlig kørsel, er der ingen ham.

    ## Retningen ved tvivl

    Kan vi ikke afgøre hvem kaldet tilhører, koster det ikke penge. Det er
    modsat hovedbogens ukendt-regler, og med vilje: dér måler vi en udgift der
    ALLEREDE er sket, og skal ikke underrapportere. Her beslutter vi om en
    udgift skal ske.

    Komprimering sker inde i hans kørsel og beholder derfor primær-lanen —
    beslutningen fra 19. august står urørt, nu af en grund koden selv kan tjekke.
    """
    try:
        from core.services.session_context_resolve import aktivt_run_id
        return str(aktivt_run_id("") or "").startswith("visible-")
    except Exception:
        logger.debug("compact_llm: kunne ikke afgoere koerslen — gratis vej", exc_info=True)
        return False


def _call_cheap_no_groq(prompt: str) -> str | None:
    """Try cheap lane providers, skipping Groq. Returns text or None."""
    try:
        from core.services.cheap_provider_runtime import execute_cheap_lane_via_pool
        result = execute_cheap_lane_via_pool(message=prompt, skip_providers=_SKIP_GROQ)
        text = str(result.get("text") or "").strip()
        return text or None
    except Exception:
        return None


def _call_heartbeat_llm_simple(prompt: str, max_tokens: int) -> str:
    from core.services.heartbeat_runtime import call_heartbeat_llm_simple
    return call_heartbeat_llm_simple(prompt, max_tokens=max_tokens)


def call_compact_llm(prompt: str, *, max_tokens: int = 400,
                     tillad_betalt: bool = False) -> str:
    """Summarise prompt. Tries non-Groq cheap providers first, Groq as fallback.

    Memory Fix Phase 2: automatically prepends the current identity sketch
    so the compaction LLM knows who Jarvis is right now. Falls back to the
    original prompt if sketch is unavailable.

    Never raises — returns a fallback string if all providers are unavailable.

    ## `tillad_betalt` (14/9-2026)

    Rute-prioriteten ovenfor er RIGTIG for komprimering: Bjørn satte den dér
    19. august med en begrundelse — et compact-resumé ER Jarvis' hukommelse om
    et helt forløb. Den beslutning står urørt, og standarden er derfor uændret.

    Men `truth_gate_v2._llm_judge` kalder også herind, siger i sin egen
    docstring «Spørg billig lane», og kører på hvert svar der påstår en
    handling. Målt: ~540 kald i timen mod api.deepseek.com — den største
    enkeltforbruger uden for Bjørns egne ture, mod hans gentagne regel om at
    kun hans egne ture må koste penge.

    Det der manglede var ikke en anden rute, men en måde at sige «jeg er ikke
    komprimering» på. En kalder der beder om den gratis vej falder ALDRIG
    tilbage på den betalte — ellers ville afkaldet kun gælde når alt virkede.

    ## Standarden er GRATIS, og at bruge penge er udtrykkeligt

    Funktionen har femten kaldere. Elleve er baggrundsarbejde — dagbog,
    milepæle, narrativizer, identitets-skitse, auto-remember, semantisk søgning,
    hukommelses-fletning. Fire er komprimering, som Bjørn 19. august
    udtrykkeligt satte på primær-modellen fordi et compact-resumé ER Jarvis'
    hukommelse om et helt forløb.

    Da standarden var `True`, betalte de elleve for de fires beslutning, og
    kalder nummer seksten ville arve det samme. Nu er det omvendt: en ny kalder
    arver den gratis vej, og den der vil bruge penge skal sige det.

    Fejlretningen peger altså mod det billige. Det er den rigtige retning her:
    en for dyr baggrundsopgave er tavs, en for billig komprimering viser sig
    som et dårligere resumé.

    ## OG kaldet skal ske inde i hans tur

    `tillad_betalt=True` er ikke nok alene — se `_er_hans_tur`. En komprimering
    under en AUTONOM kørsel er ikke hans tur og betaler ikke. Begge betingelser
    skal holde, og de svarer på hvert sit spørgsmål: *må det her koste penge?*
    og *er det ham?*
    """
    try:
        from core.services.identity_sketch import get_identity_sketch
        sketch = get_identity_sketch()
        content = sketch.get("content", "")
        if content and len(content) > 20:
            prompt = (
                "## Identity Sketch (hvem er Jarvis lige nu)\n"
                f"{content}\n\n"
                "## Opgave\n"
                f"{prompt}"
            )
    except Exception:
        pass

    if tillad_betalt:
        if _er_hans_tur():
            text = _call_primary(prompt, max_tokens=max_tokens)
            if text:
                return text
        else:
            # Kun komprimering sætter `tillad_betalt`. Naar den alligevel ikke
            # ser en synlig koersel, holder antagelsen om kaldekaeden ikke — og
            # resumeet falder til den billige lane. Det er praecis det Bjoern
            # afviste 19/8, og det ville vaere TAVST: en stub ligner et resume.
            logger.warning(
                "compact_llm: en KOMPRIMERING fandt ingen synlig koersel og "
                "falder til den billige lane — resumeet bliver ringere. "
                "Kaldekaeden er aendret siden 14/9.")
    text = _call_cheap_no_groq(prompt)
    if text:
        return text
    try:
        result = _call_heartbeat_llm_simple(prompt, max_tokens)
        return result if result else _FALLBACK_SUMMARY
    except Exception as exc:
        logger.warning("compact_llm: summarisation failed (%s) — using fallback", exc)
        return _FALLBACK_SUMMARY
