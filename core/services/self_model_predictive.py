"""Predictive self-model — frequencies, not aspirations.

runtime_self_model.py describes who Jarvis *says* he is. This module
describes who he *empirically* is, based on tracked signals:

- Tick quality distribution: avg, p50, p90 over last N days
- Mood baseline by dimension: mean + stdev
- Decision adherence: % kept vs revoked
- Crisis frequency: how often, what kind
- Productive idle ratio: % of ticks that recovered fatigue

These numbers turn the self-model from an aspiration ("I am curious")
into a prediction ("In 73% of recent ticks, my curiosity > 0.55").

When the empirical model diverges from the aspirational one, that IS
information — either his actual behavior has shifted, or the
aspiration was inaccurate.

Output: dict that can be rendered as prompt section. Cheap to compute
(reads state_store + recent jobs). Cached briefly per call.
"""
from __future__ import annotations

import logging
import statistics
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _tick_quality_stats(days: int = 14) -> dict[str, Any]:
    try:
        from core.services.agent_self_evaluation import tick_quality_summary
        s = tick_quality_summary(days=days)
        if s.get("count", 0) < 3:
            return {}
        return {
            "avg": s.get("avg_score"),
            "last_5_avg": s.get("last_5_avg"),
            "trend": s.get("trend"),
            "samples": s.get("count"),
        }
    except Exception:
        return {}


def _mood_baseline(days: int = 14) -> dict[str, dict[str, Any]]:
    try:
        from core.services.personality_drift import compute_baseline
        return compute_baseline(lookback_days=days) or {}
    except Exception:
        return {}


def _decision_adherence() -> dict[str, Any]:
    try:
        from core.services.agent_self_evaluation import decision_adherence_summary
        return decision_adherence_summary() or {}
    except Exception:
        return {}


def _crisis_frequency(days: int = 30) -> dict[str, Any]:
    try:
        from core.services.crisis_marker_detector import list_crisis_markers
        markers = list_crisis_markers(days_back=days, limit=200) or []
    except Exception:
        markers = []
    if not markers:
        return {"count": 0, "per_week": 0.0, "by_kind": {}}
    by_kind: dict[str, int] = {}
    for m in markers:
        k = str(m.get("kind", "unknown"))
        by_kind[k] = by_kind.get(k, 0) + 1
    weeks = max(1.0, days / 7.0)
    return {
        "count": len(markers),
        "per_week": round(len(markers) / weeks, 2),
        "by_kind": by_kind,
    }


def _productive_idle_ratio(days: int = 7) -> float | None:
    """Fraction of ticks that ran productive idle vs all ticks."""
    try:
        from core.runtime.state_store import load_json
        ticks = load_json("recent_ticks", [])
        if not isinstance(ticks, list) or not ticks:
            return None
    except Exception:
        return None
    cutoff = datetime.now(UTC) - timedelta(days=days)
    relevant: list[dict[str, Any]] = []
    for t in ticks[-500:]:
        if not isinstance(t, dict):
            continue
        ts = str(t.get("at", ""))
        try:
            if datetime.fromisoformat(ts) < cutoff:
                continue
        except ValueError:
            continue
        relevant.append(t)
    if not relevant:
        return None
    productive = sum(1 for t in relevant if t.get("productive_idle"))
    return round(productive / len(relevant), 2)


def build_predictive_self_model(days: int = 14) -> dict[str, Any]:
    """Compute the empirical self-model. Cheap; fresh each call."""
    model = {
        "window_days": days,
        "tick_quality": _tick_quality_stats(days=days),
        "mood_baseline": _mood_baseline(days=days),
        "adherence": _decision_adherence(),
        "crisis_frequency_30d": _crisis_frequency(days=30),
        "productive_idle_ratio_7d": _productive_idle_ratio(days=7),
    }
    # Lukket loop: persistér en kompakt, verificerbar prediktion afledt af
    # denne model, så score_predictions() senere kan holde den mod virkeligheden.
    # Self-safe — må aldrig vælte selve model-beregningen.
    try:
        _maybe_record_from_model(model)
    except Exception:
        pass
    return model


# Debounce: gem højst én tick_quality-prediktion pr. dette vindue (i timer), så
# hyppige kald ikke oversvømmer storen med næsten-identiske records.
_RECORD_DEBOUNCE_HOURS = 6.0


def _maybe_record_from_model(model: dict[str, Any]) -> None:
    """Uddrag en verificerbar prediktion fra modellen og persistér den.

    Pt. tick_quality.avg vs baseline-tærskel 50: forudsig at avg forbliver på
    samme side af 50 som nu, med en sandsynlighed afledt af hvor langt fra
    tærsklen vi ligger. Debounced. Self-safe.
    """
    tq = model.get("tick_quality") or {}
    if not isinstance(tq, dict):
        return
    avg = tq.get("avg")
    if avg is None:
        return
    try:
        avg_f = float(avg)
    except (TypeError, ValueError):
        return

    # Debounce mod seneste tick_quality-prediktion.
    try:
        preds = _load_predictions()
        for p in reversed(preds):
            if isinstance(p, dict) and p.get("metric") == "tick_quality.avg":
                age = _age_hours(str(p.get("made_at", "")))
                if age is not None and age < _RECORD_DEBOUNCE_HOURS:
                    return
                break
    except Exception:
        pass

    threshold = 50.0
    predicted_above = avg_f > threshold
    # Længere fra tærsklen → højere tillid (0.5..0.95).
    distance = min(abs(avg_f - threshold) / 50.0, 1.0)
    probability = round(0.5 + 0.45 * distance, 3)
    record_prediction(
        metric="tick_quality.avg",
        threshold=threshold,
        predicted_above=predicted_above,
        probability=probability,
    )


def predictive_self_model_section() -> str:
    """Render predictive self-model as a prompt awareness section."""
    m = build_predictive_self_model(days=14)
    lines: list[str] = ["Who you *empirically* are (last 14 days):"]

    tq = m.get("tick_quality") or {}
    if tq:
        lines.append(
            f"- Tick quality: {tq.get('avg')}/100 (n={tq.get('samples')}, "
            f"trend: {tq.get('trend')}, last 5: {tq.get('last_5_avg')})"
        )

    mood = m.get("mood_baseline") or {}
    if mood:
        salient: list[str] = []
        for dim, info in sorted(mood.items()):
            if not isinstance(info, dict):
                continue
            mean = info.get("mean")
            stdev = info.get("stdev")
            if mean is None:
                continue
            stable = "stable" if (stdev or 0) < 0.1 else "varying"
            try:
                salient.append(f"{dim}={float(mean):.2f} ({stable})")
            except (TypeError, ValueError):
                continue
        if salient:
            lines.append("- Mood baseline: " + ", ".join(salient[:5]))

    adh = m.get("adherence") or {}
    if isinstance(adh, dict) and adh.get("total"):
        rate = adh.get("adherence_rate")
        flag = adh.get("flag")
        bit = f"- Decision adherence: {rate} ({adh.get('total')} commitments)"
        if flag:
            bit += f" ⚠ {flag}"
        lines.append(bit)

    cf = m.get("crisis_frequency_30d") or {}
    if cf.get("count"):
        kinds = ", ".join(f"{k}:{v}" for k, v in (cf.get("by_kind") or {}).items())
        lines.append(
            f"- Crises last 30 days: {cf.get('count')} ({cf.get('per_week')}/week) — {kinds}"
        )

    pi = m.get("productive_idle_ratio_7d")
    if pi is not None:
        lines.append(f"- Productive idle ratio (7d): {pi}")

    if len(lines) == 1:
        return ""  # no signal yet
    return "\n".join(lines)


# ── Lukket forudsigelses-loop (predict → observe-actual → score → learn) ─────
#
# build_predictive_self_model FORUDSIGER allerede ("i 73% af ticks er curiosity
# > 0.55"), men scorede aldrig sig selv mod virkeligheden. Dette loop lukker
# den sløjfe additivt:
#
#   record_prediction(...)  persistér en kompakt prediktions-record
#   score_predictions()     hent FAKTISK observeret værdi → hit/miss + accuracy
#   prediction_accuracy      eksponeret i surface + absorberet som central-nerve
#
# Kilde til "faktisk værdi": samme kilde forudsigelsen brugte — pt.
# tick_quality.avg via _tick_quality_stats(). Ren statistik, ingen LLM.
# Alt self-safe: fejl → tom/neutral, kaster ALDRIG.

_PRED_STORE_KEY = "self_model_predictions"
_PRED_MAX = 200           # hold storen kompakt
_ACCURACY_N = 30          # rullende accuracy over seneste N scorede


def _load_predictions() -> list[dict[str, Any]]:
    """Læs udestående/scorede prediktions-records. Aldrig kast."""
    try:
        from core.runtime.state_store import load_json
        data = load_json(_PRED_STORE_KEY, [])
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_predictions(preds: list[dict[str, Any]]) -> None:
    """Persistér prediktions-records (kompakt, capped). Aldrig kast."""
    try:
        from core.runtime.state_store import save_json
        save_json(_PRED_STORE_KEY, list(preds)[-_PRED_MAX:])
    except Exception:
        pass


def _observe_actual(metric: str) -> float | None:
    """Hent den FAKTISKE observerede værdi for en metric — samme kilde som
    forudsigelsen brugte. Returnér None hvis ukendt/utilgængelig. Aldrig kast.
    """
    try:
        if metric == "tick_quality.avg":
            tq = _tick_quality_stats(days=14)
            v = tq.get("avg") if isinstance(tq, dict) else None
            return float(v) if v is not None else None
    except Exception:
        return None
    return None


def _absorb(cluster: str, nerve: str, value: Any, **kwargs: Any) -> None:
    """Indirektion over central_absorb.absorb — patchbar i test, self-safe."""
    try:
        from core.services.central_absorb import absorb
        absorb(cluster, nerve, value, **kwargs)
    except Exception:
        pass


def record_prediction(
    metric: str,
    threshold: float,
    predicted_above: bool,
    probability: float,
    made_at: str | None = None,
) -> None:
    """Persistér en kompakt prediktions-record. Skalar, self-safe, aldrig kast.

    metric          hvilken størrelse (fx "tick_quality.avg")
    threshold       tærskel prediktionen udtaler sig om
    predicted_above forudsiger vi at metric > threshold (True) eller < (False)
    probability     modellens sandsynlighed for udsagnet (0..1)
    made_at         ISO-tid (default: nu)
    """
    try:
        rec = {
            "metric": str(metric),
            "threshold": float(threshold),
            "predicted_above": bool(predicted_above),
            "probability": float(probability),
            "made_at": made_at or datetime.now(UTC).isoformat(),
            "scored": False,
        }
    except Exception:
        return
    try:
        preds = _load_predictions()
        preds.append(rec)
        _save_predictions(preds)
    except Exception:
        pass


def _age_hours(made_at: str) -> float | None:
    try:
        made = datetime.fromisoformat(made_at)
        if made.tzinfo is None:
            made = made.replace(tzinfo=UTC)
        return (datetime.now(UTC) - made).total_seconds() / 3600.0
    except Exception:
        return None


def score_predictions(min_age_hours: float = 24.0) -> dict[str, Any]:
    """Scor modne, uscorede prediktioner mod virkeligheden. Aldrig kast.

    For hver udestående prediktion ældre end ``min_age_hours``: hent den
    FAKTISKE observerede værdi og afgør om udsagnet holdt (hit/miss). Beregn
    en rullende ``accuracy`` (hit-rate) over de seneste N scorede.

    Returnerer {"scored": int, "accuracy": float|None, "n": int} — accuracy er
    None når intet endnu er scoret (neutral, ingen data).
    """
    try:
        preds = _load_predictions()
    except Exception:
        preds = []
    if not isinstance(preds, list):
        preds = []

    newly_scored = 0
    now_iso = datetime.now(UTC).isoformat()
    for p in preds:
        try:
            if not isinstance(p, dict) or p.get("scored"):
                continue
            age = _age_hours(str(p.get("made_at", "")))
            if age is None or age < float(min_age_hours):
                continue
            actual = _observe_actual(str(p.get("metric", "")))
            if actual is None:
                continue
            threshold = float(p.get("threshold"))
            predicted_above = bool(p.get("predicted_above"))
            actual_above = actual > threshold
            hit = (actual_above == predicted_above)
            p["scored"] = True
            p["hit"] = bool(hit)
            p["actual"] = round(float(actual), 3)
            p["scored_at"] = now_iso
            newly_scored += 1
        except Exception:
            # Skør enkelt-record forgifter aldrig hele scoringen.
            continue

    if newly_scored:
        _save_predictions(preds)

    try:
        scored = [p for p in preds if isinstance(p, dict) and p.get("scored")]
        recent = scored[-_ACCURACY_N:]
        n = len(recent)
        if n == 0:
            accuracy: float | None = None
        else:
            hits = sum(1 for p in recent if p.get("hit"))
            accuracy = round(hits / n, 3)
    except Exception:
        accuracy = None
        n = 0

    return {"scored": newly_scored, "accuracy": accuracy, "n": n}


def build_self_model_predictive_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Added during 2026-05-13 coverage push (system_cartographer dark-edge
    closure). Reports module presence so the cartographer registers it as
    observed. Specific state-readers added as the module evolves.

    2026-07-06: lukker forudsigelses-loopet (rådets #2). Lazy scoring ved
    læsning (enkleste der virker — ingen ny cadence-registrering nødvendig):
    scorer modne prediktioner, eksponerer ``prediction_accuracy`` og
    absorberer den som central-nerve, så Centralen VED hvor god den er til at
    forudsige sig selv — og lærer. Self-safe: fejl → neutral.
    """
    surface: dict[str, object] = {
        "active": True,
        "mode": "self_model_predictive",
        "summary": "Module loaded; entry points available.",
        "authority": "derived-read-only",
    }
    try:
        acc = score_predictions()
    except Exception:
        acc = {"scored": 0, "accuracy": None, "n": 0}
    surface["prediction_accuracy"] = acc

    # Absorbér som levende central-nerve — Centralen lærer sin egen præcision.
    try:
        n = int(acc.get("n") or 0)
        accuracy = acc.get("accuracy")
        _absorb(
            "self",
            "prediction_accuracy",
            {"accuracy": accuracy, "n": n},
            learn_key="self:prediction_accuracy",
            flag_if=lambda v: (v.get("n", 0) >= 5) and (v.get("accuracy") is not None) and (v["accuracy"] < 0.4),
            flag_reason="lav forudsigelses-præcision",
        )
    except Exception:
        pass

    return surface


