"""Modelvalg for agenter: premium-agentpulje -> ejerafhaengig fallback (agent-contract-v1 D, spec 7.1).

Raekkefoelgen er en regel, ikke en praeference:

1. ``explicit`` - kun hvis modellen er blandt ejerens tilladte ruter OG ikke er DeepSeek-API'et mens
   puljen har en egnet kandidat. Et haardt krav der ikke kan opfyldes fejler; en praeference falder
   tilbage til puljen.
2. ``agent_pool`` - de betalte (premium) kandidater i agent-lanen, rangeret af ``central_route``.
   Puljen er foerst udtoemt naar HVER kandidat er afvist paa dokumenteret grundlag; en fejl paa den
   oeverste model er ikke udtoemning.
3. Udtoemt pulje, derefter ejeren: Bjoern -> ``owner_deepseek_fallback`` (under budget); alle andre ->
   ``cheap_lane_fallback`` (en faktisk egnet gratis rute; en tom/degraderet bund er et afslag).
4. Ellers ``MODEL_UNAVAILABLE`` med alle aarsager.

DeepSeek-API'et (``OWNER_ONLY_PROVIDERS``) er Bjoerns penge. Det naas aldrig for en anden ejer - hverken
som eksplicit valg, rollemodel, retry, barnebarn eller default - og rettigheden kontrolleres igen VED
providerkaldet (``guard_call``), ikke kun her. Ejeren kommer fra den autentificerede opgave, aldrig fra
et toolargument.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

OWNER_ONLY_PROVIDERS: frozenset[str] = frozenset({"deepseek"})
DEFAULT_OWNER_FALLBACK = ("deepseek", "deepseek-v4-flash")
TOOL_CAPABILITY_FLOOR = 0.6          # samme gulv som agent_runtime_spawn bruger for vaerktoejsroller
DEFAULT_EST_TOKENS = 20_000


MAX_REJECTED = 40          # CT105 maalte 86 afvisninger for en almindelig bruger; raekken skal ikke vokse med dem


def _capped(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(rows) <= MAX_REJECTED:
        return rows
    return rows[:MAX_REJECTED] + [{"stage": "summary", "provider": "", "model": "",
                                   "reason": f"{len(rows) - MAX_REJECTED}_flere_afvisninger_udeladt"}]


class ModelUnavailable(RuntimeError):
    """``MODEL_UNAVAILABLE``: ingen tilladt rute. ``reasons`` er hver afvisning med aarsag."""

    code = "MODEL_UNAVAILABLE"

    def __init__(self, detail: str, reasons: list[dict[str, Any]] | None = None) -> None:
        super().__init__(detail)
        self.detail, self.reasons = detail, _capped(list(reasons or []))


class ProviderDenied(RuntimeError):
    """Ejeren maa ikke bruge denne provider (haandhaevet ved selve kaldet)."""

    code = "POLICY_DENIED"


# --------------------------------------------------------------- ejer og rettigheder


def is_platform_owner(owner_user_id: str) -> bool:
    """Bjoern? Fail-closed: kan ejeren ikke afgoeres, er svaret nej."""
    uid = str(owner_user_id or "").strip()
    if not uid:
        return False
    try:
        from core.identity.owner_resolver import owner_user_id as platform_owner
        platform = str(platform_owner() or "").strip()
    except Exception:
        logger.warning("platformens ejer kunne ikke afgoeres - behandler %r som ikke-ejer", uid,
                       exc_info=True)
        return False
    return bool(platform) and uid == platform


def provider_denied_reason(owner_user_id: str, provider: str) -> str:
    """Tom streng = tilladt, ellers aarsagen."""
    if str(provider or "").strip() in OWNER_ONLY_PROVIDERS and not is_platform_owner(owner_user_id):
        return f"{provider}_er_kun_for_platformens_ejer"
    return ""


def guard_call(*, owner_user_id: str, provider: str, model: str = "") -> None:
    """Kontrollen VED providerkaldet. Kaldes af hver modelanmodning for en bundet agent."""
    if not str(owner_user_id or "").strip():
        raise ProviderDenied("agenten har ingen autentificeret ejer")
    if (why := provider_denied_reason(owner_user_id, provider)):
        raise ProviderDenied(f"{provider}/{model}: {why}")


# --------------------------------------------------------------- kandidater


def _agent_candidates(*, role: str, min_tokens: int, exclude: frozenset[str],
                      allow_paid: bool) -> list[tuple[str, str]]:
    from core.services import central_route
    scored = central_route._scored_candidates(
        "agent", {"kind": role, "min_tokens": min_tokens, "allow_paid": allow_paid}, exclude)
    return [(p, m) for _c, _r, p, m in scored]


def _cost_class(provider: str) -> str:
    from core.services.cheap_provider_runtime_adapters import provider_cost_class
    return provider_cost_class(provider)


def _evaluate(provider: str, model: str, *, owner: str, role: str, needs_tools: bool) -> tuple[str, bool]:
    """(afvisningsaarsag eller '', fitness_ukendt)."""
    if (why := provider_denied_reason(owner, provider)):
        return why, False
    ukendt = False
    try:
        from core.services.agent_model_fitness import er_blokeret
        if er_blokeret(provider, model, rolle=role):
            return "fitness:maalt_uegnet", False
    except Exception:
        logger.warning("fitness-kontrollen fejlede for %s/%s - ukendt, ikke godkendt", provider, model,
                       exc_info=True)
        ukendt = True
    if needs_tools:
        from core.services.central_route import _model_capability
        from core.services.tool_calling_evidence import kan_kalde_vaerktoejer
        if not kan_kalde_vaerktoejer(provider, model):
            return "kapabilitet:maalt_til_ikke_at_kalde_vaerktoejer", ukendt
        if _model_capability(provider, model) < TOOL_CAPABILITY_FLOOR:
            return "kapabilitet:under_vaerktoejsgulvet", ukendt
    return "", ukendt


def _split_requested(requested: str) -> tuple[str, str]:
    """('provider','model') for ``provider/model`` eller et bart modelnavn fra kataloget; ellers ('','')."""
    from core.services.cheap_provider_runtime_adapters import CHEAP_PROVIDER_DEFAULTS
    req = str(requested or "").strip()
    if not req:
        return "", ""
    if "/" in req:
        prov, _, mod = req.partition("/")
        if prov in CHEAP_PROVIDER_DEFAULTS and mod:
            return prov, mod
    owners = [p for p, cfg in CHEAP_PROVIDER_DEFAULTS.items()
              if req in (cfg.get("static_models") or [])]
    if len(owners) == 1:
        return owners[0], req
    if "deepseek" in owners:        # DeepSeek-navne maa aldrig staa uafklaret
        return "deepseek", req
    return "", ""


def _deepseek_budget_reason() -> str:
    """Tom = indenfor budget. Fail-closed: et ukendt budget er et afslag, ikke et ja."""
    try:
        from core.costing.ledger import today_cost
        from core.services.cost_optimization_daemon import _load_budgets
        cap = float((_load_budgets() or {}).get("cost_daily_budget_usd", 0) or 0)
        if cap <= 0:
            return "budget:ukendt_dagsloft"
        spent = float(today_cost() or 0.0)
    except Exception:
        logger.warning("DeepSeek-budgettet kunne ikke laeses", exc_info=True)
        return "budget:kunne_ikke_laeses"
    return "" if spent < cap else f"budget:dagsloftet_naaet({spent:.2f}/{cap:.2f})"


def _estimate_cost(provider: str, model: str, budget_tokens: int) -> dict[str, Any]:
    tokens = int(budget_tokens or 0) or DEFAULT_EST_TOKENS
    if provider == "deepseek":
        from core.services.cheap_provider_runtime_adapters import _estimate_deepseek_cost
        usd = float(_estimate_deepseek_cost({"model": model, "prompt_tokens": int(tokens * 0.7),
                                             "completion_tokens": int(tokens * 0.3)}))
        return {"estimated_cost_usd": round(usd, 6), "cost_basis": "deepseek_prisliste", "tokens": tokens}
    if _cost_class(provider) == "paid":
        return {"estimated_cost_usd": None, "cost_basis": "premium_request_uden_dollarpris",
                "tokens": tokens}
    return {"estimated_cost_usd": 0.0, "cost_basis": "gratis", "tokens": tokens}


# --------------------------------------------------------------- beslutningen


def decide_route(*, owner_user_id: str, requested_model: str = "", hard: bool = False,
                 role: str = "researcher", needs_tools: bool = True, min_tokens: int = 0,
                 budget_tokens: int = 0, exclude: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Faststil ruten FOER agenten oprettes. Rejser ``ModelUnavailable`` hvis ingen rute er tilladt."""
    owner = str(owner_user_id or "").strip()
    if not owner:
        raise ModelUnavailable("ejeren er ukendt", [{"stage": "owner", "reason": "owner_ukendt"}])
    owner_is_platform = is_platform_owner(owner)
    rejected: list[dict[str, Any]] = []
    fitness_ukendt = False

    def reject(stage: str, p: str, m: str, why: str) -> None:
        row = {"stage": stage, "provider": p, "model": m, "reason": why}
        # Ejerens eget krav staar FOERST: det er den afgoerende aarsag, ikke de maalte uegnede modeller
        rejected.insert(0, row) if stage == "explicit" else rejected.append(row)

    pool_ok: list[tuple[str, str]] = []
    for p, m in _agent_candidates(role=role, min_tokens=min_tokens, exclude=exclude, allow_paid=True):
        if _cost_class(p) != "paid":
            continue                                   # puljen er de betalte premium-kandidater
        why, ukendt = _evaluate(p, m, owner=owner, role=role, needs_tools=needs_tools)
        fitness_ukendt = fitness_ukendt or ukendt
        if why:
            reject("agent_pool", p, m, why)
        else:
            pool_ok.append((p, m))

    chain: list[dict[str, str]] = []

    def add(source: str, p: str, m: str) -> None:
        if not any(c["provider"] == p and c["model"] == m for c in chain):
            chain.append({"route_source": source, "provider": p, "model": m})

    wants_deepseek_model = ""
    requested = str(requested_model or "").strip()
    if requested:
        rp, rm = _split_requested(requested)
        if not rp:
            reject("explicit", requested, "", "ukendt_model")
            if hard:
                raise ModelUnavailable(f"modelkravet {requested!r} kan ikke opfyldes", rejected)
        elif rp in OWNER_ONLY_PROVIDERS:
            if (why := provider_denied_reason(owner, rp)):
                reject("explicit", rp, rm, why)
                if hard:
                    raise ModelUnavailable(f"modelkravet {rp}/{rm} er ikke tilladt for ejeren", rejected)
            elif pool_ok:
                reject("explicit", rp, rm, "agentpuljen_har_en_egnet_kandidat")
                if hard:
                    raise ModelUnavailable(f"modelkravet {rp}/{rm} afvises mens puljen har en egnet "
                                           "kandidat", rejected)
            else:
                wants_deepseek_model = rm
        else:
            allowed = {(p, m) for p, m in _agent_candidates(role=role, min_tokens=min_tokens,
                                                           exclude=exclude, allow_paid=True)}
            if (rp, rm) not in allowed:
                reject("explicit", rp, rm, "ikke_i_ejerens_tilladte_ruter")
            else:
                why, ukendt = _evaluate(rp, rm, owner=owner, role=role, needs_tools=needs_tools)
                fitness_ukendt = fitness_ukendt or ukendt
                if why:
                    reject("explicit", rp, rm, why)
                else:
                    add("explicit", rp, rm)
            if hard and not chain:
                raise ModelUnavailable(f"modelkravet {rp}/{rm} kan ikke opfyldes", rejected)

    if not (hard and chain):
        for p, m in pool_ok:
            add("agent_pool", p, m)
        # Ejerens fallback staar ALTID efter puljens kandidater i kaeden: runtime proever andre
        # puljekandidater foer den, og den er det eneste valg naar puljen er udtoemt.
        if owner_is_platform:
            dp, dm = DEFAULT_OWNER_FALLBACK[0], wants_deepseek_model or DEFAULT_OWNER_FALLBACK[1]
            if (why := _deepseek_budget_reason()):
                reject("owner_deepseek_fallback", dp, dm, why)
            else:
                add("owner_deepseek_fallback", dp, dm)
        else:
            from core.services.cheap_lane_floor import floor_targets
            for p, m in _agent_candidates(role=role, min_tokens=min_tokens, exclude=exclude,
                                          allow_paid=False):
                if _cost_class(p) == "paid":
                    continue
                why, ukendt = _evaluate(p, m, owner=owner, role=role, needs_tools=needs_tools)
                fitness_ukendt = fitness_ukendt or ukendt
                if why:
                    reject("cheap_lane_fallback", p, m, why)
                else:
                    add("cheap_lane_fallback", p, m)
            if not chain:
                reject("cheap_lane_fallback", "", "",
                       "ingen_egnet_kandidat" if floor_targets() else "bunden_er_tom")
    if not chain:
        raise ModelUnavailable("ingen tilladt og egnet model", rejected)
    head = chain[0]
    return {"contract": "agent-route-v1", "route_source": head["route_source"],
            "provider": head["provider"], "model": head["model"], "candidates": chain,
            "rejected": _capped(rejected), "rejected_total": len(rejected), "owner_user_id": owner, "hard": bool(hard),
            "requested_model": requested, "role": role, "fitness_ukendt": fitness_ukendt,
            "decided_at": datetime.now(UTC).isoformat(),
            **_estimate_cost(head["provider"], head["model"], budget_tokens)}
