"""Test: self-model render dropper log/event-navne (Jarvis-spec 2026-06-23 #2)."""
from __future__ import annotations

from core.services import self_model_signal_tracking as sm


def test_machine_id_title_is_dropped(monkeypatch):
    def _fake_surface(limit=5):
        return {
            "summary": {"active_count": 2},
            "items": [
                {"status": "active", "confidence": "high",
                 "title": "Strength: plugin_container_process_kill_load_reduction_success"},
                {"status": "active", "confidence": "high",
                 "title": "Strength: tålmodig og grundig fejlsøgning"},
            ],
        }
    monkeypatch.setattr(sm, "build_runtime_self_model_signal_surface", _fake_surface, raising=False)
    out = sm.build_self_model_signal_prompt_section(limit=5) or ""
    assert "plugin_container_process_kill" not in out      # maskin-id droppet
    assert "tålmodig" in out                               # menneskelæsbar beholdt


def test_porten_i_selvmodellen_aabner_naar_en_critic_er_bekraeftet_to_gange(isolated_runtime):
    """Porten er ``support_count >= 2`` (``self_model_signal_tracking:319``).

    Før 4/11-2026 kunne den aldrig opfyldes: merge brugte ``max(existing,
    incoming)`` mens kaldestederne sender INKREMENTET 1, så 967 af 967
    reflective critics stod fast på 1 — også de to der var merget 194 og 84
    gange. Otte moduler havde derfor beviseligt døde porte; selvmodellen er den
    der også sulter oppositionens ``challenge-calibration`` (den kræver
    ``active_self_model``).

    Testen måler BEGGE tilstande: én observation skal holde porten lukket, to
    uafhængige sessioner skal åbne den. Uden den første halvdel ville en
    fjernet port bestå lige så fint som en virkende.
    """
    from core.runtime.db_runtime_cognition_signals import upsert_runtime_reflective_critic

    def _critic(session_id: str, *, evidens: str) -> None:
        upsert_runtime_reflective_critic(
            critic_id=f"critic-{session_id}-{evidens[:5]}",
            critic_type="user_correction",
            canonical_key="reflective-critic:mismatch:danish-concise-calibration",
            status="active",
            title="Critic: user_correction",
            summary="Should have verified before responding",
            rationale="Auto-fired after correction",
            source_kind="cadence_producer",
            confidence="medium",
            evidence_summary=evidens,
            support_summary="outcome=failed",
            support_count=1,
            session_count=1,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            run_id=f"run-{session_id}-{evidens[:5]}",
            session_id=session_id,
        )

    besked = "kan du skrive det kortere paa dansk"

    _critic("s-a", evidens="foerste korrektion")
    foerste = sm.track_runtime_self_model_signals_for_visible_turn(
        session_id="s-a", run_id="run-1", user_message=besked
    )
    assert not [
        item
        for item in foerste.get("items", [])
        if item.get("signal_type") == "current-limitation"
    ], (
        "porten aabnede paa ÉN observation — så er support_count >= 2 ikke "
        "laengere en port, og et enkelt slip bliver til en sandhed om selvet"
    )

    _critic("s-b", evidens="anden korrektion")
    anden = sm.track_runtime_self_model_signals_for_visible_turn(
        session_id="s-b", run_id="run-2", user_message=besked
    )
    limitationer = [
        item
        for item in anden.get("items", [])
        if item.get("signal_type") == "current-limitation"
    ]
    assert limitationer, (
        "porten aabnede ikke efter to bekraeftede observationer — så er max() "
        "tilbage, og selvmodellen kan aldrig opstaa fra en critic"
    )

