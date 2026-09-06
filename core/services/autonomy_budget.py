"""Dagligt budget for selvvalgte handlinger + tælling af stilheden (blok E, 4/9).

Målt 4/9-2026: initiativ-køen VIRKER — 985 initiativer på 30 dage, 203 handlet.
Men en impuls kan dø tre steder før den overhovedet når heartbeat-allowlisten:

1. `push_initiative` slettede impulsen helt ved mood-niveau 0.
2. Køen udløb efter 90 minutter, uanset prioritet.
3. `apply_conflict_resolution` omskriver fire af seks udfald til noop —
   `stay_quiet`, `defer`, `quiet_hold` og (indtil 2/9) `continue_internal`.

Stilheden er et legitimt valg. Problemet var at den var USYNLIG: der fandtes
intet tal for hvor tit han valgte den, så ingen kunne se om vægten sad rigtigt.

Dette modul gør to ting og ikke mere:

* **Tæller stilheden** pr. udfald og begrundelse, og leverer et ugentligt
  resumé i den proaktive kø: «Jeg valgte at tie 41 gange i denne uge — oftest
  fordi …». Det er materialet til at skrue på vægten med belæg.
* **Budgetterer handlingen**: højst `DEFAULT_DAILY_BUDGET` selvvalgte
  handlinger i døgnet, med synlig log. Et loft er lettere at give plads under
  end en tavs bremse — og det gør «for meget» til noget vi kan måle frem for
  frygte.
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_DAILY_BUDGET = 5
_BUDGET_KEY = "autonomy_daily_budget"
_SPENT_KEY = "autonomy_actions_spent"
_SILENCE_KEY = "autonomy_silence_counts"
_WEEKLY_KEY = "autonomy_weekly_last_run"
_WEEKLY_DAYS = 7


def _state_get(key: str, default: Any = None) -> Any:
    try:
        from core.runtime.db import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return default if v is None else v
    except Exception:
        return default


def _state_set(key: str, value: Any) -> None:
    try:
        from core.runtime.db import set_runtime_state_value
        set_runtime_state_value(key, value)
    except Exception:
        pass


def daily_budget() -> int:
    try:
        return max(0, int(_state_get(_BUDGET_KEY, DEFAULT_DAILY_BUDGET)))
    except Exception:
        return DEFAULT_DAILY_BUDGET


def set_daily_budget(value: int) -> int:
    budget = max(0, int(value))
    _state_set(_BUDGET_KEY, budget)
    return budget


def _today(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).date().isoformat()


def _spent_today(now: datetime | None = None) -> dict[str, Any]:
    raw = _state_get(_SPENT_KEY, {}) or {}
    if not isinstance(raw, dict) or str(raw.get("day") or "") != _today(now):
        return {"day": _today(now), "count": 0, "actions": []}
    return {
        "day": str(raw.get("day") or ""),
        "count": int(raw.get("count") or 0),
        "actions": list(raw.get("actions") or [])[-20:],
    }


def remaining(now: datetime | None = None) -> int:
    return max(0, daily_budget() - int(_spent_today(now).get("count") or 0))


def may_act(action: str = "", *, now: datetime | None = None) -> dict[str, Any]:
    """Er der plads i dagens budget? Fail-open: enhver fejl → ja."""
    try:
        left = remaining(now)
    except Exception:
        return {"allowed": True, "remaining": daily_budget(), "reason": "budget-unreadable"}
    if left <= 0:
        return {"allowed": False, "remaining": 0, "reason": "daily-budget-spent",
                "budget": daily_budget()}
    return {"allowed": True, "remaining": left, "budget": daily_budget()}


def note_action(action: str, *, now: datetime | None = None) -> dict[str, Any]:
    """Registrér en selvvalgt handling. Synlig log, ikke en tavs bremse."""
    now = now or datetime.now(UTC)
    state = _spent_today(now)
    state["count"] = int(state.get("count") or 0) + 1
    actions = list(state.get("actions") or [])
    actions.append({"action": str(action or "")[:60], "at": now.isoformat()})
    state["actions"] = actions[-20:]
    _state_set(_SPENT_KEY, state)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("runtime.autonomy_action_spent", {
            "action": str(action or "")[:60],
            "spent": state["count"], "budget": daily_budget(),
        })
    except Exception:
        pass
    return {"spent": state["count"], "remaining": remaining(now)}


def note_silence(*, outcome: str, reason_code: str = "") -> None:
    """Han valgte at tie. Tæl det — det er den eneste måde vægten kan vurderes."""
    key = f"{str(outcome or 'unknown')}|{str(reason_code or '')[:40]}"
    try:
        counts = dict(_state_get(_SILENCE_KEY, {}) or {})
        counts[key] = int(counts.get(key, 0)) + 1
        if len(counts) > 60:
            counts = dict(sorted(counts.items(), key=lambda kv: -int(kv[1]))[:60])
        _state_set(_SILENCE_KEY, counts)
    except Exception as exc:
        logger.debug("autonomy_budget: note_silence failed: %s", exc)


def silence_counts() -> dict[str, int]:
    try:
        return {str(k): int(v) for k, v in dict(_state_get(_SILENCE_KEY, {}) or {}).items()}
    except Exception:
        return {}


def build_weekly_summary() -> str:
    """Ugens stilhed i én linje — "" når han ikke har tiet nævneværdigt."""
    counts = silence_counts()
    total = sum(counts.values())
    if total < 5:
        return ""
    by_reason: Counter[str] = Counter()
    for key, n in counts.items():
        _outcome, _, reason = str(key).partition("|")
        by_reason[reason or _outcome] += int(n)
    top = "; ".join(f"{reason} ({n}×)" for reason, n in by_reason.most_common(3))
    spent = int(_spent_today().get("count") or 0)
    return (
        f"Denne uge valgte jeg at holde igen {total} gange. Oftest: {top}. "
        f"I dag har jeg brugt {spent} af {daily_budget()} selvvalgte handlinger. "
        "Skal jeg holde mindre igen?"
    )


def run_weekly_review(*, force: bool = False, now: datetime | None = None) -> dict[str, Any]:
    """Ugentligt: læg stilheds-resuméet i den proaktive kø og nulstil tælleren."""
    now = now or datetime.now(UTC)
    last = _state_get(_WEEKLY_KEY)
    if not force and last:
        try:
            prev = datetime.fromisoformat(str(last))
            if prev.tzinfo is None:
                prev = prev.replace(tzinfo=UTC)
            if (now - prev) < timedelta(days=_WEEKLY_DAYS):
                return {"ran": False, "reason": "cadence"}
        except Exception:
            pass
    text = build_weekly_summary()
    result: dict[str, Any] = {"ran": True, "surfaced": bool(text)}
    if text:
        try:
            from core.services.proactive_candidates import add_candidate
            result["candidate"] = add_candidate(
                source="autonomy_budget", kind="silence_review",
                text=text, priority="low",
            )
        except Exception as exc:
            logger.debug("autonomy_budget: add_candidate failed: %s", exc)
        _state_set(_SILENCE_KEY, {})
    _state_set(_WEEKLY_KEY, now.isoformat())
    return result


def build_autonomy_budget_surface() -> dict[str, Any]:
    state = _spent_today()
    return {
        "active": True,
        "budget": daily_budget(),
        "spent_today": int(state.get("count") or 0),
        "remaining": remaining(),
        "silence_total": sum(silence_counts().values()),
        "summary": (
            f"{int(state.get('count') or 0)}/{daily_budget()} selvvalgte handlinger i dag"
        ),
    }


__all__ = [
    "DEFAULT_DAILY_BUDGET", "build_autonomy_budget_surface", "build_weekly_summary",
    "daily_budget", "may_act", "note_action", "note_silence", "remaining",
    "run_weekly_review", "set_daily_budget", "silence_counts",
]
