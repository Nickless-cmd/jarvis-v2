"""Smoke tests for db_runtime_cognition_signals.py — exercise the read/write paths against an isolated DB."""
from __future__ import annotations


def test_db_runtime_cognition_signals_read_paths_are_callable(isolated_runtime):
    import core.runtime.db_runtime_cognition_signals as m

    # LIST functions on the fresh isolated DB must run against the schema and
    # return an empty list.
    assert m.list_runtime_reflective_critics() == []
    assert m.list_runtime_awareness_signals() == []
    assert m.list_runtime_reflection_signals() == []
    assert m.list_runtime_witness_signals() == []
    assert m.list_runtime_internal_opposition_signals() == []
    assert m.list_runtime_meaning_significance_signals() == []
    assert m.list_runtime_metabolism_state_signals() == []
    assert m.list_runtime_executive_contradiction_signals() == []

    # GET functions for missing ids must return None (not raise).
    assert m.get_runtime_reflective_critic("nope") is None
    assert m.get_runtime_awareness_signal("nope") is None
    assert m.get_runtime_reflection_signal("nope") is None
    assert m.get_runtime_witness_signal("nope") is None
    assert m.get_runtime_internal_opposition_signal("nope") is None
    assert m.get_runtime_meaning_significance_signal("nope") is None
    assert m.get_runtime_metabolism_state_signal("nope") is None
    assert m.get_runtime_executive_contradiction_signal("nope") is None

    # update-status on a missing id must return None (not raise).
    assert (
        m.update_runtime_reflection_signal_status(
            "nope", status="settled", updated_at="2026-01-01T00:00:00Z"
        )
        is None
    )

    # supersede on an empty table must run and report zero rows changed.
    assert (
        m.supersede_runtime_reflection_signals_for_domain(
            domain_key="dk",
            exclude_signal_id="x",
            updated_at="2026-01-01T00:00:00Z",
            status_reason="none",
        )
        == 0
    )


def test_reflective_critic_roundtrip(isolated_runtime):
    import core.runtime.db_runtime_cognition_signals as m

    created = m.upsert_runtime_reflective_critic(
        critic_id="critic-1",
        critic_type="drift",
        canonical_key="reflective-critic:drift:demo",
        status="active",
        title="Demo critic",
        summary="A summary",
        rationale="Because reasons",
        source_kind="observation",
        confidence="medium",
        evidence_summary="evidence",
        support_summary="support",
        support_count=1,
        session_count=1,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    assert created["critic_id"] == "critic-1"
    assert created["was_created"] is True

    fetched = m.get_runtime_reflective_critic("critic-1")
    assert fetched is not None
    assert fetched["title"] == "Demo critic"

    listed = m.list_runtime_reflective_critics()
    assert any(row["critic_id"] == "critic-1" for row in listed)


def test_merget_signal_taeller_op_saa_doede_porte_kan_aabne(isolated_runtime):
    """Målt 4/11-2026: alle 15 merge-implementeringer brugte
    ``max(existing, incoming)``, mens kaldestederne sender INKREMENTET 1. Tallet
    kunne derfor aldrig vokse: 967 af 967 reflective critics stod på 1 — også de
    to der var merget 194 og 84 gange. Otte moduler har porte der var beviseligt
    døde; den vigtigste er ``self_model_signal_tracking``: ``support_count >= 2``
    er porten der skal åbne for at et selvmodel-signal overhovedet kan opstå, og
    oppositionens challenge-calibration kræver ``active_self_model``.
    """
    import core.runtime.db_runtime_cognition_signals as m

    def _upsert(session_id: str, *, evidens: str) -> dict:
        return m.upsert_runtime_reflective_critic(
            critic_id=f"critic-{session_id}-{evidens[:6]}",
            critic_type="user_correction",
            canonical_key="critic:user_correction",
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
            run_id=f"run-{session_id}-{evidens[:6]}",
            session_id=session_id,
        )

    foerste = _upsert("session-a", evidens="foerste korrektion")
    assert foerste["was_created"] is True
    assert foerste["support_count"] == 1
    assert foerste["session_count"] == 1

    anden = _upsert("session-b", evidens="anden korrektion")
    assert anden["was_created"] is False
    assert anden["support_count"] == 2, (
        "support_count steg ikke ved en NY session — så er max() tilbage, og "
        "porten support_count >= 2 kan aldrig aabne"
    )
    assert anden["session_count"] == 2

    # Samme session, NY observation: støtten stiger, sessions-tallet må ikke.
    tredje = _upsert("session-b", evidens="tredje korrektion")
    assert tredje["support_count"] == 3
    assert tredje["session_count"] == 2, (
        "samme session blev talt som en ny session — så maaler session_count kald, "
        "ikke uafhaengige sessioner"
    )

    # Helt identisk kald er ikke en ny observation og må ikke oppuste tallet.
    identisk = _upsert("session-b", evidens="tredje korrektion")
    assert identisk["merge_state"] == "unchanged", (
        "et identisk kald blev behandlet som ny støtte — så kan same_payload-grenen "
        "aldrig naas"
    )
    assert identisk["support_count"] == 3


def test_den_delte_upsert_akkumulerer_ogsaa(isolated_runtime):
    """Den håndskrevne reflective-critic er kun ÉN af 15 implementeringer.
    ``_upsert_signal`` bærer 20+ familier og havde samme ``max()`` — så testen
    holder begge veje, ikke kun den jeg først fandt.
    """
    import core.runtime.db_runtime_cognition_signals as m

    def _upsert(session_id: str, *, evidens: str) -> dict:
        return m.upsert_runtime_reflection_signal(
            signal_id=f"refl-{session_id}-{evidens[:6]}",
            signal_type="pattern",
            canonical_key="reflection-signal:pattern:demo",
            status="active",
            title="Reflection",
            summary="sum",
            rationale="rat",
            source_kind="observation",
            confidence="low",
            evidence_summary=evidens,
            support_summary="sup",
            support_count=1,
            session_count=1,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
            run_id=f"run-{session_id}-{evidens[:6]}",
            session_id=session_id,
        )

    assert _upsert("s-a", evidens="foerste")["support_count"] == 1
    anden = _upsert("s-b", evidens="anden")
    assert anden["support_count"] == 2, (
        "_upsert_signal akkumulerer stadig med max() — 20+ familier er saa stadig "
        "taerlagte"
    )
    assert anden["session_count"] == 2


def test_reflection_signal_roundtrip(isolated_runtime):
    import core.runtime.db_runtime_cognition_signals as m

    m.upsert_runtime_reflection_signal(
        signal_id="refl-1",
        signal_type="pattern",
        canonical_key="reflection-signal:pattern:demo",
        status="active",
        title="Reflection",
        summary="sum",
        rationale="rat",
        source_kind="observation",
        confidence="low",
        evidence_summary="ev",
        support_summary="sup",
        support_count=1,
        session_count=1,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )

    fetched = m.get_runtime_reflection_signal("refl-1")
    assert fetched is not None
    assert fetched["signal_id"] == "refl-1"

    listed = m.list_runtime_reflection_signals()
    assert [row["signal_id"] for row in listed] == ["refl-1"]
