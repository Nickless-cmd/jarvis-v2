"""Skill-fladen nævner et skill — og intet kræver et svar (2/10-2026).

Bjørn: «din skill gate, hvorfor bruger du den aldrig? jeg kan se forslagene
rammer dig?» og «jeg synes bestemt du bør bruge dine skills mere».

## Målt samme dag, i koden og mod den kørende runtime

* Fladen fyrer **reelt**: `code-review`, `excel-automation`, `docx`, `pdf`
  matcher på almindelige opgaver, og Bjørn ser den i chatten.
* Men i de **agentiske runder** (117 værktøjer, router + præfiks-lås) overlevede
  INTET skill-værktøj. Kun `load_more_tools` og `call_loaded_tool` er garanteret.
  Den betingede skill-pin fandtes kun i første pas.
* Sidste faktiske skill-brug var **29/9**. Nul i oktober.

Vejen til et skill var derfor tre trin — `load_more_tools` → `call_loaded_tool`
→ `skill_invoke` — mod bash' ét. Tilbuddet tabte hver gang. Ikke fordi det var
dårligt, men fordi alternativet altid var åbent.

## Det manglende led

En regel i prosa («brug dine skills») håndhæver ingenting. Vagten her gør
tilbuddet til et krav der ikke kan ties ihjel: et **stærkt** match (primær,
dvs. score ≥ 0,77 eller skillets navn i beskeden) skal besvares. Enten
invokeres skillet, eller svaret nævner det ved navn — så valget er truffet med
åbne øjne. Er ingen af delene sandt, får modellen ÉN runde til at svare.

Fail-open overalt: kan noget ikke afgøres, fyrer vagten ikke. En vagt der
kaster ville vælte hver tur den rører.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_ENV = "JARVIS_SKILL_GATE_GUARD"

#: De værktøjer der tæller som «skillet blev brugt». `load_more_tools` gør ikke
#: — den henter kun skemaet — og `skill_suggest` er et opslag, ikke en brug.
SKILL_TOOL_NAMES: tuple[str, ...] = ("skill_invoke", "skill_gate", "skill_chain")


def skill_gate_guard_enabled() -> bool:
    """Default TRUE (Bjørn bad om det 2/10-2026). Env vinder, så den kan slås
    fra uden genstart. Enhver tvivl → til."""
    raw = ""
    try:
        raw = str(os.environ.get(_ENV) or "").strip()
    except Exception:  # miljøet kan ikke læses → standarden (til) gælder
        return True
    if not raw:
        return True
    return raw.lower() not in {"0", "false", "no", "off"}


def is_unanswered_skill_match(
    *,
    primary_matches: list[str] | tuple[str, ...] | None,
    called_tool_names: list[str] | tuple[str, ...] | None,
    final_text: str,
    nudged_already: bool = False,
) -> bool:
    """True når et stærkt skill-match stod klar og blev hverken brugt eller nævnt.

    Ren funktion — ingen I/O, ingen tilstand. Kaster aldrig: enhver fejl → False
    (normal afslutning, præcis som før vagten fandtes).
    """
    try:
        if nudged_already:
            return False
        navne = [str(n).strip() for n in (primary_matches or []) if str(n).strip()]
        if not navne:
            return False
        kaldte = {str(n).strip() for n in (called_tool_names or []) if str(n).strip()}
        if kaldte & set(SKILL_TOOL_NAMES):
            return False
        tekst = str(final_text or "")
        if not tekst.strip():
            # Intet svar at vurdere — det er empty-completion, en anden vagts sag.
            return False
        from core.services.skill_relevance_surface import _navnet_staar_i
        if any(_navnet_staar_i(n, tekst) for n in navne):
            return False
        return True
    except Exception:
        logger.debug("is_unanswered_skill_match fejlede", exc_info=True)
        return False


def build_nudge(primary_matches: list[str] | tuple[str, ...] | None) -> str:
    """Beskeden der lægges i turen. Navngiver skillet og giver de to veje."""
    navne = [str(n).strip() for n in (primary_matches or []) if str(n).strip()]
    if not navne:
        return ""
    liste = ", ".join(navne[:3])
    foerste = navne[0]
    return (
        f"\n\n[SKILL-BESLUTNING] Et stærkt skill-match stod klar til denne opgave: "
        f"{liste}. Svaret brugte det ikke og nævnte det ikke. Vælg nu: kald "
        f'skill_invoke("{foerste}") og læs SKILL.md — eller skriv én linje om '
        f"hvorfor den manuelle vej er bedre her."
    )
