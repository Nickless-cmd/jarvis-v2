"""Bogfoer en koersels omkostning — ét sted.

Udskilt fra `visible_runs` (Boy Scout-reglen: filen er paa 7.534 linjer).

## Hvorfor der er TO skrivninger

`visible_runs` skriver hovedbogen to gange i samme funktion, og det er med
vilje. Den foerste ligger lige FOER `yield _sse("done", ...)`, fordi SSE-v2
lukker legacy-generatoren saa snart den ser `done` — kode efter det yield bliver
aldrig koert. Den anden ligger til sidst og baerer den beregnede pris for de
veje der naar dertil.

## Fejlen der blev rettet 1/10-2026

Den foerste skrivning haardkodede `lane="visible"`. Den anden brugte
`lane=run.lane`. Da det er den FOERSTE der faktisk koerer paa SSE-v2-vejen, blev
AUTONOME koersler bogfoert som synlige: 1.087 raekker i hovedbogen med
`run_id LIKE 'autonomous-%'` og `lane='visible'`, mens koerslernes egen lane er
`primary` (9.145 raekker i `visible_runs`).

Ingen penge blev flyttet — den foerste skrivning saetter `cost_usd=0.0`, fordi
de rigtige beloeb staar paa runde-raekkerne (`lane='agentic_round'`). Men enhver
opgoerelse af «den synlige lane» indeholdt autonomt arbejde, og det er den slags
fejl der foerst opdages naar nogen traeffer en beslutning paa tallet.

Begge skrivninger tager nu lane fra koerslen selv. Naar de to kaldssteder deler
én funktion, kan de ikke drive fra hinanden igen.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def bogfoer_koerslens_omkostning(
    run: Any,
    *,
    input_tokens: int,
    output_tokens: int,
    cache_hit_tokens: int,
    cache_miss_tokens: int,
    cost_usd: float = 0.0,
) -> None:
    """Skriv koerslens raekke i hovedbogen.

    `lane` tages fra koerslen — aldrig et fast ord. En autonom koersel har
    `lane='primary'`, og den skal ikke staa som synlig.

    `cost_usd=0.0` er standarden med vilje: paa den normale SSE-v2-vej baerer
    runde-raekkerne beloebet, og en pris her ville taelle dobbelt. Kaldssteder
    der HAR den samlede pris, sender den med.
    """
    from core.costing.ledger import record_cost

    record_cost(
        lane=str(getattr(run, "lane", "") or "visible"),
        provider=str(getattr(run, "provider", "") or ""),
        model=str(getattr(run, "model", "") or ""),
        input_tokens=int(input_tokens or 0),
        output_tokens=int(output_tokens or 0),
        cost_usd=float(cost_usd or 0.0),
        cache_hit_tokens=int(cache_hit_tokens or 0),
        cache_miss_tokens=int(cache_miss_tokens or 0),
        run_id=str(getattr(run, "run_id", "") or ""),
    )
