"""Smoke tests for db_runtime_misc.py — exercise the read/write paths against an isolated DB."""
from __future__ import annotations


def test_db_runtime_misc_read_paths_are_callable(isolated_runtime):
    import core.runtime.db_runtime_misc as m

    # LIST / GET / summary readers on a fresh empty DB: must not raise and
    # must return empty/zero/None per each function's real return type.
    assert m.list_recurrence_iterations() == []
    assert m.get_latest_recurrence_iteration() is None
    assert m.list_broadcast_events() == []
    assert m.list_meta_cognition_records() == []
    assert m.list_attention_blink_results() == []
    assert m.session_summary_recent() == []
    assert m.session_summary_for_session("nope") is None
    assert m.signal_archive_recent() == []
    assert m.aesthetic_motif_log_unique_motifs() == []
    assert m.aesthetic_motif_log_summary() == []
    assert m.list_session_distillation_records() == []
    assert m.get_cached_affective_state() is None

    # experiment_settings: defaults to enabled=True when no row exists.
    assert m.get_experiment_enabled("unknown-exp") is True

    # cleanup helpers on empty tables delete zero rows.
    assert m.session_summary_cleanup() == 0
    assert m.signal_archive_cleanup() == 0


def test_session_summary_recent_scopes_to_current_user(isolated_runtime):
    """Værn: de nyeste summaries må ikke lække på tværs af brugere.

    Målt 6/10-2026: funktionen hentede de nyeste på tværs af ALLE brugere, og
    `build_previous_session_summaries` injicerede dem i prompten
    (transcript_sections.py:120) — så Michelles eller Mikkels samtale kunne ligge
    i Bjørns prompt mens han talte med Jarvis.
    """
    import core.runtime.db_runtime_misc as m
    from core.identity.workspace_context import reset_context, set_context
    from core.runtime.db_core import connect

    with connect() as conn:
        m._ensure_session_summaries_table(conn)
        conn.execute(
            "INSERT INTO session_summaries (session_id, summary, created_at) "
            "VALUES ('s-owner', 'ejerens samtale', '2026-09-03T10:00:00')"
        )
        conn.execute(
            "INSERT INTO session_summaries (session_id, summary, created_at) "
            "VALUES ('s-other', 'en anden brugers samtale', '2026-09-03T11:00:00')"
        )
        for sid, uid in (("s-owner", "owner-uid"), ("s-other", "other-uid")):
            conn.execute(
                "INSERT INTO chat_messages (message_id, session_id, role, content, user_id, created_at) "
                "VALUES (?, ?, 'user', 'x', ?, '2026-09-03T10:00:00')",
                (f"m-{sid}", sid, uid),
            )
        conn.commit()

    t = set_context(workspace_name="bjorn", user_id="owner-uid")
    try:
        sids = [r["session_id"] for r in m.session_summary_recent(limit=10)]
        assert "s-owner" in sids
        assert "s-other" not in sids, "en anden brugers summary lækkede ind i prompt-vejen"
    finally:
        reset_context(t)

    t = set_context(workspace_name="michelle", user_id="other-uid")
    try:
        sids = [r["session_id"] for r in m.session_summary_recent(limit=10)]
        assert "s-other" in sids, "ejeren skal kunne se sin EGEN samtale"
        assert "s-owner" not in sids
    finally:
        reset_context(t)


def test_recurrence_iteration_round_trip(isolated_runtime):
    import core.runtime.db_runtime_misc as m

    m.insert_recurrence_iteration(
        iteration_id="it-1",
        content="a stable recurring thought",
        keywords="stable recurring",
        stability_score=0.75,
        iteration_number=1,
    )
    latest = m.get_latest_recurrence_iteration()
    assert latest is not None
    assert latest["iteration_id"] == "it-1"
    assert latest["stability_score"] == 0.75

    rows = m.list_recurrence_iterations()
    assert len(rows) == 1
    assert rows[0]["iteration_id"] == "it-1"


def test_channel_attachment_round_trip(isolated_runtime):
    import core.runtime.db_runtime_misc as m
    from core.runtime.db_core import connect

    with connect() as conn:
        m.store_channel_attachment(
            conn=conn,
            attachment_id="att-1",
            session_id="sess-1",
            channel_type="discord",
            filename="photo.png",
            mime_type="image/png",
            size_bytes=123,
            local_path="/tmp/photo.png",
            source_url="",
        )
        conn.commit()

    with connect() as conn:
        got = m.get_channel_attachment(conn=conn, attachment_id="att-1")
        assert got is not None
        assert got["attachment_id"] == "att-1"
        assert got["filename"] == "photo.png"

        listed = m.list_channel_attachments(conn=conn, session_id="sess-1")
        assert len(listed) == 1
        assert listed[0]["attachment_id"] == "att-1"

        # Missing attachment returns None.
        assert m.get_channel_attachment(conn=conn, attachment_id="missing") is None
