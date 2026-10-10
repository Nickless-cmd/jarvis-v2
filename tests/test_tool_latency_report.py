from __future__ import annotations

from scripts.tool_latency_report import aggregate


def _timing(**values):
    return {
        "kind": "tool.execution_timing",
        "payload": {"tool": "bash", "route": "server_persistent_shell", **values},
    }


def test_report_counts_where_slow_calls_waited():
    rows = [
        _timing(total_visible_ms=900, dispatch_to_lock_ms=700, process_ms=40),
        _timing(total_visible_ms=120, dispatch_to_lock_ms=0, process_ms=80),
    ]
    report = aggregate(rows, slow_ms=500)
    assert report["calls"] == 2
    assert report["slow_calls"] == 1
    assert report["dominant_wait_stage"]["shell_lock"] == 1
    assert report["duration_ms"] == {"p50": 510.0, "p90": 822.0, "p95": 861.0, "max": 900.0}


def test_report_handles_empty_and_malformed_old_events():
    report = aggregate([
        {"kind": "tool.execution_timing", "payload": None},
        {"kind": "tool.execution_timing", "payload": {"total_visible_ms": "old"}},
        {"kind": "unknown", "payload": {}},
    ])
    assert report["calls"] == 0
    assert report["slow_calls"] == 0
    assert report["duration_ms"] == {"p50": None, "p90": None, "p95": None, "max": None}


def test_mixed_routes_and_unmeasured_waits_are_not_forced_to_sum():
    report = aggregate([
        _timing(total_visible_ms=700, dispatch_to_lock_ms=4, process_ms=600),
        _timing(route="operator_bridge", total_visible_ms=800,
                dispatch_to_spawn_ms=650, process_ms=50),
        _timing(route="server_fallback", total_visible_ms=900),
        _timing(route="operator_bridge", total_visible_ms=950,
                process_exit_to_result_emit_ms=800, process_ms=20),
    ], slow_ms=500)
    assert report["routes"] == {
        "operator_bridge": 2,
        "server_fallback": 1,
        "server_persistent_shell": 1,
    }
    assert report["dominant_wait_stage"] == {
        "bridge_or_spawn": 1,
        "process": 1,
        "result_surface": 1,
        "shell_lock": 0,
        "unattributed": 1,
    }


def test_prompt_cache_outcomes_phases_and_builds_are_counted():
    report = aggregate([
        {"kind": "prompt.assembly_cache", "payload": {
            "cache_outcome": "hit", "caller_phase": "post_tool", "lookup_ms": 0.4,
            "process_role": "api", "pid": 1, "key_hash": "same",
        }},
        {"kind": "prompt.assembly_cache", "payload": {
            "cache_outcome": "miss", "caller_phase": "initial", "build_ms": 15_000,
            "process_role": "runtime", "pid": 2, "key_hash": "same",
        }},
        {"kind": "prompt.assembly_cache", "payload": {
            "cache_outcome": "expired", "caller_phase": "post_tool", "build_ms": 6_000,
            "process_role": "api", "pid": 3, "key_hash": "other",
        }},
        {"kind": "prompt.assembly_size", "payload": {"assembly_ms": 14_900}},
        {"kind": "prompt.assembly_size", "payload": {"assembly_ms": 2_000}},
    ])
    assert report["prompt_cache"]["outcomes"] == {"expired": 1, "hit": 1, "miss": 1}
    assert report["prompt_cache"]["phases"] == {"initial": 1, "post_tool": 2}
    assert report["prompt_cache"]["process_roles"] == {"api": 2, "runtime": 1}
    assert report["prompt_cache"]["key_hashes"] == {"other": 1, "same": 2}
    assert report["prompt_cache"]["processes"] == {"api:1": 1, "api:3": 1, "runtime:2": 1}
    assert report["prompt_cache"]["build_ms"]["max"] == 15_000.0
    assert report["prompt_builds"]["assembly_ms"] == {
        "p50": 8_450.0, "p90": 13_610.0, "p95": 14_255.0, "max": 14_900.0,
    }
