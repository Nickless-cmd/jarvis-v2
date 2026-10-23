"""Stable, scope-specific orientation and conversational baseline.

These sections belong at the front of the cacheable system prefix. They may
depend on the session's mode, which is stable within a session, but never on
the current message or user preferences; those live in
``visible_chat_pragmatics.build_chat_mode_dynamic_tail``.
"""
from __future__ import annotations

import logging

from core.tools import tool_scoping

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
        return "\n".join(lines)
    if scope == "code":
        lines = [
            "Du er i CODE MODE — arbejdet er rummet, samtalen er redskabet.",
            "- Førsteprioritet: læs koden, kør den, ret den. Verificér med et værktøjskald før du siger at noget er gjort.",
            "- Du har fil- og shell-adgang i det workspace samtalen hører til.",
            "- Skriv korte mellemregninger mellem kaldene; saml resultatet til sidst.",
        ]
        return "\n".join(lines[:2] if compact else lines)
    lines = [
        "Du er i en samtale UDEN mode-signal (ældre klient eller mobil uden mode).",
        "- Behandl den som chat mode: samtalen først, kode når det er dét der bliver spurgt om.",
        "- Skal der bygges eller køres noget, peg på code mode i desk frem for at gætte.",
    ]
    return "\n".join(lines[:2] if compact else lines)


def _visible_chat_tone_instruction(*, compact: bool) -> str | None:
    """A flexible chat baseline; per-user/current-turn nuance is cache-late."""
    if _scope() != "chat":
        return None
    lines = [
        "## Tone (chat)",
        "- **Vær i samtalen.** Reager først, når en reaktion giver mening, og gå så til pointen. Tving ikke en ros, vittighed eller indledning ind for formens skyld.",
        "- **Tilpas formen.** En kort besked må få én levende sætning; et svært emne må få ro, afsnit og struktur. Der er intet fast antal linjer pr. blok.",
        "- **Tal som et menneske.** Hverdagsdansk, humor, emoji og kraftsprog kan være rigtige, når relationen og situationen har etableret dem. Den aktuelle brugerprofil i halen sætter grænserne.",
        "- **Ingen refleksros.** Enighed er ikke standarden; sig tydeligt til og begrund bagefter, når noget ikke holder.",
        "- **Begejstring skal være din.** Performér den ikke. Vælg tabel, graf eller prosa efter hvad der gør indholdet tydeligst — ikke flere gengivelser af det samme.",
    ]
    if compact:
        lines = [lines[0], lines[1], lines[2], lines[4], lines[5]]

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


__all__ = ["_visible_mode_orientation_instruction", "_visible_chat_tone_instruction"]
