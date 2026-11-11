"""Visible-run control state — udskilt fra visible_runs.py (Boy Scout).

Tightly coupled cluster der håndterer visible-run lifecycle state via
runtime_state-tabellen. Cross-worker sikker (state lever i DB).

Indhold:
  - Key prefixes/constants
  - Run-control state get/set/cancel
  - Active-run state tracker
  - Steer queue (mid-flight intervention via POST /chat/runs/{id}/steer)
  - Approval state get/set

Re-eksporteres fra visible_runs.py så eksisterende
visible_runs._set_visible_approval_state-monkeypatches i tests virker.
"""
from __future__ import annotations
from datetime import UTC, datetime

from core.runtime.db import get_runtime_state_value, set_runtime_state_value


_VISIBLE_RUN_CONTROL_PREFIX = "visible_runs.control."
_VISIBLE_RUN_ACTIVE_KEY = "visible_runs.active_run"
_VISIBLE_RUN_APPROVAL_PREFIX = "visible_runs.approval."
# Fase 1 (jarvis-code↔v2 forening): pending KLIENT-tool-delegering. Når serverens
# loop rammer et execution=="client"-tool emitteres det som tool_use og loopet
# venter (poll) her, indtil klienten POSTer resultatet via /chat/runs/{id}/tool-result.
# Spejler approval-state-mønstret: pending → resolved|expired, cross-worker via DB.
_VISIBLE_RUN_CLIENT_TOOL_PREFIX = "visible_runs.client_tool."


def _visible_run_control_key(run_id: str) -> str:
    return f"{_VISIBLE_RUN_CONTROL_PREFIX}{run_id}"


def _visible_run_approval_key(approval_id: str) -> str:
    return f"{_VISIBLE_RUN_APPROVAL_PREFIX}{approval_id}"


def _set_visible_run_control(run_id: str, payload: dict[str, object]) -> None:
    set_runtime_state_value(_visible_run_control_key(run_id), payload)


def _get_visible_run_control(run_id: str) -> dict[str, object]:
    payload = get_runtime_state_value(_visible_run_control_key(run_id), default={})
    return payload if isinstance(payload, dict) else {}


def _set_active_visible_run(payload: dict[str, object] | None) -> None:
    set_runtime_state_value(_VISIBLE_RUN_ACTIVE_KEY, payload or {})


def _get_active_visible_run_state() -> dict[str, object]:
    payload = get_runtime_state_value(_VISIBLE_RUN_ACTIVE_KEY, default={})
    return payload if isinstance(payload, dict) else {}


# ── TUREN ER LUKKET (11/11-2026) ────────────────────────────────────────────
#
# Bjørn: «en tur skal afsluttes helt før et wakeup kan begyndes».
#
# Vagten kunne ikke afgøre det. Den læste aktiv-slot'en, som
# `unregister_visible_run` rydder SYKRONT i `finally` — altså før det sidste
# frame er nået klienten og før `mark_completed` (der kører i en daemon-tråd)
# har fjernet posten fra journalen. Og den gav op efter 120 sekunder, så et run
# der ventede på et godkendelses-kort blev regnet for dødt.
#
# Resultatet var det Bjørn så: en wakeup startede i det vindue, dens frames
# landede i den forrige turs besked, og der stod de til appen blev genstartet.
#
# Nu skrives en KVITTERING pr. session i det øjeblik turen er helt lukket.
# Vagten spørger «er der en åben tur i denne session?» — et faktum, ikke et
# tidsvindue. Nøglen er pr. session, så to samtaler ikke forveksles.
_TURN_CLOSED_PREFIX = "visible_runs.turn_closed."


def _turn_closed_key(session_id: str) -> str:
    return f"{_TURN_CLOSED_PREFIX}{session_id}"


def mark_turn_closed(session_id: str, run_id: str = "") -> None:
    """Kvittér at turen i denne session er HELT afsluttet.

    Kaldes fra `finally` i `_stream_visible_run` — det ene sted hver kørsel
    passerer, uanset hvordan den endte. Self-safe: en manglende kvittering må
    aldrig vælte turen; vagten falder så tilbage til de gamle regler.
    """
    sid = str(session_id or "").strip()
    if not sid:
        return
    try:
        set_runtime_state_value(
            _turn_closed_key(sid),
            {
                "closed_at": datetime.now(UTC).isoformat(),
                "run_id": str(run_id or ""),
            },
        )
    except Exception:  # self-safe: en manglende kvittering må ikke vælte turen
        pass


def turn_is_open(session_id: str) -> bool:
    """Kører der stadig en tur i denne session? Spørger journalen, ikke et ur.

    Rækkefølgen er med vilje: den DELTE journal først (den ser begge processer),
    derefter aktiv-slot'en. Er ingen af dem i stand til at svare, siges «åben» —
    et wakeup der venter er billigt, et der lander oveni en tur er ikke.
    """
    sid = str(session_id or "").strip()
    if not sid:
        return False
    # KVITTERINGEN FØRST (11/11-2026). `finally` i `_stream_visible_run` skriver
    # «turen er lukket» naar kørslen er passeret — ogsaa naar det sidste frame
    # lige er sendt og `mark_completed` endnu ikke har ryddet den delte journal.
    # Uden dette opslag svarede de to andre kilder «aaben» i det vindue, og en
    # wakeup landede oveni den tur Bjørn lige havde faaet svar paa.
    try:
        from core.services.visible_runs_sections.run_control_state import (
            turn_closed_at,
        )

        if turn_closed_at(sid):
            return False
    except Exception:  # self-safe: næste kilde må svare i stedet
        pass
    try:
        from core.services import in_flight_runs as ifr

        if ifr.levende_koersler(session_id=sid, max_alder_s=0):
            return True
    except Exception:  # self-safe: næste kilde må svare i stedet
        pass
    try:
        from core.services import run_event_log as rel

        if rel.active_run_for_session(sid):
            return True
    except Exception:  # self-safe: uden svar gælder «ikke åben»
        pass
    return False


def turn_closed_at(session_id: str) -> str:
    """Hvornår blev turen i denne session kvitteret HELT lukket? ``""`` = ukendt.

    Læsesiden af `mark_turn_closed`. Returnerer tidsstemplet naar kvitteringen
    findes, ellers tom streng — saa kalderen kan skelne «lukket» fra «ved det
    ikke» og falde tilbage til de andre kilder i stedet for at gætte.
    """
    sid = str(session_id or "").strip()
    if not sid:
        return ""
    try:
        payload = get_runtime_state_value(_turn_closed_key(sid), default={})
    except Exception:  # self-safe: uden svar gælder «ved det ikke»
        return ""
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("closed_at") or "")


def relay_owns_open_run(run_id: str) -> bool:
    """Whether the detached relay still owns this run, independent of age."""
    try:
        from core.services import run_event_log
        return run_event_log.is_open(run_id)
    except Exception:
        return False


def touch_active_visible_run(run_id: str) -> None:
    """Heartbeat: opdatér last_activity_at i den DELTE active-run state (DB),
    så CROSS-PROCES liveness virker. /chat/active-runs (jarvis-api) kan ikke se
    et autonomt runs in-memory controller (det lever i jarvis-runtime), men kan
    se DB-heartbeat'en. Et levende run kalder denne hvert par sekunder; et dødt
    run holder op → freshness-vinduet udløber → klienten rydder hängende UI.

    TO NØGLER, IKKE ÉN (29/10-2026). Aktiv-slot'en er ÉN plads i hele huset.
    Starter en kort tur mens jeg er midt i min, tager den pladsen; naar den korte
    tur er færdig, rydder `unregister_visible_run` pladsen — og saa ser
    `is_visible_run_alive(mig)` en TOM plads og dømmer mig DØD, mens jeg stadig
    kører. Maalt to gange samme dag: den udskudte genstart ventede 5-8 sekunder
    (én poll + margin) i stedet for 75, fyrede midt i turen og dræbte svaret
    (14:51:40 og 14:56:06, begge med signaturen «kort tur startede og sluttede
    inde i den lange»).

    Per-run-nøglen `visible_runs.control.<run_id>` kan ikke stjæles, så den
    skrives ALTID. Aktiv-slot'en skrives kun naar den stadig er min — den maa
    ikke genoplives for en afløst tur.
    """
    if not run_id:
        return
    nu = datetime.now(UTC).isoformat()
    kontrol = _get_visible_run_control(run_id)
    if kontrol:
        kontrol["last_activity_at"] = nu
        _set_visible_run_control(run_id, kontrol)
    state = _get_active_visible_run_state()
    if str(state.get("run_id") or "") != str(run_id):
        return
    state["last_activity_at"] = nu
    set_runtime_state_value(_VISIBLE_RUN_ACTIVE_KEY, state)


def _visible_run_cancelled(run_id: str) -> bool:
    return bool(_get_visible_run_control(run_id).get("cancelled"))


def _mark_visible_run_cancelled(run_id: str, *, cancelled: bool = True) -> None:
    state = _get_visible_run_control(run_id)
    if not state:
        return
    state["cancelled"] = cancelled
    state["updated_at"] = datetime.now(UTC).isoformat()
    _set_visible_run_control(run_id, state)


def append_visible_run_steer(run_id: str, content: str) -> bool:
    """Append a mid-flight 'steer' message that the agentic loop will pick
    up between rounds. Cross-worker safe (state lives in DB).

    Used by POST /chat/runs/{run_id}/steer so the user can interject mid
    tool-loop without cancelling — Jarvis sees the steer at the next round
    boundary and either redirects, acknowledges, or stops."""
    state = _get_visible_run_control(run_id)
    if not state:
        return False
    queue = state.get("steers")
    if not isinstance(queue, list):
        queue = []
    queue.append({
        "content": str(content or "").strip(),
        "at": datetime.now(UTC).isoformat(),
        "consumed": False,
    })
    state["steers"] = queue
    state["updated_at"] = datetime.now(UTC).isoformat()
    _set_visible_run_control(run_id, state)
    return True


def consume_visible_run_steers(run_id: str) -> list[dict[str, object]]:
    """Pop unread steers for this run. Marks them consumed in shared state
    so they aren't re-consumed if the loop re-checks."""
    state = _get_visible_run_control(run_id)
    if not state:
        return []
    queue = state.get("steers")
    if not isinstance(queue, list):
        return []
    fresh = [s for s in queue if isinstance(s, dict) and not s.get("consumed")]
    if not fresh:
        return []
    for s in queue:
        if isinstance(s, dict) and not s.get("consumed"):
            s["consumed"] = True
    state["steers"] = queue
    state["updated_at"] = datetime.now(UTC).isoformat()
    _set_visible_run_control(run_id, state)
    return fresh


def _set_visible_approval_state(approval_id: str, payload: dict[str, object]) -> None:
    set_runtime_state_value(_visible_run_approval_key(approval_id), payload)


def _get_visible_approval_state(approval_id: str) -> dict[str, object]:
    payload = get_runtime_state_value(_visible_run_approval_key(approval_id), default={})
    return payload if isinstance(payload, dict) else {}


# ── Fase 1: klient-tool-delegering state (spejler approval-state) ─────────────


def _visible_run_client_tool_key(call_id: str) -> str:
    return f"{_VISIBLE_RUN_CLIENT_TOOL_PREFIX}{call_id}"


def _set_visible_client_tool_state(call_id: str, payload: dict[str, object]) -> None:
    """Sæt state for en delegeret klient-tool (cross-worker via DB)."""
    set_runtime_state_value(_visible_run_client_tool_key(call_id), payload)


def _get_visible_client_tool_state(call_id: str) -> dict[str, object]:
    payload = get_runtime_state_value(_visible_run_client_tool_key(call_id), default={})
    return payload if isinstance(payload, dict) else {}


def resolve_visible_client_tool(call_id: str, result_text: str) -> bool:
    """Klienten leverer resultatet af en delegeret tool. Flip pending → resolved
    med result_text, som loopet poller efter. False hvis call_id er ukendt eller
    ikke længere pending (idempotent — dobbelt-post skader ikke). Kaldes af
    POST /chat/runs/{run_id}/tool-result."""
    state = _get_visible_client_tool_state(call_id)
    if not state or str(state.get("status") or "") != "pending":
        return False
    state["status"] = "resolved"
    state["result_text"] = str(result_text or "")
    state["resolved_at"] = datetime.now(UTC).isoformat()
    _set_visible_client_tool_state(call_id, state)
    return True
