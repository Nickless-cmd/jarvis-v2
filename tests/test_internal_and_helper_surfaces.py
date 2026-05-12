from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace


def test_selective_attention_prioritizes_context_and_chords(monkeypatch):
    from core.services import selective_attention as attention

    monkeypatch.setattr(attention, "_autonomy_enabled", lambda: True)
    monkeypatch.setattr(
        "core.services.signal_pressure_accumulator.get_dominant_pressures",
        lambda min_accumulated=0.05: [
            SimpleNamespace(direction="explore", accumulated=0.4),
            SimpleNamespace(direction="create", accumulated=0.3),
        ],
    )
    monkeypatch.setattr(
        "core.services.emotional_chords._map_pressures_to_families",
        lambda dominant: {"curiosity": 0.4, "desire": 0.3, "boredom": 0.1},
    )
    monkeypatch.setattr(
        "core.services.epistemic_pragmatic.compute_epistemic_pragmatic",
        lambda: SimpleNamespace(mode="pragmatic"),
    )
    monkeypatch.setattr(
        "core.services.emotional_chords.compute_active_chords",
        lambda: [SimpleNamespace(chord_name="creative_itch")],
    )

    spotlight = attention.compute_selective_attention()
    detail = attention.get_attention_spotlight_detail()

    assert spotlight is not None
    assert spotlight.primary_focus == "desire"
    assert spotlight.focus_width in {"narrow", "medium"}
    assert spotlight.prompt_hint.startswith("fokus: desire")
    assert any(d.action == "amplify" for d in spotlight.directives)
    assert any(d.action == "attenuate" for d in spotlight.directives)
    assert detail["primary_focus"] == "desire"
    assert detail["directives"]


def test_resonance_decay_reports_active_field(monkeypatch):
    from core.services import resonance_decay as resonance

    resonance.clear_resonances()
    monkeypatch.setattr(resonance, "_autonomy_enabled", lambda: True)
    monkeypatch.setattr(resonance, "_scan_for_new_resonances", lambda: None)
    monkeypatch.setattr(resonance, "_active_resonances", [
        resonance.Resonance(
            source="frustration",
            intensity=0.6,
            born_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            decay_rate=0.0,
            peak=0.6,
            label="frustration",
        )
    ])

    field = resonance.assess_resonance_field()
    line = resonance.get_resonance_line()

    assert field.quality == "frisk skarp"
    assert field.dominant_source == "frustration"
    assert field.total_energy == 0.6
    assert line == "genklang: [frustration 60%] frisk skarp"


def test_auto_code_review_flags_scope_and_tests(monkeypatch):
    from core.services import auto_code_review as review

    monkeypatch.setattr(
        review,
        "_git_diff_stats",
        lambda repo, files: {
            "core/services/example.py": {"added": 120, "removed": 10},
            "core/services/other.py": {"added": 90, "removed": 0},
        },
    )

    report = review.review_pending_commit(
        repo_root=SimpleNamespace(),
        files=["core/services/example.py", "core/services/other.py"],
        message="feat: example",
        rationale="prove helper",
    )

    assert report["status"] == "ok"
    assert report["verdict"] == "ok-with-flags"
    kinds = {flag["kind"] for flag in report["flags"]}
    assert "no-tests" in kinds
    assert "docs-only" not in kinds


def test_delegation_advisor_routes_broad_search_outward():
    from core.services import delegation_advisor as advisor

    verdict = advisor.advise("find and map all usages across the entire repo")

    assert verdict["status"] == "ok"
    assert verdict["verdict"] == "delegate"
    assert verdict["role_suggestion"] == "researcher"
    assert verdict["score"] >= 30


def test_good_enough_gate_stops_when_evidence_and_pressure_align(monkeypatch):
    from core.services import good_enough_gate as gate

    events = [
        {
            "kind": "tool.completed",
            "created_at": "2026-05-12T19:00:00+00:00",
            "payload": {
                "run_id": "run-1",
                "tool": "verify_state",
                "status": "ok",
            },
        }
    ]
    monkeypatch.setattr(
        "core.eventbus.bus.event_bus",
        SimpleNamespace(recent=lambda limit=100: events),
    )

    verdict = gate.evaluate_good_enough(
        run_id="run-1",
        iterations_done=10,
        iteration_budget=10,
        minutes_elapsed=30.0,
        minutes_budget=30.0,
    )

    assert verdict["verdict"] == "stop_now"
    assert verdict["score"] == 70.0
    assert verdict["signals"]["verify_ok"] == 1
