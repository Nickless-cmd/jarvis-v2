"""Modelkald for en agent: genvalidering ved kaldet og failover i kandidatkaeden (agent-contract-v1 D).

``decide_route`` fastlaegger kaeden ved dispatch. Her haandhaeves den hver gang agenten kalder en model:

* ejeren slaas op fra DB (``agent_registry.owner_user_id``) - aldrig fra et argument - og
  ``guard_call`` afviser en provider ejeren ikke maa bruge FOER noget forlader serveren;
* svigter modellen, og agenten endnu ikke har udfoert noget der kan have en effekt, proeves den NAESTE
  kandidat i kaeden (puljen foer ejerens fallback). Hvert skifte er et nyt ``attempt`` i
  ``agent_route_decisions`` og opdaterer agentens provider/model, saa skiftet er synligt og varigt;
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


def _switch(agent_id: str, latest: dict[str, Any], cand: dict[str, str], why: str) -> None:
    """Gem skiftet: nyt route-forsoeg + agentens aktuelle provider/model."""
    from core.runtime import db_agent_route as r
    decision = dict(latest["decision"])
    decision.update({"route_source": cand["route_source"], "provider": cand["provider"],
                     "model": cand["model"], "failover_reason": why[:300]})
    r.record_decision(assignment_id=latest["assignment_id"], agent_id=agent_id,
                      owner_user_id=latest["owner_user_id"], decision=decision,
                      attempt=int(latest["attempt"]) + 1)
    conn = _conn()
    conn.execute("UPDATE agent_registry SET provider=?, model=? WHERE agent_id=?",
                 (cand["provider"], cand["model"], agent_id))
    conn.commit()
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("agent.route_failover", {
            "agent_id": agent_id, "assignment_id": latest["assignment_id"],
            "to": f"{cand['provider']}/{cand['model']}", "route_source": cand["route_source"],
            "reason": why[:200]})
    except Exception:
        logger.debug("route_failover-event kunne ikke publiceres", exc_info=True)


def call_agent_model(*, agent: dict[str, Any], tools_executed: bool = False, facade: Any = None,
                     **execute_kwargs: Any) -> dict[str, Any]:
    """Kald agentens model. ``execute_kwargs`` er argumenterne til ``execute_with_role_or_fallback``.

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
            _switch(agent_id, latest, cand, attempts[-1]["reason"] if attempts else "failover")
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
