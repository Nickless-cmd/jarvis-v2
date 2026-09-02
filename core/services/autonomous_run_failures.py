"""Fejlede autonome kørsler — set af Jarvis selv, ikke gemt i hans mund.

Bjørn 2026-09-02: «de skal ikke lande i hans hukommelse eller mund... ellers
skal de noteres i hans prompt som failed autonome runs, så han er bevidst om at
de er fejlet? måske give ham mulighed for selv at vælge om han vil prøve igen?»

Baggrunden: en udbyders fejlbesked blev gemt som Jarvis' EGET svar — 35 gange
på 14 dage stod aihubmix' kvote-afvisning ordret i hans mund og dermed i hans
hukommelse. Vagten mod det fandtes, men kun på anden pas, som næsten aldrig
kører.

At kassere teksten er nødvendigt, men ikke nok: så mislykkes turen usynligt, og
det var netop det mønster der lod runtime kaste hans beslutninger væk i
månedsvis uden at nogen opdagede det. Derfor journaliseres fejlen i stedet:

    kasseret som svar   →   noteret som kendsgerning   →   han kan vælge at prøve igen

Tre egenskaber, bevidst valgt:

* **Ikke hans ord.** Journalen er en observation OM en kørsel, formuleret af
  runtime. Den kan aldrig forveksles med noget han har sagt eller husker.
* **Afgrænset.** Højst ``_MAX_KEPT`` poster, korte uddrag. En fejlende udbyder
  må ikke kunne fylde hans prompt.
* **Intet automatisk genforsøg.** ``request_retry()`` findes som API, men
  intet værktøj er wiret til den endnu, og prompten lover derfor ikke et.
  Runtime prøver ALDRIG igen af sig selv — det ville gøre en fejlende
  gratis-pulje til en løkke. Valget skal være hans, når kroget findes.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

_KEY = "autonomous_run_failures"
_MAX_KEPT = 12
_MAX_DETAIL_CHARS = 160
# Ældre end dette er ikke længere handlingsanvisende — han skal ikke bære
# en uge gammel kvotefejl rundt i hver eneste prompt.
_PROMPT_WINDOW_HOURS = 24
_PROMPT_MAX_LINES = 4


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _kv_get(default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(_KEY, default)
        return v if v is not None else default
    except Exception:
        return default


def _kv_set(value: Any) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(_KEY, value)
    except Exception:
        pass


def _load() -> list[dict]:
    raw = _kv_get([])
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    return [r for r in raw if isinstance(r, dict)] if isinstance(raw, list) else []


def record_failure(
    *,
    run_id: str,
    session_id: str = "",
    origin: str = "",
    provider: str = "",
    model: str = "",
    detail: str = "",
    kind: str = "provider_error",
) -> dict:
    """Journalisér at en autonom kørsel mislykkedes. Kaster aldrig."""
    post = {
        "id": str(run_id or "")[:64] or _now(),
        "at": _now(),
        "run_id": str(run_id or "")[:64],
        "session_id": str(session_id or "")[:64],
        "origin": str(origin or "")[:32],
        "provider": str(provider or "")[:40],
        "model": str(model or "")[:60],
        "kind": str(kind or "provider_error")[:40],
        "detail": str(detail or "").strip()[:_MAX_DETAIL_CHARS],
        "retry_requested": False,
        "retried_at": "",
    }
    try:
        poster = [p for p in _load() if p.get("id") != post["id"]]
        poster.append(post)
        _kv_set(poster[-_MAX_KEPT:])
    except Exception:
        pass
    return post


def recent_failures(limit: int = _MAX_KEPT) -> list[dict]:
    """Nyeste først."""
    return list(reversed(_load()))[: max(0, int(limit))]


def _within_window(post: dict, hours: int) -> bool:
    try:
        t = datetime.fromisoformat(str(post.get("at") or "").replace("Z", "+00:00"))
        if t.tzinfo is None:
            t = t.replace(tzinfo=UTC)
        return (datetime.now(UTC) - t).total_seconds() <= hours * 3600
    except Exception:
        return False


def request_retry(failure_id: str) -> bool:
    """Marker at HAN vil forsøge igen. Runtime gør det ikke af sig selv."""
    poster = _load()
    ramt = False
    for p in poster:
        if p.get("id") == str(failure_id or ""):
            p["retry_requested"] = True
            ramt = True
    if ramt:
        _kv_set(poster)
    return ramt


def pending_retries() -> list[dict]:
    return [p for p in _load() if p.get("retry_requested") and not p.get("retried_at")]


def mark_retried(failure_id: str) -> None:
    poster = _load()
    for p in poster:
        if p.get("id") == str(failure_id or ""):
            p["retried_at"] = _now()
    _kv_set(poster)


def clear() -> None:
    _kv_set([])


def prompt_section() -> str:
    """Blokken Jarvis ser. Tom streng når der intet er at vide.

    Formuleret som runtime der fortæller HAM noget — aldrig som noget han selv
    har sagt. Og med det valg han faktisk har: prøve igen, eller lade være.
    """
    friske = [p for p in recent_failures() if _within_window(p, _PROMPT_WINDOW_HOURS)]
    if not friske:
        return ""
    linjer = ["━━━━━━━━━━ [ FEJLEDE AUTONOME KØRSLER ] ━━━━━━━━━━",
              "Kørsler af DIG der ikke lykkedes det seneste døgn. Udbyderens "
              "fejltekst er kasseret — den er ikke dine ord og står ikke i din "
              "hukommelse. Du behøver ikke gøre noget; det står her så du ved "
              "det, og kan tage det med i hvad du vælger nu."]
    for p in friske[:_PROMPT_MAX_LINES]:
        maerke = " · genforsøg ønsket" if p.get("retry_requested") else ""
        linjer.append(
            "· [%s] %s — %s%s" % (
                str(p.get("id") or "")[:16],
                str(p.get("origin") or "autonom") or "autonom",
                str(p.get("detail") or p.get("kind") or "ukendt fejl"),
                maerke))
    if len(friske) > _PROMPT_MAX_LINES:
        linjer.append("· (+%d flere)" % (len(friske) - _PROMPT_MAX_LINES))
    return "\n".join(linjer)
