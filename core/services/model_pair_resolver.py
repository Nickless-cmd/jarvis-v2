"""Findes den valgte model hos den valgte udbyder?

## Hvorfor filen findes

`ollama/glm-5.2` kørte 162 gange mellem 20. juli og 9. september 2026 og
svarede TOMT hver eneste gang. På ollama hedder modellen `glm-5.2:cloud`; det
bare navn findes kun i routerens alibaba-post. Parret var altså forkert, men
intet kontrollerede det.

Resultatet var det værst tænkelige: HTTP 200, nul tokens, ingen fejl og ingen
faktura. Bare tavshed — og runnet blev markeret `completed`. Fejlen kunne ikke
opdages bagefter, fordi den lignede en succes i enhver optælling.

`central_router_adapt.resolve_visible_model` lader med vilje et eksplicit
model-valg gå uændret igennem: brugerens valg skal vinde. Det er rigtigt som
POLITIK. Men "dit valg vinder" er ikke det samme som "dit valg tjekkes aldrig",
og det var forskellen der kostede syv uger.

## Hvad den gør

* Kan vi ikke slå udbyderens modelliste op → **lad parret gå**. En utilgængelig
  udbyder er ikke det samme som en forkert model, og at blokere her ville gøre
  en kortvarig netværksfejl til et afvist svar.
* Findes modellen præcist → lad den gå.
* Findes den kun med ét suffiks (`glm-5.2` → `glm-5.2:cloud`) → **oversæt**, og
  sig det i loggen. Ollama rapporterer selv det bare navn som `remote_model`
  for sine cloud-modeller, så det bare navn ER et legitimt alias.
* Flere kandidater, eller ingen → **fejl højt**. Et tomt svar er værre end en
  fejlbesked, fordi ingen kan se hvad der gik galt.

## Kun ollama slås op

Suffiks-skemaet (`:cloud`, `:8b`, `:latest`) er ollamas. For andre udbydere
lader vi parret gå — vi har ikke en billig, pålidelig liste, og et gæt ville
være værre end ingenting.
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


class UnknownModelPair(RuntimeError):
    """Modellen findes ikke hos udbyderen — eller navnet er tvetydigt."""


#: Modellisten er ikke gratis at hente, og den her ligger på den varme sti.
_CACHE_TTL_S = 300.0
_cache: dict[str, tuple[float, list[str]]] = {}


def _nulstil_cache_for_tests() -> None:
    _cache.clear()


def _ollama_modeller(base_url: str | None = None) -> list[str] | None:
    """Ollamas modelnavne. `None` betyder «kunne ikke spørge», ikke «tom»."""
    now = time.monotonic()
    key = str(base_url or "")
    hit = _cache.get(key)
    if hit and now - hit[0] < _CACHE_TTL_S:
        return hit[1]
    try:
        import httpx
        from core.services.semantic_memory import _ollama_base_url
        base = base_url or _ollama_base_url()
        data = httpx.get(f"{base}/api/tags", timeout=5.0).json()
        navne = [str(m.get("name") or "") for m in (data.get("models") or [])]
        navne = [n for n in navne if n]
    except Exception:
        logger.warning("model_pair_resolver: kunne ikke hente ollamas modelliste",
                       exc_info=True)
        return None
    _cache[key] = (now, navne)
    return navne


def kandidater(navne: list[str], model: str) -> list[str]:
    """Hvilke navne på listen kunne `model` mene?

    Ren funktion. Præcist match vinder alene; ellers alle med samme basisnavn.
    """
    want = str(model or "").strip()
    if not want:
        return []
    if want in navne:
        return [want]
    base = want.split(":", 1)[0]
    return sorted(n for n in navne if n.split(":", 1)[0] == base)


def resolve(provider: str, model: str, *, base_url: str | None = None) -> tuple[str, str]:
    """Returnér (provider, model) med modellen oversat hvis det er entydigt.

    Kaster `UnknownModelPair` når modellen ikke findes eller navnet er
    tvetydigt. Kaster ALDRIG fordi udbyderen ikke kunne spørges.
    """
    p, m = str(provider or "").strip(), str(model or "").strip()
    if p != "ollama" or not m:
        return p, m

    navne = _ollama_modeller(base_url)
    if navne is None:
        # Kunne ikke spørge. At blokere her ville gøre en kortvarig netværksfejl
        # til et afvist svar.
        return p, m
    if not navne:
        logger.warning("model_pair_resolver: ollama rapporterer NUL modeller — "
                       "lader %r gå uændret", m)
        return p, m

    k = kandidater(navne, m)
    if k == [m]:
        return p, m
    if len(k) == 1:
        logger.info("model_pair_resolver: oversatte %s/%s → %s (bart navn er et "
                    "alias for cloud-modellen)", p, m, k[0])
        return p, k[0]
    if len(k) > 1:
        raise UnknownModelPair(
            f"{p}/{m} er tvetydigt — det kunne være {', '.join(k)}. "
            "Vælg det fulde navn."
        )
    raise UnknownModelPair(
        f"{p}/{m} findes ikke. {p} har: {', '.join(sorted(navne)[:12])}"
        + (" …" if len(navne) > 12 else "")
    )


def resolve_safe(provider: str, model: str, *, base_url: str | None = None
                 ) -> tuple[str, str, str]:
    """Som `resolve`, men returnerer fejlen frem for at kaste.

    Returnerer `(provider, model, problem)` hvor `problem` er tom når alt er
    godt. Til kaldesteder der har lovet aldrig at kaste — de kan så vælge at
    vise fejlen frem for at streame ingenting.
    """
    try:
        p, m = resolve(provider, model, base_url=base_url)
        return p, m, ""
    except UnknownModelPair as e:
        return str(provider or ""), str(model or ""), str(e)
