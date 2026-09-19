"""Svarstil pr. bruger — og påmindelsen der følger med hver tur.

Claude Codes output styles (Jarvis' kortlægning cc-codex-hvad-vi-mangler.md):
stilen injiceres som en påmindelse HVER tur («output style is active …
turnReminder»), og det er derfor den holder hele sessionen i stedet for at
glide. Vi havde samme mekanisme i `prompt_contract`, men den var død: den
læste `config/jarvisx_prefs.json`, som ingen desk- eller mobil-vælger
skrev — målt 19/9-2026: filen fandtes ikke på CT105. Og den var GLOBAL: én
brugers valg ville have styret alles svar, med teksten «Bjørn prefers …».

Nu: stilen gemmes pr. bruger (runtime_state_kv), og påmindelsen siger
«the user», ikke et navn. Den gamle fil læses stadig som faldback, så et
valg der blev gemt dér, ikke forsvinder.
"""
from __future__ import annotations

import json
import logging
from typing import Final

logger = logging.getLogger(__name__)

__all__ = ["STILE", "STANDARD", "hent_stil", "saet_stil", "hint_for_bruger"]

STILE: Final[tuple[str, ...]] = ("balanced", "concise", "detailed", "technical")
STANDARD: Final[str] = "balanced"

_HINTS: Final[dict[str, str]] = {
    "balanced": "",  # standarden — ingen påmindelse
    "concise": ("Output style: CONCISE. The user prefers short, dense answers right now. "
                "Skip preamble. One paragraph max where possible. Code blocks fine, prose around them minimal."),
    "detailed": ("Output style: DETAILED. The user wants thorough explanations. Walk through the "
                 "reasoning, mention edge cases, give examples."),
    "technical": ("Output style: TECHNICAL. Lean into code, types, exact paths, file:line references. "
                  "Less narrative prose, more concrete artifacts."),
}


def _noegle(uid: str) -> str:
    return f"output_style:{uid}"


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


def hent_stil(uid: str) -> str:
    """Brugerens stil; standarden hvis intet er valgt."""
    u = (uid or "").strip()
    if u:
        try:
            from core.runtime.db_core import get_runtime_state_value
            v = get_runtime_state_value(_noegle(u), "")
            if isinstance(v, str) and v in STILE:
                return v
        except Exception:
            logger.debug("output_style: kunne ikke læse %s", u, exc_info=True)
    return _gammel_fil() or STANDARD


def saet_stil(uid: str, stil: str) -> str:
    u = (uid or "").strip()
    s = (stil or "").strip()
    if not u:
        raise ValueError("ingen bruger")
    if s not in STILE:
        raise ValueError(f"ukendt stil {s!r} (gyldige: {', '.join(STILE)})")
    from core.runtime.db_core import set_runtime_state_value
    set_runtime_state_value(_noegle(u), s)
    return s


def hint_for_bruger(uid: str) -> str:
    """Påmindelsen til denne tur — tom for standarden."""
    return _HINTS.get(hent_stil(uid), "")
