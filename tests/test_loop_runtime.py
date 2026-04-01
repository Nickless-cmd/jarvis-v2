from __future__ import annotations

from datetime import UTC, datetime


def _open_loop_item(*, status: str, canonical_key: str, title: str) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "signal_id": f"signal-{canonical_key}",
        "canonical_key": canonical_key,
        "status": status,
        "title": title,
        "summary": f"{title} summary",
        "updated_at": now,
        "created_at": now,
    }


def _proactive_item(
    *,
    status: str,
    loop_kind: str,
    loop_focus: str,
    loop_state: str,
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    return {
        "signal_id": f"signal-{loop_kind}-{loop_focus}",
        "canonical_key": f"{loop_kind}:{loop_focus}",
        "status": status,
        "title": f"{loop_kind} {loop_focus}",
        "summary": f"{loop_kind} summary",
        "loop_kind": loop_kind,
        "loop_focus": loop_focus,
        "loop_state": loop_state,
        "updated_at": now,
        "created_at": now,
    }


def test_loop_runtime_builds_bounded_states_from_existing_loop_surfaces(
    isolated_runtime,
) -> None:
    loop_runtime = isolated_runtime.loop_runtime
    surface = loop_runtime.build_loop_runtime_from_sources(
        open_loop_surface={
            "items": [
                _open_loop_item(
                    status="open",
                    canonical_key="open-loop:alpha",
                    title="Alpha open loop",
                ),
                _open_loop_item(
                    status="softening",
                    canonical_key="open-loop:beta",
                    title="Beta softening loop",
                ),
                _open_loop_item(
                    status="closed",
                    canonical_key="open-loop:gamma",
                    title="Gamma closed loop",
                ),
            ]
        },
        proactive_loop_surface={
            "items": [
                _proactive_item(
                    status="active",
                    loop_kind="question-loop",
                    loop_focus="alpha",
                    loop_state="loop-question-worthy",
                )
            ]
        },
        quiet_initiative={"active": False, "state": "holding"},
    )

    statuses = {item["title"]: item["runtime_status"] for item in surface["items"]}
    assert statuses["Alpha open loop"] == "active"
    assert statuses["Beta softening loop"] == "standby"
    assert statuses["Gamma closed loop"] == "closed"
    assert statuses["question-loop alpha"] == "active"
    assert surface["summary"]["active_count"] == 2
    assert surface["summary"]["standby_count"] == 1
    assert surface["summary"]["closed_count"] == 1
    assert surface["authority"] == "authoritative"
    assert surface["visibility"] == "internal-only"


def test_loop_runtime_marks_resumed_when_standby_returns_to_active(
    isolated_runtime,
) -> None:
    loop_runtime = isolated_runtime.loop_runtime
    previous = loop_runtime.build_loop_runtime_from_sources(
        open_loop_surface={
            "items": [
                _open_loop_item(
                    status="softening",
                    canonical_key="open-loop:alpha",
                    title="Alpha open loop",
                )
            ]
        },
        proactive_loop_surface={"items": []},
        quiet_initiative={"active": False, "state": "holding"},
    )
    resumed = loop_runtime.build_loop_runtime_from_sources(
        open_loop_surface={
            "items": [
                _open_loop_item(
                    status="open",
                    canonical_key="open-loop:alpha",
                    title="Alpha open loop",
                )
            ]
        },
        proactive_loop_surface={"items": []},
        quiet_initiative={"active": False, "state": "holding"},
        previous=previous,
    )

    assert resumed["items"][0]["runtime_status"] == "resumed"
    assert resumed["summary"]["resumed_count"] == 1
    assert resumed["summary"]["active_count"] == 0


def test_loop_runtime_maps_quiet_hold_to_standby_and_promotion_to_closed(
    isolated_runtime,
) -> None:
    loop_runtime = isolated_runtime.loop_runtime
    standby = loop_runtime.build_loop_runtime_from_sources(
        open_loop_surface={"items": []},
        proactive_loop_surface={"items": []},
        quiet_initiative={
            "active": True,
            "focus": "Ask about calibration",
            "reason_code": "quiet-hold-started",
            "state": "holding",
            "created_at": datetime.now(UTC).isoformat(),
            "last_seen_at": datetime.now(UTC).isoformat(),
        },
    )
    closed = loop_runtime.build_loop_runtime_from_sources(
        open_loop_surface={"items": []},
        proactive_loop_surface={"items": []},
        quiet_initiative={
            "active": False,
            "focus": "Ask about calibration",
            "reason_code": "quiet-hold-promoted",
            "state": "promoted",
            "created_at": datetime.now(UTC).isoformat(),
            "last_seen_at": datetime.now(UTC).isoformat(),
        },
        previous=standby,
    )

    assert standby["items"][0]["runtime_status"] == "standby"
    assert standby["items"][0]["loop_kind"] == "quiet-held-loop"
    assert closed["items"][0]["runtime_status"] == "closed"
    assert closed["summary"]["closed_count"] == 1


def test_heartbeat_prompt_section_includes_loop_runtime_grounding(
    isolated_runtime,
    monkeypatch,
) -> None:
    prompt_contract = isolated_runtime.prompt_contract
    monkeypatch.setattr(
        isolated_runtime.loop_runtime,
        "build_loop_runtime_prompt_section",
        lambda surface=None: "\n".join(
            [
                "Loop runtime (authoritative runtime truth, internal-only):",
                "- active=1 | standby=1 | resumed=0 | closed=0",
                "- current=Alpha open loop | status=active | kind=open-loop",
            ]
        ),
    )

    section = prompt_contract._heartbeat_self_knowledge_section()
    assert section is not None
    assert "Loop runtime" in section
    assert "active=1 | standby=1" in section


def test_mission_control_runtime_and_endpoint_expose_loop_runtime(
    isolated_runtime,
    monkeypatch,
) -> None:
    mission_control = isolated_runtime.mission_control
    runtime_surface = {
        "active": True,
        "authority": "authoritative",
        "visibility": "internal-only",
        "kind": "loop-runtime-state",
        "items": [
            {
                "loop_id": "open-loop:alpha",
                "title": "Alpha open loop",
                "runtime_status": "active",
                "loop_kind": "open-loop",
                "reason_code": "open-loop-active",
            }
        ],
        "summary": {
            "active_count": 1,
            "standby_count": 0,
            "resumed_count": 0,
            "closed_count": 0,
            "current_loop": "Alpha open loop",
            "current_status": "active",
            "current_kind": "open-loop",
            "current_reason": "open-loop-active",
            "loop_count": 1,
        },
        "freshness": {"built_at": datetime.now(UTC).isoformat(), "state": "fresh"},
        "seam_usage": {
            "heartbeat_context": True,
            "heartbeat_prompt_grounding": True,
            "runtime_self_model": True,
            "mission_control_runtime_truth": True,
        },
    }
    monkeypatch.setattr(
        isolated_runtime.loop_runtime,
        "build_loop_runtime_surface",
        lambda: runtime_surface,
    )
    monkeypatch.setattr(mission_control, "build_loop_runtime_surface", lambda: runtime_surface)

    endpoint = mission_control.mc_loop_runtime()
    runtime = mission_control.mc_runtime()

    assert endpoint["summary"]["current_status"] == "active"
    assert runtime["runtime_loop_state"]["summary"]["current_status"] == "active"
    assert runtime["runtime_loop_state"]["visibility"] == "internal-only"
