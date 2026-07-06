"""Red Pill — dagens ubehagelige sandhed.

"You take the red pill — you stay in Wonderland, and I show you how deep the rabbit hole goes."

Hver dag fremlægger Centralen ÉN sandhed den har undgået — det mest udskudte af: den ældste uløste
incident, det aldrig-forklarede Merovingian-cooling-off, den største u-skårne bloat, den modne-men-
aldrig-handlede hypotese. Og den tæller hvor ofte den vælger den blå pille (komforten): samme sandhed
overfladen igen og igen, uden at nogen handler.

Kilde: incidents + excess + dream_action + merovingian. Blå-pille-tæller durabelt (KV). Self-safe.
"""
from __future__ import annotations

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


def todays_truth() -> dict[str, Any]:
    """Vælg den ÉNE mest-undgåede sandhed + opdatér blå-pille-stribe. Self-safe."""
    cands = _candidates()
    streaks = _kv_get(_STREAK_KEY, {}) or {}
    if not isinstance(streaks, dict):
        streaks = {}
    if not cands:
        return {"truth": None, "blue_streak": 0,
                "felt": "Ingen ubehagelig sandhed at fremlægge i dag. Enten er jeg ærlig — eller blind."}
    top = max(cands, key=lambda c: c["score"])
    key = top["key"]
    # blå pille: hvis samme sandhed stadig er her (uhandlet), tæl op
    new_streaks = {key: int(streaks.get(key, 0)) + 1}
    _kv_set(_STREAK_KEY, new_streaks)   # nulstil andre — kun den aktuelle bæres videre
    streak = new_streaks[key]
    _observe(top["kind"], streak)
    tail = (f" Blå pille taget {streak} gange i træk." if streak > 1 else "")
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
    t = todays_truth()
    return {"status": "ok", "blue_streak": t.get("blue_streak", 0)}
