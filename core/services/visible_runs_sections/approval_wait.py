"""Vent på brugerens godkendelse — uden at runnet dør imens.

Boy Scout-udtrækning (2026-08-21): `visible_runs.py` er 7.055 linjer, og den
samme approval-ventelokke lå duplikeret to steder (den simple sti ~2085 og den
agentiske ~4065). Denne enhed samler den, så der findes ÉT svar på "hvad sker
der mens vi venter på Bjørn".

## Bug'en der gjorde udtrækningen nødvendig

Ventelokken pollede godkendelsestilstanden hvert 0,25s i op til 300 sekunder —
og sendte **nul frames** imens. Men `visible_runs_sse_v2._translation_loop`
tolker 9 × 20s uden en eneste legacy-frame som "kilden er død" og cancellerer
den levende generator (`_MAX_IDLE_TICKS`). To konstanter i direkte konflikt:

    approval-vindue   300s      ← hvor længe Jarvis VIL vente
    idle-loft         180s      ← hvor længe streamen TILLADER tavshed

De sidste 120s af approval-vinduet kunne derfor aldrig bruges. Enhver
godkendelse der tog over tre minutter dræbte runnet med
`run-abandoned-before-finalization:CancelledError`, og svaret gik tabt —
inklusive alt arbejde fra de forudgående runder.

Målt live 21. aug 2026 på Bjørns session: run `6f6235b0` kørte 15 runder over
365s. Kl. 07:59:33 returnerede et `bash`-kald `approval_needed`. Derefter
loggede runnet **intet** i 180 sekunder, og kl. 08:02:33 kom
`run_abandoned_midflight ... stage=agentic_tool_exec_r15 vis_len=0`. Nul tegn
persisteret: hverken svaret eller den ærlige afbrudt-besked nåede sessionen.

Det forklarer hvorfor det ramte netop de LANGE runs: jo flere runder, jo større
chance for at ramme et approval-gate — og ventetiden er den eneste fase i et run
der er både lang og fuldstændig tavs.

## Fixet

Ventelokken yielder nu en heartbeat hvert `heartbeat_interval_s` (10s, komfortabelt
under både idle-tick'ets 20s og `is_live`-vinduets 45s). Det har tre virkninger:
runnet overlever ventetiden, `run_event_log.is_live` forbliver frisk, og klienten
kan se at han venter på et menneske i stedet for at se en død stream.

De 300 sekunder er dermed ægte ventetid for første gang — før var det reelt 180.
"""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

logger = logging.getLogger(__name__)

# Under idle-tick'ets 20s OG is_live-vinduets 45s, med margin til et travlt
# event-loop. Hæves den over 20s, er bug'en tilbage.
HEARTBEAT_INTERVAL_S = 10.0
DEFAULT_APPROVAL_WINDOW_S = 300.0
_POLL_INTERVAL_S = 0.25


async def wait_for_approval(
    *,
    approval_id: str,
    tool_name: str,
    run_id: str,
    round_no: int,
    out: dict,
    window_s: float = DEFAULT_APPROVAL_WINDOW_S,
    heartbeat_interval_s: float = HEARTBEAT_INTERVAL_S,
) -> AsyncIterator[str]:
    """Poll godkendelsestilstanden og yield keepalive imens.

    Lægger resultatet i ``out["result_text"]``: en streng ved godkendelse, eller
    ``None`` ved afvisning/udløb. Kalderen afgør hvad der så skal ske — denne
    enhed tager ikke stilling til afvisningens ordlyd.

    Frames der yieldes er heartbeats i samme form som ``run_tool_batch``s, så
    klienten ikke skal kende to formater for "jeg arbejder stadig".
    """
    from core.services.visible_runs import _sse
    from core.services.visible_runs_sections.run_control_state import (
        _get_visible_approval_state,
        touch_active_visible_run,
    )

    loop = asyncio.get_running_loop()
    deadline = loop.time() + window_s
    next_beat = loop.time() + heartbeat_interval_s
    beats = 0
    started = loop.time()
    resolved: str | None = None

    logger.info(
        "approval-wait-start run_id=%s round=%d approval_id=%s tool=%s window_s=%.0f",
        run_id, round_no, approval_id, tool_name, window_s,
    )

    while loop.time() < deadline:
        state = _get_visible_approval_state(approval_id)
        status = str(state.get("status") or "")
        if status == "approved":
            resolved = str(state.get("result_text") or "")
            logger.info(
                "approval-resolved run_id=%s approval_id=%s result_chars=%d waited_s=%.0f",
                run_id, approval_id, len(resolved), loop.time() - started,
            )
            break
        if status in {"denied", "expired"}:
            logger.info(
                "approval-rejected run_id=%s approval_id=%s status=%s waited_s=%.0f",
                run_id, approval_id, status, loop.time() - started,
            )
            break

        now = loop.time()
        if now >= next_beat:
            beats += 1
            next_beat = now + heartbeat_interval_s
            # Cross-process liveness — samme touch som tool-exec bruger, så et run
            # der venter på et menneske ser lige så levende ud som et der arbejder.
            try:
                touch_active_visible_run(run_id)
            except Exception:
                pass
            yield _sse("heartbeat", {
                "type": "heartbeat",
                "run_id": run_id,
                "phase": "awaiting_approval",
                "approval_id": approval_id,
                "tool": tool_name,
                "round": round_no,
                "elapsed_s": int(now - started),
                "beat": beats,
            })
        await asyncio.sleep(_POLL_INTERVAL_S)
    else:
        logger.warning(
            "approval-timeout run_id=%s approval_id=%s waited_s=%.0f",
            run_id, approval_id, loop.time() - started,
        )

    out["result_text"] = resolved
