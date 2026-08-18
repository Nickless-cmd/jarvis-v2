"""Kalibreret forventning til selv-overraskelse.

Udskilt fra `visible_runs.py` (Boy Scout — 7004 linjer): detektoren skal eje sin egen
forventning, ikke få den stukket i hånden af kaldsstedet.

**Hvorfor den anden halvdel af buggen fandtes.** Rettelsen 17. aug gjorde negativ
overraskelse *mulig* (strong→0.8, weak→0.5 mod gaten `> 0.6`), men efterlod en
to-værdi-konstant. For en svag model betød `0.5` reelt *"jeg forventer at fejle"* —
og da 98% af alle runs lykkes, blev hver eneste succes registreret som en positiv
overraskelse. 54 rækker på ét døgn. Det er ikke overraskelse, det er en tæller.

Ægte overraskelse kræver tre ting den konstant ikke havde:

1. **En varierende forventning** — modellens *empiriske* succesrate fra dens egne
   seneste runs, glattet mod en styrke-baseret prior. Ikke et gæt, men bevis.
2. **En død zone** — havde jeg ingen sikker forventning, kan intet udfald overraske
   mig. Overraskelse er en usandsynlig begivenhed under min egen model af mig selv;
   uden en skarp forudsigelse er der ingenting at modsige.
3. **Uafgjorte udfald tæller ikke** — `cancelled`/`interrupted` er Bjørns handling,
   ikke min præstation. Hverken bevis eller overraskelse.

Self-safe hele vejen: enhver DB-fejl falder tilbage på prior'en, aldrig på en påstand.
"""
from __future__ import annotations

_SUCCESS = ("completed", "success", "ok")
_FAILURE = ("failed", "error", "degenerated")
# Uafgjort: afbrudt udefra. Siger intet om min kompetence, så det er hverken bevis
# (indgår ikke i raten) eller overraskelse (kan ikke udløse en detektion).
_INDECISIVE = ("cancelled", "interrupted", "aborted", "")

_LOOKBACK = 50
_PRIOR_WEIGHT = 8.0  # hvor mange runs' bevis en prior er værd, før empirien overtager
_PRIOR_STRONG = 0.85
_PRIOR_WEAK = 0.50

# Den døde zone. Uden for den har jeg en skarp forudsigelse der kan modsiges.
CONFIDENT_SUCCESS = 0.75
CONFIDENT_FAILURE = 0.35


def classify_outcome(outcome: str) -> str:
    """``'success'`` | ``'failure'`` | ``'indecisive'``.

    Ukendte statusser bliver ``indecisive``, ikke ``failure``: en status vi ikke
    forstår må aldrig blive til en anklage om at jeg fejlede.
    """
    o = str(outcome or "").strip().lower()
    if o in _SUCCESS:
        return "success"
    if o in _FAILURE:
        return "failure"
    return "indecisive"


def _recent_outcomes(model: str, *, lookback: int) -> tuple[int, int]:
    """``(successes, decisive_total)`` fra modellens egne seneste runs.

    Self-safe → ``(0, 0)``, hvilket lader prior'en stå alene.
    """
    model = str(model or "").strip()
    if not model:
        return (0, 0)
    try:
        from core.runtime.db_core import connect

        with connect() as conn:
            rows = conn.execute(
                "SELECT status FROM visible_runs WHERE model = ? "
                "ORDER BY started_at DESC LIMIT ?",
                (model, int(lookback)),
            ).fetchall()
    except Exception:
        return (0, 0)

    successes = decisive = 0
    for r in rows:
        try:
            status = r["status"]
        except Exception:
            status = r[0] if r else ""
        kind = classify_outcome(status)
        if kind == "indecisive":
            continue
        decisive += 1
        if kind == "success":
            successes += 1
    return (successes, decisive)


def expected_success_rate(model: str, *, lookback: int = _LOOKBACK) -> float:
    """Empirisk P(succes) for DENNE model, glattet mod en styrke-baseret prior.

    Glatningen gør forventningen brugbar fra første run: uden historik står prior'en
    alene, og med historik overtager empirien gradvist. En helt ukendt svag model
    lander på 0.50 — midt i den døde zone — så den kan ikke overraske mig før den
    har optjent en faktisk track-record. Det er meningen.
    """
    try:
        from core.services.model_trust import model_strength

        prior = _PRIOR_STRONG if model_strength(model) == "strong" else _PRIOR_WEAK
    except Exception:
        prior = _PRIOR_WEAK

    successes, decisive = _recent_outcomes(model, lookback=lookback)
    return (successes + _PRIOR_WEIGHT * prior) / (decisive + _PRIOR_WEIGHT)


def expectation_verdict(expected: float, outcome_kind: str) -> str | None:
    """``'positive'`` | ``'negative'`` | ``None`` (død zone / uafgjort udfald).

    Den ENESTE port til en overraskelse. Begge retninger kræver en *sikker*
    forventning der bliver modsagt — derfor er der ingen vej fra midterfeltet.
    """
    if outcome_kind == "indecisive":
        return None
    if expected >= CONFIDENT_SUCCESS and outcome_kind == "failure":
        return "negative"
    if expected <= CONFIDENT_FAILURE and outcome_kind == "success":
        return "positive"
    return None


def is_legacy_degenerate(expected_confidence: float) -> bool:
    """Sand for de 19.731 rækker fra den defekte detektor.

    Signaturen er bevisbar: den gamle kalder sendte en hardkodet ``0.6``, og den
    døde zone (0.35–0.75) kan pr. konstruktion ALDRIG udsende en række med 0.6.
    Derfor er enhver 0.6-række nødvendigvis fra før rettelsen. Bruges til at
    filtrere læsesiden uden at slette data.
    """
    try:
        return abs(float(expected_confidence) - 0.6) < 1e-6
    except Exception:
        return False
