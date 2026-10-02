"""core/services/shadow_experiment_registry.py

SHADOW-EKSPERIMENT-REGISTER + review-påmindelse.

Jarvis kører mange SHADOW-eksperimenter (event-trigger, convene_judge,
reasoning_interceptor RED, merovingian, ...). De kører tavst, og BÅDE Bjørn og
Claude glemmer at komme tilbage og evaluere dem når deres vindue er modent.

Dette modul er et durabelt register (KV via
`core.runtime.db_core.get/set_runtime_state_value`, nøgle `shadow_experiments`):
hvert eksperiment registrerer sit start-tidspunkt + hvor længe vinduet skal løbe.
Når vinduet er forbi bliver eksperimentet "ripe" (modent) og meldes ad TRE veje:
`GET /central/shadow-review`, en passiv `central_meta/shadow_review_due` i
Central-feeden, og — siden 2/10-2026 — en besked i Bjørns chat gennem
daemon-vagten.

Den tredje findes fordi de to første ikke rakte. Docstringen her sagde før at
registeret surfacede via `jc shadows`; den kommando findes IKKE (verificeret
2/10 — intet «shadows» i apps/central_cli). Og den passive observe lander i
`central_trace`-sinken, som er en deque i hukommelsen der dør ved hver genstart.
Resultatet var otte eksperimenter forfaldne i op til 78 dage uden at nogen
påmindelse nåede frem.

Self-safe: alt er best-effort; en KV-fejl → tomt/uændret, kaster aldrig ind i
kalderen (heartbeat/route/import).

Tiden injiceres (`now_ts`/`started_ts`, default `time.time()`) så testene er
deterministiske.
"""
from __future__ import annotations

import time
from typing import Any

_KEY = "shadow_experiments"

#: Hvor ofte paamindelsen maa fyre. Vinduerne maales i uger, saa én gang i
#: doegnet er rigeligt og naevner aldrig det samme to gange paa en dag.
PAAMINDELSE_INTERVAL_TIMER: float = 24.0

#: EGEN durabel noegle. Klokken MAA ikke ligge i en modul-global: den gamle
#: trigger var `_HEARTBEAT_TICK_COUNTER % 60`, og taelleren nulstilles ved hver
#: genstart. Maalt 2/10-2026: hjerteslaget tikker ~9 gange paa 6 timer, saa 60
#: tik er ~40 TIMER — og med tre genstarter paa ét doegn naaede taelleren aldrig
#: derop. Paamindelsen om at vi glemmer skygge-vinduer blev selv glemt, anden
#: gang. En durabel klokke kan en genstart ikke nulstille.
_PAAMINDELSE_NOEGLE = "shadow_review_last_reminder"


# ── KV-lag (self-safe) ─────────────────────────────────────────────────────
def _load() -> dict[str, dict]:
    """Læs hele register-dict'en fra KV. Self-safe → {} ved fejl/ugyldig form."""
    from core.runtime import db_core
    raw = db_core.get_runtime_state_value(_KEY, {})
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict] = {}
    for name, rec in raw.items():
        if isinstance(rec, dict):
            out[str(name)] = dict(rec)
    return out


def _save(data: dict[str, dict]) -> None:
    """Skriv hele register-dict'en durabelt. Self-safe (best-effort)."""
    try:
        from core.runtime import db_core
        db_core.set_runtime_state_value(_KEY, data)
    except Exception:
        pass


# ── offentligt API ─────────────────────────────────────────────────────────
def register_experiment(
    name: str,
    review_after_hours: float,
    note: str = "",
    started_ts: float | None = None,
) -> None:
    """Registrér et shadow-eksperiment. Idempotent på navn: hvis det allerede er
    registreret og IKKE reviewet, nulstilles `started_ts` ikke (vinduet løber
    videre). Self-safe."""
    try:
        clean = str(name or "").strip()
        if not clean:
            return
        now = time.time() if started_ts is None else float(started_ts)
        data = _load()
        existing = data.get(clean)
        if isinstance(existing, dict) and not bool(existing.get("reviewed", False)):
            # Bevar oprindeligt startpunkt; opdatér blot vindue/note (billig frisk-info).
            existing["review_after_hours"] = float(review_after_hours)
            if note:
                existing["note"] = str(note)
            data[clean] = existing
        else:
            data[clean] = {
                "name": clean,
                "started_ts": float(now),
                "review_after_hours": float(review_after_hours),
                "note": str(note or ""),
                "reviewed": False,
            }
        _save(data)
    except Exception:
        pass


def _annotate(rec: dict, now: float) -> dict:
    """Berig én rå-record med `hours_running` + `ripe`."""
    started = float(rec.get("started_ts") or 0.0)
    win_h = float(rec.get("review_after_hours") or 0.0)
    reviewed = bool(rec.get("reviewed", False))
    hours_running = max(0.0, (now - started) / 3600.0)
    ripe = (not reviewed) and (now >= started + win_h * 3600.0)
    return {
        "name": str(rec.get("name") or ""),
        "started_ts": started,
        "review_after_hours": win_h,
        "note": str(rec.get("note") or ""),
        "reviewed": reviewed,
        "hours_running": round(hours_running, 2),
        "ripe": bool(ripe),
    }


def list_experiments(now_ts: float | None = None) -> list[dict]:
    """Alle registrerede eksperimenter, beriget med `hours_running` + `ripe`.
    Self-safe → [] ved fejl."""
    try:
        now = time.time() if now_ts is None else float(now_ts)
        data = _load()
        items = [_annotate(rec, now) for rec in data.values()]
        items.sort(key=lambda x: (not x["ripe"], -x["hours_running"]))
        return items
    except Exception:
        return []


def ready_for_review(now_ts: float | None = None) -> list[dict]:
    """De modne (ripe), ikke-reviewede eksperimenter. Self-safe → []."""
    return [it for it in list_experiments(now_ts=now_ts) if it["ripe"]]


def mark_reviewed(name: str) -> None:
    """Markér et eksperiment som reviewet (fjerner det fra `ripe`). Self-safe."""
    try:
        clean = str(name or "").strip()
        if not clean:
            return
        data = _load()
        rec = data.get(clean)
        if isinstance(rec, dict):
            rec["reviewed"] = True
            data[clean] = rec
            _save(data)
    except Exception:
        pass


# ── kendte LIVE shadows (bekræftet via live-telemetri 2026-07-13) ──────────
# Registreres idempotent ved import af de respektive shadow-moduler + ved
# surface-bygning, så registeret altid er seedet når runtime kører. Kun
# eksperimenter der ER bekræftet aktive — INTET opdigtet.
_KNOWN_SHADOWS: tuple[tuple[str, float, str], ...] = (
    ("event_trigger", 24.0, "C5 delta-trigger shadow — kalibrér θ fra 24t spor"),
    ("convene_judge", 24.0, "Grund-dommer mode=shadow — flip til 'on' efter kalibrering"),
    ("reasoning_interceptor_red", 168.0,
     "Reasoning-interceptor RED stadig shadow (yellow flippet live) — afventer flere samples"),
    ("merovingian", 336.0, "Merovingian drift-værn enforce OFF — flip efter 14d shadow-eval"),
)


def register_known_shadows() -> None:
    """Seed registeret med de bekræftede live shadows (idempotent, self-safe)."""
    for name, hours, note in _KNOWN_SHADOWS:
        register_experiment(name, review_after_hours=hours, note=note)


def _sidste_paamindelse() -> float:
    """Hvornaar fyrede vi sidst? 0.0 betyder «aldrig». Self-safe."""
    try:
        from core.runtime import db_core
        raw = db_core.get_runtime_state_value(_PAAMINDELSE_NOEGLE, {})
        if isinstance(raw, dict):
            return float(raw.get("ts") or 0.0)
        return float(raw or 0.0)
    except Exception:
        # Kan klokken ikke laeses, behandles det som «aldrig» → vi paaminder.
        # Retningen er med vilje: en paamindelse for meget er billigere end en
        # glemt kalibrering i 78 dage.
        return 0.0


def _stempl_paamindelse(now: float) -> None:
    """Gem klokken durabelt. Self-safe (best-effort)."""
    try:
        from core.runtime import db_core
        db_core.set_runtime_state_value(_PAAMINDELSE_NOEGLE, {"ts": float(now)})
    except Exception:
        # Lykkes skrivningen ikke, bliver den daglige paamindelse en
        # 6-timers — det er mildt, men det skal kunne SES, for ellers ser en
        # stribe gentagelser ud som en fejl i selve modenheds-beregningen.
        import logging
        logging.getLogger(__name__).warning(
            "shadow_experiment_registry: kunne ikke gemme paamindelses-klokken",
            exc_info=True)


# ── surfacing (passiv påmindelse) ──────────────────────────────────────────
def build_shadow_review_surface(now_ts: float | None = None) -> dict[str, Any]:
    """Byg surface til Central-route/`jc shadows`. Seeder kendte shadows,
    beregner ripe, og EMIT'er en passiv Central-påmindelse når noget er modent
    (så det dukker op i feeden uden at nogen kører en særlig kommando).

    Self-safe → tom surface ved fejl."""
    try:
        register_known_shadows()  # best-effort seed (idempotent)
        experiments = list_experiments(now_ts=now_ts)
        ripe = [it for it in experiments if it["ripe"]]
        if ripe:
            _emit_reminder([r["name"] for r in ripe])
        return {
            "experiments": experiments,
            "ripe": ripe,
            "ripe_count": len(ripe),
        }
    except Exception:
        return {"experiments": [], "ripe": [], "ripe_count": 0}


def _emit_reminder(ripe_names: list[str]) -> None:
    """Passiv Central-påmindelse: observe `central_meta/shadow_review_due`.
    Best-effort; kaster aldrig."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "central_meta",
            "nerve": "shadow_review_due",
            "kind": "reminder",
            "ripe": list(ripe_names),
            "count": len(ripe_names),
        })
    except Exception:
        pass


def tick_shadow_review_reminder(now_ts: float | None = None) -> dict[str, Any]:
    """Tick: byg surface, og naar noget er modent OG klokken er forfalden,
    send en paamindelse der faktisk ANKOMMER. Self-safe.

    Maa kaldes saa ofte man vil — den durable klokke afgoer, saa to triggere
    (hjerteslaget og det periodiske job) ikke kan paaminde dobbelt. Beslutningen
    bor ÉT sted; kun triggerne er flere.

    Hvorfor en besked og ikke kun `observe`: `central().observe()` lander i
    `central_trace`-sinken, som er en 2.000-pladsers deque i HUKOMMELSEN. Den
    doer ved hver genstart, og ingen laeser den medmindre de aabner Centralen.
    En passiv paamindelse om noget alle glemmer er en selvmodsigelse. Beskeden
    gaar gennem daemon-vagten (ikke-akut), saa den koees hvis Bjoern arbejder og
    flushes naar hans tur er omme — den kan altsaa ikke afbryde ham.
    """
    now = time.time() if now_ts is None else float(now_ts)
    surf = build_shadow_review_surface(now_ts=now)
    modne = surf.get("ripe") or []
    svar: dict[str, Any] = {
        "ripe_count": surf.get("ripe_count", 0),
        "ripe": [r.get("name") for r in modne],
        "notified": False,
    }
    if not modne:
        return svar
    sidst = _sidste_paamindelse()
    if now - sidst < PAAMINDELSE_INTERVAL_TIMER * 3600.0:
        svar["suppressed_until_ts"] = sidst + PAAMINDELSE_INTERVAL_TIMER * 3600.0
        return svar
    svar["notified"] = _send_paamindelse(modne)
    if svar["notified"]:
        _stempl_paamindelse(now)
    return svar


def _byg_besked(modne: list[dict]) -> str:
    """Teksten Bjoern faar. Naevner de mest forfaldne ved navn og hvor laenge —
    et tal han kan handle paa, ikke «noget er modent»."""
    efter_forfald = sorted(
        modne,
        key=lambda r: float(r.get("hours_running") or 0.0) - float(r.get("review_after_hours") or 0.0),
        reverse=True,
    )
    linjer = [f"🔬 **{len(modne)} skygge-eksperiment(er) venter på review.**", ""]
    for r in efter_forfald[:5]:
        navn = str(r.get("name") or "?")
        forfald_dage = (float(r.get("hours_running") or 0.0)
                        - float(r.get("review_after_hours") or 0.0)) / 24.0
        vindue_t = float(r.get("review_after_hours") or 0.0)
        linjer.append(f"• `{navn}` — {forfald_dage:.0f} dage forfalden "
                      f"(vindue var {vindue_t:.0f}t)")
    if len(efter_forfald) > 5:
        linjer.append(f"• … og {len(efter_forfald) - 5} mere")
    linjer += ["", "Hele registret: `GET /central/shadow-review`. "
               "Afslut ét med `shadow_experiment_registry.mark_reviewed(navn)`."]
    return "\n".join(linjer)


def _send_paamindelse(modne: list[dict]) -> bool:
    """Lever paamindelsen gennem daemon-vagten. True hvis den blev antaget.

    `push=False`: dette er en bunke efterslaeb, ikke noget akut. Bjoern har
    netop faaet ryddet op i proaktive push-kilder, og en ny daglig telefon-push
    ville vaere at give med den ene haand og tage med den anden.
    """
    try:
        from core.services.notification_bridge import (
            delivery_succeeded,
            send_session_notification,
        )
        svar = send_session_notification(
            _byg_besked(modne),
            source="shadow-review-due",
            push=False,
        )
        if delivery_succeeded(svar):
            return True
        import logging
        logging.getLogger(__name__).warning(
            "shadow_experiment_registry: paamindelse afvist: %s", svar)
        return False
    except Exception:
        import logging
        logging.getLogger(__name__).warning(
            "shadow_experiment_registry: kunne ikke sende paamindelse", exc_info=True)
        return False
