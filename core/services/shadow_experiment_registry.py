"""core/services/shadow_experiment_registry.py

SHADOW-EKSPERIMENT-REGISTER + review-påmindelse.

Jarvis kører mange SHADOW-eksperimenter (event-trigger, convene_judge,
reasoning_interceptor RED, merovingian, ...). De kører tavst, og BÅDE Bjørn og
Claude glemmer at komme tilbage og evaluere dem når deres vindue er modent.

Dette modul er et durabelt register (KV via
`core.runtime.db_core.get/set_runtime_state_value`, nøgle `shadow_experiments`):
hvert eksperiment registrerer sit start-tidspunkt + hvor længe vinduet skal løbe.
Når vinduet er forbi bliver eksperimentet "ripe" (modent) og surfacer sig selv —
både via `jc shadows` OG passivt i Central-feeden (observe
`central_meta/shadow_review_due`) så ingen behøver at spørge.

Self-safe: alt er best-effort; en KV-fejl → tomt/uændret, kaster aldrig ind i
kalderen (heartbeat/route/import).

Tiden injiceres (`now_ts`/`started_ts`, default `time.time()`) så testene er
deterministiske.
"""
from __future__ import annotations

import time
from typing import Any

_KEY = "shadow_experiments"


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
    """Heartbeat-venlig tick: byg surface (som emit'er påmindelsen ved modenhed)
    og returnér en lille status-dict. Self-safe."""
    surf = build_shadow_review_surface(now_ts=now_ts)
    return {"ripe_count": surf.get("ripe_count", 0),
            "ripe": [r.get("name") for r in surf.get("ripe", [])]}
