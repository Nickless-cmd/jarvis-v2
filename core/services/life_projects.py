from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.services.initiative_queue import (
    abandon_long_term_intention,
    list_active_long_term_intentions,
    seed_long_term_intention,
)


def create_life_project(
    *,
    title: str,
    why: str,
    source: str = "life-project",
    source_id: str = "",
    priority: str = "medium",
) -> dict[str, object]:
    initiative_id = seed_long_term_intention(
        title=title,
        why=why,
        source=source,
        source_id=source_id,
        priority=priority,
    )
    items = list_active_long_term_intentions(limit=3)
    item = next((entry for entry in items if str(entry.get("initiative_id") or "") == initiative_id), None)
    return {
        "status": "ok",
        "initiative_id": initiative_id,
        "life_project": item or {},
    }


def build_life_projects_surface() -> dict[str, object]:
    items = list_active_long_term_intentions(limit=3)
    return {
        "active": bool(items),
        "count": len(items),
        "items": items,
        "summary": (
            f"{len(items)} active life projects"
            if items
            else "No active life projects"
        ),
    }


def abandon_life_project(initiative_id: str, *, note: str = "") -> dict[str, object]:
    item = abandon_long_term_intention(initiative_id, note=note)
    if item is None:
        return {"status": "error", "error": f"life project {initiative_id!r} not found"}
    return {"status": "ok", "life_project": item}


def endorse_life_project(initiative_id: str, *, note: str = "") -> dict[str, object]:
    """«Det er i orden» — projektet lever videre, nu med et menneskes ja bag sig."""
    from core.services.initiative_queue import endorse_long_term_intention
    item = endorse_long_term_intention(initiative_id, note=note)
    if item is None:
        return {"status": "error", "error": f"life project {initiative_id!r} not found"}
    return {"status": "ok", "life_project": item}


def _har_spor(item: dict[str, object], *, now: datetime, threshold: timedelta) -> bool:
    """Er projektet blevet LOEFTET inden for decay-vinduet — ikke bare rørt?

    Et menneskes ja (`user_approved_at`) er tilladelse, ikke arbejde, og tæller
    derfor ikke med: et projekt Bjørn har godkendt, og som jeg så ikke har rørt,
    ER blevet ord.

    Sporet skal være FERSKT. Målt 7/11-2026: trust-projektet havde et spor fra
    en materialisering i oktober, og et «nogensinde»-kriterium ville gøre det
    udødeligt — dommen ville aldrig kunne lukke noget der bare var blevet rørt
    én gang. Spørgsmålet er ikke om projektet nogensinde levede, men om det
    lever nu.

    Feltnavnene er laast til det faktiske skema: `mark_attempted` skriver
    `last_attempt_at`, mens `mark_acted` skriver `last_action_at` — ikke
    `acted_at`. At tjekke et felt der aldrig skrives ville gøre dommen blind.

    MEN `last_action_at`/`acted_at` er UDELUKKET, og det er hele pointen.
    Maalt 7/11-2026: `proactivity_bridge.py:321` kalder `mark_acted(...,
    action_summary="surfaced via proactivity_bridge")`, og
    `runtime_action_executor.py:526` kalder den med
    "promoted-to-visible-lane". Begge skriver `last_action_at` — saa en
    VISNING blev laest som et livstegn, og projektet fik 14 nye dage for at
    blive vist. Det er samme fejlklasse som `mark_acted`-fixet 1/11 fjernede:
    en status der ser ud som information, men beskriver noget andet.

    Kun `last_attempt_at` tæller: det skrives udelukkende af
    `mark_attempted`, som kaldes naar heartbeat faktisk griber projektet.
    """
    for felt in ("last_attempt_at",):
        raw = str(item.get(felt) or "").strip()
        if not raw:
            continue
        try:
            hvornaar = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except (ValueError, TypeError):  # et ulaeseligt tidsstempel er intet spor — det skal ikke goere projektet udoedeligt
            continue
        if hvornaar.tzinfo is None:
            hvornaar = hvornaar.replace(tzinfo=UTC)
        if (now - hvornaar) <= threshold:
            return True
    return False


def tick_life_projects_reassessment(
    *, trigger: str = "heartbeat", last_visible_at: str = ""
) -> dict[str, object]:
    """Periodisk re-vurdering af aktive life projects.

    Cadence: 1440 min (24t).
    Kill-switch: layer_life_projects_enabled i runtime.json.
    Gennemgår aktive long_term_intentions og markerer dem der er due for re-assessment
    (last_reviewed_at ældre end layer_life_projects_decay_days dage, default 14).
    """
    from core.runtime.secrets import read_runtime_key

    try:
        enabled = read_runtime_key("layer_life_projects_enabled")
    except Exception:
        enabled = True
    if not enabled:
        return {"status": "disabled", "reason": "layer_life_projects_enabled=false"}

    try:
        decay_days = int(read_runtime_key("layer_life_projects_decay_days"))
    except Exception:
        decay_days = 14
    threshold = timedelta(days=decay_days)
    now = datetime.now(UTC)

    from core.runtime import db as runtime_db

    items = list_active_long_term_intentions(limit=20)
    reviewed = 0
    fornyet = 0
    lukket = 0
    skipped = 0

    for item in items:
        last_reviewed_raw = str(item.get("updated_at") or item.get("detected_at") or "")
        if not last_reviewed_raw:
            skipped += 1
            continue
        try:
            last_reviewed = datetime.fromisoformat(last_reviewed_raw.replace("Z", "+00:00"))
            if last_reviewed.tzinfo is None:
                last_reviewed = last_reviewed.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            skipped += 1
            continue

        if (now - last_reviewed) >= threshold:
            initiative_id = str(item.get("initiative_id") or "")
            if _har_spor(item, now=now, threshold=threshold):
                # Projektet er blevet løftet mindst én gang: det er arbejde, ikke
                # ord. Levetiden fornyes ved at gøre det due, så heartbeat griber
                # det i næste cyklus i stedet for at lade det ligge.
                runtime_db.update_runtime_initiative(
                    initiative_id,
                    next_attempt_at=now.isoformat(),
                    updated_at=now.isoformat(),
                )
                dom = "fornyet"
                fornyet += 1
            else:
                # Aldrig forsøgt, aldrig handlet: rækken blev ikke løftet den dag
                # den blev seedet, og den er ikke blevet det siden. Så er den ord.
                # Målt 7/11-2026: tre projekter seedet 15. maj stod `pending` i
                # syv måneder uden ét eneste forsøg — fordi `_expire_stale`
                # bevidst springer long_term_intention over, og den her
                # re-vurdering kun råbte om det til en bus uden lyttere.
                runtime_db.update_runtime_initiative(
                    initiative_id,
                    status="expired",
                    abandoned_at=now.isoformat(),
                    blocked_reason=(
                        f"aldrig loeftet paa {decay_days} dage — ord, ikke projekt"
                    ),
                    updated_at=now.isoformat(),
                )
                dom = "lukket"
                lukket += 1

            from core.eventbus.bus import event_bus
            event_bus.publish(
                "life_projects.reassessment_due",
                {
                    "initiative_id": initiative_id,
                    "title": str(item.get("focus") or ""),
                    "last_reviewed_at": last_reviewed_raw,
                    "decay_days": decay_days,
                    "trigger": trigger,
                    "dom": dom,
                },
            )
            reviewed += 1
        else:
            skipped += 1

    return {
        "status": "ok",
        "reviewed": reviewed,
        "fornyet": fornyet,
        "lukket": lukket,
        "skipped": skipped,
        "trigger": trigger,
    }
