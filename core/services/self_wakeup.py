"""Self-wakeup — Jarvis' equivalent of Claude Code's ScheduleWakeup.

Jarvis already has schedule_task (one-shot future work) and the periodic
job scheduler (recurring), but neither matches the conversational wake-up
pattern: "in 90 seconds, re-enter THIS line of thought with prompt X".

This module adds that capability. Three operations:

- schedule_self_wakeup(delay_seconds, prompt, reason) — set a future
  self-message
- list_self_wakeups() — see what's queued
- cancel_self_wakeup(wakeup_id) — abort a pending one

When a wakeup's time arrives:
- Surfaces in prompt awareness on the next visible run/heartbeat tick
  (NOT injected magically — Jarvis sees "⏰ You scheduled yourself to
  resume X — go" and decides what to do)
- After he acts, mark_wakeup_consumed() clears it so it doesn't
  re-surface forever

Persistent: survives restarts via state_store. Audit trail in eventbus
(self_wakeup.scheduled, self_wakeup.fired, self_wakeup.consumed,
self_wakeup.cancelled).

Bounds:
- delay clamped to [60, 86400] (1 min to 24 hours) — anything longer
  should be a real scheduled task
- max 20 pending wakeups at once (don't let it become a backlog)
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)


_STATE_KEY = "self_wakeups"
_MIN_DELAY_SECONDS = 60
_MAX_DELAY_SECONDS = 86400  # 24 hours
#: Loft paa SAMTIDIGE ventende. Det fanger ikke en kaede, for en kaede har
#: altid dybde 0 eller 1: Jarvis forbruger én og booker én. Maalt 5/10-2026 i
#: `self_wakeups.json`: 140 poster, 116 consumed, 24 cancelled, NUL ventende —
#: dette loft har aldrig vaeret i naerheden af at fyre.
_MAX_PENDING = 20

#: Loft paa KAEDEN, pr. samtale pr. rullende doegn. Det er det loft der mangler.
#:
#: Bjoern 5/10-2026: «Hvorfor for jeg 3 til 5 beskeder på et svar??» Hver
#: kvitteret vaekning bookede en ny — hans egne ord i chatten: «Vaekningen
#: kvitteret, ny kontrol booket om 30 minutter». Kaeden 30/9 koerte fjorten led
#: paa fire timer, hvert kvarter, alle med samme indhold: «allerede haandteret».
#: Oprettede vaekninger pr. dag: 2/10: 15 · 3/10: 69 · 4/10: 141.
#:
#: TALLET er maalt, ikke valgt. Fordelingen pr. samtale:
#:   pr. TIME : p50 2, p90 4, maks 6   → timeniveauet er sundt, ikke her
#:   pr. DOEGN: 44 · 28 · 12 · 11 · 11 · 7 · 5 · 4
#: Normalen topper ved 12; 28 og 44 er loebet. 20 giver normalen rigelig luft
#: og skaerer kun loebet. Et lavere tal ville ramme en legitim CI-vagt.
_MAX_PR_SAMTALE_PR_DOEGN = 20


def _load() -> list[dict[str, Any]]:
    raw = load_json(_STATE_KEY, [])
    if not isinstance(raw, list):
        return []
    return [r for r in raw if isinstance(r, dict)]


def _save(records: list[dict[str, Any]]) -> None:
    save_json(_STATE_KEY, records)


def schedule_self_wakeup(
    *,
    delay_seconds: int,
    prompt: str,
    reason: str = "",
    extra: str = "",
    channel: str | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
    workspace_name: str | None = None,
    user_display_name: str | None = None,
    role: str | None = None,
    context_channel: str | None = None,
) -> dict[str, Any]:
    """Queue a self-wakeup. Returns the wakeup record."""
    prompt = (prompt or "").strip()
    reason = (reason or "").strip()
    extra = (extra or "").strip()
    if not prompt:
        return {"status": "error", "error": "prompt is required"}
    delay = int(max(_MIN_DELAY_SECONDS, min(_MAX_DELAY_SECONDS, delay_seconds)))

    records = _load()
    pending = [r for r in records if r.get("status") == "pending"]
    if len(pending) >= _MAX_PENDING:
        return {
            "status": "error",
            "error": f"max {_MAX_PENDING} pending wakeups; cancel one first",
        }
    sid = (session_id or "").strip()
    i_doegnet = bookinger_seneste_doegn(records, sid)
    if sid and i_doegnet >= _MAX_PR_SAMTALE_PR_DOEGN:
        return {
            "status": "error",
            "error": (
                f"{i_doegnet} wakeups already booked from this conversation in the "
                f"last 24h (limit {_MAX_PR_SAMTALE_PR_DOEGN}). You are in a chain: "
                "each handled wakeup booking another one is how this gets here. "
                "Stop re-booking, or ask Bjoern whether the watch is still wanted."
            ),
            "bookinger_seneste_doegn": i_doegnet,
        }

    fire_at = datetime.now(UTC) + timedelta(seconds=delay)
    wakeup_id = f"wake-{uuid4().hex[:10]}"
    record = {
        "wakeup_id": wakeup_id,
        "scheduled_at": datetime.now(UTC).isoformat(),
        "fire_at": fire_at.isoformat(),
        "delay_seconds": delay,
        "prompt": prompt[:1000],
        "reason": reason[:200],
        # Bjørns tilføjelse: han skriver ofte en ekstra besked lige efter en tur.
        # Den hører til wakeup'en, ikke kun turen — så den følger med i
        # awareness-noten og i dispatcherens self_directive (12/9-2026).
        "extra": extra[:1000] or None,
        "status": "pending",
        "fired_at": None,
        "consumed_at": None,
        # Leverings-destination. Default "app" (jarvis-desk) — wakeups må ALDRIG
        # default'e til Discord (Bjørn 2026-06-13). Dispatcheren guarder mod det.
        "channel": (channel or "app").strip().lower(),
        "session_id": (session_id or "").strip() or None,
        # Persist the originating identity context. The dispatcher runs outside
        # the request, so it must restore this before starting the background run.
        "user_id": (user_id or "").strip() or None,
        "workspace_name": (workspace_name or "").strip() or None,
        "user_display_name": (user_display_name or "").strip() or None,
        "role": (role or "").strip().lower() or None,
        "context_channel": (context_channel or "").strip().lower() or None,
    }
    records.append(record)
    _save(records)

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "self_wakeup.scheduled",
            {"wakeup_id": wakeup_id, "fire_at": record["fire_at"],
             "reason": reason[:80], "delay_seconds": delay},
        )
    except Exception:
        pass

    # ── Indbakken (Opgave 1, 3/10-2026) ─────────────────────────────────────
    #
    # DETTE er oprettelsespunktet spec'en mener med «verificeret ejer bestemmes
    # ved integrationens oprettelsespunkt». Her — og kun her — er alle tre dele
    # til stede samtidig: et tool-kald, et levende run, og en autentificeret
    # bruger. Et minut senere findes ingen af dem, og så kan proveniensen ikke
    # bevises af nogen.
    #
    # Uden dette kald ville indbakken være korrekt og tom: `inbox_items` havde
    # ingen skriver, og hele kæden — visning, gate, værktøjer — ville virke
    # upåklageligt på nul rækker. Det er husets hyppigste fejl, og den er
    # sværest at se netop når koden er rigtig.
    try:
        from core.services.inbox_state import registrer_kilde
        from core.services.session_context_resolve import aktivt_run_id
        from core.services.inbox_state import bruger_for_workspace
        _ib = registrer_kilde(
            # Vaekningen hoerer til den bruger den blev booket FOR. Er
            # `user_id` tom (ejerens egen, ubundne vej), OVERSAETTES workspacet
            # til et bruger-id — det skrives aldrig raat.
            #
            # RETTET 4/10-2026: her stod `record.get("workspace_name")`
            # direkte i `bruger_id`, og det blandede to navnerum i én kolonne.
            # Maalt samme dag stod der to indbakker til samme person, 36
            # raekker under navnet «bjorn» og 70 under hans rigtige id
            # 1246415163603816499 — og de 36 blev aldrig arbejdet i, fordi
            # hans sessioner oploeste til id'et. 34 kilde_id'er stod ordret
            # under BEGGE.
            bruger_id=(str(record.get("user_id") or "").strip()
                       or bruger_for_workspace(record.get("workspace_name") or "")),
            kildetype="wakeup",
            kilde_id=wakeup_id,
            oprettende_run_id=aktivt_run_id(""),
            beskrivelse=prompt[:200] or reason[:200],
        )
        if _ib.get("status") != "ok":
            logger.warning("self_wakeup: %s blev IKKE registreret i indbakken: %s",
                           wakeup_id, _ib.get("error"))
    except Exception as exc:  # noqa: BLE001
        # Vaekningen er GEMT. En fejl i indbakke-registreringen maa ikke
        # rulle den tilbage — men den maa heller ikke vaere tavs, for saa
        # staar en forpligtelse uden sin post, og det er usynligt.
        logger.warning("self_wakeup: kunne ikke registrere %s i indbakken: %s",
                       wakeup_id, exc)

    # Tallet med i SVARET, ikke kun i afvisningen. Han ser det altsaa hver
    # gang han booker — og det er der beslutningen om et led mere tages.
    # `i_doegnet` blev talt FOER denne blev tilfoejet, derfor +1.
    return {"status": "ok", "wakeup": record,
            "bookinger_seneste_doegn": i_doegnet + 1,
            "loft_pr_samtale_pr_doegn": _MAX_PR_SAMTALE_PR_DOEGN}


def bookinger_seneste_doegn(
    records: list[dict[str, Any]],
    session_id: str,
    *,
    nu: datetime | None = None,
) -> int:
    """Hvor mange vaekninger er booket fra DENNE samtale det seneste doegn.

    Taelles paa `scheduled_at`, altsaa hvornaar den blev BOOKET — ikke hvornaar
    den fyrer. En kaede bygges af bookinger, og en vaekning der er sat til at
    fyre i morgen er stadig et led i kaeden i dag.

    Status ignoreres med vilje: consumed, cancelled og pending taeller alle med.
    Taltes kun de ventende, ville vi maale `_MAX_PENDING` om igen og ramme
    samme blinde vinkel — en kaede forbruger hvert led foer den booker det
    naeste, saa de forbrugte ER kaeden.

    Oprydningen holder consumed og cancelled i 7 dage
    (`cleanup_old_wakeups`), saa doegn-vinduet bliver ikke beskaaret under os.
    """
    sid = (session_id or "").strip()
    if not sid:
        return 0
    # `nu` kan gives udefra, saa vinduet kan ankres et andet sted end dette
    # oejeblik. Uden det kan vagten ikke afspilles mod historikken: hver
    # historisk booking ligger uden for et vindue maalt fra i dag, saa
    # afspilningen svarer «nul afvist» uanset hvor slemt loebet var. Den
    # fejl gjorde jeg, og det tomme svar lignede en virkende vagt.
    graense = (nu or datetime.now(UTC)) - timedelta(hours=24)
    n = 0
    for r in records:
        if str(r.get("session_id") or "").strip() != sid:
            continue
        stamp = str(r.get("scheduled_at") or "")
        if not stamp:
            continue
        try:
            tid = datetime.fromisoformat(stamp)
        except ValueError:  # skraldet tidsstempel: kan ikke placeres i vinduet, taeller ikke med
            continue
        if tid >= graense:
            n += 1
    return n


def due_wakeups(*, include_fired_unconsumed: bool = True) -> list[dict[str, Any]]:
    """Return wakeups whose fire_at has passed and not yet consumed."""
    records = _load()
    now_iso = datetime.now(UTC).isoformat()
    out: list[dict[str, Any]] = []
    changed = False
    for r in records:
        status = str(r.get("status") or "")
        if status == "pending" and str(r.get("fire_at", "")) <= now_iso:
            r["status"] = "fired"
            r["fired_at"] = now_iso
            changed = True
            try:
                from core.eventbus.bus import event_bus
                event_bus.publish(
                    "self_wakeup.fired",
                    {"wakeup_id": r.get("wakeup_id"),
                     "reason": str(r.get("reason", ""))[:80]},
                )
            except Exception:
                pass
            out.append(r)
        elif status == "fired" and include_fired_unconsumed:
            out.append(r)
    if changed:
        _save(records)
    return out


def mark_wakeup_consumed(wakeup_id: str) -> dict[str, Any]:
    """Clear a fired wakeup once Jarvis has acted on it."""
    records = _load()
    record = next((r for r in records if r.get("wakeup_id") == wakeup_id), None)
    if record is None:
        return {"status": "error", "error": "wakeup not found"}
    status = str(record.get("status") or "")
    # Kilden kan være ALLEREDE terminal. At kvittere den igen er en no-op,
    # ikke en fejl — og forskellen er hele sagen.
    #
    # `_luk_kilden` i `inbox_state` accepterer «already» som succes og lader
    # den durable afgørelse lukke rækken. Et «error» gør det modsatte: rækken
    # bliver stående `aaben` med `kraever_handling=1`, og så gater posten
    # permanent — og vejen ud går gennem det værktøj gaten blokerer.
    #
    # Målt live 4/10-2026: `inbox_done(wake-558ac30db3)` → «status=consumed,
    # can't consume», mens rækken stod åben og gatede alt `bash`. Samme form
    # efter `cancel_wakeup` på `wake-99ac19041a`: annulleringen lukkede
    # vækningen, ikke dens durable række.
    #
    # `drop` rammes ikke — den kalder ikke kilden, den afgør rækken direkte.
    # Det er derfor `inbox_drop` virkede hvor `inbox_done` nægtede.
    if status in ("consumed", "cancelled"):
        return {"status": "already", "wakeup_id": wakeup_id, "tilstand": status}
    if status not in ("pending", "fired"):
        return {"status": "error", "error": f"wakeup status={status}, can't consume"}
    was_fired = status == "fired"
    record["status"] = "consumed"
    record["consumed_at"] = datetime.now(UTC).isoformat()
    # 12/9-2026: luk den sidste stille kant. Dispatcheren filtrerer på
    # status=='fired', så en FYRET wakeup der kvitteres før næste tick (60 s)
    # er usynlig for den: hverken `dispatched` eller `dispatch_skipped` nåede
    # at blive sat, og recorden stod tavs. Instruktionerne overlevede
    # (awareness bar dem), men sporet manglede. Vi skriver det HER, hvor vi
    # ved at den fyrede ubehandlet — så `list_self_wakeups` kan skelne
    # «kørte» / «afvist» / «nåede aldrig frem».
    if was_fired and not record.get("dispatched") and not record.get("dispatch_skipped"):
        record["consumed_without_dispatch"] = True
        record["consumed_without_dispatch_reason"] = "consumed_before_dispatch_tick"
    _save(records)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("self_wakeup.consumed", {"wakeup_id": wakeup_id})
    except Exception:
        pass
    return {"status": "ok", "wakeup_id": wakeup_id}


def add_wakeup_extra(wakeup_id: str, extra: str) -> dict[str, Any]:
    """Læg en tilføjelse på en booket wakeup — så den følger med i noten.

    Bjørns vane (12/9-2026): han skriver ofte en ekstra besked lige efter en
    tur. Den hører til wakeup'en, ikke kun turen. Vi APPENDER frem for at
    overskrive, så flere tilføjelser samler sig i rækkefølge.

    Virker på både 'pending' og 'fired' — en tilføjelse kan komme efter
    fyre-tidspunktet, men før wakeup'en er kvitteret.
    """
    extra = (extra or "").strip()
    if not extra:
        return {"status": "error", "error": "extra is required"}
    records = _load()
    record = next((r for r in records if r.get("wakeup_id") == wakeup_id), None)
    if record is None:
        return {"status": "error", "error": "wakeup not found"}
    if record.get("status") not in ("pending", "fired"):
        return {
            "status": "error",
            "error": f"wakeup status={record.get('status')}, can't add extra",
        }
    existing = str(record.get("extra") or "").strip()
    merged = f"{existing}\n{extra}".strip() if existing else extra
    record["extra"] = merged[:1000]
    record["extra_updated_at"] = datetime.now(UTC).isoformat()
    _save(records)
    return {"status": "ok", "wakeup_id": wakeup_id, "extra": record["extra"]}


def cancel_wakeup(wakeup_id: str) -> dict[str, Any]:
    """Cancel a pending wakeup before it fires."""
    records = _load()
    record = next((r for r in records if r.get("wakeup_id") == wakeup_id), None)
    if record is None:
        return {"status": "error", "error": "wakeup not found"}
    if record.get("status") != "pending":
        return {"status": "error", "error": f"can't cancel wakeup with status={record.get('status')}"}
    record["status"] = "cancelled"
    _save(records)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("self_wakeup.cancelled", {"wakeup_id": wakeup_id})
    except Exception:
        pass
    return {"status": "ok", "wakeup_id": wakeup_id}


def list_wakeups(*, status: str | None = None, limit: int = 30) -> list[dict[str, Any]]:
    records = _load()
    if status:
        records = [r for r in records if r.get("status") == status]
    records.sort(key=lambda r: str(r.get("scheduled_at", "")), reverse=True)
    return records[:limit]


def cleanup_old_wakeups(
    *,
    consumed_age_hours: int = 168,  # 7 days
    cancelled_age_hours: int = 168,
    stale_fired_age_hours: int = 24,
) -> dict[str, int]:
    """Ryd op i gamle consumed/cancelled/stale-fired wakeups.

    Args:
        consumed_age_hours: remove consumed entries older than this (default 7 dage)
        cancelled_age_hours: remove cancelled entries older than this (default 7 dage)
        stale_fired_age_hours: remove fired-but-never-consumed entries older than this (default 24h)

    Returns:
        {removed, remaining} — antal fjernede og tilbageværende wakeups
    """
    records = _load()
    now = datetime.now(UTC)
    kept: list[dict[str, Any]] = []
    removed = 0

    for r in records:
        status = str(r.get("status") or "")
        if status == "consumed":
            consumed_at = r.get("consumed_at")
            if consumed_at:
                try:
                    age = (now - datetime.fromisoformat(consumed_at)).total_seconds() / 3600
                    if age >= consumed_age_hours:
                        removed += 1
                        continue
                except (ValueError, TypeError):
                    pass
        elif status == "cancelled":
            # Brug scheduled_at som proxy hvis cancelled_at ikke findes
            cancelled_ref = r.get("cancelled_at") or r.get("scheduled_at") or ""
            if cancelled_ref:
                try:
                    age = (now - datetime.fromisoformat(cancelled_ref)).total_seconds() / 3600
                    if age >= cancelled_age_hours:
                        removed += 1
                        continue
                except (ValueError, TypeError):
                    pass
        elif status == "fired" and not r.get("consumed_at"):
            fired_at = r.get("fired_at") or ""
            if fired_at:
                try:
                    age = (now - datetime.fromisoformat(fired_at)).total_seconds() / 3600
                    if age >= stale_fired_age_hours:
                        removed += 1
                        continue
                except (ValueError, TypeError):
                    pass
        kept.append(r)

    _save(kept)
    logger.info("cleanup_old_wakeups: removed=%d, remaining=%d", removed, len(kept))
    return {"removed": removed, "remaining": len(kept)}


def tick_wakeup_cleanup() -> dict[str, int]:
    """Daemon tick — ryd op i gamle wakeups.

    Kører periodisk (default 60 min) for at forhindre wakeup-bloat.
    Returnerer antal fjernede og tilbageværende.
    """
    return cleanup_old_wakeups()


def self_wakeup_section() -> str | None:
    """Awareness section showing fired-but-not-consumed wakeups."""
    fired = due_wakeups(include_fired_unconsumed=True)
    fired = [r for r in fired if str(r.get("status") or "") == "fired"]
    if not fired:
        return None
    lines = [f"⏰ Du planlagde {len(fired)} self-wakeup(s) der nu er klar:"]
    for r in fired[:3]:
        wid = str(r.get("wakeup_id", ""))
        prompt = str(r.get("prompt", ""))[:200]
        reason = str(r.get("reason", ""))
        reason_part = f" ({reason})" if reason else ""
        # 12/9-2026: skeln «dispatchet af sig selv» fra «faldt tilbage til
        # awareness fordi du var aktiv». Uden dette står begge som 'fired',
        # og Jarvis kan ikke se om mekanismen kørte (målt: wake-d07eaea13d
        # fyrede midt i en aktiv tur, uden dispatched-flag, uden forklaring).
        skip_part = ""
        if r.get("dispatch_skipped"):
            skip_part = (
                f" [IKKE dispatchet — {r.get('dispatch_skipped_reason') or 'ukendt'}; "
                "instrukserne står her, følg op selv]"
            )
        lines.append(f"  • {wid}{reason_part}{skip_part}: {prompt}")
        extra = str(r.get("extra") or "").strip()
        if extra:
            lines.append(f"      ↳ tilføjelse: {extra[:300]}")
    lines.append(
        "Når du har handlet på en af dem, brug `mark_wakeup_consumed(wakeup_id)` "
        "så den ikke gentager sig i din awareness."
    )
    # Kaeden skal vaere synlig HER — det er her du beslutter om du booker en ny.
    # Et loft der rammer uden varsel er ikke en hjaelp. Taelles kun op naar den
    # er halvvejs, saa den ikke stoejer i det normale tilfaelde (p90 er 4/time,
    # og normalen topper ved 12 pr. doegn).
    # Ingen try her, med vilje. `current_session_id()` giver "" naar
    # ContextVar'en er vaek, og `_load()` falder tilbage til [] paa en
    # oedelagt fil — begge faldene er paa plads NEDENFOR. En except her kunne
    # aldrig fyre af den grund jeg foerst skrev, og saa var fejlen blevet en
    # vaerdi jeg ikke kunne skelne fra et lovligt svar.
    from core.identity.workspace_context import current_session_id
    _sid = str(current_session_id() or "")
    _n = bookinger_seneste_doegn(_load(), _sid) if _sid else 0
    if _n >= _MAX_PR_SAMTALE_PR_DOEGN // 2:
        lines.append(
            f"⚠️ Du har booket {_n} wakeups i DENNE samtale det seneste døgn "
            f"(loft {_MAX_PR_SAMTALE_PR_DOEGN}). Hver kvitteret vækning der "
            "booker en ny er en kæde, og hvert led skriver i Bjørns chat. "
            "Fandt kontrollen intet nyt, så book ikke en ny — luk den."
        )
    return "\n".join(lines)


# ── Tools ──────────────────────────────────────────────────────


def _exec_schedule_self_wakeup(args: dict[str, Any]) -> dict[str, Any]:
    from core.identity.workspace_context import (
        current_channel,
        current_role,
        current_session_id,
        current_user_display_name,
        current_user_id,
        current_workspace_name,
    )

    svar = schedule_self_wakeup(
        delay_seconds=int(args.get("delay_seconds") or 60),
        prompt=str(args.get("prompt") or ""),
        reason=str(args.get("reason") or ""),
        extra=str(args.get("extra") or ""),
        session_id=current_session_id() or None,
        user_id=current_user_id() or None,
        workspace_name=current_workspace_name() or None,
        user_display_name=current_user_display_name() or None,
        role=current_role() or None,
        context_channel=current_channel() or None,
    )
    # Peak-vaernet (7/10-2026): bookingen gaar igennem, men lander den i
    # myldretiden, staar det i svaret. Tidspunktet laeses fra den GEMTE record —
    # ikke regnet om her — saa varslet ikke kan drifte fra bookingen.
    from core.services.peak_hours import tilfoej_booking_varsel
    return tilfoej_booking_varsel(svar, (svar.get("wakeup") or {}).get("fire_at"))


def _exec_list_self_wakeups(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "wakeups": list_wakeups(
            status=args.get("status"),
            limit=int(args.get("limit") or 30),
        ),
    }


def _exec_cancel_self_wakeup(args: dict[str, Any]) -> dict[str, Any]:
    return cancel_wakeup(str(args.get("wakeup_id") or ""))


def _exec_mark_wakeup_consumed(args: dict[str, Any]) -> dict[str, Any]:
    return mark_wakeup_consumed(str(args.get("wakeup_id") or ""))


def _exec_add_wakeup_extra(args: dict[str, Any]) -> dict[str, Any]:
    return add_wakeup_extra(
        str(args.get("wakeup_id") or ""),
        str(args.get("extra") or ""),
    )


SELF_WAKEUP_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "schedule_self_wakeup",
            "description": (
                "Schedule a self-wakeup: when delay_seconds passes, the prompt "
                "surfaces in your awareness so you can resume that line of "
                "thought. Equivalent to Claude Code's ScheduleWakeup but "
                "persistent across restarts. Use for: 'wait 5 min then check X', "
                "'remind me to ask the user Y in 1 hour'. Bounded to "
                "60-86400 seconds (1 min - 24 hours)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "delay_seconds": {"type": "integer"},
                    "prompt": {"type": "string", "description": "What to resume / do when waking."},
                    "reason": {"type": "string", "description": "Short label for telemetry."},
                    "extra": {
                        "type": "string",
                        "description": (
                            "Optional extra note carried with the wakeup — surfaces "
                            "in awareness and in the dispatched self-directive."
                        ),
                    },
                },
                "required": ["delay_seconds", "prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_self_wakeups",
            "description": "List your queued/fired/consumed self-wakeups. Optional status filter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["pending", "fired", "consumed", "cancelled"]},
                    "limit": {"type": "integer"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_self_wakeup",
            "description": "Cancel a pending wakeup before it fires.",
            "parameters": {
                "type": "object",
                "properties": {"wakeup_id": {"type": "string"}},
                "required": ["wakeup_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mark_wakeup_consumed",
            "description": "Mark a fired wakeup as consumed so it doesn't re-surface in awareness.",
            "parameters": {
                "type": "object",
                "properties": {"wakeup_id": {"type": "string"}},
                "required": ["wakeup_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_wakeup_extra",
            "description": (
                "Append an extra note to a queued or fired wakeup so it carries "
                "into awareness and the dispatched directive. Use when the user "
                "adds something right after a turn that belongs to the wakeup."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "wakeup_id": {"type": "string"},
                    "extra": {"type": "string", "description": "Note to append."},
                },
                "required": ["wakeup_id", "extra"],
            },
        },
    },
]
