"""Et ukendt udfald maa aldrig gentages automatisk — Fase 3, K7.

«non-idempotent `outcome_unknown` is never automatically retried.»

K6 gjorde tilstanden virkelig: et doedt run efterlader nu enten
`aborted_before_dispatch` («skete aldrig» — sikkert at proeve igen) eller
`outcome_unknown` («vi afsendte og saa aldrig udfaldet»). K7 er hvad man saa
maa goere ved den anden.

## Hvorfor «ukendt effekt» taeller som ikke-idempotent

Maalt 9/9-2026: effekt-klassen er erklaeret for 8 af 466 vaerktoejer. 458
staar som `unknown` — herunder `gmail_send`, `stripe_create_issuing_card` og
`operator_bash`. At behandle «ved det ikke» som «sikkert at gentage» ville
vaere at gaette paa den forkerte side af en mail der sendes to gange.

Saa: kun et vaerktoej der beviseligt IKKE aendrer noget, maa gentages efter et
ukendt udfald. Alt andet skal et menneske se paa.

## Hvad der IKKE er et automatisk genforsoeg

Maalt paa de eksisterende veje:

  * runde-genforsoeget i `visible_runs` re-sampler MODELLEN og koerer aldrig
    et vaerktoej igen — invarianten staar skrevet i koden dér.
  * `background_resume` genoptager en TUR naar en shell producerer output;
    den udfoerer intet paa ny.
  * broen afviser i forvejen en gen-overtagelse af SAMME post.

Intet i systemet gentager altsaa et vaerktoej af sig selv i dag. Denne modul
findes for at det bliver ved med at vaere sandt — og for hullet de tre
ovenstaaende ikke daekker: et NYT kald der goer noejagtig det samme.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Dom:
    tilladt: bool
    grund: str
    tidligere: tuple[str, ...] = ()


def _er_beviseligt_uskadeligt(tool_name: str) -> bool:
    """Kun `read_only` — og kun naar den er ERKLAERET, ikke gaettet."""
    try:
        from core.tools.tool_definition_v2 import READ_ONLY, describe
        d = describe(tool_name)
        return d is not None and d.effect_class == READ_ONLY
    except Exception:
        return False


def may_auto_retry(tool_name: str, arguments: dict | None) -> Dom:
    """Maa dette kald gentages AUTOMATISK — uden at et menneske ser paa det?"""
    try:
        from core.runtime.db_approval_bridge import prior_unknown_outcome
        tidligere = tuple(prior_unknown_outcome(tool_name, arguments))
    except Exception:
        # Kan vi ikke slaa op, ved vi ikke om det allerede er sket én gang.
        # Dét er selve tilstanden K7 handler om, saa svaret er nej.
        logger.warning("K7: kunne ikke slaa tidligere udfald op for %s — "
                       "naegter automatisk genforsoeg", tool_name, exc_info=True)
        return Dom(False, "kunne ikke afgoere om det allerede er sket")

    if not tidligere:
        return Dom(True, "")

    if _er_beviseligt_uskadeligt(tool_name):
        return Dom(True, "read_only — en gentagelse aendrer intet", tidligere)

    return Dom(
        False,
        (f"{tool_name} efterlod et UKENDT udfald ({len(tidligere)} gang(e)) og "
         "er ikke erklaeret read_only. Et automatisk genforsoeg kan goere det "
         "samme to gange — et menneske skal se paa det."),
        tidligere,
    )


def advar_hvis_gentagelse(tool_name: str, arguments: dict | None) -> None:
    """Sig hoejt at dette kald gentager noget med ukendt udfald.

    Bruges paa den auto-godkendte sti, hvor registreringen ALDRIG maa blokere
    et kald (se `invocation_record`). Her er den rigtige handling at goere det
    synligt — ikke at stoppe det og ikke at tie.
    """
    try:
        dom = may_auto_retry(tool_name, arguments)
        if not dom.tilladt and dom.tidligere:
            logger.warning("K7: %s gentager et kald med UKENDT udfald "
                           "(tidligere: %s) — %s",
                           tool_name, ", ".join(dom.tidligere[:3]), dom.grund)
    except Exception:
        pass
