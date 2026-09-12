"""JarvisX process-supervisor + trading + operator-wakeup route group.

Managed background process list/log/stop/remove/spawn, read-only trading
dashboard state, and the operator-wakeup fired hook. Extracted from
routes/jarvisx.py.

Behavior-preserving: pure code movement, no logic changes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from core.runtime.jarvisx_auth import require_owner
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from apps.api.jarvis_api.routes.jarvisx_common import _require_owner, logger

router = APIRouter(prefix="/api", tags=["jarvisx"])


# ── Process supervisor surface ────────────────────────────────────
# Backs the JarvisX bottom-drawer terminal panel: list managed
# background processes Jarvis has spawned, tail their logs, stop them.
# Only `owner` can stop/remove — members observe.


@router.get("/processes")
def list_managed_processes(include_stopped: bool = Query(default=True)) -> dict[str, Any]:
    """List processes Jarvis has spawned via the process_supervisor."""
    from core.services.process_supervisor import list_processes
    return list_processes(include_stopped=include_stopped)


@router.get("/processes/{name}/log")
def tail_managed_process_log(
    name: str,
    lines: int = Query(default=200, ge=1, le=2000),
) -> dict[str, Any]:
    """Return the tail of a managed process's combined stdout/stderr log.

    Used by the JarvisX terminal drawer for polling-based live tail.
    """
    from core.services.process_supervisor import tail_process_log
    out = tail_process_log(name, lines=lines)
    if out.get("status") == "error":
        raise HTTPException(status_code=404, detail=out.get("error") or "log unavailable")
    return out


@router.get("/jobs")
def list_background_jobs(include_done: bool = Query(default=False)) -> dict[str, Any]:
    """Alle kørende baggrundsopgaver — supervisor OG operatørens egne shells.

    To kilder, ét svar. Et panel der kun viste den ene ville være sandt om sin
    form og tavst om sit indhold: man ville tro der ikke kørte noget, mens der
    gjorde.

    `bridge_ok=false` betyder at vi ikke VED hvad der kører på operatørens
    maskine — ikke at der ingenting kører. De to er stik modsat, og klienten
    skal kunne sige forskel.
    """
    from core.identity.workspace_context import current_user_id
    from core.services.background_jobs import liste
    uid = current_user_id() or ""
    return liste(uid=uid, exec_fn=_operator_exec_for_jobs, kun_aktive=not include_done)


def _operator_exec_for_jobs(navn: str, args: dict[str, Any]) -> dict[str, Any]:
    """Bro-kald til operatørens maskine. Adskilt, så testen kan erstatte den."""
    from apps.api.jarvis_api.routes.chat import _operator_exec
    return _operator_exec(navn, args)


@router.post("/jobs/{kilde}/{job_id}/pause")
def pause_background_job(kilde: str, job_id: str) -> dict[str, Any]:
    """Sæt en opgave på pause. Ejer-kun."""
    _require_owner()
    return _signal_job(kilde, job_id, "pause")


@router.post("/jobs/{kilde}/{job_id}/resume")
def resume_background_job(kilde: str, job_id: str) -> dict[str, Any]:
    """Kør videre hvor den slap. Ejer-kun."""
    _require_owner()
    return _signal_job(kilde, job_id, "resume")


@router.post("/jobs/{kilde}/{job_id}/stop")
def stop_background_job(kilde: str, job_id: str) -> dict[str, Any]:
    """Stop en opgave for altid. Ejer-kun."""
    _require_owner()
    return _signal_job(kilde, job_id, "stop")


_SIGNALER = {"pause": "STOP", "resume": "CONT", "stop": "TERM"}


def _signal_job(kilde: str, job_id: str, handling: str) -> dict[str, Any]:
    """Én vej for begge kilder — de signaleres bare ikke samme sted.

    Supervisoren har sine egne funktioner med et værn mod at signalere
    serverens EGEN proces-gruppe. Operatørens shells ligger på en anden
    maskine, så de går over broen — og `shell_id` valideres mod mønstret, for
    et id er en del af en kommandolinje derovre.
    """
    if handling not in _SIGNALER:
        raise HTTPException(status_code=400, detail="ukendt handling")
    if kilde == "supervisor":
        from core.services.process_supervisor import (
            pause_process, resume_process, stop_process,
        )
        fn = {"pause": pause_process, "resume": resume_process, "stop": stop_process}[handling]
        out = fn(job_id)
        if out.get("status") == "error":
            raise HTTPException(status_code=400, detail=out.get("error") or "handling fejlede")
        return out
    if kilde == "operator":
        import re
        # SAMME moenster som operator_background._valid. Uden det kunne et id
        # smugle sti- eller kommando-fragmenter ind i en kommandolinje der
        # koerer paa Bjoerns maskine.
        if not re.fullmatch(r"bg_[0-9a-f]{12}", job_id):
            raise HTTPException(status_code=400, detail="ugyldigt job-id")
        from core.identity.workspace_context import current_user_id
        uid = current_user_id() or ""
        sig = _SIGNALER[handling]
        cmd = f'pid=$(cat /tmp/jarvis-bg/{job_id}.pid 2>/dev/null); [ -n "$pid" ] && kill -{sig} "$pid" && echo ok'
        res = _operator_exec_for_jobs("operator_bash", {"command": cmd, "_user_id": uid})
        if res.get("status") != "ok":
            raise HTTPException(status_code=502, detail="broen svarede ikke")
        if "ok" not in str((res.get("result") or {}).get("stdout") or ""):
            raise HTTPException(status_code=400, detail="processen svarede ikke — er den allerede slut?")
        return {"status": "ok"}
    raise HTTPException(status_code=400, detail="ukendt kilde")


@router.post("/processes/{name}/stop")
def stop_managed_process(name: str, grace: int = Query(default=5, ge=0, le=60)) -> dict[str, Any]:
    """SIGTERM (then SIGKILL after grace) a managed process. Owner-only."""
    _require_owner()
    from core.services.process_supervisor import stop_process
    out = stop_process(name, grace=grace)
    if out.get("status") == "error":
        raise HTTPException(status_code=400, detail=out.get("error") or "stop failed")
    return out


@router.delete("/processes/{name}")
def remove_managed_process(name: str) -> dict[str, Any]:
    """Remove a stopped process from the registry. Owner-only.

    Refuses if the process is still alive — caller must stop first.
    """
    _require_owner()
    from core.services.process_supervisor import remove_process
    out = remove_process(name)
    if out.get("status") == "error":
        raise HTTPException(status_code=400, detail=out.get("error") or "remove failed")
    return out


# ── Process spawn (owner-only) ────────────────────────────────────
# Lets the JarvisX TaskBar trigger predefined commands via the
# process_supervisor. Read/list/stop already public above.


class _SpawnPayload(BaseModel):
    name: str
    command: str
    cwd: str | None = None
    replace_if_running: bool = True


@router.post("/processes")
def spawn_managed_process(payload: _SpawnPayload) -> dict[str, Any]:
    """Spawn a managed background process. Owner-only.

    Wraps process_supervisor.spawn_process. Caller-supplied cwd is
    used verbatim; the supervisor itself handles env, log routing,
    and the reaper thread.
    """
    _require_owner()
    from core.services.process_supervisor import spawn_process
    out = spawn_process(
        name=payload.name,
        command=payload.command,
        cwd=payload.cwd,
        replace_if_running=payload.replace_if_running,
    )
    if out.get("status") == "error":
        raise HTTPException(status_code=400, detail=out.get("error") or "spawn failed")
    return out


# ── Trading dashboard (read-only) ─────────────────────────────────
# Read-only window into the grid bot's state. Jarvis writes the
# state file from his trading code at his own pace; this endpoint
# just exposes whatever's there to the JarvisX TradingView.
#
# Contract: ~/.jarvis-v2/state/trading_state.json
#
#   {
#     "status": "inactive" | "active" | "paused" | "stopped" | "error",
#     "mode": "paper" | "simulation" | "testnet" | "live",
#     "symbol": "BTCUSDT",
#     "config": {
#       "grid_levels": int, "grid_spacing_pct": float,
#       "order_size_usdt": float, "stop_loss_pct": float
#     },
#     "capital": {
#       "usdt": float, "asset": float, "asset_symbol": "BTC",
#       "total_value_usdt": float, "starting_value_usdt": float
#     },
#     "pnl": {
#       "realized_today": float, "realized_total": float,
#       "unrealized": float, "fees_today": float, "fees_total": float
#     },
#     "drawdown": {
#       "current_pct": float, "max_pct_today": float, "cap_pct": float
#     },
#     "trades_today": int,
#     "open_orders": [{"id", "side", "price", "quantity", "placed_at"}],
#     "recent_trades": [{"type", "price", "qty", "profit_usdt?", "timestamp"}],
#     "last_price": float,
#     "last_updated": ISO timestamp,
#     "last_error": str?  # set when status == 'error'
#   }
#
# When the file doesn't exist or is unparsable, we return a synthetic
# "inactive" record so the UI has something to render. No 500s.


@router.get("/trading/state", dependencies=[Depends(require_owner)])
def trading_state() -> dict[str, Any]:
    """Read the current trading-bot state. Read-only.

    Public read (no _require_owner) on the assumption that the running
    bot's PnL is part of what JarvisX members may want to see — same
    privacy posture as MoodPill / PresencePill. If you want this gated,
    flip the call site.
    """
    import json as _json
    from core.runtime.config import STATE_DIR
    state_file = Path(STATE_DIR) / "trading_state.json"
    if not state_file.is_file():
        return _trading_inactive_default("no state file written yet")
    try:
        raw = state_file.read_text(encoding="utf-8")
        data = _json.loads(raw)
    except _json.JSONDecodeError as exc:
        return _trading_inactive_default(f"state file malformed: {exc}")
    except Exception as exc:
        return _trading_inactive_default(f"state read failed: {exc}")
    if not isinstance(data, dict):
        return _trading_inactive_default("state file is not a dict")
    # Don't validate the full schema — the bot's contract may evolve.
    # The UI tolerates missing fields. Just stamp last_seen for the UI
    # so it can show "data is N seconds old".
    try:
        mtime = state_file.stat().st_mtime
        data["_state_file_mtime"] = mtime
    except Exception:
        pass
    return data


def _trading_inactive_default(reason: str) -> dict[str, Any]:
    """Synthetic 'inactive' state so UI always has something to render."""
    return {
        "status": "inactive",
        "mode": "paper",
        "symbol": "",
        "config": {},
        "capital": {
            "usdt": 0.0, "asset": 0.0, "asset_symbol": "",
            "total_value_usdt": 0.0, "starting_value_usdt": 0.0,
        },
        "pnl": {
            "realized_today": 0.0, "realized_total": 0.0,
            "unrealized": 0.0, "fees_today": 0.0, "fees_total": 0.0,
        },
        "drawdown": {"current_pct": 0.0, "max_pct_today": 0.0, "cap_pct": 5.0},
        "trades_today": 0,
        "open_orders": [],
        "recent_trades": [],
        "last_price": 0.0,
        "last_updated": None,
        "_inactive_reason": reason,
    }


# Rate-guard for operator-wakeup re-engagements: cost-backstop, men IKKE en hård
# daglig cap der dræber funktionen TAVST (Bjørn ramte 12/dag under test og
# "ingenting skete" — wakeup'en fyrede men intet run startede). Rullende time.
_OP_WAKEUP_TIMES: list[float] = []
_OP_WAKEUP_MAX_PER_HOUR = 30


@router.post("/operator/wakeup-fired")
def operator_wakeup_fired(payload: dict) -> dict:
    """Hit af jarvis-desk når en operator_wakeup-timer fyrer.

    2026-06-13 (v2): starter nu STRAKS et autonomt run i samtalen i stedet for
    at gå via self_wakeup (som havde 60s minimum-delay OG en hård 12/dag-cap der
    dræbte funktionen tavst). Binder til desk-sessionen; guarder mod Discord-leak.
    Rate-guard = cost-backstop (max N/rullende time), ikke en daglig dødsdom.
    """
    import time as _time
    wid = str(payload.get("wakeup_id") or "")
    title = (str(payload.get("title") or ""))[:80]
    message = (str(payload.get("message") or ""))[:200]
    sess = str(payload.get("session_id") or "").strip() or None
    try:
        logger.warning(
            "operator_wakeup_fired: wakeup_id=%s session=%s title=%r",
            wid, sess, title,
        )
    except Exception:
        pass

    re_engaged = False
    skipped = ""
    try:
        from core.identity.owner_resolver import (
            resolve_owner_app_session,
            session_is_external_channel,
        )
        from core.services.visible_runs import start_autonomous_run
        now = _time.monotonic()
        _OP_WAKEUP_TIMES[:] = [t for t in _OP_WAKEUP_TIMES if now - t < 3600]
        if len(_OP_WAKEUP_TIMES) >= _OP_WAKEUP_MAX_PER_HOUR:
            skipped = f"rate-limit ({_OP_WAKEUP_MAX_PER_HOUR}/time) nået"
        else:
            # GUARD: aldrig Discord. Brug desk-sessionen hvis app/ikke-ekstern,
            # ellers app-resolveren (springer Discord/Telegram over).
            target = sess if (sess and not session_is_external_channel(sess)) \
                else (resolve_owner_app_session() or None)
            _prompt = (
                f"[OPERATOR-WAKEUP FYREDE — wakeup_id={wid}]\n"
                f"Du planlagde denne wakeup: {title}."
                + (f" Din besked: {message}." if message else "")
                + "\nGenengager kort med Bjørn i DENNE samtale NU — skriv "
                "beskeden / følg op. Når du er færdig er turen slut."
            )
            # follow MIDLERTIDIGT FRA (2026-06-13): translate_to_v2-wrapping i
            # run-tråden brækkede livscyklussen (pending ping-task + manglende
            # unregister → active-state hang → liveness/bgActive hang). Tilbage
            # til ren drain (besked "dumpes" ind, men STABILT). Follow-streaming
            # genoptages med translate-i-endpoint-design — se memory
            # project_autonomous_run_followstream.
            start_autonomous_run(_prompt, session_id=target)
            _OP_WAKEUP_TIMES.append(now)
            re_engaged = True
    except Exception as exc:
        skipped = str(exc)[:160]

    return {"received": True, "wakeup_id": wid, "re_engaged": re_engaged, "skipped": skipped}
