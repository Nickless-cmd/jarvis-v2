"""Kvote-regnskab pr. søgeprovider — målt hos KILDEN, ikke gættet.

## Hvorfor (målt 18/10-2026)

Søgekæden (`core/tools/simple_tools_web._fetch_alle_providers`) bruger Exa
først og falder tilbage til SerpAPI og Tavily. Ingen af dem havde et
forbrugsregnskab, og ingen advarede før kvoten var væk. Målt den dag:

    Tavily    198 / 1000 pr. md   (plan "Researcher")
    SerpAPI    43 /  250 pr. md   (Free Plan, fornyes 18/11)
    Exa       ingen nøgle → intet kvote-endpoint

SerpAPIs loft er 10× mindre end Tavilys. Bliver den fast lane, rammer loftet
først dér — og opdages først når kæden fejler og falder tilbage.

## Det vigtigste designvalg: spørg kilden

Tavily og SerpAPI **ved** hvor meget der er brugt. En lokal tæller ville kun
vide hvad *denne* proces har kaldt — ikke kald fra scripts, tests eller en
tidligere proces før en genstart. At tælle lokalt for alle tre ville være at
måle sin egen antagelse, som er dagens dyreste målefælde i ren form.

Derfor: **live fra provideren når den kan, lokal tælling kun når den ikke kan**
(Exa, som kører uden nøgle gennem MCP).

## Spredning er en NØDBREMSE, ikke en default

En nærliggende læsning af «brug den provider med mest tilbage» er at sprede
forbruget jævnt. Det ville sænke kvaliteten: målt top-1-præcision er Exa 70 %,
SerpAPI 50 %, Tavily 20 %. At sende hver tredje søgning til Tavily for at spare
Exas kvote ville bytte et reelt kvalitetstab for en kvote vi ikke er ved at
løbe tør for.

Derfor vælger `bedste_provider()` den foretrukne så længe den har plads, og
skifter kun når den nærmer sig loftet. Kvaliteten bevares, og vi udtømmes
gradvist i stedet for at ramme en væg uden varsel.

## Fail-open, altid

Kan kvoten ikke læses, antages der plads. En vagt der blokerer søgninger fordi
den ikke kunne læse et regnskab, er værre end ingen vagt.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

#: De tre kilder i kæden, i kvalitetsrækkefølge (målt top-1 18/10-2026).
PROVIDERS: tuple[str, ...] = ("exa", "serpapi", "tavily")

#: Nulstillingsperiode pr. provider — og dermed hvilken slags loft der gælder.
#:
#: MÅLT 19/10-2026: Exa er IKKE på $10-kreditloftet (2.500 kald/md) sådan som
#: den anonyme MCP-vej bruges her. `mcp.exa.ai` uden egen nøgle er
#: IP-rate-limitet: kilden (`exa-labs/exa-mcp-server`, `api/mcp.ts`) sætter
#: `RATE_LIMIT_QPS` (default 2) og `RATE_LIMIT_DAILY` (default 50) for kald
#: uden API-nøgle, og begge limitere initialiseres sammen.
#:
#: QPS-loftet blev målt samme dag: 3 af 6 parallelle kald gav 429 med
#: `Retry-After: 1` — altså et vindue der nulstilles med det samme, ikke et
#: forbrugsloft. Det DAGLIGE tal er ikke målt; 50 er kildens default, og
#: `noter_429()` retter det når loftet faktisk rammes.
PERIODER: dict[str, str] = {"exa": "dag", "serpapi": "maaned", "tavily": "maaned"}

#: Kendte gratis-loft. `None` = ukendt (kan ikke varsles imod).
GRAENSER: dict[str, int | None] = {
    "exa": 50,       # pr. DAG — antaget fra kilden, kalibreres af noter_429()
    "serpapi": 250,  # pr. måned, læses live
    "tavily": 1000,  # pr. måned, læses live
}

#: Ved denne andel af kvoten varsles der.
LOFT_FRAKTION = 0.80

#: Live-kvote caches så vi ikke spørger provideren ved hvert søgekald.
LIVE_TTL_SEKUNDER = 600

#: Én advarsel pr. provider pr. døgn — ellers fyrer den ved hvert kald.
VARSEL_COOLDOWN_SEKUNDER = 86400

_STATE_PREFIX = "search_quota"


# ---------------------------------------------------------------- state


def _laes(key: str, default: Any = None) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value

        raa = get_runtime_state_value(key, None)
        if raa is None:
            return default
        return json.loads(raa) if isinstance(raa, str) else raa
    except Exception:  # state må aldrig kunne vælte en søgning
        return default


def _skriv(key: str, vaerdi: Any) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value

        set_runtime_state_value(key, json.dumps(vaerdi))
    except Exception as exc:  # tavs regnskabsfejl er bedre end en død søgning
        logger.warning("search_quota: kunne ikke gemme %s: %s", key, exc)


def _maaned() -> str:
    """Kvoterne nulstilles ved månedsskifte, ikke ved midnat.

    SerpAPI fornyes på `plan_renewal_date`, Tavily ved månedsskifte. At nøgle
    på dato ville nulstille tælleren 30 gange hvor kilden nulstiller én gang —
    og dermed undervurdere forbruget groft.
    """
    return datetime.now(UTC).strftime("%Y-%m")


def _periode_noegle(navn: str) -> str:
    """Nøglen tælleren gemmes under — og dermed hvornår den nulstilles.

    Exa er IP-limitet pr. DØGN (målt 19/10-2026), så en månedsnøgle ville
    undervurdere forbruget med op til 30× og aldrig fyre varselet. De to andre
    er kreditlofter pr. måned.
    """
    if PERIODER.get(str(navn).strip().lower()) == "dag":
        return datetime.now(UTC).strftime("%Y-%m-%d")
    return _maaned()


def _api_key(navn: str) -> str:
    try:
        from core.tools.simple_tools_web import _read_api_key

        return _read_api_key(f"{navn}_api_key")
    except Exception:  # uden nøgle findes ingen live-kvote at læse
        return ""


# ------------------------------------------------------- live-kilder


def _http_json(url: str, *, headers: dict[str, str] | None = None,
               timeout: float = 12.0) -> dict[str, Any] | None:
    # User-Agent er ikke valgfri: Cloudflare afviser `Python-urllib` med
    # error 1010 (målt 18/10-2026 på mcp.exa.ai, samme fælde som ntfy).
    h = {"User-Agent": "Jarvis/1.0 (agent)", "Accept": "application/json"}
    h.update(headers or {})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h),
                                    timeout=timeout) as svar:
            return json.loads(svar.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError,
            ValueError) as exc:  # netværk/parse → «ukendt», ikke «tom»
        logger.warning("search_quota: %s svarede ikke: %s", url.split("?")[0], exc)
        return None


def _tavily_live() -> dict[str, Any] | None:
    """Tavilys eget regnskab: `/usage` → plan_usage / plan_limit."""
    noegle = _api_key("tavily")
    if not noegle:
        return None
    data = _http_json("https://api.tavily.com/usage",
                      headers={"Authorization": f"Bearer {noegle}"})
    if not data:
        return None
    konto = data.get("account") or {}
    brugt, graense = konto.get("plan_usage"), konto.get("plan_limit")
    if graense is None:
        return None
    return {"brugt": int(brugt or 0), "graense": int(graense),
            "plan": konto.get("current_plan") or ""}


def _serpapi_live() -> dict[str, Any] | None:
    """SerpAPIs eget regnskab: `/account` → this_month_usage / searches_per_month."""
    from urllib import parse as urllib_parse

    noegle = _api_key("serpapi")
    if not noegle:
        return None
    url = "https://serpapi.com/account?" + urllib_parse.urlencode({"api_key": noegle})
    data = _http_json(url)
    if not data:
        return None
    graense = data.get("searches_per_month")
    if graense is None:
        return None
    return {"brugt": int(data.get("this_month_usage") or 0),
            "graense": int(graense), "plan": str(data.get("plan_name") or "")}


def _exa_lokal() -> dict[str, Any] | None:
    """Exa tælles lokalt: der findes intet kvote-endpoint uden nøgle.

    Tælleren er et minimum, ikke sandheden — kald fra scripts og fra processer
    før en genstart tælles ikke med. Det er netop derfor de to andre læses live.

    Grænsen er den MÅLTE hvis loftet er ramt mindst én gang (se `noter_429`),
    ellers den dokumenterede default fra kilden. Virkeligheden slår kilden.
    """
    brugt = _laes(f"{_STATE_PREFIX}:lokal:{_periode_noegle('exa')}:exa", 0)
    maalt = _laes(f"{_STATE_PREFIX}:maalt_graense:exa")
    graense = int(maalt) if maalt else GRAENSER.get("exa")
    if graense is None:
        return None
    return {"brugt": int(brugt or 0), "graense": int(graense),
            "plan": "gratis (målt loft)" if maalt else "gratis (antaget loft)"}


_LIVE = {"tavily": _tavily_live, "serpapi": _serpapi_live, "exa": _exa_lokal}


# --------------------------------------------------------------- status


def noter_kald(provider: str, antal: int = 1) -> None:
    """Tæl et kald op lokalt. Supplement til live-kilden, ikke en erstatning."""
    if antal <= 0:
        return
    navn = str(provider or "").strip().lower()
    if navn not in PROVIDERS:
        return
    noegle = f"{_STATE_PREFIX}:lokal:{_periode_noegle(navn)}:{navn}"
    _skriv(noegle, int(_laes(noegle, 0) or 0) + antal)


#: Et 429 med kortere Retry-After end dette er QPS-vinduet, ikke et forbrugsloft.
QPS_RETRY_TAERSKEL = 60


def noter_429(provider: str, retry_after: float | None = None) -> bool:
    """Registrér et 429 og skel QPS-loft fra forbrugsloft. True = forbrugsloft.

    MÅLT 19/10-2026: `mcp.exa.ai` svarer `Retry-After: 1` når QPS-loftet
    rammes. Det nulstilles straks og siger intet om forbruget. Den daglige
    kvote nulstilles timer senere, så et LANGT `Retry-After` er beviset på at
    forbrugsloftet blev ramt.

    Netop derfor kan 429'en kalibrere grænsen: når loftet rammes, ER forbruget
    på det tidspunkt grænsen. Vi gemmer det målte tal som et MINIMUM — tælleren
    kan have misset kald fra scripts — og lader det vinde over den dokumenterede
    default. Hellere skifte for tidligt end løbe tør.
    """
    navn = str(provider or "").strip().lower()
    if navn not in PROVIDERS:
        return False
    if retry_after is None or retry_after <= QPS_RETRY_TAERSKEL:
        return False  # QPS-vindue, ikke et forbrugsloft

    brugt = int(_laes(f"{_STATE_PREFIX}:lokal:{_periode_noegle(navn)}:{navn}", 0) or 0)
    if brugt <= 0:
        return True
    forrige = _laes(f"{_STATE_PREFIX}:maalt_graense:{navn}")
    if forrige and int(forrige) <= brugt:
        return True  # allerede kalibreret til et lige så lavt tal
    _skriv(f"{_STATE_PREFIX}:maalt_graense:{navn}", brugt)
    logger.warning(
        "search_quota: %s ramte forbrugsloftet ved %s kald — grænsen kalibreret "
        "til det målte tal (var %s)", navn, brugt, GRAENSER.get(navn))
    return True


def kvote_status(provider: str, *, brug_cache: bool = True) -> dict[str, Any]:
    """Status for én provider.

    Felter: `provider`, `brugt`, `graense`, `tilbage`, `andel`, `kilde`
    (`live`/`lokal`/`ukendt`), `over_loft`, `plan`.

    Ukendt kvote → `over_loft=False` (fail-open). En søgning må ikke blokeres
    fordi et regnskab ikke kunne læses.
    """
    navn = str(provider or "").strip().lower()
    if navn not in PROVIDERS:
        return {"provider": navn, "brugt": None, "graense": None, "tilbage": None,
                "andel": None, "kilde": "ukendt", "over_loft": False, "plan": ""}

    cache_noegle = f"{_STATE_PREFIX}:cache:{navn}"
    if brug_cache:
        cachet = _laes(cache_noegle)
        if isinstance(cachet, dict):
            alder = datetime.now(UTC).timestamp() - float(cachet.get("at") or 0)
            if 0 <= alder < LIVE_TTL_SEKUNDER and isinstance(cachet.get("data"), dict):
                return _form(cachet["data"], navn, kilde=cachet.get("kilde") or "live")

    data = _LIVE[navn]() if navn in _LIVE else None
    if data is None:
        return {"provider": navn, "brugt": None, "graense": None, "tilbage": None,
                "andel": None, "kilde": "ukendt", "over_loft": False, "plan": ""}

    kilde = "lokal" if navn == "exa" else "live"
    if brug_cache:
        _skriv(cache_noegle, {"at": datetime.now(UTC).timestamp(),
                              "data": data, "kilde": kilde})
    return _form(data, navn, kilde=kilde)


def _form(data: dict[str, Any], navn: str, *, kilde: str) -> dict[str, Any]:
    brugt = int(data.get("brugt") or 0)
    graense = int(data.get("graense") or 0)
    tilbage = max(0, graense - brugt)
    andel = (brugt / graense) if graense else None
    return {
        "provider": navn, "brugt": brugt, "graense": graense, "tilbage": tilbage,
        "andel": andel, "kilde": kilde,
        "over_loft": bool(andel is not None and andel >= LOFT_FRAKTION),
        "plan": str(data.get("plan") or ""),
    }


def alle_status(*, brug_cache: bool = True) -> dict[str, dict[str, Any]]:
    return {p: kvote_status(p, brug_cache=brug_cache) for p in PROVIDERS}


# ------------------------------------------------------------- varsling


def _varsel_koel(navn: str) -> bool:
    """True hvis der IKKE er varslet for nylig — ellers sæt ny tidsstempel."""
    noegle = f"{_STATE_PREFIX}:varslet:{navn}"
    sidst = float(_laes(noegle, 0) or 0)
    nu = datetime.now(UTC).timestamp()
    if sidst and (nu - sidst) < VARSEL_COOLDOWN_SEKUNDER:
        return False
    _skriv(noegle, nu)
    return True


def varsle_hvis_over_loft(status: dict[str, Any]) -> bool:
    """Send ét varsel når en provider nærmer sig sit loft. True = sendt.

    Varselet går til notifikations-fladen (klokken/feedet) OG til telefonen —
    en tavs loglinje er præcis den beskyttelse der fejlede med CI i to døgn
    (målt 3/10-2026): beskyttelsen var en vane, ikke en alarm.
    """
    if not status.get("over_loft"):
        return False
    navn = str(status.get("provider") or "")
    if not navn or not _varsel_koel(navn):
        return False

    brugt, graense = status.get("brugt"), status.get("graense")
    tilbage = status.get("tilbage")
    tekst = (f"{navn}: {brugt}/{graense} brugt ({int((status.get('andel') or 0) * 100)} %), "
             f"{tilbage} tilbage. Kilden: {status.get('kilde')}.")

    try:
        from core.services.notifikationer import opret

        opret(user_id="owner", slags="search_quota",
              kilde=f"search_quota:{navn}",
              titel=f"Søgekvote nær loft: {navn}", tekst=tekst)
    except Exception as exc:  # notifikations-laget må ikke vælte søgningen
        logger.warning("search_quota: kunne ikke oprette notifikation: %s", exc)

    try:
        from core.services.ntfy_gateway import send_notification

        send_notification(tekst, title="Jarvis: søgekvote", priority="default")
    except Exception as exc:  # telefonen er en ekstra kanal, ikke en forudsætning
        logger.warning("search_quota: ntfy fejlede: %s", exc)
    return True


# ---------------------------------------------------------- prioritering


def bedste_provider(foretrukken: str = "exa", *,
                    brug_cache: bool = True) -> tuple[str | None, dict[str, dict[str, Any]]]:
    """Den foretrukne hvis den har plads — ellers den næstbedste med plads.

    Rækkefølgen er kvalitetsrækkefølgen (målt top-1): exa → serpapi → tavily.
    Returnerer `(navn, alle_status)`. `None` betyder at alle er over loft; så
    skal kæden alligevel forsøge, for «over loft» er ikke «nede».
    """
    status = alle_status(brug_cache=brug_cache)
    rækkefølge = [foretrukken] + [p for p in PROVIDERS if p != foretrukken]
    for navn in rækkefølge:
        s = status.get(navn) or {}
        if not s.get("over_loft"):
            return navn, status
    return None, status


def rapport() -> str:
    """Menneskelæsbar linje pr. provider — til drift og til et værktøjssvar."""
    linjer = []
    for navn, s in alle_status(brug_cache=False).items():
        if s.get("graense"):
            linjer.append(
                f"{navn}: {s['brugt']}/{s['graense']} "
                f"({int((s.get('andel') or 0) * 100)} %) — {s['tilbage']} tilbage "
                f"[{s['kilde']}]"
            )
        else:
            linjer.append(f"{navn}: kvote ukendt (fail-open)")
    return " · ".join(linjer)
