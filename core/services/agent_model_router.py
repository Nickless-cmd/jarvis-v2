"""Modelkald for en agent: genvalidering ved kaldet og failover i kandidatkaeden (agent-contract-v1 D).

``decide_route`` fastlaegger kaeden ved dispatch. Her haandhaeves den hver gang agenten kalder en model:

* ejeren slaas op fra DB (``agent_registry.owner_user_id``) - aldrig fra et argument - og
  ``guard_call`` afviser en provider ejeren ikke maa bruge FOER noget forlader serveren;
* svigter modellen, og agenten endnu ikke har udfoert noget der kan have en effekt, proeves den NAESTE
  kandidat i kaeden (puljen foer ejerens fallback). Hvert skifte er et nyt ``attempt`` i
  ``agent_route_decisions`` OG et nyt ``agent_runs``-forsoeg i samme assignment (det svigtede faar en
  fejlpost; intet terminalt udfald - se ``db_agent_attempts``), saa skiftet er synligt og varigt;
* har agenten udfoert et vaerktoejskald (og politikken kan skrive) skjules et modelskift ikke: kaldet
  fejler i stedet for at blive gentaget paa en anden model.

En agent uden bundet ejer (``legacy_unscoped``) kører som hidtil gennem den gamle sti.
"""
from __future__ import annotations

import logging
from typing import Any

from core.runtime.db_agent_contract import LEGACY_UNSCOPED, _conn

logger = logging.getLogger(__name__)

READ_ONLY_PREFIX = "read-only"


class ModelCallFailed(RuntimeError):
    """Modelkaldet svigtede (provider, kredit, circuit breaker). Bruges af strict-stien."""

    code = "MODEL_CALL_FAILED"

    def __init__(self, detail: str, *, provider: str = "", model: str = "") -> None:
        super().__init__(detail)
        self.detail, self.provider, self.model = detail, provider, model


def bound_owner(agent_id: str) -> str:
    """Agentens autentificerede ejer, eller '' for en legacy-agent."""
    row = _conn().execute("SELECT owner_user_id FROM agent_registry WHERE agent_id=?",
                          (str(agent_id or ""),)).fetchone()
    owner = str(row["owner_user_id"] or "").strip() if row else ""
    return "" if owner in ("", LEGACY_UNSCOPED) else owner


def _chain(agent_id: str) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    from core.runtime import db_agent_route as r
    latest = r.latest_for_agent(agent_id)
    if latest is None:
        return None, []
    cands = [c for c in (latest["decision"].get("candidates") or []) if isinstance(c, dict)]
    return latest, cands


def _effectful(agent: dict[str, Any]) -> bool:
    return not str(agent.get("tool_policy") or "").startswith(READ_ONLY_PREFIX)


def _current_run(latest: dict[str, Any], run_id: str) -> str:
    """Det forsoeg der koerer nu: kalderens run (foelg failover-kaeden), ellers assignmentets seneste run."""
    from core.runtime.db_agent_attempts import live_run_id
    if run_id:
        return live_run_id(run_id)
    row = _conn().execute("SELECT run_id FROM agent_runs WHERE assignment_id=? ORDER BY attempt_no DESC "
                          "LIMIT 1", (latest["assignment_id"],)).fetchone()
    return str(row["run_id"]) if row else ""


def _switch(agent_id: str, latest: dict[str, Any], cand: dict[str, str], why: str, run_id: str = "") -> str:
    """Failover som NYT synligt runforsoeg (G, spec 7.1): det svigtede forsoeg faar sin egen fejlpost, et nyt
    ``agent_runs``-forsoeg i samme assignment aabnes, og rutebeslutningen + registret opdateres i samme
    transaktion. Intet terminalt udfald, ingen ventekontrakt og ingen vaekning beroeres. Returnerer det nye
    runs id. Er leasen mistet eller assignmentet afsluttet, rejses ``ContractError`` og INTET skifter."""
    from core.runtime.db_agent_attempts import begin_failover_attempt
    decision = dict(latest["decision"])
    decision.update({"route_source": cand["route_source"], "provider": cand["provider"],
                     "model": cand["model"], "failover_reason": why[:300]})
    started = begin_failover_attempt(from_run_id=_current_run(latest, run_id), decision=decision, reason=why)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("agent.route_failover", {
            "agent_id": agent_id, "assignment_id": latest["assignment_id"],
            "run_id": started["run_id"], "failed_run_id": started["failed_run_id"],
            "attempt_no": started["attempt_no"],
            "to": f"{cand['provider']}/{cand['model']}", "route_source": cand["route_source"],
            "reason": why[:200]})
    except Exception:
        logger.debug("route_failover-event kunne ikke publiceres", exc_info=True)
    return started["run_id"]


def call_agent_model(*, agent: dict[str, Any], tools_executed: bool = False, facade: Any = None,
                     run_id: str = "", **execute_kwargs: Any) -> dict[str, Any]:
    """Kald agentens model. ``execute_kwargs`` er argumenterne til ``execute_with_role_or_fallback``.

    ``run_id`` er kalderens nuvaerende runforsoeg; et failover afloeser det med et nyt (``live_run_id``).

    ``facade`` er den facade kalderen allerede loeser sine modelkald igennem (tests patcher den)."""
    from core.services.agent_model_policy import ModelUnavailable, ProviderDenied, guard_call

    agent_id = str(agent.get("agent_id") or "")
    owner = bound_owner(agent_id)
    facade = facade or _facade()
    if not owner:                                           # legacy_unscoped: uaendret adfaerd
        return facade.execute_with_role_or_fallback(**execute_kwargs)
    latest, cands = _chain(agent_id)
    cur_p, cur_m = str(agent.get("provider") or ""), str(agent.get("model") or "")
    if latest is not None and int(latest["attempt"]) > 1:
        # efter et failover er den gemte rute sandheden - agent-dicten kan vaere laest foer skiftet
        cur_p, cur_m = latest["provider"], latest["model"]
    pos = [i for i, c in enumerate(cands) if c["provider"] == cur_p and c["model"] == cur_m]
    if not pos:                    # modellen staar ikke i ruten: kald praecis den (guardet), aldrig en anden
        cands, pos = [{"route_source": "explicit", "provider": cur_p, "model": cur_m}], [0]
    start = pos[0]
    attempts: list[dict[str, Any]] = []
    for idx in range(start, len(cands)):
        cand = cands[idx]
        p, m = cand["provider"], cand["model"]
        try:
            guard_call(owner_user_id=owner, provider=p, model=m)
        except ProviderDenied as exc:
            attempts.append({"provider": p, "model": m, "reason": f"policy:{exc}"[:200]})
            continue
        if idx != start and latest is not None:
            why = "; ".join(f"{a['provider']}/{a['model']}: {a['reason']}" for a in attempts) or "failover"
            _switch(agent_id, latest, cand, why, run_id)
            latest, _ = _chain(agent_id)
        kw = dict(execute_kwargs, provider=p, model=m, owner_user_id=owner)
        try:
            return facade.execute_with_role_or_fallback(**kw)
        except ModelCallFailed as exc:
            attempts.append({"provider": p, "model": m, "reason": f"kald:{exc.detail}"[:200]})
            if tools_executed and _effectful(agent):
                # et muligt udfoert skrivende kald maa ikke skjules af et modelskift
                raise
            continue
    raise ModelUnavailable("alle kandidater i ruten er afproevet", attempts)


def _facade():
    import core.services.agent_runtime_base as base
    return base._facade()
