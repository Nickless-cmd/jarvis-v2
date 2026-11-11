from __future__ import annotations


def test_somatic_body_reacts_to_interruption(isolated_runtime) -> None:
    from core.services.somatic_runtime_body import build_somatic_body_prompt_section, update_somatic_body

    result = update_somatic_body(event_type="runtime-interruption", intensity=0.9, detail="timeout")
    assert result["posture"] == "startled"
    assert "resume" in result["regulation"].lower()

    section = build_somatic_body_prompt_section()
    assert section is not None
    assert "Somatic runtime body" in section


def test_perceptual_event_updates_somatic_body(isolated_runtime) -> None:
    from core.services.perceptual_event_engine import record_perceptual_event
    from core.services.somatic_runtime_body import build_somatic_body_surface

    record_perceptual_event(change_type="tool-error", summary="Tool failed", salience="high")
    surface = build_somatic_body_surface()
    assert surface["active"] is True
    assert surface["levels"]["frustration"] > 0


def test_tool_error_on_real_tool_path_raises_levels_and_gates_behavior(
    isolated_runtime, monkeypatch
) -> None:
    """Accept 3: execute_tool-fejl rammer kroppen DIREKTE, og efter nok fejl
    bærer fejl-resultatet `somatic_gate` (adfærdsforgrening på niveauet)."""
    from core.services.somatic_runtime_body import build_somatic_body_surface
    from core.tools import simple_tools

    def _boom(_args):
        return {"status": "error", "error": "nope"}

    monkeypatch.setitem(simple_tools._TOOL_HANDLERS, "somatic_probe", _boom)

    first = simple_tools.execute_tool("somatic_probe", {})
    assert build_somatic_body_surface()["levels"]["frustration"] > 0
    assert "somatic_gate" not in first  # ét fejl-skud er ikke nok

    last = first
    for _ in range(4):
        last = simple_tools.execute_tool("somatic_probe", {})
    assert last["somatic_gate"]["posture"] == "pressured"
    assert "narrow" in last["somatic_gate"]["instruction"].lower()


def test_successful_tool_does_not_touch_body_or_gate(isolated_runtime, monkeypatch) -> None:
    from core.services.somatic_runtime_body import build_somatic_body_surface
    from core.tools import simple_tools

    monkeypatch.setitem(simple_tools._TOOL_HANDLERS, "somatic_ok", lambda _a: {"status": "ok"})
    out = simple_tools.execute_tool("somatic_ok", {})
    assert "somatic_gate" not in out
    assert build_somatic_body_surface()["active"] is False


def test_decay_levels_reduces_startle() -> None:
    from core.services.somatic_runtime_body import _decay_levels

    # startle rate 0.003/s; 300s of inactivity → 0.9 fully fades to 0.0
    out = _decay_levels({"startle": 0.9}, 300.0)
    assert out["startle"] == 0.0


def test_decay_levels_partial_and_clamped() -> None:
    from core.services.somatic_runtime_body import _decay_levels

    # 100s → startle drops by 0.3 (0.003 * 100); never below 0.0
    out = _decay_levels({"startle": 0.5, "fatigue": 0.1}, 100.0)
    assert abs(out["startle"] - 0.2) < 1e-9
    # fatigue is sticky (0.0005/s): 100s → -0.05 → 0.1 - 0.05 = 0.05
    assert abs(out["fatigue"] - 0.05) < 1e-9


def test_decay_levels_zero_age_is_noop() -> None:
    from core.services.somatic_runtime_body import _decay_levels

    levels = {"startle": 0.7}
    assert _decay_levels(levels, 0.0) is levels


def test_startle_unsticks_after_inactivity(isolated_runtime) -> None:
    """The root-cause fix: a high startle posture must recover over time.

    Seeds a 'startled' state timestamped in the past, then a neutral event
    triggers time-based decay so posture is no longer stuck at 'startled'.
    """
    from datetime import UTC, datetime, timedelta

    from core.runtime.db import set_runtime_state_value
    from core.services.somatic_runtime_body import _STATE_KEY, update_somatic_body

    old_ts = (datetime.now(UTC) - timedelta(seconds=400)).isoformat()
    set_runtime_state_value(
        _STATE_KEY,
        {
            "active": True,
            "levels": {"pressure": 0.2, "fatigue": 0.1, "startle": 0.9, "frustration": 0.0, "relief": 0.0},
            "posture": "startled",
            "regulation": "x",
            "updated_at": old_ts,
        },
        updated_at=old_ts,
    )

    # Neutral event: adds no startle, so only decay applies (400s * 0.003 = 1.2 → 0.0)
    result = update_somatic_body(event_type="tool-result", intensity=0.5)
    assert result["levels"]["startle"] == 0.0
    assert result["posture"] != "startled"
