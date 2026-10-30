"""Lease and dispatch one explicitly autonomous side task while Jarvis is idle."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_MIN_IDLE_SECONDS = 15 * 60
_DAILY_LIMIT = 2
_BUDGET_KEY = "autonomous_side_task_daily_budget"


def _daily_budget_allows() -> bool:
    """At most two idle side-task starts per local runtime day; fail closed."""
    try:
        from core.runtime.db_core import get_runtime_state_value
        from core.util.timezone import dk_now

        day = dk_now().date().isoformat()
        state = get_runtime_state_value(_BUDGET_KEY, {}) or {}
        count = int(state.get("count") or 0) if str(state.get("day") or "") == day else 0
        return count < _DAILY_LIMIT
    except Exception:  # unreadable accounting must fail closed
        return False


def _note_daily_start(task_id: str) -> None:
    from core.runtime.db_core import get_runtime_state_value, set_runtime_state_value
    from core.util.timezone import dk_now

    day = dk_now().date().isoformat()
    state = get_runtime_state_value(_BUDGET_KEY, {}) or {}
    count = int(state.get("count") or 0) if str(state.get("day") or "") == day else 0
    set_runtime_state_value(_BUDGET_KEY, {
        "day": day, "count": count + 1, "last_task_id": str(task_id or "")[:120],
        "last_started_at": datetime.now(UTC).isoformat(),
    })


def _idle_long_enough() -> bool:
    """Fail closed when recent human activity cannot be measured."""
    try:
        from core.services.assembly_prewarm import _seconds_since_last_user_activity

        age = _seconds_since_last_user_activity()
        return age is not None and age >= _MIN_IDLE_SECONDS
    except Exception:  # unknown activity must fail closed
        return False


def _something_running() -> bool:
    try:
        from core.services.inbox_idle_waker import _noget_koerer

        return bool(_noget_koerer())
    except Exception:  # unknown run state must fail closed
        return True


def _target_session() -> str:
    try:
        from core.identity.owner_resolver import (
            resolve_owner_app_session,
            session_is_external_channel,
        )

        session_id = str(resolve_owner_app_session() or "").strip()
        if not session_id or session_is_external_channel(session_id):
            return ""
        return session_id
    except Exception:  # no verified owner session means no dispatch
        return ""


def _session_for_task(task: dict[str, Any]) -> str:
    """Hvilken SAMTALE hører denne opgave til?

    MÅLT 25/10-2026: her stod kun `_target_session()`, og den blev kaldt FØR
    opgaven var claimet. Dispatcheren kunne derfor per konstruktion ikke svare
    på «hvor hører DETTE arbejde til» — kun «hvad er ejerens app-samtale».
    Målt i drift pegede svaret på Bjørns igangværende samtale, så et autonomt
    run ville skrive sig ind midt i en snak han sad i.

    Rækkefølgen er den SAMME som de tre andre vække-veje bruger
    (`inbox_idle_waker._maal_session`, `scheduled_tasks`, `wakeup_dispatcher`)
    — ikke en kopi af den. To definitioner af «hvor skal dette lande» driver
    fra hinanden, og så bliver den ene stille virkningsløs:

      1. Opgavens egen samtale (`arbejds_session`, ellers `session_id`) — den
         mest præcise adresse der findes: opgaven blev flagget i en bestemt
         samtale, og en ekstern kanal afvises af guarden.
      2. Ejerens app-samtale (`_target_session`, som allerede springer
         Discord/Telegram over).
      3. Tom streng ⇒ INGEN start. Et run uden en samtale er den silo vi
         fjerner; opgaven venter hellere i køen til næste runde.
    """
    from core.identity.owner_resolver import (
        resolve_owner_target_session,
        session_is_external_channel,
    )
    from core.services.wakeup_dispatcher import pick_wakeup_run_target

    egen = str(task.get("arbejds_session") or task.get("session_id") or "").strip()
    # `flag()` skriver `session_id="_default"` når ingen gives (side_tasks.py:325).
    # Det er en PLADSHOLDER, ikke en adresse — og der findes ingen session med
    # det id (målt 25/10-2026: 0 rækker i `chat_sessions`). Uden dette led ville
    # et run lande i en samtale der ikke eksisterer, hvilket er den samme silo
    # som et tomt svar. Huset kender allerede konventionen: `side_tasks.py:252`
    # behandler `_default` som «ingen session».
    if egen in {"_default", "default", "legacy_unscoped"}:
        egen = ""
    valgt = pick_wakeup_run_target(
        channel="app",
        record_session=egen,
        app_resolver=_target_session,
        owner_resolver=resolve_owner_target_session,
        is_external=session_is_external_channel,
    ) or ""
    if not valgt:
        return ""

    # EN AUTONOM KOERSEL MA A IKKE LAND I EN SAMTALE DER LEVER (28/10-2026)
    #
    # Maalt 28/10 kl. 12:05 og 12:17: to opgaver med mode=inspect landede i
    # `chat-c05e28bb...` — Bjorns igangvaerende samtale — fordi dette var det
    # ENESTE led der ikke spurgte om nogen talte i den. De tre andre
    # vae kke-veje (`inbox_idle_waker`, `scheduled_tasks`, `dispatch_due_wakeups`)
    # spoerger allerede; reglen fandtes, den blev blot ikke brugt her.
    #
    # Hvorfor ikke et `kind`-forbud (den oprindelige opgaves forslag): maalt i
    # `chat_sessions` findes kun to vaerdier — 'chat' (651) og 'code' (55) — og
    # BEGGE er samtaler Bjorn sidder i (titlerne i kind='code' er «yo»,
    # «godmorgen j..»). Et kind-forbud ville derfor afvise ALT og goere
    # dispatchen virkningsloes. Det er samme faelde som «fald mod det der
    # standser, ikke mod det der fortsaetter» — her: en regel der ser rigtig ud
    # og slukker funktionen.
    #
    # I stedet genbruges de to karantaener der allerede er maalt og begrundet
    # i `wakeup_dispatcher`: en fersk tur blokerer, og en fersk besked fra
    # hver rolle blokerer. Posten gaar ikke tabt — den bliver i koeen til en
    # senere runde (samme kontrakt som `_target_session`'s tomme svar).
    from core.services.wakeup_dispatcher import (
        _active_turn_blocks,
        _bruger_skrev_for_nylig,
        _jarvis_skrev_for_nylig,
    )

    grund = _active_turn_blocks(valgt)
    if grund:
        logger.info(
            "autonomous_side_task: session %s er optaget (%s) — opgaven venter",
            valgt[:28], grund,
        )
        return ""
    if _bruger_skrev_for_nylig(valgt) or _jarvis_skrev_for_nylig(valgt):
        logger.info(
            "autonomous_side_task: session %s er i karantaene — opgaven venter",
            valgt[:28],
        )
        return ""
    return valgt


def _start(text: str, *, session_id: str, origin: str, task_id: str,
           max_tool_calls: int, max_seconds: float) -> bool:
    from core.services.background_start_reservation import reserve_background_start
    from core.services.visible_autonomous_run import start_autonomous_run

    with reserve_background_start(session_id) as reservation:
        if not reservation.acquired:
            logger.info(
                "autonomous_side_task: start afvist for %s: %s",
                session_id[:28], reservation.reason,
            )
            return False
        return bool(start_autonomous_run(
            text, session_id=session_id, origin=origin, task_id=task_id,
            max_tool_calls=max_tool_calls, max_seconds=max_seconds,
        ))


def _directive(task: dict[str, Any]) -> str:
    task_id = str(task.get("side_task_id") or "")
    mode = str(task.get("autonomy_mode") or "inspect")
    return (
        f"[AUTONOM SIDE-OPGAVE — {task_id}]\n"
        f"Titel: {task.get('title') or '(uden titel)'}\n"
        f"Opgave: {task.get('prompt') or '(uden beskrivelse)'}\n\n"
        f"RAMME: mode={mode}; højst {int(task.get('max_minutes') or 20)} minutter; "
        f"højst {int(task.get('max_tool_calls') or 12)} værktøjskald. Brug kun de "
        "værktøjer denne origin allerede har fået. Forsøg aldrig at udvide tilladelserne.\n"
        "STOPREGLER:\n"
        "- Et isoleret fund registreres med flag_side_task og arbejdet fortsætter kun, hvis det er sikkert.\n"
        "- En blokering stopper denne opgave; rapportér årsag og bevar evidensen.\n"
        "- En kritisk/integritetstruende fejl stopper straks uden flere mutationer.\n"
        f"- Er opgaven verificeret løst, luk den med dismiss_side_task(side_task_id=\"{task_id}\", "
        "decision=\"completed\", bevis=\"<konkret bevis>\").\n"
        "- Kan den ikke løses inden for rammen, lad den stå åben og forklar præcist hvorfor."
    )


def _report_exhausted() -> None:
    from core.services import side_tasks
    from core.services.background_attention import report_background_outcome

    for task in side_tasks.unreported_exhausted_autonomy():
        task_id = str(task.get("side_task_id") or "")
        result = report_background_outcome(
            source_kind="side-task", source_id=task_id,
            status="blocked", severity="high",
            summary=(
                f"Side-opgaven {task.get('title') or task_id} er stadig åben "
                f"efter {int(task.get('autonomy_attempts') or 0)} autonome forsøg."
            ),
            suggested_next_step="Gennemgå evidensen og vælg: ny ramme, manuel løsning eller afvisning.",
            requires_attention=True, safe_to_continue=False,
            session_id=str(task.get("arbejds_session") or task.get("session_id") or ""),
        )
        if result.get("inbox") == "ok":
            side_tasks.mark_autonomy_exhausted_reported(task_id)


def dispatch_one() -> dict[str, Any]:
    """Start at most one task.  Every uncertain precondition means no start."""
    try:
        _report_exhausted()
    except Exception:  # reporting is retried on the next scheduler tick
        logger.warning("autonomous_side_task: udmattede forsøg kunne ikke rapporteres", exc_info=True)
    if not _idle_long_enough():
        return {"status": "ok", "started": 0, "reason": "not-idle"}
    if _something_running():
        return {"status": "ok", "started": 0, "reason": "active-run"}
    if not _daily_budget_allows():
        return {"status": "ok", "started": 0, "reason": "daily-budget"}

    from core.services import side_tasks

    worker_id = f"idle-side-task-{uuid4().hex[:10]}"
    # Longest permitted task is 60 minutes; the extra ten prevents the lease
    # from expiring while that legitimate run is still winding down.
    task = side_tasks.claim_autonomous(worker_id=worker_id, lease_minutes=70)
    if task is None:
        return {"status": "ok", "started": 0, "reason": "no-eligible-task"}

    task_id = str(task.get("side_task_id") or "")
    mode = str(task.get("autonomy_mode") or "inspect")

    # 25/10-2026: sessionen bestemmes EFTER claim, aldrig før. Før stod
    # `_target_session()` øverst, før vi vidste hvilken opgave der var tale om —
    # så svaret var «ejerens aktive samtale» uanset hvilket arbejde der skulle
    # udføres, og et autonomt run kunne lande midt i en igangværende snak.
    # Nu bærer opgaven sin egen adresse ind i valget. Er der ingen samtale at
    # lande i, frigives leasen og opgaven bliver i køen — et run uden en
    # samtale er præcis den silo vække-vejene findes for at undgå.
    session_id = _session_for_task(task)
    if not session_id:
        side_tasks.release_autonomous_claim(
            task_id, worker_id=worker_id, reason="ingen samtale at lande i",
        )
        return {"status": "ok", "started": 0, "reason": "no-session"}

    try:
        started = _start(
            _directive(task), session_id=session_id,
            origin=f"side-task-{mode}", task_id=task_id,
            max_tool_calls=int(task.get("max_tool_calls") or 12),
            max_seconds=float(int(task.get("max_minutes") or 20) * 60),
        )
    except Exception as exc:  # noqa: BLE001
        side_tasks.release_autonomous_claim(
            task_id, worker_id=worker_id, reason=f"startfejl: {type(exc).__name__}",
        )
        logger.warning("autonomous_side_task: start failed for %s: %s", task_id, exc)
        return {"status": "ok", "started": 0, "reason": "start-error"}
    if not started:
        side_tasks.release_autonomous_claim(
            task_id, worker_id=worker_id, reason="starter afviste runnet",
        )
        return {"status": "ok", "started": 0, "reason": "start-rejected"}

    side_tasks.attach_autonomous_session(
        task_id, worker_id=worker_id, session_id=session_id,
    )
    try:
        _note_daily_start(task_id)
    except Exception:  # the already-started run remains authoritative
        # The run already exists; a failed accounting write must be visible,
        # but cannot un-start it.  Fail closed on the next poll via the reader.
        logger.warning("autonomous_side_task: kunne ikke bogfoere dagsbudget", exc_info=True)
    return {"status": "ok", "started": 1, "side_task_id": task_id, "mode": mode}


__all__ = ["dispatch_one"]
