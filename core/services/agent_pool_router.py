"""Agent-pool router (spec §4 + §5.5). Tyndt lag over central_route så agenter
router gennem det Central-ejede beslutnings-punkt — kvote-bevidst allerede på
den PRIMÆRE hop (i dag er kun fallback kvote-aware).

Bærer også kvalitets-lærings-loopet (§4.4): task_scores opdateres fra rigtige
agent-outcomes så poolen lærer hvilke modeller der er gode til hvad.

## Ejerparameteren (tilføjet 7/10-2026)

Indtil i dag kunne `route_agent_task` ikke se hvem den arbejdede for. Spec'ens
§7.1 hviler på præcis det ene argument: kun Bjørns opgaver må falde tilbage til
hans DeepSeek-API, og ingen anden ejer må nå den. Uden ejeren i kaldet kan den
regel ikke håndhæves nogen steder i kæden — den kan ikke engang formuleres.

Parameteren er derfor en forudsætning, ikke en tilføjelse der kan vente: den
skal ind FØR nogen anden leverance rører modelvalg, ellers bygges
fallback-logikken oven på en funktion der ikke kan se hvem den arbejder for.

Den lukker ikke grænsen alene. Spec'en kræver at rettigheden kontrolleres igen
VED providerkaldet, ikke kun i routeren. Parameteren her er det input det
værn skal bruge — ikke værnets afløser.

## `route_source` og `fitness_ukendt`

Spec'ens §7.1 gemmer beslutningen med `route_source` (`explicit`, `agent_pool`,
`owner_deepseek_fallback`, `cheap_lane_fallback`). Denne funktion ER
agent-pool-hoppet, så den sætter `agent_pool` — og kalderen kan se om svaret kom
fra poolen eller fra et fitness-fald nedenfor.

`fitness_ukendt=True` betyder at fitness-kontrollen FEJLEDE, ikke at modellen er
godkendt. Se kommentaren i except-grenen.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def route_agent_task(*, kind: str = "default", min_tokens: int = 0,
                     quality_threshold: float = 0.0, allow_paid: bool = False,
                     exclude: frozenset[str] = frozenset(),
                     owner_user_id: str | None = None) -> dict[str, Any]:
    """Vælg (provider, model) for en agent-task via central_route. Aldrig tør.

    allow_paid=False (default): kun GRATIS modeller (Jarvis' frie valg). allow_paid=True
    ("rigtig opgave"): betalte Copilot-premium (Claude/GPT-5.6) bliver også kandidater,
    scoret på kvalitet — de vælges først (høj prioritet) fordi de er bedst.

    `owner_user_id` er den autentificerede ejer af opgaven. Den følger med ind i
    rutebeslutningen, så §7.1's ejerafhængige fallback kan afgøres på fakta i
    stedet for på et gæt om hvem der spørger."""
    from core.services import central_route

    def _rut(ekskl: frozenset[str]):
        return central_route.route(
            lane="agent",
            task={"kind": kind, "min_tokens": min_tokens,
                  "quality_threshold": quality_threshold, "allow_paid": allow_paid,
                  "owner_user_id": owner_user_id},
            exclude=ekskl,
        )

    r = _rut(exclude)
    # ── SONDENS DOM SKAL BRUGES (Bjørn 7/9-2026) ────────────────────────────
    # «Hans agenter må aldrig fejle og skal altid levere.» Den konkrete fejl:
    # explore fik nemotron-3-ultra, som kaldte `search`, fik de rigtige
    # filstier tilbage — og skrev derefter en sti der ikke findes, med
    # opdigtede klassenavne og «confidence: Høj» ovenpå. Sonden gav den 0 på
    # `follows`. Dommen fandtes; ingen læste den.
    #
    # Ukendt er TILLADT. Kun kendt-dårlig rutes udenom, så en tom
    # karakter-tabel ikke lammer agent-arbejdet før første fejning er kørt.
    try:
        from core.services.agent_model_fitness import bedste_egnede, er_blokeret
        ekskl = set(exclude)
        for _ in range(3):
            p, m = str(r.get("provider") or ""), str(r.get("model") or "")
            if not p or not m or not er_blokeret(p, m, rolle=kind):
                break
            logger.info("agent-router: %s/%s er målt uegnet til %s — vælger igen", p, m, kind)
            ekskl.add(p)
            r = _rut(frozenset(ekskl))
        else:
            # Ruteren bliver ved med at pege på noget vi har målt som uegnet.
            # Hellere en model vi VED virker end en vi ved ikke gør.
            p2, m2 = bedste_egnede(undtagen=frozenset(exclude))
            if p2 and m2:
                logger.info("agent-router: falder tilbage til målt bedste %s/%s", p2, m2)
                r = dict(r); r["provider"], r["model"] = p2, m2
                r["fitness_fallback"] = True
    except Exception as exc:
        # MÅLT 7/10-2026: grenen hed `except Exception: pass`. Den kunne ikke
        # skelne «fitness-tabellen er tom» (ukendt → tilladt, korrekt) fra
        # «fitness-kontrollen er i stykker» (bør ses). Begge endte samme sted,
        # så en måling der ALDRIG kørte så ud som et lovligt svar. Det er samme
        # fejlform som `_BILLEDVAERKTOEJ`-sagen: tavs fejl bliver til en værdi
        # man ikke kan skelne fra et gyldigt udfald.
        #
        # Værn: fejlen logges, og returværdien siger eksplicit at kontrollen
        # ikke kørte — så kaldestedet kan se forskel på «ukendt» og «godkendt».
        logger.warning("agent-router: fitness-kontrollen fejlede — ruten er "
                       "ukontrolleret, ikke godkendt: %s", exc)
        r = dict(r)
        r["fitness_ukendt"] = True

    # Denne funktion ER agent-pool-hoppet. Uden kilden på returværdien kan
    # kalderen ikke se om svaret kom fra puljen eller fra et fald nedenfor.
    r.setdefault("route_source", "agent_pool")
    return r


def _load_task_scores(provider: str, model: str) -> dict[str, float]:
    """Nuværende task_scores for (provider, model) fra runtime-state. {} ved intet."""
    try:
        from core.runtime.db_core import get_runtime_state_value
        key = f"task_scores:{provider}:{model}"
        val = get_runtime_state_value(key, None)
        return dict(val) if isinstance(val, dict) else {}
    except Exception:
        return {}


def _save_task_scores(provider: str, model: str, scores: dict[str, float]) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(f"task_scores:{provider}:{model}", scores)
    except Exception:
        pass


def update_task_score(*, provider: str, model: str, kind: str,
                      outcome_quality: float, lr: float = 0.1) -> None:
    """§4.4 kvalitets-læring: EMA-opdatér task_score for (model, kind) fra et
    outcome-signal ∈ [0,1]. Emitter task_score_updated til Central."""
    scores = _load_task_scores(provider, model)
    prev = float(scores.get(kind, 0.5))
    new = (1.0 - lr) * prev + lr * float(outcome_quality)
    scores[kind] = new
    _save_task_scores(provider, model, scores)
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "task_score_updated",
                           "provider": provider, "model": model, "kind": kind,
                           "prev": prev, "new": new})
    except Exception:
        pass
