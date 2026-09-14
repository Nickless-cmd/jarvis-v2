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
        return 0.0
    i = 1 if er_myldretid(at) else 0
    hit = int(cache_hit_tokens or 0)
    miss = int(cache_miss_tokens or 0)
    if hit == 0 and miss == 0 and int(input_tokens or 0) > 0:
        miss = int(input_tokens)
    return (hit * p["cache_hit"][i]
            + miss * p["cache_miss"][i]
            + int(output_tokens or 0) * p["output"][i])
