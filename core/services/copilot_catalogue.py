"""Hvad Copilot-abonnementet FAKTISK giver — spurgt, ikke antaget.

Bjoern 10/9-2026: de gratis modeller kostede en hel eftermiddag. Af alle
modeller i agent-poolen var `copilot-free/gpt-4.1` den ENESTE der kaldte
vaerktoejer (74 % mod 0 % for fem andre). Abonnementet er betalt; det skal
bruges til det arbejde der kraever at nogen faktisk laeser filen.

TO TING MAALT PAA API'ET 10/9-2026, og begge aendrer det repoet troede:

1. MULTIPLIER-MODELLEN FINDES IKKE MERE. Hver model svarer `billing: {}`, og
   API'et siger det selv:

       «Your billing plan has changed to usage-based billing and model
        multipliers no longer apply.»

   Repoets opdeling i `copilot-free` (0x) og `copilot-premium` (1x+) afspejler
   altsaa ikke virkeligheden. Omkostningsstyring maa komme fra DISCIPLIN i
   brugen — den rigtige model til opgaven — ikke fra en gratis/betalt-graense
   der ikke laengere findes.

2. KATALOGET VAR FORAELDET. `claude-sonnet-4.6` og `gemini-3.1-pro-preview`
   staar i config og findes ikke paa API'et. Det er samme forfald som
   cheap-lane havde: en statisk liste raadner hurtigere end koden omkring den.
   Derfor spoerger vi API'et og bruger kun en statisk liste som noedplan — og
   siger det naar vi goer.

RANGERINGEN ER GITHUB'S EGEN. `model_picker_category` er leverandoerens
klassifikation, ikke min fornemmelse: `lightweight` / `versatile` /
`powerful`. At opfinde en score ovenpaa ville vaere at gaette med et tal i.
"""
from __future__ import annotations

import json
import logging
import pathlib
import time
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_CRED = ("/home/bs/.jarvis-v2/auth/profiles/copilot/providers/"
         "github-copilot/credentials.json")
_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"
_MODELS_URL = "https://api.githubcopilot.com/models"
_HEADERS = {"Editor-Version": "vscode/1.90.0",
            "Copilot-Integration-Id": "vscode-chat",
            "User-Agent": "GitHubCopilotChat/0.8.0"}

#: Modellisten skifter sjaeldent. En time er rigeligt, og det holder os fra at
#: veksle en token ved hvert eneste opslag.
_CACHE_SEKUNDER = 3600.0
_cache: list[dict[str, Any]] | None = None
_cache_tid: float = 0.0

#: Noedplan hvis API'et ikke svarer. MAALT 10/9-2026 — og markeret som
#: `fra_katalog=False` i svaret, saa ingen forveksler den med en maaling.
# Kun modeller der er MAALT naabare via /chat/completions (10/9-2026).
# Foerste udgave listede gpt-5.6-terra, grok-4.6 og gpt-5.4-mini — alle tre
# svarer kun paa /responses, saa noedplanen ville have vaeret lige saa doed
# som den liste den skulle redde os fra.
_NOEDPLAN = {
    "powerful": ["claude-opus-5", "kimi-k3", "gpt-5.4"],
    "versatile": ["claude-sonnet-5", "gemini-3.8-flash"],
    "lightweight": ["claude-haiku-4.5", "gemini-3.5-flash", "gpt-5-mini"],
}

#: Hvilke kategorier en opgave skal have, bedste foerst. Rene navne frem for
#: tal: en opgave er ikke «7 vaerd», den kraever en bestemt slags model.
OPGAVE_TIER: dict[str, tuple[str, ...]] = {
    # Undersoegelse: laese, soege, sammenfatte. Kraever vaerktoejskald og
    # taalmodighed, ikke dyb ræsonnering.
    "research": ("versatile", "lightweight", "powerful"),
    # Kodearbejde: skrive og aendre. Her er den dyre model billigst, fordi et
    # forkert svar koster en runde mere.
    "kode": ("powerful", "versatile"),
    # Smaating: klassificere, formatere, korte svar.
    "let": ("lightweight", "versatile"),
}


def _api_token() -> str:
    d = json.loads(pathlib.Path(_CRED).read_text())
    req = urllib.request.Request(
        _TOKEN_URL, headers={**_HEADERS, "Authorization": f"token {d['access_token']}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return str(json.loads(r.read()).get("token") or "")


def hent_modeller(*, tving: bool = False) -> list[dict[str, Any]]:
    """Live-listen fra API'et. Tom liste hvis den ikke kan hentes.

    Tom betyder «vi kunne ikke spoerge» — ikke «der er ingen modeller».
    Kalderen skal kunne skelne, ellers bliver en netvaerksfejl til en dom.
    """
    global _cache, _cache_tid
    if not tving and _cache is not None and (time.monotonic() - _cache_tid) < _CACHE_SEKUNDER:
        return _cache
    try:
        req = urllib.request.Request(
            _MODELS_URL, headers={**_HEADERS, "Authorization": f"Bearer {_api_token()}"})
        with urllib.request.urlopen(req, timeout=25) as r:
            data = json.loads(r.read()).get("data") or []
    except Exception:
        logger.warning("kunne ikke hente Copilot-modellisten", exc_info=True)
        return []
    _cache, _cache_tid = list(data), time.monotonic()
    return _cache


#: Foer vi doemmer en model uegnet paa historik. Lavt, fordi fejlen her er
#: DETERMINISTISK (HTTP 400 «unsupported_api_for_model»), ikke flakkende —
#: modsat en timeout, hvor tre uheld intet betyder.
_MIN_FORSOEG = 3

#: HVOR LAENGE EN NAABARHEDS-MAALING GAELDER. Et doegn: en model bliver
#: sjaeldent understoettet og uunderstoettet i samme dag, og et doegn holder
#: proeverne nede paa en haandfuld.
_NAABAR_TTL = 86400.0

#: MAALT NAABARHED — {model: (naabar, tidspunkt)}. Proces-lokal med vilje:
#: den koster ét lille kald pr. model pr. doegn, og en delt tabel ville vaere
#: mere maskineri end problemet.
_naabar_cache: dict[str, tuple[bool, float]] = {}


def _naabar(model: str, *, timeout_s: float = 20.0) -> bool:
    """Svarer modellen overhovedet? ÉT lille kald, cachet et doegn.

    Foerste udgave havde en HAARDKODET liste over doede modeller. Jarvis
    fandt at jeg dermed havde erstattet to doede (`claude-fable-*`) med FIRE
    doede (`claude-opus-4.7/4.8/4.8-fast/5`) — de har alle
    `/chat/completions` OG `tool_calls` i feltet, og svarer
    `model_not_supported`. Mens `claude-sonnet-5` fra samme familie virker.

    Hans indvending mod min liste er den rigtige: «han har maalt det» er
    samme slags paastand som feltet — troevaerdig, og ikke det samme som
    efterproevet. En liste jeg vedligeholder i hovedet raadner; en maaling
    goer ikke.

    INGEN `max_tokens`. Den parameter faar `gpt-5.4` til at svare 400, og det
    kostede os en forkert dom om modellen i dag. Proeven maa ikke selv
    frembringe den fejl den leder efter.
    """
    import time as _t
    m = str(model or "").strip()
    if not m:
        return False
    naa = _naabar_cache.get(m)
    if naa is not None and (_t.monotonic() - naa[1]) < _NAABAR_TTL:
        return naa[0]
    try:
        req = urllib.request.Request(
            "https://api.githubcopilot.com/chat/completions",
            data=json.dumps({"model": m,
                             "messages": [{"role": "user", "content": "ping"}]}).encode(),
            headers={**_HEADERS, "Authorization": f"Bearer {_api_token()}",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout_s):
            ud = True
    except Exception as exc:
        # En NETVAERKSFEJL er ikke en dom over modellen. Kun et svar fra
        # tjenesten — en HTTPError — betyder «denne model kan ikke kaldes».
        if not isinstance(exc, urllib.error.HTTPError):
            logger.debug("naabarheds-proeven naaede ikke %s", m, exc_info=True)
            return True
        ud = False
        logger.info("copilot-model %s svarer ikke (%s) — udelades", m, exc.code)
    _naabar_cache[m] = (ud, _t.monotonic())
    return ud


def _maalt_uegnet() -> set[str]:
    """Modeller der ER proevet og ALDRIG svarede.

    Endpoint-feltet lover for meget: `gpt-5.4` staar med `/chat/completions`
    og svarer HTTP 400. Feltet er altsaa noedvendigt og ikke tilstraekkeligt,
    saa historikken faar det sidste ord — den er MAALT, feltet er PAASTAAET.

    Huset logger i forvejen hvert forsoeg i `cheap_provider_invocations`, saa
    dette kraever ingen nye probes. Systemet laerer af det det alligevel goer.
    """
    try:
        from core.runtime.db_core import connect
        with connect() as conn:
            raekker = conn.execute(
                "SELECT model, COUNT(*) n, SUM(status = 'completed') ok "
                "FROM cheap_provider_invocations WHERE provider LIKE 'copilot%' "
                "GROUP BY model"
            ).fetchall()
    except Exception:
        logger.warning("kunne ikke laese copilot-historikken", exc_info=True)
        return set()
    return {str(r["model"]) for r in raekker
            if int(r["n"] or 0) >= _MIN_FORSOEG and not int(r["ok"] or 0)}


def _brugbar(m: dict[str, Any], *, uegnet: set[str] | None = None) -> bool:
    """Kun modeller der kan KALDE VAERKTOEJER og er valgbare.

    Uden vaerktoejskald fabrikerer den — det er hele grunden til at vi er her.
    """
    # `type` ligger paa CAPABILITIES, ikke paa topniveau. Foerste udgave
    # laeste `m["type"]`, fik `None`, og kasserede alle 56 modeller — og
    # noedplanen skjulte det, fordi `fra_katalog=False` saa ud som «API'et
    # svarede ikke». Feltet paa det forkerte niveau, og en etiket der ikke
    # kunne skelne. Begge dele er dagens moenster.
    cap = m.get("capabilities") or {}
    # KAN DEN OVERHOVEDET NAAS? API'et siger det selv i `supported_endpoints`,
    # og kataloget hentede feltet uden at laese det. MAALT 10/9-2026: 32 af 56
    # modeller kan IKKE kaldes via `/chat/completions`, som er den protokol
    # huset taler — de svarer kun paa `/responses`.
    #
    # Konsekvensen var praecis den slags der ser ud som et modelproblem:
    # `research`-poolen var gpt-5.6-terra, grok-4.5, grok-4.6 (alle doede) og
    # gemini-3.8-flash (levende) — og `_EXPLORE_MAKS_RUNDER = 3`. Rotationen
    # koerte de tre doede og stoppede ÉT skridt foer den der virker. Hver
    # fejl faldt tilbage til `copilot-free/gpt-4.1`, hvor faldbacken er
    # TEKST-ONLY med vilje: den bedste vaerktoejskalder i huset fik opgaven
    # «laes denne fil» uden vaerktoejer, og gaettede et troevaerdigt svar.
    #
    # 100 % korrelation maalt: hver model der fejler mangler feltet, hver der
    # virker har det. (Jarvis' femte koersel.)
    _ep = m.get("supported_endpoints") or []
    _id = str(m.get("id") or "")
    if uegnet and _id in uegnet:
        return False                # proevet og aldrig svaret
    return (bool((cap.get("supports") or {}).get("tool_calls"))
            and bool(m.get("model_picker_enabled"))
            and "/chat/completions" in _ep
            and str(cap.get("type") or m.get("type") or "") == "chat")


def rangeret(opgave: str = "research", *, maks: int = 4) -> dict[str, Any]:
    """Modeller til denne opgave, bedste foerst.

    Returnerer ogsaa HVOR listen kommer fra. En noedplan der ligner en maaling
    er vaerre end ingen liste.
    """
    tiers = OPGAVE_TIER.get(str(opgave or "research"), OPGAVE_TIER["research"])
    _raa = hent_modeller()
    _uegnet = _maalt_uegnet()
    live = [m for m in _raa if _brugbar(m, uegnet=_uegnet)]
    if live:
        efter_tier: dict[str, list[dict[str, Any]]] = {}
        for m in live:
            efter_tier.setdefault(str(m.get("model_picker_category") or "-"), []).append(m)
        valgt: list[dict[str, Any]] = []
        for t in tiers:
            # Inden for en tier: stoerst kontekst foerst. Det er det eneste
            # OBJEKTIVE tal API'et giver — resten ville vaere min fornemmelse.
            for m in sorted(efter_tier.get(t, []),
                            key=lambda x: -int(((x.get("capabilities") or {})
                                                .get("limits") or {})
                                               .get("max_context_window_tokens") or 0)):
                # MAAL FOER DU LOVER. Feltet siger `/chat/completions` og
                # `tool_calls` for fire opus-modeller der svarer
                # `model_not_supported` — mens `claude-sonnet-5` fra samme
                # familie virker. Kun et RIGTIGT kald kan se forskel, og det
                # er billigt her: kun de kandidater vi er ved at love, og kun
                # ét kald pr. model pr. doegn.
                if not _naabar(str(m.get("id") or "")):
                    continue
                valgt.append({"model": str(m.get("id") or ""), "tier": t,
                              "vendor": str(m.get("vendor") or ""),
                              "kontekst": int(((m.get("capabilities") or {})
                                               .get("limits") or {})
                                              .get("max_context_window_tokens") or 0)})
                if len(valgt) >= maks:
                    break
            if len(valgt) >= maks:
                break
        return {"opgave": opgave, "fra_katalog": True, "modeller": valgt}

    noed: list[dict[str, Any]] = []
    for t in tiers:
        for navn in _NOEDPLAN.get(t, []):
            noed.append({"model": navn, "tier": t, "vendor": "", "kontekst": 0})
            if len(noed) >= maks:
                break
        if len(noed) >= maks:
            break
    # SKEL MELLEM «KUNNE IKKE SPOERGE» OG «SPURGTE, FIK INTET BRUGBART».
    # De to ser ens ud i en noedplan, og den ene er en netvaerksfejl mens den
    # anden er en fejl i vores eget filter. Foerste udgave sagde det samme om
    # begge — og skjulte praecis saadan en filterfejl i en time.
    _grund = ("API'et svarede ikke" if not _raa else
              f"API'et gav {len(_raa)} modeller, men INGEN passerede filteret "
              "— det er en fejl hos os, ikke hos dem")
    return {"opgave": opgave, "fra_katalog": False, "modeller": noed,
            "hentede": len(_raa),
            "note": f"{_grund}. Dette er en noedplan maalt 10/9-2026, ikke en "
                    "aktuel liste."}
