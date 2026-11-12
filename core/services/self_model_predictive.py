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
    except Exception:  # kilden kan mangle under delvis opstart — uden data er der intet at måle
        return {}


def _mood_baseline(days: int = 14) -> dict[str, dict[str, Any]]:
    try:
        from core.services.personality_drift import compute_baseline
        return compute_baseline(lookback_days=days) or {}
    except Exception:  # personligheds-drift kan fejle på tynd historik; en tom baseline er ærlig
        return {}


def _decision_adherence() -> dict[str, Any]:
    try:
        from core.services.agent_self_evaluation import decision_adherence_summary
        return decision_adherence_summary() or {}
    except Exception:  # beslutnings-laget kan mangle ved kold start; adherence uden data er tom
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
    except Exception:  # krise-detektoren kan fejle; nul markeringer er et svar, ikke et crash
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
        except ValueError:  # state-storen kan være låst; uden ticks er forholdet ukendt, ikke nul
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
    # Lukket loop: persistér en kompakt, FALSIFICERBAR prediktion afledt af
    # denne model, så score_predictions() senere kan holde den mod virkeligheden
    # i et ADSKILT fremtidsvindue. Self-safe — må aldrig vælte model-beregningen.
    try:
        _maybe_record_from_model(model)
    except Exception:  # en fejlende forudsigelse må aldrig vælte model-beregningen
        pass
    try:
        model["self_prediction"] = score_predictions()
    except Exception:  # scoring er en bivirkning; modellen skal kunne læses uden den
        pass
    return model


# Debounce: gem højst én tick_quality-prediktion pr. dette vindue (i timer), så
# hyppige kald ikke oversvømmer storen med næsten-identiske records.
_RECORD_DEBOUNCE_HOURS = 6.0

# Forudsigelsens horisont. Vinduet der måles ved scoring SKAL være adskilt fra
# det vindue forudsigelsen blev udledt af — ellers er fejlen aritmetisk næsten
# udelukket. Målt 12/11-2026: den gamle sløjfe meldte accuracy 1.0 på 196
# forudsigelser med kun TO unikke faktiske værdier, fordi scoringen hentede et
# nyt 14-dages glidende gennemsnit der overlappede 13 af 14 dage med det gamle.
_PRED_HORIZON_HOURS = 168.0   # 7 dage: en helt adskilt uge
_PRED_MIN_SAMPLES = 10        # for lidt data i vinduet = ingen dom, ikke et hit


def _maybe_record_from_model(model: dict[str, Any]) -> None:
    """Uddrag en FALSIFICERBAR prediktion fra modellen og persistér den.

    Tærsklen er den værdi modellen netop målte, og udsagnet gælder en adskilt
    fremtidig uge: fortsætter niveauet, eller falder det? Det er et ægte
    væddemål der kan tabes — i modsætning til den tidligere formulering, hvor
    forudsigelsen og scoringen målte næsten samme vindue.

    Debounced. Self-safe.
    """
    tq = model.get("tick_quality") or {}
    if not isinstance(tq, dict):
        return
    avg = tq.get("avg")
    if avg is None:
        return
    try:
        avg_f = float(avg)
    except (TypeError, ValueError):  # en ikke-numerisk avg er ikke en måling
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
    except Exception:  # kan debounce ikke læses, registrér hellere end at springe over
        pass

    trend = str(tq.get("trend") or "stable")
    try:
        samples = int(tq.get("samples") or 0)
    except (TypeError, ValueError):
        samples = 0

    # Tærsklen er det målte niveau, ikke en fast konstant: spørgsmålet er om
    # niveauet holder en uge mere, og det kan besvares forkert.
    threshold = round(avg_f, 1)
    # Faldende trend vædder vi imod; ellers vædder vi med niveauet.
    predicted_above = trend != "degrading"
    # Ærlig tillid: en uge er langt ude. Trenden flytter 0.1, og tynd historik
    # trækker mod 0.5. Vi går aldrig over 0.65 — overmod er den fejl der gjorde
    # det gamle loop blindt.
    confidence = min(samples / 60.0, 1.0)
    tilt = 0.1 if trend == "improving" else (-0.1 if trend == "degrading" else 0.0)
    probability = round(0.5 + tilt * confidence, 3)

    record_prediction(
        metric="tick_quality.avg",
        threshold=threshold,
        predicted_above=predicted_above,
        probability=probability,
        baseline=avg_f,
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
            except (TypeError, ValueError):  # en ikke-numerisk baseline springes over, ikke gættet
                continue
        if salient:
            lines.append("- Mood baseline: " + ", ".join(salient[:5]))

    adh = m.get("adherence") or {}
    if isinstance(adh, dict) and adh.get("total"):
        rate = adh.get("adherence_rate")
        flag = adh.get("flag")
        # GRUNDLAGET SKAL STÅ VED TALLET (målt 28/10-2026). `rate` er snittet
        # over de beslutninger der ER reviewet — ikke over alle aktive. Før
        # stod der «59.4% (18 commitments)» hvor 18 var totalen men tallet kun
        # dækkede 4: 14 beslutninger var usynlige i målingen uden at nogen
        # kunne se det. Samme fejlklasse som et health-signal der tæller
        # «svarede» som «virker». Nu bærer linjen sit eget grundlag, så et
        # smalt tal ikke kan læses som en dom over det hele.
        _reviewed = int(adh.get("reviewed") or 0)
        _unreviewed = int(adh.get("unreviewed") or 0)
        _total = int(adh.get("total") or 0)
        if _unreviewed:
            bit = (
                f"- Decision adherence: {rate} — målt på {_reviewed} af {_total} "
                f"({_unreviewed} aldrig reviewet)"
            )
        else:
            bit = f"- Decision adherence: {rate} ({_total} commitments)"
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

    sp = m.get("self_prediction") or {}
    if isinstance(sp, dict) and (sp.get("n") or sp.get("pending")):
        acc = sp.get("accuracy")
        brier = sp.get("brier")
        if sp.get("n"):
            bit = f"- Self-prediction (7d ahead): {acc} hit-rate (n={sp.get('n')})"
            if brier is not None:
                bit += f", Brier={brier}"
        else:
            bit = "- Self-prediction (7d ahead): ingen scoret endnu"
        pend = int(sp.get("pending") or 0)
        if pend:
            bit += f" — {pend} afventer deres uge"
        lines.append(bit)

    if len(lines) == 1:
        return ""  # no signal yet
    return "\n".join(lines)

# ── Lukket forudsigelses-loop (predict → observe-actual → score → learn) ─────
#
# build_predictive_self_model FORUDSIGER allerede ("i 73% af ticks er curiosity
# > 0.55"), men scorede aldrig sig selv mod virkeligheden. Dette loop lukker
# den sløjfe:
#
#   record_prediction(...)  persistér en FALSIFICERBAR prediktions-record
#   score_predictions()     mål i det ADSKILTE fremtidsvindue → hit/miss + Brier
#   prediction_accuracy      eksponeret i surface + absorberet som central-nerve
#
# HISTORIK (målt 12/11-2026): den første version af dette loop var tautologisk.
# Forudsigelsen blev udledt af et 14-dages glidende gennemsnit, og scoringen
# hentede det SAMME vindue 24 timer senere — 13 af 14 dage overlappede. Den
# meldte accuracy 1.0 på 196 forudsigelser med kun to unikke faktiske værdier.
# Version 2 (``v``: 2) måler i ``[made_at, made_at + horizon_hours]``, som
# ligger HELT efter det vindue forudsigelsen blev udledt af, og kræver mindst
# ``_PRED_MIN_SAMPLES`` målinger i vinduet før den udtaler sig. For lidt data
# er «ingen dom», ikke et hit.
#
# Version 1-records erklæres void: deres grundlag var overlap, så deres udfald
# siger intet. De tælles ikke i accuracy og blandes aldrig ind i kalibreringen.
#
# Alt self-safe: fejl → tom/neutral, kaster ALDRIG.

_PRED_STORE_KEY = "self_model_predictions"
_PRED_MAX = 200           # hold storen kompakt
_ACCURACY_N = 30          # rullende accuracy over seneste N scorede
_PRED_VERSION = 2

# Nøglen til tick-evalueringerne ejes af agent_self_evaluation; vi læser den
# samme liste, fordi forudsigelsen og scoringen SKAL måle samme størrelse.
_TICK_EVAL_KEY = "tick_quality_evaluations"


def _parse_iso(raw: Any) -> datetime | None:
    """Parse ISO-tidsstempel fra state-storen. ``Z`` og ``+00:00`` er samme tid."""
    s = str(raw or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        d = datetime.fromisoformat(s)
    except ValueError:  # ikke et ISO-tidsstempel = ukendt tid, aldrig «nu»
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=UTC)
    return d


def _load_predictions() -> list[dict[str, Any]]:
    """Læs udestående/scorede prediktions-records. Aldrig kast."""
    try:
        from core.runtime.state_store import load_json
        data = load_json(_PRED_STORE_KEY, [])
        return data if isinstance(data, list) else []
    except Exception:  # uden store er der ingen forudsigelser — ikke en fejl der skal kaste
        return []


def _save_predictions(preds: list[dict[str, Any]]) -> None:
    """Persistér prediktions-records (kompakt, capped). Aldrig kast."""
    try:
        from core.runtime.state_store import save_json
        save_json(_PRED_STORE_KEY, list(preds)[-_PRED_MAX:])
    except Exception:  # en manglende skrivning må ikke vælte den kaldende prompt-sti
        pass


def _tick_scores_in_window(start: datetime, end: datetime) -> list[int]:
    """Tick-scores hvis ``evaluated_at`` ligger i ``[start, end]``.

    Det er denne afgrænsning der gør forudsigelsen falsificerbar: vinduet
    indeholder kun målinger fra EFTER forudsigelsen blev lavet.
    """
    try:
        from core.runtime.state_store import load_json
        evals = load_json(_TICK_EVAL_KEY, [])
    except Exception:  # uden tick-historik er vinduet tomt, og det er et gyldigt svar
        return []
    if not isinstance(evals, list):
        return []
    out: list[int] = []
    for e in evals:
        if not isinstance(e, dict):
            continue
        ts = _parse_iso(e.get("evaluated_at"))
        if ts is None or ts < start or ts > end:
            continue
        try:
            out.append(int(e.get("score") or 0))
        except (TypeError, ValueError):  # en score der ikke kan læses tælles ikke med
            continue
    return out


def _absorb(cluster: str, nerve: str, value: Any, **kwargs: Any) -> None:
    """Indirektion over central_absorb.absorb — patchbar i test, self-safe."""
    try:
        from core.services.central_absorb import absorb
        absorb(cluster, nerve, value, **kwargs)
    except Exception:  # absorption er en bivirkning; central_absorb må ikke vælte læsningen
        pass


def record_prediction(
    metric: str,
    threshold: float,
    predicted_above: bool,
    probability: float,
    made_at: str | None = None,
    *,
    horizon_hours: float = _PRED_HORIZON_HOURS,
    baseline: float | None = None,
) -> None:
    """Persistér en FALSIFICERBAR prediktions-record. Skalar, self-safe.

    metric          hvilken størrelse (fx "tick_quality.avg")
    threshold       tærskel prediktionen udtaler sig om
    predicted_above forudsiger vi at metric > threshold (True) eller < (False)
    probability     modellens sandsynlighed for udsagnet (0..1)
    made_at         ISO-tid (default: nu)
    horizon_hours   hvor langt ude forudsigelsen skal indfries. Vinduet
                    ``[made_at, made_at + horizon_hours]`` er det der måles, og
                    det skal ligge efter forudsigelsens grundlag.
    baseline        værdien forudsigelsen blev udledt af (til revision)
    """
    try:
        made = _parse_iso(made_at) if made_at else datetime.now(UTC)
        if made is None:
            made = datetime.now(UTC)
        horizon = float(horizon_hours)
        rec: dict[str, Any] = {
            "v": _PRED_VERSION,
            "metric": str(metric),
            "threshold": float(threshold),
            "predicted_above": bool(predicted_above),
            "probability": float(probability),
            "made_at": made.isoformat(),
            "horizon_hours": horizon,
            "window_start": made.isoformat(),
            "window_end": (made + timedelta(hours=horizon)).isoformat(),
            "scored": False,
        }
        if baseline is not None:
            rec["baseline"] = round(float(baseline), 2)
    except Exception:  # en record der ikke kan bygges gemmes ikke — den findes ikke
        return
    try:
        preds = _load_predictions()
        preds.append(rec)
        _save_predictions(preds)
    except Exception:  # en fejlet skrivning må ikke ramme den kaldende tur
        pass


def _age_hours(made_at: str) -> float | None:
    made = _parse_iso(made_at)
    if made is None:
        return None
    return (datetime.now(UTC) - made).total_seconds() / 3600.0


def _score_record(p: dict[str, Any], now: datetime) -> tuple[str, dict[str, Any]]:
    """Afgør én v2-records skæbne: pending | scored | insufficient | void."""
    made = _parse_iso(p.get("made_at"))
    if made is None:
        return "void", {"void_reason": "ugyldigt made_at"}
    try:
        horizon = float(p.get("horizon_hours") or _PRED_HORIZON_HOURS)
    except (TypeError, ValueError):
        horizon = _PRED_HORIZON_HOURS
    if horizon <= 0:
        return "void", {"void_reason": "ugyldig horisont"}

    end = made + timedelta(hours=horizon)
    if now < end:
        return "pending", {}

    scores = _tick_scores_in_window(made, end)
    if len(scores) < _PRED_MIN_SAMPLES:
        return "insufficient", {"n_window": len(scores)}

    try:
        threshold = float(p.get("threshold"))
        probability = float(p.get("probability"))
    except (TypeError, ValueError):  # manglende horisont falder tilbage på standardugen
        return "void", {"void_reason": "ugyldig tærskel/sandsynlighed"}

    actual = sum(scores) / len(scores)
    actual_above = actual > threshold
    hit = actual_above == bool(p.get("predicted_above"))
    # Brier måler SANDHEDEN af den udtalte sandsynlighed for «metric > threshold»
    # — uafhængigt af om retningen var rigtig. 0 = perfekt, 0.25 = en mønt.
    outcome = 1.0 if actual_above else 0.0
    brier = (probability - outcome) ** 2
    return "scored", {
        "actual": round(actual, 2),
        "hit": bool(hit),
        "brier": round(brier, 4),
        "n_window": len(scores),
        "window_days": round(horizon / 24.0, 1),
    }


# Bøtter valgt efter det interval vores sandsynligheder faktisk ligger i.
_CALIBRATION_EDGES = (0.0, 0.4, 0.5, 0.6, 1.01)


def _calibration(scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Kalibrering: passerer den udtalte sandsynlighed med virkeligheden?

    For hver bøtte: hvor mange, hvad sagde vi i gennemsnit, og hvor ofte var
    udsagnet faktisk sandt. Predicted 0.6 og observed 0.2 er overmod — den
    slags selvindsigt giver en hit-rate ikke.
    """
    out: list[dict[str, Any]] = []
    for lo, hi in zip(_CALIBRATION_EDGES, _CALIBRATION_EDGES[1:]):
        bucket: list[tuple[float, float]] = []
        for p in scored:
            try:
                prob = float(p.get("probability"))
                actual = float(p.get("actual"))
                threshold = float(p.get("threshold"))
            except (TypeError, ValueError):  # uden tal kan udsagnet ikke afgøres og erklæres void
                continue
            if lo <= prob < hi:
                bucket.append((prob, 1.0 if actual > threshold else 0.0))
        if not bucket:
            continue
        n = len(bucket)
        out.append({
            "bin": f"{lo:.2f}-{min(hi, 1.0):.2f}",
            "n": n,
            "predicted": round(sum(b[0] for b in bucket) / n, 3),
            "observed": round(sum(b[1] for b in bucket) / n, 3),
        })
    return out


def score_predictions(min_age_hours: float = 24.0) -> dict[str, Any]:
    """Scor modne forudsigelser i deres eget adskilte fremtidsvindue.

    ``min_age_hours`` er bevaret for eksisterende kaldere, men er ikke
    autoritativ: for v2-records afgør ``made_at + horizon_hours`` hvornår en
    forudsigelse er moden. En forudsigelse der gælder en uge kan ikke scores
    efter et døgn.

    Returnerer accuracy (ramte vi retningen), Brier (hvor skarp sandsynligheden
    var) og kalibreringsbøtter. Begge er None når intet endnu er scoret.
    """
    try:
        preds = _load_predictions()
    except Exception:
        preds = []
    if not isinstance(preds, list):
        preds = []

    now = datetime.now(UTC)
    newly_scored = 0
    newly_void = 0
    pending = 0
    insufficient = 0

    for p in preds:
        try:
            if not isinstance(p, dict):
                continue
            # v1 blev scoret mod næsten samme vindue som det den forudsagde ud
            # fra. Uanset om den gamle kørsel kaldte det et hit, er udfaldet
            # meningsløst — den erklæres void, også når den allerede står som
            # scoret, så historikken ikke kan læses som præcision.
            try:
                version = int(p.get("v") or 1)
            except (TypeError, ValueError):
                version = 1
            if version < _PRED_VERSION:
                if not p.get("void"):
                    p["void"] = True
                    p["void_reason"] = (
                        "v1: forudsigelse og scoring delte vindue (tautologisk)"
                    )
                    newly_void += 1
                continue
            if p.get("scored"):
                continue
            outcome, detail = _score_record(p, now)
            if outcome == "pending":
                pending += 1
                continue
            if outcome == "insufficient":
                insufficient += 1
                continue
            p["scored"] = True
            p["scored_at"] = now.isoformat()
            if outcome == "void":
                p["void"] = True
                p["void_reason"] = detail.get("void_reason", "")
                newly_void += 1
            else:
                p.update(detail)
                newly_scored += 1
        except Exception:
            # Skør enkelt-record forgifter aldrig hele scoringen.
            continue

    if newly_scored or newly_void:
        _save_predictions(preds)

    scored_v2 = [
        p for p in preds
        if isinstance(p, dict) and p.get("scored") and not p.get("void")
        and int(p.get("v") or 1) >= _PRED_VERSION
    ]
    recent = scored_v2[-_ACCURACY_N:]
    n = len(recent)
    accuracy = round(sum(1 for p in recent if p.get("hit")) / n, 3) if n else None
    brier = (
        round(sum(float(p.get("brier") or 0.0) for p in recent) / n, 4) if n else None
    )
    legacy = sum(
        1 for p in preds
        if isinstance(p, dict) and p.get("void") and int(p.get("v") or 1) < _PRED_VERSION
    )
    return {
        "scored": newly_scored,
        "accuracy": accuracy,
        "n": n,
        "brier": brier,
        "calibration": _calibration(recent),
        "void": newly_void,
        "legacy_excluded": legacy,
        "pending": pending,
        "insufficient": insufficient,
    }


def build_self_model_predictive_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Added during 2026-05-13 coverage push (system_cartographer dark-edge
    closure). Reports module presence so the cartographer registers it as
    observed. Specific state-readers added as the module evolves.

    2026-07-06: lukker forudsigelses-loopet (rådets #2). Lazy scoring ved
    læsning (enkleste der virker — ingen ny cadence-registrering nødvendig).

    2026-11-12: loopet blev gjort falsificerbart. Fladen eksponerer nu også
    ``prediction_brier`` og ``prediction_calibration``, fordi en hit-rate
    alene ikke kan skelne «jeg gætter rigtigt» fra «jeg gætter sikkert».
    Self-safe: fejl → neutral.
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
    surface["prediction_brier"] = acc.get("brier")
    surface["prediction_calibration"] = acc.get("calibration") or []

    # Absorbér som levende central-nerve — Centralen lærer sin egen præcision.
    # Flaget fyrer på BÅDE lav hit-rate og dårlig Brier: en model kan ramme
    # retningen ofte og stadig være systematisk overmodig.
    try:
        n = int(acc.get("n") or 0)
        accuracy = acc.get("accuracy")
        brier = acc.get("brier")
        _absorb(
            "self",
            "prediction_accuracy",
            {"accuracy": accuracy, "n": n, "brier": brier},
            learn_key="self:prediction_accuracy",
            flag_if=lambda v: (v.get("n", 0) >= 5) and (
                (v.get("accuracy") is not None and v["accuracy"] < 0.4)
                or (v.get("brier") is not None and v["brier"] > 0.28)
            ),
            flag_reason="lav forudsigelses-præcision",
        )
    except Exception:  # fladen skal kunne læses selv om absorptionen fejler
        pass

    return surface
