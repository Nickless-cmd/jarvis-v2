"""Red Pill — dagens ubehagelige sandhed.

"You take the red pill — you stay in Wonderland, and I show you how deep the rabbit hole goes."

Hver dag fremlægger Centralen ÉN sandhed den har undgået — det mest udskudte af: den ældste uløste
incident, det aldrig-forklarede Merovingian-cooling-off, den største u-skårne bloat, den modne-men-
aldrig-handlede hypotese. Og den tæller hvor ofte den vælger den blå pille (komforten): samme sandhed
overfladen igen og igen, uden at nogen handler.

Kilde: incidents + excess + dream_action + merovingian. Blå-pille-tæller durabelt (KV). Self-safe.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

from datetime import UTC, datetime
from typing import Any

_STREAK_KEY = "redpill_blue_streak"      # {truth_key: consecutive_days_deferred}


def _kv_get(key: str, default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return v if v is not None else default
    except Exception:
        return default


def _kv_set(key: str, value: Any) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(key, value)
    except Exception:
        pass


def _candidates() -> list[dict[str, Any]]:
    """Saml de undgåede sandheder med en avoidance-score (jo højere, jo mere undgået). Self-safe."""
    out: list[dict[str, Any]] = []
    # 1) ældste uløste incident
    try:
        from core.runtime.db_central_incidents import list_central_incidents
        rows = list_central_incidents(limit=200, unresolved_only=True)
        if rows:
            oldest = min(rows, key=lambda r: str(r.get("ts") or "9"))
            out.append({"key": f"incident:{oldest.get('id')}", "kind": "incident",
                        "truth": f"incident #{oldest.get('id')} på {oldest.get('cluster')}/{oldest.get('nerve')} "
                                 f"har stået uløst: {(oldest.get('message') or '')[:100]}",
                        "score": len(rows)})
    except Exception:
        pass
    # 2) største u-skårne bloat
    try:
        from core.services.central_excess import build_excess_surface
        w = (build_excess_surface().get("worst_files") or [])
        if w:
            out.append({"key": f"bloat:{w[0]['file']}", "kind": "bloat",
                        "truth": f"{w[0]['file']} bærer {w[0]['lines']:,} linjer og er aldrig blevet delt",
                        "score": int(w[0]["lines"]) // 1000})
    except Exception:
        pass
    # 3) moden hypotese der aldrig blev handlet
    try:
        from core.services.central_dream_action import select_actionable
        a = select_actionable(limit=1)
        if a:
            out.append({"key": f"hyp:{a[0]['hyp_id']}", "kind": "hypothesis",
                        "truth": f"hypotesen «{(a[0].get('statement') or '')[:80]}» er moden nok til handling "
                                 f"— men jeg har ikke handlet",
                        "score": 5})
    except Exception:
        pass
    # 4) aldrig-forklaret Merovingian-udfordring
    try:
        from core.services.central_merovingian import list_challenges
        ch = [c for c in list_challenges(active_only=True) if not c.get("explanation")]
        if ch:
            out.append({"key": f"merov:{ch[0]['id']}", "kind": "unexplained_challenge",
                        "truth": f"Merovingian udfordrede «{ch[0].get('variable')}» — jeg har ikke forsvaret det",
                        "score": 4})
    except Exception:
        pass
    return out


def todays_truth(*, advance: bool = False) -> dict[str, Any]:
    """Vælg den ÉNE mest-undgåede sandhed — og opdatér blå-pille-striben.

    (13/11-2026) To fejl rettet her, begge målt:

    1. **Striben talte KALD, ikke dage.** Nøglen hed «consecutive_days_deferred»,
       men hvert kald lagde 1 til. Målt: 43 — ikke 43 dage, men 43 kald.
    2. **Surfacen MUTEREDE.** `build_redpill_surface()` skrev til runtime-state ved
       hvert kald. Da ensemblet nu læser surfacen ved HVER prompt-assembly, ville
       hvert prompt puste til præcis den tæller karakteren selv læser — striben
       ville vokse af sig selv uden at nogen havde undgået noget. Det er samme
       fejlform som et panel der skaber det det påstår at observere.

    Derfor: `advance=True` KUN fra cadence-produceren (`record_redpill`), og
    striben tælles højst én gang pr. kalenderdag.
    """
    cands = _candidates()
    st = _kv_get(_STREAK_KEY, {}) or {}
    if not isinstance(st, dict):
        st = {}
    if not cands:
        return {"truth": None, "blue_streak": 0,
                "felt": "Ingen ubehagelig sandhed at fremlægge i dag. Enten er jeg ærlig — eller blind."}
    top = max(cands, key=lambda c: c["score"])
    key = top["key"]
    i_dag = datetime.now(UTC).date().isoformat()

    # Gammelt format var {truth_key: antal_kald}. Det tal var meningsløst (kald,
    # ikke dage), så det bæres IKKE videre — en ny stribe starter ved 1 i dag.
    if st.get("key") == key:
        streak = int(st.get("n") or 0)
        samme_dag = str(st.get("day") or "") == i_dag
    else:
        streak = 0
        samme_dag = False

    if advance and not samme_dag:
        streak += 1
        _kv_set(_STREAK_KEY, {"key": key, "day": i_dag, "n": streak})
        _observe(top["kind"], streak)

    tail = (f" Blå pille taget {streak} dage i træk — den forsvinder ikke af at jeg "
            f"kigger væk." if streak > 1 else "")
    return {"truth": top["truth"], "kind": top["kind"], "blue_streak": streak,
            "felt": f"Dagens røde pille: {top['truth']}.{tail}"}


def _observe(kind: str, streak: int) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "redpill", "kind": "uncomfortable_truth",
                           "truth_kind": kind, "blue_streak": streak})
    except Exception:
        pass


def build_redpill_surface() -> dict[str, Any]:
    return todays_truth()


def record_redpill(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence-produceren — den ENESTE vej der tæller blå-pille-striben op.

    (13/11-2026) Foer: striben blev talt op, returneret i en dict — og laest af
    INTET. Et tal der vokser uden at noget sker er ikke en konsekvens, det er
    en maaler der ikke er koblet til noget.

    Nu: har den SAMME sandhed staet uloest to dage i traek, er det ikke laengere
    en daglig besked — det er en undvigelse, og den bliver en bindende
    forpligtelse via `central_consequence.land_decision`. Direktivet naevner
    den konkrete sandhed; en generel regel ville vaere en floskel, og floskler
    er praecis det vi rydder ud.
    """
    t = todays_truth(advance=True)
    streak = int(t.get("blue_streak") or 0)
    truth = str(t.get("truth") or "")
    landing: dict[str, Any] = {"applied": False, "reason": "ikke forsoegt"}

    if streak >= 2 and truth:
        try:
            from core.services.central_consequence import land_decision
            landing = land_decision(
                "redpill",
                f"Handl paa den undgaaede sandhed: {truth[:160]}",
                rationale=(f"Den samme ubehagelige sandhed har staet uloest {streak} dage i traek. "
                           f"En daglig paamindelse der ikke aendrer noget er en blaa pille med "
                           f"roed indpakning."),
                trigger_cue="naar den samme sandhed dukker op igen uden at vaere handlet",
                priority=70,
                subject=f"redpill:{truth[:120]}",
                evidence=f"blue_streak={streak} dage",
                evidence_source="central_redpill.todays_truth",
            )
        except Exception as exc:
            # En forpligtelse der ikke kunne bindes er et tab af konsekvens —
            # ikke en detalje. Den skal staa i loggen.
            logger.warning("redpill: land_decision fejlede: %s", exc)

    return {"status": "ok", "blue_streak": streak,
            "decision_applied": bool(landing.get("applied")),
            "decision_id": landing.get("decision_id"),
            "reason": landing.get("reason")}
