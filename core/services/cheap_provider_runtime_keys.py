"""Udbydere hvis ejer-nøgle bor i `runtime.json` — ikke i auth-profil-arkivet.

De fleste cheap-lane-udbydere henter deres nøgle gennem `get_provider_credentials`
(en fil pr. profil). Nogle få har i stedet ÉN delt ejer-nøgle i `runtime.json`,
fordi de ikke er per-bruger: HuggingFace-tokenet deles med `hf_connector`, og
xkiro-nøglen lagde Bjørn samme sted.

Det her er ikke en detalje man kan nøjes med at rette ét sted. Nøglen skal
bruges TO steder — i `provider_auth_ready()` (ellers markeres udbyderen som
ikke-klar og kommer aldrig i puljen) og i credential-opslaget ved dispatch
(ellers rejses `auth-not-ready` selvom nøglen findes). Da HuggingFace blev
tilføjet, blev begge steder skrevet i hånden; ved den anden udbyder ville det
være to kopier mere. Derfor ét sted med et navn.

Boy-Scout-udskillelse 7/9-2026: `cheap_provider_runtime_adapters` var 2.021
linjer. `_huggingface_runtime_token` re-eksporteres derfra, så eksisterende
kaldere og tests virker uændret.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# provider → (nøgle i runtime.json, env-override)
RUNTIME_KEY_PROVIDERS: dict[str, tuple[str, str]] = {
    "huggingface": ("huggingface_token", "HUGGINGFACE_TOKEN"),
    "xkiro": ("xkiro_api_key", "XKIRO_API_KEY"),
}


def runtime_owner_key(provider: str) -> str:
    """Den delte ejer-nøgle for `provider`, eller "" hvis den ikke findes.

    Tom streng frem for en undtagelse: en manglende nøgle betyder «udbyderen er
    ikke klar», ikke «systemet er i stykker». Cheap-lane skal kunne køre videre
    på de andre udbydere.
    """
    par = RUNTIME_KEY_PROVIDERS.get(str(provider or "").strip())
    if not par:
        return ""
    navn, env = par
    try:
        from core.runtime.secrets import read_runtime_key
        return str(read_runtime_key(navn, env_override=env) or "").strip()
    except Exception:
        logger.debug("runtime_owner_key(%s): kunne ikke læse %s", provider, navn, exc_info=True)
        return ""


def has_runtime_owner_key(provider: str) -> bool:
    """Bruges af readiness. Adskilt fra `runtime_owner_key` så kaldere ikke
    kommer til at logge eller sammenligne på selve nøglen."""
    return bool(runtime_owner_key(provider))
