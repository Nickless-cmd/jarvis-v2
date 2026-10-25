"""Publish first-pass tool outcomes before post-tool prompt assembly.

This is the terminal UI half of first-pass execution.  It resolves approvals,
closes execution traces, and emits the existing capability/working-step/app
events.  Transcript persistence remains with the visible-run orchestrator.
"""
from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import AsyncIterator
from uuid import uuid4


logger = logging.getLogger(__name__)


def surface_tool_result(sr: dict, status: str | None = None) -> None:
    """Close one measured call immediately before its terminal UI fact."""
    from core.services.tool_execution_trace import surface_result
    from core.services.tool_failure_surface import normalise_tool_failure

    result = sr.get("result") or {}
    resolved_status = status or str(sr.get("status") or "unknown")
    concrete_text = normalise_tool_failure(
        resolved_status,
        str(sr.get("result_text") or ""),
        result,
    )
    if concrete_text:
        sr["result_text"] = concrete_text
    exit_code = result.get("exit_code")
    surface_result(
        str(sr.get("call_id") or ""),
        status=resolved_status,
        exit_code=exit_code if isinstance(exit_code, int) else None,
        result_text=concrete_text,
        raw_result=result,
    )


def _ejer_kan_svare(run) -> bool:
    """Er der et menneske i den anden ende af DENNE kørsel?

    To steder traf modsatte beslutninger om samme tilfælde, og det gjorde en
    vækning tandløs (målt 20/10-2026, Bjørn: «wakeups skal forsætte med sessions
    permissions»):

    - `visible_tool_exec` sætter `force = run.autonomous and not _tilstede` med
      begrundelsen «en vækning i Bjørns samtale har et menneske der kan svare,
      så godkendelses-gaten skal være levende — ellers arvede kørslen
      rettighederne uden at arve spørgsmålet». Kørslen bad altså om et KORT.
    - her blev kortet afvist ubetinget på `run.autonomous`, så vækningen fik
      «Autonomous run cannot approve tool calls» — selv om han sad ved
      skærmen. En vækning der ville verificere en release med `gh release view`
      måtte falde tilbage til `web_fetch` mod en HTML-side.

    Spørgsmålet stilles til SESSIONEN, gennem samme definition som
    værktøjspolitikken bruger (`presence_for_run`), så de tre steder ikke kan
    svare forskelligt. Den kræver: ikke en system-silo, BEVIST Bjørns egen
    app-samtale, og en vækning — så et autonomt baggrunds-run arver intet her.

    Fail-closed: enhver fejl → False, og så gælder afvisningen som før.
    """
    try:
        from core.tools.autonomous_tool_policy import presence_for_run
        return bool(presence_for_run(run))
    except Exception:  # uden svar kan vi ikke bevise nogen — så afvises den
        return False


async def publish_first_pass_results(
    results: list[dict],
    *,
    run,
    step_counter: int,
    out: dict,
) -> AsyncIterator[str]:
    """Resolve approvals and publish terminal UI facts; do not persist transcript."""
    from core.services import approval_runtime as _ar
    from core.services import visible_runs as _vr
    from core.services.tool_chip_payload import build_tool_capability_payload

    resolved: dict[int, str] = {}
    out["resolved_result_texts"] = resolved

    for idx, sr in enumerate(results):
        if sr["status"] == "approval_needed":
            if run.autonomous and not _ejer_kan_svare(run):
                resolved[idx] = (
                    f"[{sr['tool_name']}]: Autonomous run cannot approve tool calls — skipped."
                )
                surface_tool_result(sr, "denied")
                yield _vr._sse("capability", {
                    "type": "tool_denied",
                    "tool": sr["tool_name"],
                    "capability_id": str(sr.get("call_id") or ""),
                })
                continue
            if run.trust_all:
                classification = str(sr["result"].get("classification", "") or "")
                if classification != "destructive":
                    resolved[idx] = str(sr["result"].get("result_text") or "")
                    surface_tool_result(sr, "approved")
                    yield _vr._sse("capability", {
                        "type": "tool_approved",
                        "tool": sr["tool_name"],
                        "auto": True,
                    })
                    continue

            approval_id = f"approval-{uuid4().hex[:12]}"
            created_at = datetime.now(UTC).isoformat()
            request = _ar.build_request(
                tool_name=sr["tool_name"],
                arguments=sr["arguments"],
                result=sr["result"],
                run=run,
                created_at=created_at,
            )
            _vr.saet_godkendelse(approval_id, request)
            sr["approval_id"] = approval_id
            try:
                from core.services.approval_bridge_shadow import note_requested

                note_requested(
                    approval_id,
                    tool_name=sr["tool_name"],
                    arguments=sr["arguments"],
                    run_id=run.run_id or "",
                    session_id=run.session_id or "",
                )
            except Exception as exc:
                logger.debug("approval shadow request could not be recorded: %s", exc)
            _vr._set_visible_approval_state(approval_id, {
                "approval_id": approval_id,
                "status": "pending",
                **request,
            })
            _vr._publicer_approval_requested(
                approval_id=approval_id,
                tool=sr["tool_name"],
                run_id=run.run_id,
                session_id=run.session_id,
                result=sr["result"],
            )
            _live_registered = False
            try:
                from core.runtime.settings import load_settings
                if load_settings().live_tool_output_enabled:
                    from core.services.tool_execution_trace import BoundedOutputBuffer
                    from core.services.visible_runs_sections.approval_wait import (
                        register_live_approval,
                    )
                    register_live_approval(
                        approval_id,
                        call_id=str(sr.get("call_id") or ""),
                        run_id=str(run.run_id or ""),
                        output_buffer=BoundedOutputBuffer(),
                    )
                    _live_registered = True
            except Exception as exc:
                logger.debug("approval live-output registration failed: %s", exc)
            # Tell the caller to snapshot after it has handed this frame
            # outward, but before this generator resumes into approval wait.
            out["approval_snapshot_needed"] = True
            yield _vr._sse("approval_request", {
                "type": "approval_request",
                "approval_id": approval_id,
                "tool": sr["tool_name"],
                "message": sr["result"].get("message", ""),
                "detail": sr["result"].get("path") or sr["result"].get("command", ""),
            })
            approval_out: dict = {}
            try:
                async for frame in _vr.wait_for_approval(
                    approval_id=approval_id,
                    tool_name=sr["tool_name"],
                    run_id=run.run_id,
                    round_no=0,
                    out=approval_out,
                ):
                    yield frame
            finally:
                if _live_registered:
                    from core.services.visible_runs_sections.approval_wait import (
                        unregister_live_approval,
                    )
                    unregister_live_approval(approval_id)
            approved_text = approval_out["result_text"]
            # `outcome` skelner et menneskes nej fra en frist der løb ud
            # (25/10-2026). Før skrev begge grene «denied by user», også når
            # ingen havde svaret — en påstand om et menneske der ikke var der.
            _udfald = str(approval_out.get("outcome") or "denied")
            if approved_text is None:
                if _udfald in {"expired", "timeout"}:
                    resolved[idx] = (
                        f"[{sr['tool_name']}]: Godkendelsen udløb uden svar — "
                        "kaldet blev ikke udført."
                    )
                    surface_tool_result(sr, "expired")
                    yield _vr._sse("capability", {
                        "type": "tool_expired",
                        "tool": sr["tool_name"],
                        "capability_id": str(sr.get("call_id") or ""),
                    })
                else:
                    resolved[idx] = f"[{sr['tool_name']}]: Tool call denied by user."
                    surface_tool_result(sr, "denied")
                    yield _vr._sse("capability", {
                        "type": "tool_denied",
                        "tool": sr["tool_name"],
                        "capability_id": str(sr.get("call_id") or ""),
                    })
            else:
                resolved[idx] = approved_text
                surface_tool_result(sr, "ok")
                yield _vr._sse("capability", {
                    "type": "tool_result",
                    "tool": sr["tool_name"],
                    "status": "ok",
                    "capability_id": str(sr.get("call_id") or ""),
                })
            continue

        if sr["status"] == "gate_blocked":
            gate_type = str(sr.get("result", {}).get("gate_type", "unknown"))
            gate_message = str(sr.get("result", {}).get("message", ""))
            resolved[idx] = f"[{gate_type}] {gate_message}"
            surface_tool_result(sr, "gate_blocked")
            yield _vr._sse("capability", {
                "type": "gate_blocked",
                "gate_type": gate_type,
                "tool": sr["tool_name"],
                "message": gate_message,
            })
            yield _vr._sse("working_step", {
                "type": "working_step",
                "run_id": run.run_id,
                "action": sr["tool_name"],
                "step": step_counter - len(results) + idx + 1,
                "status": "done",
            })
            continue

        resolved[idx] = sr["result_text"]
        surface_tool_result(sr)
        yield _vr._sse("capability", build_tool_capability_payload(
            tool=sr["tool_name"],
            status=sr["status"],
            arguments=sr.get("arguments"),
            result_text=sr.get("result_text", ""),
            call_id=str(sr.get("call_id") or ""),
        ))
        yield _vr._sse("working_step", {
            "type": "working_step",
            "run_id": run.run_id,
            "action": sr["tool_name"],
            "step": step_counter - len(results) + idx + 1,
            "status": "done",
        })
        try:
            from core.tools.app_control_tool import build_app_action_event

            app_event = build_app_action_event(
                sr.get("result"),
                user_message=run.user_message,
                session_id=run.session_id or "",
            )
            if app_event:
                yield _vr._sse("app_action_request", app_event)
        except Exception as exc:
            logger.debug("app action event could not be built: %s", exc)
