"""Workspace-capability planning + execution for visible runs.

Boy Scout-udtrækning (2026-07-07): udskilt fra ``core/services/visible_runs.py``.
Ren KODE-FLYTNING — ingen logik-ændring. Funktionerne re-eksporteres tilbage til
``visible_runs`` i bunden af den fil, så bare kald i ``_stream_visible_run`` og
eksisterende call-sites/monkeypatches fortsat virker.

Main-residente symboler (``_update_visible_execution_trace``,
``set_last_visible_capability_use``, ``_MAX_CAPABILITIES_PER_TURN``) refereres via
``_vr.X`` (facade-seam) INDE i funktions-kroppe (lazy) → ingen import-cyklus og
patches ses på kald-tidspunkt.
"""

from __future__ import annotations

import json
import re

import core.services.visible_runs as _vr

from core.eventbus.bus import event_bus
from core.tools.workspace_capabilities import (
    invoke_workspace_capability,
    load_workspace_capabilities,
)
from core.services.prompt_sections.capability_markup import (
    CAPABILITY_BLOCK_PATTERN,
    CAPABILITY_CALL_SCAN_PATTERN,
    _extract_content_after_capability_tag,
    _parse_capability_attrs,
    _parse_capability_call_markup,
)


def _extract_capability_plan(text: str) -> dict[str, object]:
    raw = str(text or "")
    parsed_matches: list[dict[str, object]] = []

    for match in CAPABILITY_BLOCK_PATTERN.finditer(raw):
        attrs = _parse_capability_attrs(match.group("attrs"))
        capability_id = str(attrs.pop("id", "")).strip()
        if not capability_id or not re.fullmatch(r"[a-z0-9:-]+", capability_id):
            continue
        arguments = dict(attrs)
        block_content = match.group("content").strip()
        if block_content:
            arguments["write_content"] = block_content
        parsed_matches.append(
            {
                "capability_id": capability_id,
                "arguments": arguments,
                "_source_order": match.start(),
                "_binding_mode": "block-content",
            }
        )

    for match in CAPABILITY_CALL_SCAN_PATTERN.finditer(raw):
        parsed = _parse_capability_call_markup(match.group(0))
        if not parsed:
            continue
        parsed_matches.append(
            {
                **parsed,
                "_source_order": match.start(),
                "_binding_mode": "tag-attributes" if parsed.get("arguments") else "id-only",
            }
        )

    parsed_matches.sort(key=lambda item: int(item.get("_source_order") or 0))
    matches = [str(item.get("capability_id") or "") for item in parsed_matches]

    all_capabilities: list[dict[str, object]] = []
    seen: set[str] = set()
    selected_binding_mode = "id-only"
    for item in parsed_matches:
        capability_id = str(item.get("capability_id") or "")
        if _is_known_workspace_capability(capability_id):
            arguments = dict(item.get("arguments") or {})
            dedupe_key = json.dumps(
                {
                    "capability_id": capability_id,
                    "arguments": arguments,
                },
                sort_keys=True,
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            all_capabilities.append({
                "capability_id": capability_id,
                "arguments": arguments,
            })
            if len(all_capabilities) == 1:
                selected_binding_mode = str(item.get("_binding_mode") or "id-only")
            if len(all_capabilities) >= _vr._MAX_CAPABILITIES_PER_TURN:
                break

    # For memory-write self-closing tags without write_content,
    # try to find markdown content after the tag in the LLM response.
    # This handles the common case where the LLM uses self-closing syntax
    # and puts the content below instead of inside a block tag.
    for cap in all_capabilities:
        cap_id = str(cap.get("capability_id") or "")
        cap_args = cap.get("arguments") or {}
        if "write-workspace-memory" in cap_id or "write-user-profile" in cap_id:
            if not cap_args.get("write_content"):
                content_after = _extract_content_after_capability_tag(raw, cap_id)
                if content_after:
                    cap["arguments"] = {**cap_args, "write_content": content_after}

    selected = str(all_capabilities[0]["capability_id"]) if all_capabilities else None
    selected_arguments = dict(all_capabilities[0]["arguments"]) if all_capabilities else {}
    argument_binding_mode = (
        selected_binding_mode if selected else "id-only"
    )
    if selected and argument_binding_mode == "id-only" and selected_arguments:
        argument_binding_mode = "tag-attributes"

    return {
        "selected_capability_id": selected,
        "selected_arguments": selected_arguments,
        "argument_source": argument_binding_mode if selected else "none",
        "argument_binding_mode": argument_binding_mode,
        "capability_ids": matches,
        "all_capabilities": all_capabilities,
        "had_markup": bool(matches),
        "multiple": len(all_capabilities) > 1,
    }



    return ""


def _execute_visible_capability_entries(
    run: "_vr.VisibleRun",
    *,
    all_capabilities: list[dict[str, object]],
) -> tuple[list[dict[str, object]], bool, list[dict[str, object]]]:
    capability_results: list[dict[str, object]] = []
    capability_events: list[dict[str, object]] = []
    any_executed = False

    for cap_entry in all_capabilities:
        cap_id = str(cap_entry["capability_id"])
        cap_args = dict(cap_entry.get("arguments") or {})

        resolved_target_path, target_source = _resolve_visible_capability_target_path(
            capability_id=cap_id,
            capability_arguments=cap_args,
            user_message=run.user_message,
        )
        resolved_command_text, command_source = _resolve_visible_capability_command_text(
            capability_id=cap_id,
            capability_arguments=cap_args,
            user_message=run.user_message,
        )
        resolved_write_content = cap_args.get("write_content") or None

        _vr._update_visible_execution_trace(
            run,
            {
                "parsed_target_path": resolved_target_path,
                "parsed_command_text": resolved_command_text,
                "argument_source": _merge_argument_sources(target_source, command_source),
                "invoke_status": "started",
            },
        )

        capability_result = invoke_workspace_capability(
            cap_id,
            run_id=run.run_id,
            target_path=resolved_target_path,
            command_text=resolved_command_text,
            write_content=resolved_write_content,
        )

        cap_status = str(capability_result.get("status") or "")
        cap_exec_mode = str(capability_result.get("execution_mode") or "")
        cap_result_obj = capability_result.get("result") or {}
        cap_result_text = ""
        if isinstance(cap_result_obj, dict):
            cap_result_text = str(cap_result_obj.get("text") or "").strip()
        cap_detail = str(capability_result.get("detail") or "").strip()

        # Surface detailed error context when a capability fails. Jarvis
        # previously only saw the short cap_detail string ("blocked-X"),
        # which made it hard to debug what went wrong. Now error results
        # include exit_code, normalized command, stderr preview, and
        # block reason as part of the result_text the LLM sees.
        if cap_status and cap_status != "executed":
            error_lines: list[str] = [f"TOOL_ERROR status={cap_status}"]
            if isinstance(cap_result_obj, dict):
                exit_code = cap_result_obj.get("exit_code")
                if exit_code is not None:
                    error_lines.append(f"exit_code={exit_code}")
                normalized_cmd = str(cap_result_obj.get("normalized_command_text") or "").strip()
                if normalized_cmd:
                    error_lines.append(f"normalized_command={normalized_cmd[:200]}")
                target_path_field = str(cap_result_obj.get("target_path") or cap_result_obj.get("path") or "").strip()
                if target_path_field:
                    error_lines.append(f"target_path={target_path_field[:200]}")
            if cap_detail:
                error_lines.append(f"detail={cap_detail[:400]}")
            error_header = " | ".join(error_lines)
            if cap_result_text:
                cap_result_text = (
                    f"{error_header}\n--- captured output ---\n{cap_result_text}"
                )
            else:
                cap_result_text = error_header

        # Echo confirmation header for memory/file writes so the LLM gets
        # explicit feedback that the write succeeded — Jarvis previously
        # only saw the merged preview text and could not tell whether the
        # write had actually been persisted.
        if cap_status == "executed" and isinstance(cap_result_obj, dict):
            write_kind = str(cap_result_obj.get("type") or "")
            if write_kind in {"workspace-memory-write", "workspace-file-write"}:
                write_path = str(cap_result_obj.get("path") or "").strip()
                bytes_written = cap_result_obj.get("bytes_written")
                bytes_before = cap_result_obj.get("bytes_before")
                bytes_delta = cap_result_obj.get("bytes_delta")
                fingerprint = str(cap_result_obj.get("content_fingerprint") or "").strip()
                fingerprint_before = str(cap_result_obj.get("content_fingerprint_before") or "").strip()
                readback_match = cap_result_obj.get("readback_match")
                readback_fp = str(cap_result_obj.get("readback_fingerprint") or "").strip()
                line_count: int | None = None
                if cap_result_text:
                    line_count = cap_result_text.count("\n") + 1
                header_parts: list[str] = [
                    f"WRITE_CONFIRMED path={write_path or 'unknown'}",
                    f"bytes={int(bytes_written) if isinstance(bytes_written, (int, float)) else 'unknown'}",
                ]
                if isinstance(bytes_before, (int, float)):
                    header_parts.append(f"bytes_before={int(bytes_before)}")
                if isinstance(bytes_delta, (int, float)):
                    header_parts.append(f"bytes_delta={int(bytes_delta):+d}")
                if line_count is not None:
                    header_parts.append(f"preview_lines={line_count}")
                if fingerprint:
                    header_parts.append(f"fingerprint={fingerprint[:16]}")
                if fingerprint_before and fingerprint_before != fingerprint:
                    header_parts.append(f"fingerprint_before={fingerprint_before[:16]}")
                # Readback verification — Jarvis can see disk truth, not
                # just a write-side claim. If readback failed, this
                # surfaces the mismatch loudly.
                if readback_match is True:
                    header_parts.append("readback=verified")
                elif readback_match is False:
                    header_parts.append("readback=MISMATCH")
                    if readback_fp:
                        header_parts.append(f"readback_fingerprint={readback_fp[:16]}")
                header_parts.append(
                    "status=persisted" if readback_match is not False else "status=persisted-but-mismatched"
                )
                confirmation_header = " | ".join(header_parts)
                cap_result_text = (
                    f"{confirmation_header}\n--- preview ---\n{cap_result_text}"
                    if cap_result_text
                    else confirmation_header
                )

        _vr._update_visible_execution_trace(
            run,
            {
                "invoke_status": cap_status,
                "blocked_reason": capability_result.get("detail"),
                "argument_source": _merge_argument_sources(target_source, command_source),
                "normalized_command_text": (
                    ((capability_result.get("result") or {}).get("normalized_command_text"))
                    or None
                ),
                "path_normalization_applied": bool(
                    (capability_result.get("result") or {}).get("path_normalization_applied", False)
                ),
                "normalization_source": (
                    ((capability_result.get("result") or {}).get("normalization_source"))
                    or "none"
                ),
            },
        )

        capability_results.append({
            "capability_id": cap_id,
            "status": cap_status,
            "execution_mode": cap_exec_mode,
            "result_text": cap_result_text,
            "detail": cap_detail,
            "invocation": capability_result,
        })

        if cap_status == "executed":
            any_executed = True

        _vr.set_last_visible_capability_use(
            run,
            capability_id=cap_id,
            invocation=capability_result,
            capability_arguments=cap_args,
            argument_source=_merge_argument_sources(target_source, command_source),
        )

        event_bus.publish(
            "runtime.visible_run_capability_used",
            {
                "run_id": run.run_id,
                "lane": run.lane,
                "provider": run.provider,
                "model": run.model,
                "capability_id": cap_id,
                "status": cap_status,
                "execution_mode": cap_exec_mode,
            },
        )

        capability_events.append(
            {
                "type": "capability",
                "run_id": run.run_id,
                "capability_id": cap_id,
                "status": cap_status,
                "execution_mode": cap_exec_mode,
                "target_path": resolved_target_path or None,
                "command_text": resolved_command_text or None,
                "capability_name": (
                    (capability_result.get("capability") or {}).get("name")
                    or cap_id
                ),
            }
        )

    return capability_results, any_executed, capability_events


def _planned_visible_capability_steps(
    run: "_vr.VisibleRun",
    *,
    all_capabilities: list[dict[str, object]],
    step_offset: int,
) -> list[dict[str, object]]:
    planned_steps: list[dict[str, object]] = []

    for index, cap_entry in enumerate(all_capabilities, start=1):
        cap_id = str(cap_entry.get("capability_id") or "")
        cap_args = dict(cap_entry.get("arguments") or {})
        resolved_target_path, _target_source = _resolve_visible_capability_target_path(
            capability_id=cap_id,
            capability_arguments=cap_args,
            user_message=run.user_message,
        )
        resolved_command_text, _command_source = _resolve_visible_capability_command_text(
            capability_id=cap_id,
            capability_arguments=cap_args,
            user_message=run.user_message,
        )
        action, detail = _visible_capability_step_description(
            capability_id=cap_id,
            target_path=resolved_target_path,
            command_text=resolved_command_text,
        )
        planned_steps.append(
            {
                "type": "working_step",
                "run_id": run.run_id,
                "action": action,
                "detail": detail,
                "step": step_offset + index,
                "status": "running",
            }
        )

    return planned_steps


def _visible_capability_step_description(
    *,
    capability_id: str,
    target_path: str | None,
    command_text: str | None,
) -> tuple[str, str]:
    normalized_id = capability_id.lower()
    normalized_command = str(command_text or "").strip()
    normalized_target = str(target_path or "").strip()

    if normalized_target and any(token in normalized_id for token in ("write", "edit", "patch", "memory")):
        return "editing", f"Editing {normalized_target}"
    if normalized_target and any(token in normalized_id for token in ("list", "dir", "folder")):
        return "browsing", f"Browsing {normalized_target}"
    if normalized_target:
        return "reading", f"Reading {normalized_target}"
    if normalized_command:
        return "running", f"Running {normalized_command}"
    return "tool", f"Using {capability_id}"


def _is_known_workspace_capability(capability_id: str) -> bool:
    runtime_capabilities = load_workspace_capabilities().get("runtime_capabilities", [])
    for capability in runtime_capabilities:
        if capability.get("capability_id") != capability_id:
            continue
        return True
    return False


def _resolve_visible_capability_target_path(
    *, capability_id: str, capability_arguments: dict[str, str], user_message: str
) -> tuple[str | None, str]:
    runtime_capabilities = load_workspace_capabilities().get("runtime_capabilities", [])
    capability = next(
        (
            item
            for item in runtime_capabilities
            if item.get("capability_id") == capability_id
        ),
        None,
    )
    if capability is None:
        return None, "none"
    if str(capability.get("execution_mode") or "") not in {"external-file-read", "external-dir-list"}:
        return None, "none"
    if str(capability_arguments.get("target_path") or "").strip():
        return str(capability_arguments.get("target_path") or "").strip(), "tag-attributes"
    if str(capability.get("target_path_source") or "") != "invocation-argument":
        return None, "none"
    fallback = _extract_external_target_path_from_user_message(user_message)
    if fallback:
        return fallback, "user-message-fallback"
    return None, "none"


def _extract_external_target_path_from_user_message(user_message: str) -> str | None:
    for match in re.finditer(r"(?P<path>(?:~|/)[^\s<>'\"]+)", str(user_message or "")):
        candidate = str(match.group("path") or "").strip()
        candidate = candidate.rstrip(".,:;!?)]}")
        if candidate:
            return candidate
    return None


def _resolve_visible_capability_command_text(
    *, capability_id: str, capability_arguments: dict[str, str], user_message: str
) -> tuple[str | None, str]:
    runtime_capabilities = load_workspace_capabilities().get("runtime_capabilities", [])
    capability = next(
        (
            item
            for item in runtime_capabilities
            if item.get("capability_id") == capability_id
        ),
        None,
    )
    if capability is None:
        return None, "none"
    if str(capability.get("execution_mode") or "") != "non-destructive-exec":
        return None, "none"
    if str(capability_arguments.get("command_text") or "").strip():
        return str(capability_arguments.get("command_text") or "").strip(), "tag-attributes"
    if str(capability.get("command_source") or "") != "invocation-argument":
        return None, "none"
    fallback = _extract_exec_command_from_user_message(user_message)
    if fallback:
        return fallback, "user-message-fallback"
    return None, "none"


def _merge_argument_sources(*sources: str) -> str:
    meaningful = [str(source or "").strip() for source in sources if str(source or "").strip() and str(source or "").strip() != "none"]
    if not meaningful:
        return "none"
    unique = []
    for item in meaningful:
        if item not in unique:
            unique.append(item)
    return "+".join(unique)


def _extract_exec_command_from_user_message(user_message: str) -> str | None:
    fenced = re.search(r"`(?P<command>[^`\n]+)`", str(user_message or ""))
    if fenced:
        command = str(fenced.group("command") or "").strip()
        if command:
            return command
    for raw_line in str(user_message or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if lowered.startswith("command:") or lowered.startswith("kommando:"):
            command = line.split(":", 1)[1].strip()
            if command:
                return command
    return None


def _capability_visible_text(*, capability_id: str, invocation: dict) -> str:
    status = str(invocation.get("status") or "unknown")
    execution_mode = str(invocation.get("execution_mode") or "unknown")
    result = invocation.get("result") or {}
    detail = str(invocation.get("detail") or "").strip()
    text = ""
    if isinstance(result, dict):
        text = str(result.get("text") or "").strip()
        if result.get("type") == "workspace-search-read":
            return _workspace_search_visible_text(
                capability_id=capability_id,
                execution_mode=execution_mode,
                result=result,
            )

    if text:
        return f"[Capability {capability_id} via {execution_mode}]\n{text}"
    if detail:
        return f"[Capability {capability_id} via {execution_mode}]\n{detail}"
    return f"[Capability {capability_id} via {execution_mode}] {status}"


def _workspace_search_visible_text(
    *, capability_id: str, execution_mode: str, result: dict
) -> str:
    path = str(result.get("path") or "ukendt")
    query = str(result.get("query") or "ukendt")
    matches = result.get("matches") or []
    lines = [
        f"[Capability {capability_id} via {execution_mode}]",
        f"File: {path}",
        f"Query: {query}",
    ]
    if isinstance(matches, list) and matches:
        for match in matches:
            if not isinstance(match, dict):
                continue
            line_number = match.get("line")
            excerpt = str(match.get("excerpt") or "").strip()
            if not excerpt:
                continue
            lines.append(f"L{line_number}: {excerpt}")
    else:
        lines.append("No matches found.")
    return "\n".join(lines)
