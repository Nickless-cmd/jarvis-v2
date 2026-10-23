"""Svarstil pr. bruger — og påmindelsen der følger med hver tur.

Claude Codes output styles (Jarvis' kortlægning cc-codex-hvad-vi-mangler.md):
stilen injiceres som en påmindelse HVER tur («output style is active …
turnReminder»), og det er derfor den holder hele sessionen i stedet for at
glide. Vi havde samme mekanisme i `prompt_contract`, men den var død: den
læste `config/jarvisx_prefs.json`, som ingen desk- eller mobil-vælger
skrev — målt 19/9-2026: filen fandtes ikke på CT105. Og den var GLOBAL: én
brugers valg ville have styret alles svar, med teksten «Bjørn prefers …».

Nu: stilen gemmes pr. ARBEJDSRUM (runtime_state_kv), og påmindelsen siger
«the user», ikke et navn. Den gamle fil læses stadig som faldback, så et
valg der blev gemt dér, ikke forsvinder.

## Hvorfor arbejdsrum og ikke user_id

`current_user_id()` er ofte TOM for ejeren inde i run-generatoren (se
enheds-linjen i prompt_contract), og ejerens samtaler bærer tre stempler
(Discord-id, `bjorn`, `system`). Et valg gemt under ét id ville aldrig blive
fundet under et andet. Arbejdsrummet er det samme på begge sider:
`rum_for_anmodning()` når valget gemmes, `rum_for_tur()` når turen bygges —
den sidste spørger samtalens ejer først, så en tabt kontekst ikke giver en
anden brugers tur ejerens stil.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Final

logger = logging.getLogger(__name__)

__all__ = [
    "STILE", "STANDARD", "CHAT_STYLE_DEFAULTS", "hent_stil", "saet_stil",
    "hent_chat_style", "saet_chat_style", "hint_for_bruger",
    "rum_for_anmodning", "rum_for_tur",
]

STILE: Final[tuple[str, ...]] = ("balanced", "concise", "detailed", "technical")
STANDARD: Final[str] = "balanced"

# Samtaletonen er et supplement til output_style, ikke endnu en længdevælger.
# Hvert felt har en adaptiv standard, så en ny bruger får Jarvis' egen stemme,
# mens et eksplicit valg følger brugeren på tværs af Desk og mobil.
CHAT_STYLE_DEFAULTS: Final[dict[str, str]] = {
    "tone": "adaptive",
    "emoji": "adaptive",
    "profanity": "adaptive",
    "visuals": "adaptive",
    "questions": "adaptive",
}
_CHAT_STYLE_VALUES: Final[dict[str, tuple[str, ...]]] = {
    "tone": ("adaptive", "warm", "direct", "playful"),
    "emoji": ("adaptive", "rare", "expressive"),
    "profanity": ("adaptive", "avoid", "comfortable"),
    "visuals": ("adaptive", "plain", "rich"),
    "questions": ("adaptive", "rare", "curious"),
}

_HINTS: Final[dict[str, str]] = {
    "balanced": "",  # standarden — ingen påmindelse
    "concise": ("Output style: CONCISE. The user prefers short, dense answers right now. "
                "Skip preamble. One paragraph max where possible. Code blocks fine, prose around them minimal."),
    "detailed": ("Output style: DETAILED. The user wants thorough explanations. Walk through the "
                 "reasoning, mention edge cases, give examples."),
    "technical": ("Output style: TECHNICAL. Lean into code, types, exact paths, file:line references. "
                  "Less narrative prose, more concrete artifacts."),
}


def _noegle(rum: str) -> str:
    return f"output_style:{rum}"


def _chat_style_noegle(rum: str) -> str:
    return f"chat_style:{rum}"


def rum_for_anmodning() -> str:
    """Arbejdsrummet for den der kalder API'et."""
    from core.identity.workspace_context import current_workspace_name
    return (current_workspace_name() or "").strip()


def rum_for_tur(session_id: str = "") -> str:
    """Arbejdsrummet for den tur der bygges: samtalens ejer først."""
    sid = (session_id or "").strip()
    if sid:
        try:
            from core.services.chat_sessions import get_session_owner
            from core.identity.session_access import arbejdsrum_for
            ejer = (get_session_owner(sid) or "").strip()
            if ejer:
                return arbejdsrum_for(ejer)
        except Exception:
            logger.debug("output_style: ejer af %s kunne ikke slås op", sid, exc_info=True)
    return rum_for_anmodning()


def _gammel_fil() -> str:
    """Den globale fil fra den pensionerede jarvisx-app — kun som faldback."""
    try:
        from pathlib import Path
        from core.runtime.config import CONFIG_DIR
        p = Path(CONFIG_DIR) / "jarvisx_prefs.json"
        if p.is_file():
            v = str(json.loads(p.read_text(encoding="utf-8")).get("output_style") or "")
            return v if v in STILE else ""
    except Exception:
        logger.debug("output_style: gammel fil kunne ikke læses", exc_info=True)
    return ""


def hent_stil(rum: str) -> str:
    """Arbejdsrummets stil; standarden hvis intet er valgt."""
    u = (rum or "").strip()
    if u:
        try:
            from core.runtime.db_core import get_runtime_state_value
            v = get_runtime_state_value(_noegle(u), "")
            if isinstance(v, str) and v in STILE:
                return v
        except Exception:
            logger.debug("output_style: kunne ikke læse %s", u, exc_info=True)
    return _gammel_fil() or STANDARD


def saet_stil(rum: str, stil: str) -> str:
    u = (rum or "").strip()
    s = (stil or "").strip()
    if not u:
        raise ValueError("intet arbejdsrum")
    if s not in STILE:
        raise ValueError(f"ukendt stil {s!r} (gyldige: {', '.join(STILE)})")
    from core.runtime.db_core import set_runtime_state_value
    set_runtime_state_value(_noegle(u), s)
    return s


def hent_chat_style(rum: str) -> dict[str, str]:
    """Returnér en valideret samtaleprofil for arbejdsrummet.

    Ukendte/fremtidige felter ignoreres, så en ældre runtime kan læse en profil
    skrevet af en nyere klient uden at gøre hele preference-endpointet dødt.
    """
    profil = dict(CHAT_STYLE_DEFAULTS)
    u = (rum or "").strip()
    if not u:
        return profil
    try:
        from core.runtime.db_core import get_runtime_state_value
        raw: Any = get_runtime_state_value(_chat_style_noegle(u), {})
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (TypeError, ValueError):
                raw = {}
        if isinstance(raw, dict):
            for felt, gyldige in _CHAT_STYLE_VALUES.items():
                value = str(raw.get(felt) or "").strip().lower()
                if value in gyldige:
                    profil[felt] = value
    except Exception:
        logger.debug("chat_style: kunne ikke læse %s", u, exc_info=True)
    return profil


def saet_chat_style(rum: str, updates: dict[str, Any]) -> dict[str, str]:
    """Flet validerede, eksplicitte tonevalg ind i arbejdsrummets profil."""
    u = (rum or "").strip()
    if not u:
        raise ValueError("intet arbejdsrum")
    if not isinstance(updates, dict) or not updates:
        raise ValueError("ingen chat_style-felter")
    ukendte = sorted(set(updates) - set(_CHAT_STYLE_VALUES))
    if ukendte:
        raise ValueError(f"ukendte chat_style-felter: {', '.join(ukendte)}")
    profil = hent_chat_style(u)
    for felt, raw in updates.items():
        value = str(raw or "").strip().lower()
        gyldige = _CHAT_STYLE_VALUES[felt]
        if value not in gyldige:
            raise ValueError(
                f"ukendt {felt} {value!r} (gyldige: {', '.join(gyldige)})"
            )
        profil[felt] = value
    from core.runtime.db_core import set_runtime_state_value
    set_runtime_state_value(_chat_style_noegle(u), profil)
    return profil


def hint_for_bruger(rum: str) -> str:
    """Påmindelsen til denne tur — tom for standarden."""
    return _HINTS.get(hent_stil(rum), "")
