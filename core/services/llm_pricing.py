"""Central LLM-pris-tabel + cost-beregner.

Kilde: api-docs.deepseek.com, efterprøvet **14. september 2026** (``VERIFICERET``).
Priser i USD pr. 1M tokens. Kun DeepSeek prises her; andre providers → 0.0.

## Hvorfor tiden er et input

Den forrige udgave af filen sagde «DeepSeek V4 har INGEN off-peak-rabat» og var
verificeret 13. juli. Begge dele holdt ikke ved en efterprøvning 14/9: der ER en
rabat, myldretid koster **præcis det dobbelte**, og hver eneste af de seks
pris-linjer var forkert. Værst stod output på flash til 0,28 mod 0,60/1,20, og
pro's cache-hit til 0,003625 mod 0,022 — en faktor 6.

En pris uden et tidspunkt kan derfor ikke være rigtig mere end halvdelen af
tiden. ``at`` er ikke pynt: det er forskellen på et tal og et gæt.

## Fejlretningen peger opad

Ukendt tidspunkt prises som **myldretid**, på linje med at et ukendt cache-split
prises som miss. Underrapportering er den fejl der er sket tre gange her i huset,
netop fordi den er tavs — en for høj regning bliver opdaget og spurgt om, en for
lav gør ikke. Sidste gang faldt saldoen $12 mod en hovedbog der sagde $2,28.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Final

_M = 1_000_000.0

#: Hvornår tabellen sidst blev holdt op mod kilden. Et tal uden en dato er en
#: påstand; den forrige stod 63 dage gammel uden at nogen kunne se det.
VERIFICERET: Final[str] = "2026-09-14"

#: Myldretid i UTC, mandag–fredag. Begge vinduer tæller — det halve af al
#: myldretid ligger i det andet.
MYLDRE_VINDUER: Final[tuple[tuple[int, int], ...]] = ((1, 4), (6, 10))

#: Ollamas myldretid i UTC, mandag–fredag. **Et ANDET vindue end DeepSeeks.**
#:
#: Ollamas egen prisliste siger ordret (målt 10/10-2026): «Off-peak pricing
#: apply outside 12:00 and 18:00 UTC on weekdays and all day on weekends.»
#: Dansk tid er det 14–20 om sommeren. Blander man de to tabeller, klassificerer
#: man 262 af vores egne kald forkert — målt på 2.973 cloud-kald siden 1/9, hvor
#: DeepSeeks vindue ville kalde 13% for myldretid mod Ollamas 22%.
OLLAMA_MYLDRE_VINDUER: Final[tuple[tuple[int, int], ...]] = ((12, 18),)

# Ollama Cloud-priser, USD pr. 1M tokens. Kilde: ollama.com/pricing, målt
# 10/10-2026. Aksen er (off_peak, peak) som i PRICING ovenfor, så konsumenterne
# kan dele kode — men bemærk at kun deepseek har en forskel; glm-modellerne har
# fast pris, og Ollama fører dem derfor som én linje.
OLLAMA_PRICING: dict[str, dict[str, tuple[float, float]]] = {
    "deepseek-v4.1-flash": {
        "input": (0.15 / _M, 0.30 / _M),
        "cached": (0.003 / _M, 0.006 / _M),
        "output": (0.60 / _M, 1.20 / _M),
    },
    "deepseek-v4-pro": {
        "input": (0.66 / _M, 1.32 / _M),
        "cached": (0.022 / _M, 0.044 / _M),
        "output": (1.98 / _M, 3.96 / _M),
    },
    "glm-5.3-flash": {
        "input": (0.15 / _M, 0.15 / _M),
        "cached": (0.03 / _M, 0.03 / _M),
        "output": (0.50 / _M, 0.50 / _M),
    },
    "glm-5.3": {
        "input": (1.40 / _M, 1.40 / _M),
        "cached": (0.26 / _M, 0.26 / _M),
        "output": (4.40 / _M, 4.40 / _M),
    },
    "glm-5.2": {
        "input": (1.40 / _M, 1.40 / _M),
        "cached": (0.26 / _M, 0.26 / _M),
        "output": (4.40 / _M, 4.40 / _M),
    },
    "gemma4": {
        "input": (0.14 / _M, 0.14 / _M),
        "cached": (0.05 / _M, 0.05 / _M),
        "output": (0.40 / _M, 0.40 / _M),
    },
    "gpt-oss:120b": {
        "input": (0.15 / _M, 0.15 / _M),
        "cached": (0.014 / _M, 0.014 / _M),
        "output": (0.60 / _M, 0.60 / _M),
    },
    "gpt-oss:20b": {
        "input": (0.07 / _M, 0.07 / _M),
        "cached": (0.035 / _M, 0.035 / _M),
        "output": (0.30 / _M, 0.30 / _M),
    },
}


def _uden_cloud_suffiks(model: str) -> str:
    """``glm-5.2:cloud`` → ``glm-5.2`` · ``gemma4:31b-cloud`` → ``gemma4:31b``.

    Ollama bruger BEGGE suffikser: ``:cloud`` på de fleste, ``-cloud`` på nogle
    (fx ``gemma4:31b-cloud``). Kun den ene blev strippet først, og vision-modellen
    faldt derfor ud af pris-tabellen — målt 10/10-2026.
    """
    tekst = str(model or "").strip().lower()
    if tekst.endswith((":cloud", "-cloud")):
        return tekst[:-6]
    return tekst


def _pris_opslag(model: str) -> dict[str, tuple[float, float]] | None:
    """Find pris-rækken for en model — prøver de former Ollama bruger.

    Rækkefølgen er fuld nøgle → uden cloud-suffiks → familienavn før kolon.
    Sidste trin fanger ``gemma4:31b-cloud``, hvor prislisten fører modellen som
    blot ``gemma4``. Uden det ville en billig model blive læst som «ukendt pris»
    og klemt af pris-loftet — den modsatte fejl af den tilsigtede.
    """
    m = str(model or "").strip().lower()
    for kandidat in (m, _uden_cloud_suffiks(m), m.split(":")[0]):
        if kandidat in OLLAMA_PRICING:
            return OLLAMA_PRICING[kandidat]
    return None


def er_ollama_myldretid(at: datetime | str | None = None) -> bool:
    """Falder tidspunktet i **Ollamas** myldretid? Ukendt tid → True (det dyre).

    ``None`` betyder «nu» (samme konvention som ``er_myldretid``); et UGYLDIGT
    tidsstempel er det der prises som myldretid. Samme fejlretning som
    ``er_myldretid``: underrapportering er den tavse fejl. Og samme skelnen:
    ``er_myldretid`` svarer på DeepSeeks spørgsmål — de to vinduer er ikke i
    nærheden af hinanden i døgnet, og et svar fra den forkerte tabel er værre
    end intet svar.
    """
    d = _som_utc(at)
    if d is None:
        return True
    d = d.astimezone(timezone.utc)
    if d.weekday() >= 5:
        return False
    return any(fra <= d.hour < til for fra, til in OLLAMA_MYLDRE_VINDUER)


def ollama_input_pris_per_m(model: str, at: datetime | str | None = None) -> float | None:
    """Input-pris i **USD pr. MILLION tokens** — eller ``None`` for ukendte.

    Enheden står i navnet med vilje: ``PRICING``/``OLLAMA_PRICING`` fører priser
    pr. token, og et loft der regner i pr. million ville læse en token-pris som
    «næsten gratis» og slippe alt igennem. Det er præcis den tavse enhedsfejl
    huset har jagtet hele dagen — så navnet bærer enheden.

    ``None``, ikke 0.0, for ukendte: et loft der læste «ukendt» som «gratis»
    ville slippe den model igennem det skulle fange.
    """
    p = _pris_opslag(model)
    if not p:
        return None
    return float(p["input"][1 if er_ollama_myldretid(at) else 0]) * _M

# (provider, model) -> akse -> (off_peak, peak) USD pr. token
PRICING: dict[tuple[str, str], dict[str, tuple[float, float]]] = {
    ("deepseek", "deepseek-v4-flash"): {
        "cache_hit": (0.003 / _M, 0.006 / _M),
        "cache_miss": (0.15 / _M, 0.30 / _M),
        "output": (0.60 / _M, 1.20 / _M),
    },
    ("deepseek", "deepseek-v4-pro"): {
        "cache_hit": (0.022 / _M, 0.044 / _M),
        "cache_miss": (0.66 / _M, 1.32 / _M),
        "output": (1.98 / _M, 3.96 / _M),
    },
}

# legacy-aliaser → v4-flash-priser.
# 2026-09-05: `deepseek-v4-flash-vision-exp` er SAMME model med syn, og prisen er
# den samme med og uden (Bjoerns research; DeepSeeks pris-side lister ikke
# varianten saerskilt). Uden denne linje ville et vision-kald prises til 0,0 og
# forsvinde ud af regnskabet — praecis den slags blindt hjoerne vi lige har
# lukket i hovedbogen. Aliaset holder prisen ét sted.
_ALIAS = {
    # 1/10-2026: `deepseek-flash` er DeepSeeks kanoniske navn i dag, og
    # `deepseek-v4-flash` serveres af den (verificeret mod API'ens eget
    # `model`-felt). Uden denne linje ville et skift af konfigurationen
    # prise hvert kald til 0,0 og lade dem forsvinde ud af regnskabet.
    "deepseek-flash": "deepseek-v4-flash",
    "deepseek-chat": "deepseek-v4-flash",
    "deepseek-reasoner": "deepseek-v4-flash",
    "deepseek-v4-flash-vision-exp": "deepseek-v4-flash",
}


def _som_utc(at: datetime | str | None) -> datetime | None:
    """Læs et tidspunkt. Returnerer None når det ikke kan afgøres.

    Et NAIVT tidsstempel læses som UTC, fordi hovedbogens `created_at` er UTC
    uden tidszone. Blev det læst som lokal tid, ville hele myldre-vinduet rykke
    og prise de forkerte kald — huset er faldet i præcis den fælde før.
    """
    if at is None:
        return datetime.now(timezone.utc)
    if isinstance(at, datetime):
        return at if at.tzinfo else at.replace(tzinfo=timezone.utc)
    tekst = str(at or "").strip()
    if not tekst:
        return None
    if tekst.endswith(("Z", "z")):
        tekst = tekst[:-1] + "+00:00"
    try:
        d = datetime.fromisoformat(tekst)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def er_myldretid(at: datetime | str | None = None) -> bool:
    """Falder tidspunktet i DeepSeeks myldretid? Ukendt tid → True (det dyre)."""
    d = _som_utc(at)
    if d is None:
        return True
    d = d.astimezone(timezone.utc)
    if d.weekday() >= 5:          # lørdag/søndag er aldrig myldretid
        return False
    return any(fra <= d.hour < til for fra, til in MYLDRE_VINDUER)


def compute_cost_usd(
    provider: str,
    model: str,
    *,
    cache_hit_tokens: int = 0,
    cache_miss_tokens: int = 0,
    output_tokens: int = 0,
    input_tokens: int = 0,
    at: datetime | str | None = None,
) -> float:
    """Beregn cost_usd fra tokens × pris. 0.0 for ukendte (provider, model).

    ``at`` er kaldets tidspunkt — udeladt betyder «nu». Ved genberegning på en
    historisk række skal rækkens eget `created_at` sendes med, ellers prises
    fortiden til nutidens myldretid.

    Cache-split ukendt (hit=miss=0) men input_tokens>0 → al input som cache_miss.
    Begge ukendt-regler peger samme vej: opad.
    """
    p = PRICING.get((provider, _ALIAS.get(model, model)))
    if not p:
        # ── OLLAMA-CLOUD (10/10-2026) ────────────────────────────────────────
        # Uden denne gren returnerede ALLE ollama-kald 0.0, og hver eneste
        # ollama-række i `costs` stod bogført til nul — målt 10/10-2026: 38M
        # tokens til glm-5.2 med cost_usd=0.0. Priserne fandtes hele tiden i
        # OLLAMA_PRICING; de blev bare aldrig spurgt. To ting gør grenen
        # nødvendig frem for at lægge ollama ind i PRICING: Ollama har sit EGET
        # myldre-vindue (12-18 UTC mod DeepSeeks 01-04/06-10), og deres akser
        # heder `input`/`cached` hvor DeepSeeks heder `cache_miss`/`cache_hit`.
        # Blander man dem, priser man den forkerte halvdel af døgnet.
        if str(provider or "").strip().lower() not in ("ollama", "ollama-a2"):
            return 0.0
        op = _pris_opslag(model)
        if not op:
            return 0.0
        i = 1 if er_ollama_myldretid(at) else 0
        hit = int(cache_hit_tokens or 0)
        miss = int(cache_miss_tokens or 0)
        if hit == 0 and miss == 0 and int(input_tokens or 0) > 0:
            miss = int(input_tokens)
        return (hit * op["cached"][i]
                + miss * op["input"][i]
                + int(output_tokens or 0) * op["output"][i])
    i = 1 if er_myldretid(at) else 0
    hit = int(cache_hit_tokens or 0)
    miss = int(cache_miss_tokens or 0)
    if hit == 0 and miss == 0 and int(input_tokens or 0) > 0:
        miss = int(input_tokens)
    return (hit * p["cache_hit"][i]
            + miss * p["cache_miss"][i]
            + int(output_tokens or 0) * p["output"][i])
