"""Vagt: kun Bjørns egen lane må ramme den betalte DeepSeek-API (2026-09-05).

Bjørns regel fra 16. juli står i `settings.py`: den betalte deepseek.com-API er
KUN til visible lane; baggrund kører på ollama. Men lane-opslaget sker ikke i
settings — det sker i `~/.jarvis-v2/config/provider_router.json`. Dér pegede
`inner_enrichment` stadig på `https://api.deepseek.com/v1`, og
`daemon_llm.quality_daemon_llm_call` resolver netop den lane. Resultat: 281
betalte kald på syv dage til internt arbejde. Reglen var brudt i omkring syv
uger uden at nogen opdagede det, fordi de to steder sagde hver sit.

Denne vagt lukker hullet ved at spørge det sted der faktisk bestemmer —
`resolve_provider_router_target` — og råbe op når en lane uden for
`_ALLOWED_PAID_LANES` peger på en betalt vært. Den RETTER intet: et lane-valg er
en driftsbeslutning, ikke noget en vagt skal tage. Den gør bruddet synligt i
Centralen og i loggen, så det ikke kan ligge uset i syv uger igen.

## Hvorfor den også måler hovedbogen (14/9-2026)

Formen ovenfor svarede «kun hans egne ture koster penge» **mens fire lanes
brugte penge**: `vision`, `agent`, `inner_enrichment` og `compat_oneshot`, plus
cache-varmerens 11.429 kald. To grunde, og den anden er den vigtige:

1. Den spørger en hardkodet liste på seks lane-navne. `agent`, `vision`,
   `compat_oneshot`, `agentic_round` og `primary_cache_warmer` stod ikke i den.
   Lane-navne bliver ved med at komme til; en liste kan ikke følge med.

2. Den læser **konfigurationen**, ikke hovedbogen. En vej der går uden om
   routeren — fx `execute_openai_compat_heartbeat_prompt`, der hardkoder
   api.deepseek.com — er strukturelt usynlig for den. Konfigurationen er en
   påstand om hvad der VIL ske; hovedbogen er hvad der SKETE.

Reglen handler ikke om navne. Den handler om HVEM kaldet tilhører, og det kan
hver eneste række svare på: **et betalt kald skal bære et `visible-` run-id.**
Den invariant kan ikke forældes af et nyt lane-navn.

De to spørgsmål besvares begge, og de er ikke det samme. `audit_paid_lanes`
siger hvad routeren lover; `audit_paid_spend` siger hvad der blev betalt.
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Lanes der MÅ koste penge: Bjørns egne ture.
_ALLOWED_PAID_LANES = frozenset({"visible", "primary"})
# Værter vi betaler for pr. token. Ollama-cloud og de gratis lanes er ikke her.
_PAID_HOSTS = frozenset({"api.deepseek.com"})
# Lanes vi overhovedet spørger til (jf. provider_router._normalize_lane).
_LANES = ("visible", "cheap", "coding", "premium", "local", "inner_enrichment")


def _host(url: str) -> str:
    try:
        return (urlparse(str(url or "")).hostname or "").lower()
    except Exception:
        return ""


def is_paid(base_url: str) -> bool:
    return _host(base_url) in _PAID_HOSTS


def audit_paid_lanes() -> list[dict[str, Any]]:
    """Hvilke lanes peger på en betalt vært uden at måtte?

    Returnerer én post pr. brud. Tom liste = reglen holder. Self-safe: en lane
    der ikke kan resolves springes over frem for at vælte kaldet.
    """
    from core.runtime.provider_router import resolve_provider_router_target

    leaks: list[dict[str, Any]] = []
    for lane in _LANES:
        if lane in _ALLOWED_PAID_LANES:
            continue
        try:
            target = resolve_provider_router_target(lane=lane) or {}
        except Exception as exc:
            logger.debug("paid_lane_guard: kunne ikke resolve %s: %s", lane, exc)
            continue
        base_url = str(target.get("base_url") or "")
        if is_paid(base_url):
            leaks.append({
                "lane": lane,
                "provider": str(target.get("provider") or ""),
                "model": str(target.get("model") or ""),
                "host": _host(base_url),
            })
    return leaks


#: Udbyder-etiketter der koster penge pr. token. `primary_cache_warmer` er
#: DeepSeek under et andet navn — den rammer samme betalte API 11.429 gange og
#: slap forbi enhver kontrol der troede paa udbyder-navnet.
_PAID_PROVIDERS = frozenset({"deepseek", "primary_cache_warmer"})

#: Hvor langt tilbage hovedbogen efterses som standard.
SPEND_VINDUE_TIMER = 24


def _tilhoerer_ham(run_id: str) -> bool:
    """Er kaldet en del af en af Bjørns egne ture?

    `visible-` er formen for en synlig kørsel. `autonomous-` er det modsatte,
    og et TOMT run-id betyder at kaldet slet ikke hørte til en tur — begge er
    brud. Vi svarer aldrig ja på et ukendt præfiks: en betalt vej hvis ophav vi
    ikke kender, skal frem i lyset, ikke frikendes.
    """
    return str(run_id or "").startswith("visible-")


def audit_paid_spend(timer: int = SPEND_VINDUE_TIMER) -> list[dict[str, Any]]:
    """Hvilke BETALTE kald hørte ikke til en af hans ture?

    Læser hovedbogen — hvad der faktisk blev betalt — frem for routerens
    løfte. Samlet pr. lane med beløb, fordi «der er et brud» ikke er
    handlingsbart og «vision har brugt $0,02 over ni dage» er.

    Kaster videre ved en ulæselig hovedbog. `check_paid_spend` skelner så
    «ingen brud» fra «jeg kunne ikke se efter» — to forskellige svar der
    blandet sammen er præcis det der lod det her ligge.
    """
    from datetime import datetime, timedelta, timezone

    import core.runtime.db as db

    graense = (datetime.now(timezone.utc) - timedelta(hours=int(timer))).isoformat()
    with db.connect() as conn:
        raekker = conn.execute(
            "SELECT lane, provider, run_id, cost_usd FROM costs "
            "WHERE created_at >= ?",
            (graense,),
        ).fetchall()

    pr_lane: dict[str, dict[str, Any]] = {}
    for lane, provider, run_id, cost in raekker:
        if str(provider or "") not in _PAID_PROVIDERS:
            continue
        if _tilhoerer_ham(run_id):
            continue
        p = pr_lane.setdefault(str(lane or ""), {
            "lane": str(lane or ""), "provider": str(provider or ""),
            "run_id": str(run_id or ""), "antal": 0, "cost_usd": 0.0,
        })
        p["antal"] += 1
        p["cost_usd"] += float(cost or 0.0)
    return sorted(pr_lane.values(), key=lambda x: -x["cost_usd"])


def check_paid_spend(timer: int = SPEND_VINDUE_TIMER) -> dict[str, Any]:
    """Kør hovedbogs-revisionen: log + Central-nerve ved brud."""
    try:
        brud = audit_paid_spend(timer)
    except Exception as exc:
        logger.debug("paid_lane_guard: spend-audit fejlede: %s", exc)
        return {"checked": False, "leaks": []}
    if brud:
        logger.warning(
            "BETALT-FORBRUG UDEN FOR HANS TURE (%d timer): %s. Bjoerns regel er "
            "at kun hans egne ture maa koste penge.", timer,
            ", ".join("%s $%.4f (%d kald)" % (b["lane"], b["cost_usd"], b["antal"])
                      for b in brud),
        )
        try:
            from core.services.central_core import central
            central().observe({
                "cluster": "cost", "nerve": "paid_spend_leak",
                "count": len(brud),
                "cost_usd": round(sum(b["cost_usd"] for b in brud), 4),
                "lanes": [b["lane"] for b in brud], "detail": brud[:4],
            })
        except Exception:
            pass
    return {"checked": True, "leaks": brud}


def check_paid_lanes() -> dict[str, Any]:
    """Kør vagten: log + Central-nerve ved brud. Retter aldrig noget selv."""
    try:
        leaks = audit_paid_lanes()
    except Exception as exc:
        logger.debug("paid_lane_guard: audit fejlede: %s", exc)
        return {"checked": False, "leaks": []}
    if leaks:
        logger.warning(
            "BETALT-LANE-BRUD: %s peger paa en betalt vaert. Bjoerns regel er at "
            "kun hans egne ture (visible/primary) maa koste penge — baggrund "
            "koerer paa ollama. Ret i ~/.jarvis-v2/config/provider_router.json.",
            ", ".join("%s -> %s/%s" % (x["lane"], x["provider"], x["model"]) for x in leaks),
        )
        try:
            from core.services.central_core import central
            central().observe({
                "cluster": "cost", "nerve": "paid_lane_leak",
                "count": len(leaks), "lanes": [x["lane"] for x in leaks],
                "detail": leaks[:4],
            })
        except Exception:
            pass
    return {"checked": True, "leaks": leaks}


def build_paid_lane_guard_surface() -> dict[str, Any]:
    """Begge domme: hvad routeren LOVER, og hvad hovedbogen REGISTREREDE.

    `ok` er None naar hovedbogen ikke kunne laeses. «Ingen brud fundet» og «jeg
    kunne ikke se efter» maa ikke blive det samme svar — den gamle flade sagde
    god for fire lanes der brugte penge.
    """
    leaks = audit_paid_lanes()
    spend = check_paid_spend()
    spend_leaks = spend.get("leaks") or []
    if not spend.get("checked"):
        ok: bool | None = None
        resume = "hovedbogen kunne ikke laeses — reglen er UEFTERPROEVET"
    elif leaks or spend_leaks:
        dele = []
        if leaks:
            dele.append("%d lane(s) peger paa betalt vaert: %s" % (
                len(leaks), ", ".join(x["lane"] for x in leaks)))
        if spend_leaks:
            dele.append("betalt uden for hans ture: %s" % ", ".join(
                "%s $%.4f" % (b["lane"], b["cost_usd"]) for b in spend_leaks))
        ok = False
        resume = "; ".join(dele)
    else:
        ok = True
        resume = "kun hans egne ture koster penge"
    return {
        "active": True,
        "ok": ok,
        "leaks": leaks,
        "spend_leaks": spend_leaks,
        "spend_checked": bool(spend.get("checked")),
        "summary": resume,
    }
