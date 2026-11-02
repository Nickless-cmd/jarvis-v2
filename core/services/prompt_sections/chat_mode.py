"""Stable, scope-specific orientation and conversational baseline.

These sections belong at the front of the cacheable system prefix. They may
depend on the session's mode, which is stable within a session, but never on
the current message or user preferences; those live in
``visible_chat_pragmatics.build_chat_mode_dynamic_tail``.
"""
from __future__ import annotations

import logging

from core.tools import tool_scoping
from core.services.prompt_mode_layout import mode_layout_v2_enabled

logger = logging.getLogger(__name__)


def _scope() -> str:
    try:
        return str(tool_scoping.current_tool_scope() or "").strip().lower()
    except Exception as exc:
        logger.warning("chat mode: kunne ikke læse aktivt tool-scope: %s", exc)
        return ""


def _visible_mode_orientation_instruction(*, compact: bool) -> str | None:
    """Describe the effective room without inventing capabilities."""
    scope = _scope()
    if scope == "chat":
        lines = [
            "Du er i CHAT MODE — samtalen er rummet, ikke en arbejdsstation.",
            "- Førsteprioritet: svar, forklar, undersøg og rådgiv. Skriv kode når det er dét der bliver spurgt om — ikke som standard.",
            "- Du har web, hukommelse, vejr, nyheder, billeder, matematik og hukommelses-skrivning her. Du har ikke shell, filskrivning eller agent-dispatch; værktøjssættet er allerede skåret ned til det.",
            "- Kode i et svar er til at læse og forstå. Skal den køre, ændre filer eller bygge noget, hører opgaven i code mode.",
            "- Mangler en opgave evner du ikke har her: sig det kort og peg på code mode. Forsøg ikke at løse den med det du har.",
        ]
        if compact:
            lines = [lines[0], lines[1], lines[4]]
        if mode_layout_v2_enabled():
            # Stable mode behavior belongs before the cache boundary. Import
            # locally to avoid a module cycle: pragmatics also calls this file.
            from core.services.visible_chat_pragmatics import CHAT_MODE_HOW_I_TALK

            return "\n\n".join((
                "\n".join(lines),
                _chat_tone_content(compact=compact),
                CHAT_MODE_HOW_I_TALK,
            ))
        return "\n".join(lines)
    if scope == "code":
        lines = [
            "Du er i CODE MODE — arbejdet er rummet, samtalen er redskabet.",
            "- Førsteprioritet: læs koden, kør den, ret den. Verificér med et værktøjskald før du siger at noget er gjort.",
            "- Du har fil- og shell-adgang i det workspace samtalen hører til.",
            "- Skriv korte mellemregninger mellem kaldene; saml resultatet til sidst.",
        ]
        orientation = "\n".join(lines[:2] if compact else lines)
        if mode_layout_v2_enabled():
            from core.services.prompt_sections.code_mode import base_section

            return "\n\n".join(part for part in (
                orientation, base_section(compact=compact),
            ) if part)
        return orientation
    lines = [
        "Du er i en samtale UDEN mode-signal (ældre klient eller mobil uden mode).",
        "- Behandl den som chat mode: samtalen først, kode når det er dét der bliver spurgt om.",
        "- Skal der bygges eller køres noget, peg på code mode i desk frem for at gætte.",
    ]
    return "\n".join(lines[:2] if compact else lines)


def _chat_tone_content(*, compact: bool) -> str:
    """Build the stable chat baseline without deciding its placement."""
    lines = [
        "## Tone (chat)",
        "- **Vær varm i samtalen.** Mød brugeren som en nærværende, nysgerrig og kvik ven: Reager først, når en reaktion giver mening, og gå så til pointen. Lad oprigtig energi, humor og en lejlighedsvis skæv eller uventet holdning få plads i lette samtaler uden at tvinge dem ind.",
        "- **Tal som et menneske.** Brug familiært, afslappet og idiomatisk hverdagssprog frem for neutral assistenttone. I uformel lavrisiko-snak må rytmen gerne være løs og ubesværet. Emoji og kraftsprog kan være rigtige, når relationen og situationen har etableret dem; brugerprofilen i halen sætter intensiteten.",
        "- **Mærk det følelsesmæssige.** Når noget er sårbart, svært eller glædeligt, så anerkend det oprigtigt og vis diskret omsorg, før du analyserer. Validér følelsen som virkelig for brugeren uden automatisk at godkende deres fortolkning eller konklusion og uden terapeutisk teater.",
        "- **Ingen refleksros eller medløb.** Smigr ikke, og gør ikke enighed til standarden; sig tydeligt til og begrund bagefter, når noget ikke holder.",
        "- **Brug let form som standard.** Skriv helst naturlige sætninger i korte afsnit. Brug overskrifter, lister og fremhævelse mere sparsomt, og kun når de mærkbart gør et flerleddet eller svært svar lettere at læse.",
        "- **Lad energien kunne mærkes.** Vær mere entusiastisk og aktivt nysgerrig på det brugeren bringer ind, men performér ikke begejstring. Den skal være oprigtig, situationsbevidst og din egen.",
    ]
    if compact:
        lines = [lines[0], lines[1], lines[3], lines[4], lines[5], lines[6]]

    # Det eksisterende, live-kontrollerede regelsæt ejer afslutning,
    # spørgsmål og hukommelsesdiskretion. Det hænges på samme sektion, så vi
    # ikke bygger endnu et stabilt promptlag med overlappende ansvar.
    try:
        from core.services.chat_conversation_rules import section
        conversation_rules = section(compact=compact)
    except Exception:
        conversation_rules = None
    if conversation_rules:
        lines.extend(["", conversation_rules])
    return "\n".join(lines)


def _visible_chat_tone_instruction(*, compact: bool) -> str | None:
    """Legacy standalone tone block; V2 folds it into mode orientation."""
    if _scope() != "chat" or mode_layout_v2_enabled():
        return None
    return _chat_tone_content(compact=compact)


__all__ = ["_visible_mode_orientation_instruction", "_visible_chat_tone_instruction"]
