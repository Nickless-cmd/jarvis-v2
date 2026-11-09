"""Den faste prompt-prefix' størrelse i tokens — DELT kilde for trigger og visning.

## Hvorfor (målt 9/11-2026)

Compaction-triggeren målte kun det rendrede transcript. Den faktiske model-request
indeholder også den stabile system-prefix (identitet, regler, værktøjskatalog,
hukommelses-sektioner). Målt på en levende kørsel:

    prompt-assembly-size chars=102495 approx_tokens=25623 hale=32705
    visible-latency prompt_chars=442449

Assembly var 25.623 tokens — men requesten var 442.449 tegn ≈ 110.000 tokens.
Forskellen er transcriptet. Triggeren så ~77 % af konteksten og undervurderede
systematisk med den faste del (~17.400 tokens = 22 % af 80k-budgettet).

Konsekvensen er præcis Bjørns observation samme dag: «den compacter ... aldrig
helt ned hvor den burde». Når triggeren fyrede ved «80k», var den reelle kontekst
~105k, og efter komprimering stod den på fast-prefix + markør — ikke på målet.

## Hvad funktionen måler

Kun den STABILE, cachebare del — samme bytes som `build_visible_stable_prefix`
bygger forrest i den ægte prompt. Den dynamiske hale (continuity, awareness,
transcript) tælles ikke med her; den bæres af transcript-målingen.

Memoiseret pr. (provider, model, workspace) i 60 s: prefixen er deterministisk og
ændrer sig kun ved workspace-edit, så et opslag pr. prompt-build er spild.

Self-safe: enhver fejl giver 0, og kalderen falder dermed tilbage til den gamle
adfærd (kun transcript) i stedet for at kaste inde i en prompt-build.
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

#: Hvor længe et prefix-estimat genbruges. Prefixen er deterministisk inden for
#: et workspace, så 60 s er rigeligt — og billigt nok til at kaldes pr. tur.
_CACHE_TTL_SEK = 60.0

# (provider, model, workspace) -> (monotonic-tid, tokens)
_cache: dict[tuple[str, str, str], tuple[float, int]] = {}


def _workspace_for_session(session_id: str) -> str:
    """Workspace-navnet der styrer hvilke identitetsfiler prefixen bærer.

    Samme opslag som statusruten brugte, flyttet her så de to ikke kan divergere.
    Ethvert fejltrin falder tilbage til «default» — et navn, ikke en gætning.
    """
    if not session_id:
        return "default"
    try:
        from core.services.chat_sessions import get_session_owner
        from core.identity.users import find_user_by_discord_id

        oid = get_session_owner(session_id) or ""
        if not oid:
            return "default"
        user = find_user_by_discord_id(oid)
        return str(getattr(user, "workspace", "") or "default")
    except Exception:
        # Workspace-opslaget er valgfrit: prefixen findes også uden et navn.
        return "default"


def stable_prefix_tokens(
    provider: str = "",
    model: str = "",
    session_id: str = "",
) -> int:
    """Tokens i den stabile system-prefix. 0 når den ikke kan måles."""
    workspace = _workspace_for_session(session_id)
    key = (str(provider or ""), str(model or ""), workspace)
    now = time.monotonic()
    hit = _cache.get(key)
    if hit and (now - hit[0]) < _CACHE_TTL_SEK:
        return hit[1]
    try:
        from core.services.prompt_contract import build_visible_stable_prefix
        from core.context.token_estimate import estimate_tokens

        prefix = build_visible_stable_prefix(
            provider=provider, model=model, name=workspace,
        )
        val = int(estimate_tokens(prefix))
    except Exception as exc:
        logger.debug("prompt_overhead: kunne ikke maale prefix (%s)", exc)
        return 0
    _cache[key] = (now, val)
    return val


def reset_cache() -> None:
    """Ryd memoen. Bruges af tests; prefixen selv ændrer sig kun ved workspace-edit."""
    _cache.clear()
