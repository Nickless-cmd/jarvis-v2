"""core/services/central_oneiric_sampler.py

GROUNDING-SAMPLER for DEN ONEIRISKE SLØJFE (LivingNeuron §4, opfølgning til
central_oneiric_loop.py). Lukker hullet dokumenteret dér: oneiriske hypoteser blev
PRE-REGISTRERET men aldrig GROUNDED → de døde altid ved TTL-tavshed, uanset om
drømmen faktisk hjalp.

Denne sampler læser den DURABLE no_progress_finalize-rate (mirrored til
central_timeseries fra visible_runs: numerator loop/no_progress_finalize, denominator
loop/agentic_run_total, begge med meta['day']), finder åbne oneiric_loop-hypoteser, og
for dem hvis observations-vindue har NOK data kalder record_governed_sample() — og
sammenligner AKTIV-arm mod KONTROL-arm pr. hypotesens success_criterion (drømmen skal
SLÅ kontrol, ikke bare korrelere).

Grounding: raten er en verificerbar verdens-optegnelse → source="world_consequence",
ground_ref = dagen (metric-ts-anker, ikke en selvrapporteret label).

ÆRLIGT: for tynd data → GØR INTET (hypotesen rider videre mod TTL). Ingen falsk
resolution. Egress-frit (kun skalarer via record_private). Self-safe: kaster ALDRIG.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

# Mindste antal agentic-runs på en dag før dens rate er meningsfuld (ellers støj).
_MIN_DAILY_RUNS = 5
# Mindste antal DAGE med data i HVER arm før vi tør registrere ét sample.
_MIN_DAYS_PER_ARM = 2
# Rate-forskel (aktiv vs kontrol, i forudsagt retning) der tæller som "drømmen slog".
_MIN_RATE_EDGE = 0.05
# Observations-vindue tilbage i den durable serie.
_WINDOW_DAYS = 30


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


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def _daily_counts(cluster: str, nerve: str, *, window_days: int = _WINDOW_DAYS) -> dict[str, int]:
    """Tæl durable timeseries-samples pr. dag (via meta['day']) for én nerve. READ-ONLY.
    Returnerer {day: count}. Self-safe → {} ved fejl."""
    out: dict[str, int] = {}
    try:
        from core.services import central_timeseries as cts
        samples = cts.recent(cluster, nerve, limit=100)
        cutoff = (datetime.now(UTC).date() - timedelta(days=int(window_days))).isoformat()
        for s in samples:
            day = str((getattr(s, "meta", None) or {}).get("day") or "")
            if not day or day < cutoff:
                continue
            out[day] = out.get(day, 0) + 1
    except Exception:
        return {}
    return out


def compute_arm_rates(*, window_days: int = _WINDOW_DAYS) -> dict[str, Any]:
    """Byg pr.-dag no_progress-rate (numerator/denominator) og partitionér dagene i
    aktiv- vs kontrol-arm via central_oneiric_loop.is_control_day. READ-ONLY, self-safe.

    'rate' = pooled-rate (sum numerator / sum denominator) over armens dage med nok runs.
    Tomme arme → rate=None."""
    try:
        from core.services import central_oneiric_loop as loop
    except Exception:
        loop = None

    num = _daily_counts("loop", "no_progress_finalize", window_days=window_days)
    den = _daily_counts("loop", "agentic_run_total", window_days=window_days)

    per_day: dict[str, dict[str, Any]] = {}
    active_num = active_den = 0
    control_num = control_den = 0
    active_days: list[str] = []
    control_days: list[str] = []

    for day, total in den.items():
        if int(total) < _MIN_DAILY_RUNS:
            continue  # for få runs → dagens rate er støj
        n = int(num.get(day, 0))
        try:
            is_control = bool(loop.is_control_day(day)) if loop is not None else False
        except Exception:
            is_control = False
        per_day[day] = {"num": n, "den": int(total),
                        "rate": round(n / int(total), 4), "control": is_control}
        if is_control:
            control_num += n
            control_den += int(total)
            control_days.append(day)
        else:
            active_num += n
            active_den += int(total)
            active_days.append(day)

    def _rate(nn: int, dd: int) -> float | None:
        return round(nn / dd, 4) if dd > 0 else None

    return {
        "active": {"rate": _rate(active_num, active_den), "days": len(active_days)},
        "control": {"rate": _rate(control_num, control_den), "days": len(control_days)},
        "per_day": per_day,
    }


def _evaluate_hypothesis(prov: dict[str, Any], arms: dict[str, Any]) -> dict[str, Any] | None:
    """Afgør supports/falsifies for ÉN oneiric-hypotese: aktiv-arm-raten skal bevæge sig i
    predicted_direction MERE end kontrol-arm-raten (mindst _MIN_RATE_EDGE). None ved for tynd
    data (→ ingen sample, hypotesen rider mod TTL). Self-safe."""
    try:
        direction = str(prov.get("predicted_direction") or "")  # 'down' | 'up'
        if direction not in ("down", "up"):
            return None
        active = arms.get("active") or {}
        control = arms.get("control") or {}
        a_rate, c_rate = active.get("rate"), control.get("rate")
        if a_rate is None or c_rate is None:
            return None  # begge arme kræves for en ægte sammenligning
        if int(active.get("days") or 0) < _MIN_DAYS_PER_ARM or \
           int(control.get("days") or 0) < _MIN_DAYS_PER_ARM:
            return None  # for tynd — ingen falsk resolution
        # 'down' → aktiv-rate LAVERE end kontrol; 'up' → HØJERE.
        if direction == "down":
            edge = float(c_rate) - float(a_rate)
        else:
            edge = float(a_rate) - float(c_rate)
        supports = edge >= _MIN_RATE_EDGE
        falsifies = edge <= -_MIN_RATE_EDGE
        return {"supports": bool(supports), "falsifies": bool(falsifies),
                "edge": round(edge, 4), "active_rate": float(a_rate),
                "control_rate": float(c_rate)}
    except Exception:
        return None


def run_oneiric_sampler_tick(*, trigger: str = "cadence", **_: Any) -> dict[str, object]:
    """Cadence: ground åbne oneiric_loop-hypoteser mod den durable no_progress-rate
    (aktiv vs kontrol). Ét grounded sample pr. hypotese der har nok data. OBSERVE-ONLY.
    Self-safe: kaster ALDRIG."""
    try:
        from core.services import central_hypothesis_generator as gen
        gen.ensure_schema()
    except Exception:
        return {"status": "error", "error": "generator utilgængelig"}

    arms = compute_arm_rates()

    try:
        from core.runtime.db import connect
        with connect() as c:
            rows = c.execute(
                "SELECT hyp_id, provenance_json FROM central_hypotheses "
                "WHERE status='active' AND source='oneiric_loop'").fetchall()
        active = [(str(r["hyp_id"]), json.loads(r["provenance_json"] or "{}")) for r in rows]
    except Exception:
        active = []

    grounded, supported, contradicted, skipped = 0, 0, 0, 0
    for hyp_id, prov in active:
        res = _evaluate_hypothesis(prov, arms)
        if res is None:
            skipped += 1
            continue
        try:
            gen.record_governed_sample(
                hyp_id, supports=bool(res["supports"]), falsifies=bool(res["falsifies"]),
                source="world_consequence", ground_ref=_today(), triggered_by="world")
        except Exception:
            skipped += 1
            continue
        grounded += 1
        if res["supports"]:
            supported += 1
        elif res["falsifies"]:
            contradicted += 1

    try:
        from core.services.central_private_observe import record_private
        record_private("dreams", "oneiric_sampling", value=float(grounded),
                       meta={"grounded": grounded, "supported": supported,
                             "contradicted": contradicted, "skipped": skipped,
                             "active_rate": (arms.get("active") or {}).get("rate"),
                             "control_rate": (arms.get("control") or {}).get("rate")})
    except Exception:
        pass

    return {"status": "ok", "grounded": grounded, "supported": supported,
            "contradicted": contradicted, "skipped": skipped,
            "active_rate": (arms.get("active") or {}).get("rate"),
            "control_rate": (arms.get("control") or {}).get("rate")}


def register_oneiric_sampler_producer() -> None:
    """Cadence-producer ~2×/dag (dagen er den eksperimentelle enhed; hyppigere tik harmløst
    — §8-evaluate er idempotent nok). Lav prioritet. Egress-frit."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_oneiric_sampler",
        cooldown_minutes=720,
        visible_grace_minutes=0,
        run_fn=run_oneiric_sampler_tick,
        priority=8,
    ))


def build_oneiric_sampler_surface() -> dict[str, object]:
    """Mission Control — read-only: aktiv- vs kontrol-arm-rate, så mennesket ser om drømmen
    faktisk slår kontrollen."""
    arms = compute_arm_rates()
    return {"active": True, "day": _today(),
            "active_rate": (arms.get("active") or {}).get("rate"),
            "control_rate": (arms.get("control") or {}).get("rate"),
            "active_days": (arms.get("active") or {}).get("days"),
            "control_days": (arms.get("control") or {}).get("days")}
