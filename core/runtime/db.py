from __future__ import annotations

import sqlite3
from pathlib import Path

from core.runtime.config import STATE_DIR

DB_PATH = Path(STATE_DIR) / "jarvis.db"
_CONFIDENCE_RANKS = {"low": 1, "medium": 2, "high": 3}
_EVIDENCE_CLASS_RANKS = {
    "weak_signal": 1,
    "runtime_support_only": 2,
    "single_session_pattern": 3,
    "explicit_user_statement": 4,
    "repeated_cross_session": 5,
}
_SOURCE_KIND_RANKS = {
    "runtime-derived-support": 1,
    "single-session-pattern": 2,
    "session-evidence": 3,
    "repeated-user-correction": 3,
    "user-explicit": 4,
}


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _rank_for(ranks: dict[str, int], value: str) -> int:
    return int(ranks.get(str(value or "").strip().lower(), 0))


def _stronger_ranked_value(current: str, proposed: str, ranks: dict[str, int]) -> str:
    if _rank_for(ranks, proposed) >= _rank_for(ranks, current):
        return str(proposed or "")
    return str(current or "")


def _merge_text_fragments(current: str, proposed: str, *, limit: int = 3) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for raw in (current, proposed):
        for piece in str(raw or "").split(" | "):
            normalized = " ".join(piece.split()).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            parts.append(normalized)
            if len(parts) >= limit:
                return " | ".join(parts)
    return " | ".join(parts)


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lane TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                cost_usd REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS visible_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL UNIQUE,
                lane TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT NOT NULL,
                text_preview TEXT,
                error TEXT,
                capability_id TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS visible_work_units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_id TEXT NOT NULL UNIQUE,
                run_id TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                lane TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT NOT NULL,
                user_message_preview TEXT,
                capability_id TEXT,
                work_preview TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS visible_work_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id TEXT NOT NULL UNIQUE,
                work_id TEXT NOT NULL,
                run_id TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                lane TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                user_message_preview TEXT,
                capability_id TEXT,
                work_preview TEXT,
                projection_source TEXT,
                created_at TEXT NOT NULL,
                finished_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL UNIQUE,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id
            ON chat_messages(session_id, id)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_contract_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id TEXT NOT NULL UNIQUE,
                candidate_type TEXT NOT NULL,
                target_file TEXT NOT NULL,
                status TEXT NOT NULL,
                source_kind TEXT NOT NULL,
                source_mode TEXT NOT NULL,
                actor TEXT NOT NULL DEFAULT '',
                session_id TEXT NOT NULL DEFAULT '',
                run_id TEXT NOT NULL DEFAULT '',
                canonical_key TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                evidence_summary TEXT NOT NULL DEFAULT '',
                support_summary TEXT NOT NULL DEFAULT '',
                status_reason TEXT NOT NULL DEFAULT '',
                proposed_value TEXT NOT NULL DEFAULT '',
                write_section TEXT NOT NULL DEFAULT '',
                confidence TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_contract_candidates_status_target
            ON runtime_contract_candidates(status, target_file, id DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_contract_candidates_canonical_key
            ON runtime_contract_candidates(candidate_type, target_file, canonical_key, id DESC)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_contract_file_writes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                write_id TEXT NOT NULL UNIQUE,
                candidate_id TEXT NOT NULL,
                target_file TEXT NOT NULL,
                canonical_key TEXT NOT NULL DEFAULT '',
                write_status TEXT NOT NULL,
                actor TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL,
                content_line TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_contract_file_writes_target
            ON runtime_contract_file_writes(target_file, id DESC)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_development_focuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                focus_id TEXT NOT NULL UNIQUE,
                focus_type TEXT NOT NULL,
                canonical_key TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                title TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                rationale TEXT NOT NULL DEFAULT '',
                source_kind TEXT NOT NULL DEFAULT '',
                confidence TEXT NOT NULL DEFAULT '',
                evidence_summary TEXT NOT NULL DEFAULT '',
                support_summary TEXT NOT NULL DEFAULT '',
                status_reason TEXT NOT NULL DEFAULT '',
                run_id TEXT NOT NULL DEFAULT '',
                session_id TEXT NOT NULL DEFAULT '',
                support_count INTEGER NOT NULL DEFAULT 1,
                session_count INTEGER NOT NULL DEFAULT 1,
                merge_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_reflective_critics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                critic_id TEXT NOT NULL UNIQUE,
                critic_type TEXT NOT NULL,
                canonical_key TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                title TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                rationale TEXT NOT NULL DEFAULT '',
                source_kind TEXT NOT NULL DEFAULT '',
                confidence TEXT NOT NULL DEFAULT '',
                evidence_summary TEXT NOT NULL DEFAULT '',
                support_summary TEXT NOT NULL DEFAULT '',
                status_reason TEXT NOT NULL DEFAULT '',
                run_id TEXT NOT NULL DEFAULT '',
                session_id TEXT NOT NULL DEFAULT '',
                support_count INTEGER NOT NULL DEFAULT 1,
                session_count INTEGER NOT NULL DEFAULT 1,
                merge_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_world_model_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT NOT NULL UNIQUE,
                signal_type TEXT NOT NULL,
                canonical_key TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                title TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                rationale TEXT NOT NULL DEFAULT '',
                source_kind TEXT NOT NULL DEFAULT '',
                confidence TEXT NOT NULL DEFAULT '',
                evidence_summary TEXT NOT NULL DEFAULT '',
                support_summary TEXT NOT NULL DEFAULT '',
                status_reason TEXT NOT NULL DEFAULT '',
                run_id TEXT NOT NULL DEFAULT '',
                session_id TEXT NOT NULL DEFAULT '',
                support_count INTEGER NOT NULL DEFAULT 1,
                session_count INTEGER NOT NULL DEFAULT 1,
                merge_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_self_model_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT NOT NULL UNIQUE,
                signal_type TEXT NOT NULL,
                canonical_key TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                title TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                rationale TEXT NOT NULL DEFAULT '',
                source_kind TEXT NOT NULL DEFAULT '',
                confidence TEXT NOT NULL DEFAULT '',
                evidence_summary TEXT NOT NULL DEFAULT '',
                support_summary TEXT NOT NULL DEFAULT '',
                status_reason TEXT NOT NULL DEFAULT '',
                run_id TEXT NOT NULL DEFAULT '',
                session_id TEXT NOT NULL DEFAULT '',
                support_count INTEGER NOT NULL DEFAULT 1,
                session_count INTEGER NOT NULL DEFAULT 1,
                merge_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_goal_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id TEXT NOT NULL UNIQUE,
                goal_type TEXT NOT NULL,
                canonical_key TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                title TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                rationale TEXT NOT NULL DEFAULT '',
                source_kind TEXT NOT NULL DEFAULT '',
                confidence TEXT NOT NULL DEFAULT '',
                evidence_summary TEXT NOT NULL DEFAULT '',
                support_summary TEXT NOT NULL DEFAULT '',
                status_reason TEXT NOT NULL DEFAULT '',
                run_id TEXT NOT NULL DEFAULT '',
                session_id TEXT NOT NULL DEFAULT '',
                support_count INTEGER NOT NULL DEFAULT 1,
                session_count INTEGER NOT NULL DEFAULT 1,
                merge_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_world_model_signals_status
            ON runtime_world_model_signals(status, id DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_world_model_signals_canonical_key
            ON runtime_world_model_signals(canonical_key, id DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_self_model_signals_status
            ON runtime_self_model_signals(status, id DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_self_model_signals_canonical_key
            ON runtime_self_model_signals(canonical_key, id DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_goal_signals_status
            ON runtime_goal_signals(status, id DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_goal_signals_canonical_key
            ON runtime_goal_signals(canonical_key, id DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_reflective_critics_status
            ON runtime_reflective_critics(status, id DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_reflective_critics_canonical_key
            ON runtime_reflective_critics(canonical_key, id DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_development_focuses_status
            ON runtime_development_focuses(status, id DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_development_focuses_canonical_key
            ON runtime_development_focuses(canonical_key, id DESC)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS heartbeat_runtime_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                state_id TEXT NOT NULL UNIQUE,
                last_tick_id TEXT NOT NULL DEFAULT '',
                last_tick_at TEXT NOT NULL DEFAULT '',
                next_tick_at TEXT NOT NULL DEFAULT '',
                schedule_state TEXT NOT NULL DEFAULT '',
                due INTEGER NOT NULL DEFAULT 0,
                last_decision_type TEXT NOT NULL DEFAULT '',
                last_result TEXT NOT NULL DEFAULT '',
                blocked_reason TEXT NOT NULL DEFAULT '',
                currently_ticking INTEGER NOT NULL DEFAULT 0,
                last_trigger_source TEXT NOT NULL DEFAULT '',
                scheduler_active INTEGER NOT NULL DEFAULT 0,
                scheduler_started_at TEXT NOT NULL DEFAULT '',
                scheduler_stopped_at TEXT NOT NULL DEFAULT '',
                scheduler_health TEXT NOT NULL DEFAULT '',
                recovery_status TEXT NOT NULL DEFAULT '',
                last_recovery_at TEXT NOT NULL DEFAULT '',
                provider TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL DEFAULT '',
                lane TEXT NOT NULL DEFAULT '',
                model_source TEXT NOT NULL DEFAULT '',
                resolution_status TEXT NOT NULL DEFAULT '',
                fallback_used INTEGER NOT NULL DEFAULT 0,
                execution_status TEXT NOT NULL DEFAULT '',
                parse_status TEXT NOT NULL DEFAULT '',
                budget_status TEXT NOT NULL DEFAULT '',
                last_ping_eligible INTEGER NOT NULL DEFAULT 0,
                last_ping_result TEXT NOT NULL DEFAULT '',
                last_action_type TEXT NOT NULL DEFAULT '',
                last_action_status TEXT NOT NULL DEFAULT '',
                last_action_summary TEXT NOT NULL DEFAULT '',
                last_action_artifact TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS heartbeat_runtime_ticks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tick_id TEXT NOT NULL UNIQUE,
                trigger TEXT NOT NULL,
                tick_status TEXT NOT NULL,
                decision_type TEXT NOT NULL DEFAULT '',
                decision_summary TEXT NOT NULL DEFAULT '',
                decision_reason TEXT NOT NULL DEFAULT '',
                blocked_reason TEXT NOT NULL DEFAULT '',
                provider TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL DEFAULT '',
                lane TEXT NOT NULL DEFAULT '',
                model_source TEXT NOT NULL DEFAULT '',
                resolution_status TEXT NOT NULL DEFAULT '',
                fallback_used INTEGER NOT NULL DEFAULT 0,
                execution_status TEXT NOT NULL DEFAULT '',
                parse_status TEXT NOT NULL DEFAULT '',
                budget_status TEXT NOT NULL DEFAULT '',
                ping_eligible INTEGER NOT NULL DEFAULT 0,
                ping_result TEXT NOT NULL DEFAULT '',
                action_status TEXT NOT NULL DEFAULT '',
                action_summary TEXT NOT NULL DEFAULT '',
                action_type TEXT NOT NULL DEFAULT '',
                action_artifact TEXT NOT NULL DEFAULT '',
                raw_response TEXT NOT NULL DEFAULT '',
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                cost_usd REAL NOT NULL DEFAULT 0,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_heartbeat_runtime_ticks_finished
            ON heartbeat_runtime_ticks(id DESC)
            """
        )
        _ensure_heartbeat_runtime_state_columns(conn)
        _ensure_heartbeat_runtime_tick_columns(conn)
        _ensure_runtime_development_focus_table(conn)
        _ensure_runtime_self_model_signal_table(conn)
        _ensure_runtime_goal_signal_table(conn)
        _ensure_runtime_private_inner_note_signal_table(conn)
        _ensure_runtime_private_initiative_tension_signal_table(conn)
        _ensure_runtime_private_inner_interplay_signal_table(conn)
        _ensure_runtime_private_state_snapshot_table(conn)
        _ensure_runtime_private_temporal_curiosity_state_table(conn)
        _ensure_runtime_private_temporal_promotion_signal_table(conn)
        _ensure_runtime_inner_visible_support_signal_table(conn)
        _ensure_runtime_regulation_homeostasis_signal_table(conn)
        _ensure_runtime_relation_state_signal_table(conn)
        _ensure_runtime_relation_continuity_signal_table(conn)
        _ensure_runtime_meaning_significance_signal_table(conn)
        _ensure_runtime_temperament_tendency_signal_table(conn)
        _ensure_runtime_self_narrative_continuity_signal_table(conn)
        _ensure_runtime_metabolism_state_signal_table(conn)
        _ensure_runtime_release_marker_signal_table(conn)
        _ensure_runtime_consolidation_target_signal_table(conn)
        _ensure_runtime_selective_forgetting_candidate_table(conn)
        _ensure_runtime_attachment_topology_signal_table(conn)
        _ensure_runtime_loyalty_gradient_signal_table(conn)
        _ensure_runtime_autonomy_pressure_signal_table(conn)
        _ensure_runtime_proactive_loop_lifecycle_signal_table(conn)
        _ensure_runtime_proactive_question_gate_table(conn)
        _ensure_runtime_webchat_execution_pilot_table(conn)
        _ensure_runtime_executive_contradiction_signal_table(conn)
        _ensure_runtime_chronicle_consolidation_signal_table(conn)
        _ensure_runtime_chronicle_consolidation_brief_table(conn)
        _ensure_runtime_chronicle_consolidation_proposal_table(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS private_inner_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                run_id TEXT NOT NULL UNIQUE,
                work_id TEXT NOT NULL,
                status TEXT NOT NULL,
                note_kind TEXT NOT NULL DEFAULT '',
                focus TEXT NOT NULL DEFAULT '',
                uncertainty TEXT NOT NULL DEFAULT '',
                identity_alignment TEXT NOT NULL DEFAULT '',
                work_signal TEXT NOT NULL DEFAULT '',
                private_summary TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS private_growth_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                run_id TEXT NOT NULL UNIQUE,
                work_id TEXT NOT NULL,
                learning_kind TEXT NOT NULL,
                lesson TEXT NOT NULL,
                mistake_signal TEXT NOT NULL DEFAULT '',
                helpful_signal TEXT NOT NULL DEFAULT '',
                identity_signal TEXT NOT NULL DEFAULT '',
                confidence TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS private_self_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                identity_focus TEXT NOT NULL,
                preferred_work_mode TEXT NOT NULL,
                recurring_tension TEXT NOT NULL,
                growth_direction TEXT NOT NULL,
                confidence TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS private_reflective_selections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                run_id TEXT NOT NULL UNIQUE,
                work_id TEXT NOT NULL,
                selection_kind TEXT NOT NULL,
                reinforce TEXT NOT NULL DEFAULT '',
                reconsider TEXT NOT NULL DEFAULT '',
                fade TEXT NOT NULL DEFAULT '',
                identity_relevance TEXT NOT NULL DEFAULT '',
                confidence TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS private_development_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state_id TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                retained_pattern TEXT NOT NULL,
                preferred_direction TEXT NOT NULL,
                recurring_tension TEXT NOT NULL,
                identity_thread TEXT NOT NULL,
                confidence TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS private_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state_id TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                frustration TEXT NOT NULL,
                fatigue TEXT NOT NULL,
                confidence TEXT NOT NULL,
                curiosity TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS protected_inner_voices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voice_id TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                run_id TEXT NOT NULL UNIQUE,
                work_id TEXT NOT NULL,
                mood_tone TEXT NOT NULL,
                self_position TEXT NOT NULL,
                current_concern TEXT NOT NULL,
                current_pull TEXT NOT NULL,
                voice_line TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS private_temporal_promotion_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                run_id TEXT NOT NULL UNIQUE,
                work_id TEXT NOT NULL,
                rhythm_state TEXT NOT NULL,
                rhythm_window TEXT NOT NULL,
                promotion_target TEXT NOT NULL,
                promotion_action TEXT NOT NULL,
                promotion_confidence TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS private_promotion_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                run_id TEXT NOT NULL UNIQUE,
                work_id TEXT NOT NULL,
                promotion_target TEXT NOT NULL,
                promotion_action TEXT NOT NULL,
                promotion_scope TEXT NOT NULL,
                confidence TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS private_retained_memory_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                run_id TEXT NOT NULL UNIQUE,
                work_id TEXT NOT NULL,
                retained_value TEXT NOT NULL,
                retained_kind TEXT NOT NULL,
                retention_scope TEXT NOT NULL,
                retention_horizon TEXT NOT NULL DEFAULT 'short-term',
                confidence TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS capability_invocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                capability_id TEXT NOT NULL,
                capability_name TEXT,
                capability_kind TEXT,
                status TEXT NOT NULL,
                execution_mode TEXT NOT NULL,
                invoked_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                result_preview TEXT,
                detail TEXT,
                approval_policy TEXT,
                approval_required INTEGER NOT NULL DEFAULT 0,
                approved INTEGER NOT NULL DEFAULT 0,
                granted INTEGER NOT NULL DEFAULT 0,
                run_id TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS capability_approval_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL UNIQUE,
                capability_id TEXT NOT NULL,
                capability_name TEXT,
                capability_kind TEXT,
                execution_mode TEXT NOT NULL,
                approval_policy TEXT,
                run_id TEXT,
                requested_at TEXT NOT NULL,
                status TEXT NOT NULL,
                approved_at TEXT,
                executed INTEGER NOT NULL DEFAULT 0,
                executed_at TEXT,
                invocation_status TEXT,
                invocation_execution_mode TEXT
            )
            """
        )
        _ensure_private_inner_note_columns(conn)
        _ensure_private_retained_memory_record_columns(conn)
        _ensure_capability_invocation_approval_columns(conn)
        _ensure_capability_approval_request_columns(conn)
        _ensure_runtime_user_understanding_signal_table(conn)
        _ensure_runtime_remembered_fact_signal_table(conn)
        _ensure_runtime_memory_md_update_proposal_table(conn)
        _ensure_runtime_selfhood_proposal_table(conn)
        conn.commit()


def _ensure_private_retained_memory_record_columns(conn: sqlite3.Connection) -> None:
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(private_retained_memory_records)")
    }
    if "retention_horizon" not in columns:
        conn.execute(
            """
            ALTER TABLE private_retained_memory_records
            ADD COLUMN retention_horizon TEXT NOT NULL DEFAULT 'short-term'
            """
        )


def recent_visible_runs(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                run_id,
                lane,
                provider,
                model,
                status,
                started_at,
                finished_at,
                text_preview,
                error,
                capability_id
            FROM visible_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "run_id": row["run_id"],
            "lane": row["lane"],
            "provider": row["provider"],
            "model": row["model"],
            "status": row["status"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "text_preview": row["text_preview"],
            "error": row["error"],
            "capability_id": row["capability_id"],
        }
        for row in rows
    ]


def recent_visible_work_units(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                work_id,
                run_id,
                status,
                lane,
                provider,
                model,
                started_at,
                finished_at,
                user_message_preview,
                capability_id,
                work_preview
            FROM visible_work_units
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "work_id": row["work_id"],
            "run_id": row["run_id"],
            "status": row["status"],
            "lane": row["lane"],
            "provider": row["provider"],
            "model": row["model"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "user_message_preview": row["user_message_preview"],
            "capability_id": row["capability_id"],
            "work_preview": row["work_preview"],
        }
        for row in rows
    ]


def recent_visible_work_notes(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                note_id,
                work_id,
                run_id,
                status,
                lane,
                provider,
                model,
                user_message_preview,
                capability_id,
                work_preview,
                projection_source,
                created_at,
                finished_at
            FROM visible_work_notes
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "note_id": row["note_id"],
            "work_id": row["work_id"],
            "run_id": row["run_id"],
            "status": row["status"],
            "lane": row["lane"],
            "provider": row["provider"],
            "model": row["model"],
            "user_message_preview": row["user_message_preview"],
            "capability_id": row["capability_id"],
            "work_preview": row["work_preview"],
            "projection_source": row["projection_source"],
            "created_at": row["created_at"],
            "finished_at": row["finished_at"],
        }
        for row in rows
    ]


def record_private_inner_note(
    *,
    note_id: str,
    source: str,
    run_id: str,
    work_id: str,
    status: str,
    note_kind: str,
    focus: str,
    uncertainty: str,
    identity_alignment: str,
    work_signal: str,
    private_summary: str,
    created_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_inner_notes (
                note_id, source, run_id, work_id, status, note_kind, focus,
                uncertainty, identity_alignment, work_signal, private_summary, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                note_id=excluded.note_id,
                source=excluded.source,
                work_id=excluded.work_id,
                status=excluded.status,
                note_kind=excluded.note_kind,
                focus=excluded.focus,
                uncertainty=excluded.uncertainty,
                identity_alignment=excluded.identity_alignment,
                work_signal=excluded.work_signal,
                private_summary=excluded.private_summary,
                created_at=excluded.created_at
            """,
            (
                note_id,
                source,
                run_id,
                work_id,
                status,
                note_kind,
                focus,
                uncertainty,
                identity_alignment,
                work_signal,
                private_summary,
                created_at,
            ),
        )
        conn.commit()


def recent_private_inner_notes(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                note_id,
                source,
                run_id,
                work_id,
                status,
                note_kind,
                focus,
                uncertainty,
                identity_alignment,
                work_signal,
                private_summary,
                created_at
            FROM private_inner_notes
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "note_id": row["note_id"],
            "source": row["source"],
            "run_id": row["run_id"],
            "work_id": row["work_id"],
            "status": row["status"],
            "note_kind": row["note_kind"],
            "focus": row["focus"],
            "uncertainty": row["uncertainty"],
            "identity_alignment": row["identity_alignment"],
            "work_signal": row["work_signal"],
            "private_summary": row["private_summary"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def record_private_growth_note(
    *,
    record_id: str,
    source: str,
    run_id: str,
    work_id: str,
    learning_kind: str,
    lesson: str,
    mistake_signal: str,
    helpful_signal: str,
    identity_signal: str,
    confidence: str,
    created_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_growth_notes (
                record_id, source, run_id, work_id, learning_kind, lesson,
                mistake_signal, helpful_signal, identity_signal, confidence, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                record_id=excluded.record_id,
                source=excluded.source,
                work_id=excluded.work_id,
                learning_kind=excluded.learning_kind,
                lesson=excluded.lesson,
                mistake_signal=excluded.mistake_signal,
                helpful_signal=excluded.helpful_signal,
                identity_signal=excluded.identity_signal,
                confidence=excluded.confidence,
                created_at=excluded.created_at
            """,
            (
                record_id,
                source,
                run_id,
                work_id,
                learning_kind,
                lesson,
                mistake_signal,
                helpful_signal,
                identity_signal,
                confidence,
                created_at,
            ),
        )
        conn.commit()


def recent_private_growth_notes(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                record_id,
                source,
                run_id,
                work_id,
                learning_kind,
                lesson,
                mistake_signal,
                helpful_signal,
                identity_signal,
                confidence,
                created_at
            FROM private_growth_notes
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "record_id": row["record_id"],
            "source": row["source"],
            "run_id": row["run_id"],
            "work_id": row["work_id"],
            "learning_kind": row["learning_kind"],
            "lesson": row["lesson"],
            "mistake_signal": row["mistake_signal"],
            "helpful_signal": row["helpful_signal"],
            "identity_signal": row["identity_signal"],
            "confidence": row["confidence"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def record_private_self_model(
    *,
    model_id: str,
    source: str,
    identity_focus: str,
    preferred_work_mode: str,
    recurring_tension: str,
    growth_direction: str,
    confidence: str,
    created_at: str,
    updated_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_self_models (
                model_id, source, identity_focus, preferred_work_mode,
                recurring_tension, growth_direction, confidence, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(model_id) DO UPDATE SET
                source=excluded.source,
                identity_focus=excluded.identity_focus,
                preferred_work_mode=excluded.preferred_work_mode,
                recurring_tension=excluded.recurring_tension,
                growth_direction=excluded.growth_direction,
                confidence=excluded.confidence,
                created_at=excluded.created_at,
                updated_at=excluded.updated_at
            """,
            (
                model_id,
                source,
                identity_focus,
                preferred_work_mode,
                recurring_tension,
                growth_direction,
                confidence,
                created_at,
                updated_at,
            ),
        )
        conn.commit()


def get_private_self_model() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                model_id,
                source,
                identity_focus,
                preferred_work_mode,
                recurring_tension,
                growth_direction,
                confidence,
                created_at,
                updated_at
            FROM private_self_models
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "model_id": row["model_id"],
        "source": row["source"],
        "identity_focus": row["identity_focus"],
        "preferred_work_mode": row["preferred_work_mode"],
        "recurring_tension": row["recurring_tension"],
        "growth_direction": row["growth_direction"],
        "confidence": row["confidence"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def record_private_reflective_selection(
    *,
    signal_id: str,
    source: str,
    run_id: str,
    work_id: str,
    selection_kind: str,
    reinforce: str,
    reconsider: str,
    fade: str,
    identity_relevance: str,
    confidence: str,
    created_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_reflective_selections (
                signal_id, source, run_id, work_id, selection_kind,
                reinforce, reconsider, fade, identity_relevance, confidence, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                signal_id=excluded.signal_id,
                source=excluded.source,
                work_id=excluded.work_id,
                selection_kind=excluded.selection_kind,
                reinforce=excluded.reinforce,
                reconsider=excluded.reconsider,
                fade=excluded.fade,
                identity_relevance=excluded.identity_relevance,
                confidence=excluded.confidence,
                created_at=excluded.created_at
            """,
            (
                signal_id,
                source,
                run_id,
                work_id,
                selection_kind,
                reinforce,
                reconsider,
                fade,
                identity_relevance,
                confidence,
                created_at,
            ),
        )
        conn.commit()


def recent_private_reflective_selections(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                signal_id,
                source,
                run_id,
                work_id,
                selection_kind,
                reinforce,
                reconsider,
                fade,
                identity_relevance,
                confidence,
                created_at
            FROM private_reflective_selections
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "signal_id": row["signal_id"],
            "source": row["source"],
            "run_id": row["run_id"],
            "work_id": row["work_id"],
            "selection_kind": row["selection_kind"],
            "reinforce": row["reinforce"],
            "reconsider": row["reconsider"],
            "fade": row["fade"],
            "identity_relevance": row["identity_relevance"],
            "confidence": row["confidence"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def record_private_development_state(
    *,
    state_id: str,
    source: str,
    retained_pattern: str,
    preferred_direction: str,
    recurring_tension: str,
    identity_thread: str,
    confidence: str,
    created_at: str,
    updated_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_development_states (
                state_id, source, retained_pattern, preferred_direction,
                recurring_tension, identity_thread, confidence, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(state_id) DO UPDATE SET
                source=excluded.source,
                retained_pattern=excluded.retained_pattern,
                preferred_direction=excluded.preferred_direction,
                recurring_tension=excluded.recurring_tension,
                identity_thread=excluded.identity_thread,
                confidence=excluded.confidence,
                created_at=excluded.created_at,
                updated_at=excluded.updated_at
            """,
            (
                state_id,
                source,
                retained_pattern,
                preferred_direction,
                recurring_tension,
                identity_thread,
                confidence,
                created_at,
                updated_at,
            ),
        )
        conn.commit()


def get_private_development_state() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                state_id,
                source,
                retained_pattern,
                preferred_direction,
                recurring_tension,
                identity_thread,
                confidence,
                created_at,
                updated_at
            FROM private_development_states
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "state_id": row["state_id"],
        "source": row["source"],
        "retained_pattern": row["retained_pattern"],
        "preferred_direction": row["preferred_direction"],
        "recurring_tension": row["recurring_tension"],
        "identity_thread": row["identity_thread"],
        "confidence": row["confidence"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_private_reflective_selection() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                signal_id,
                source,
                run_id,
                work_id,
                selection_kind,
                reinforce,
                reconsider,
                fade,
                identity_relevance,
                confidence,
                created_at
            FROM private_reflective_selections
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "signal_id": row["signal_id"],
        "source": row["source"],
        "run_id": row["run_id"],
        "work_id": row["work_id"],
        "selection_kind": row["selection_kind"],
        "reinforce": row["reinforce"],
        "reconsider": row["reconsider"],
        "fade": row["fade"],
        "identity_relevance": row["identity_relevance"],
        "confidence": row["confidence"],
        "created_at": row["created_at"],
    }


def record_private_state(
    *,
    state_id: str,
    source: str,
    frustration: str,
    fatigue: str,
    confidence: str,
    curiosity: str,
    created_at: str,
    updated_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_states (
                state_id, source, frustration, fatigue, confidence, curiosity,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(state_id) DO UPDATE SET
                source=excluded.source,
                frustration=excluded.frustration,
                fatigue=excluded.fatigue,
                confidence=excluded.confidence,
                curiosity=excluded.curiosity,
                created_at=excluded.created_at,
                updated_at=excluded.updated_at
            """,
            (
                state_id,
                source,
                frustration,
                fatigue,
                confidence,
                curiosity,
                created_at,
                updated_at,
            ),
        )
        conn.commit()


def get_private_state() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                state_id,
                source,
                frustration,
                fatigue,
                confidence,
                curiosity,
                created_at,
                updated_at
            FROM private_states
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "state_id": row["state_id"],
        "source": row["source"],
        "frustration": row["frustration"],
        "fatigue": row["fatigue"],
        "confidence": row["confidence"],
        "curiosity": row["curiosity"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def record_protected_inner_voice(
    *,
    voice_id: str,
    source: str,
    run_id: str,
    work_id: str,
    mood_tone: str,
    self_position: str,
    current_concern: str,
    current_pull: str,
    voice_line: str,
    created_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO protected_inner_voices (
                voice_id, source, run_id, work_id, mood_tone, self_position,
                current_concern, current_pull, voice_line, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                voice_id=excluded.voice_id,
                source=excluded.source,
                work_id=excluded.work_id,
                mood_tone=excluded.mood_tone,
                self_position=excluded.self_position,
                current_concern=excluded.current_concern,
                current_pull=excluded.current_pull,
                voice_line=excluded.voice_line,
                created_at=excluded.created_at
            """,
            (
                voice_id,
                source,
                run_id,
                work_id,
                mood_tone,
                self_position,
                current_concern,
                current_pull,
                voice_line,
                created_at,
            ),
        )
        conn.commit()


def get_protected_inner_voice() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                voice_id,
                source,
                run_id,
                work_id,
                mood_tone,
                self_position,
                current_concern,
                current_pull,
                voice_line,
                created_at
            FROM protected_inner_voices
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "voice_id": row["voice_id"],
        "source": row["source"],
        "run_id": row["run_id"],
        "work_id": row["work_id"],
        "mood_tone": row["mood_tone"],
        "self_position": row["self_position"],
        "current_concern": row["current_concern"],
        "current_pull": row["current_pull"],
        "voice_line": row["voice_line"],
        "created_at": row["created_at"],
    }


def record_private_temporal_promotion_signal(
    *,
    signal_id: str,
    source: str,
    run_id: str,
    work_id: str,
    rhythm_state: str,
    rhythm_window: str,
    promotion_target: str,
    promotion_action: str,
    promotion_confidence: str,
    created_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_temporal_promotion_signals (
                signal_id, source, run_id, work_id, rhythm_state, rhythm_window,
                promotion_target, promotion_action, promotion_confidence, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                signal_id=excluded.signal_id,
                source=excluded.source,
                work_id=excluded.work_id,
                rhythm_state=excluded.rhythm_state,
                rhythm_window=excluded.rhythm_window,
                promotion_target=excluded.promotion_target,
                promotion_action=excluded.promotion_action,
                promotion_confidence=excluded.promotion_confidence,
                created_at=excluded.created_at
            """,
            (
                signal_id,
                source,
                run_id,
                work_id,
                rhythm_state,
                rhythm_window,
                promotion_target,
                promotion_action,
                promotion_confidence,
                created_at,
            ),
        )
        conn.commit()


def get_private_temporal_promotion_signal() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                signal_id,
                source,
                run_id,
                work_id,
                rhythm_state,
                rhythm_window,
                promotion_target,
                promotion_action,
                promotion_confidence,
                created_at
            FROM private_temporal_promotion_signals
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "signal_id": row["signal_id"],
        "source": row["source"],
        "run_id": row["run_id"],
        "work_id": row["work_id"],
        "rhythm_state": row["rhythm_state"],
        "rhythm_window": row["rhythm_window"],
        "promotion_target": row["promotion_target"],
        "promotion_action": row["promotion_action"],
        "promotion_confidence": row["promotion_confidence"],
        "created_at": row["created_at"],
    }


def record_private_promotion_decision(
    *,
    decision_id: str,
    source: str,
    run_id: str,
    work_id: str,
    promotion_target: str,
    promotion_action: str,
    promotion_scope: str,
    confidence: str,
    created_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_promotion_decisions (
                decision_id, source, run_id, work_id, promotion_target,
                promotion_action, promotion_scope, confidence, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                decision_id=excluded.decision_id,
                source=excluded.source,
                work_id=excluded.work_id,
                promotion_target=excluded.promotion_target,
                promotion_action=excluded.promotion_action,
                promotion_scope=excluded.promotion_scope,
                confidence=excluded.confidence,
                created_at=excluded.created_at
            """,
            (
                decision_id,
                source,
                run_id,
                work_id,
                promotion_target,
                promotion_action,
                promotion_scope,
                confidence,
                created_at,
            ),
        )
        conn.commit()


def get_private_promotion_decision() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                decision_id,
                source,
                run_id,
                work_id,
                promotion_target,
                promotion_action,
                promotion_scope,
                confidence,
                created_at
            FROM private_promotion_decisions
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "decision_id": row["decision_id"],
        "source": row["source"],
        "run_id": row["run_id"],
        "work_id": row["work_id"],
        "promotion_target": row["promotion_target"],
        "promotion_action": row["promotion_action"],
        "promotion_scope": row["promotion_scope"],
        "confidence": row["confidence"],
        "created_at": row["created_at"],
    }


def record_private_retained_memory_record(
    *,
    record_id: str,
    source: str,
    run_id: str,
    work_id: str,
    retained_value: str,
    retained_kind: str,
    retention_scope: str,
    retention_horizon: str,
    confidence: str,
    created_at: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO private_retained_memory_records (
                record_id, source, run_id, work_id, retained_value,
                retained_kind, retention_scope, retention_horizon, confidence, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                record_id=excluded.record_id,
                source=excluded.source,
                work_id=excluded.work_id,
                retained_value=excluded.retained_value,
                retained_kind=excluded.retained_kind,
                retention_scope=excluded.retention_scope,
                retention_horizon=excluded.retention_horizon,
                confidence=excluded.confidence,
                created_at=excluded.created_at
            """,
            (
                record_id,
                source,
                run_id,
                work_id,
                retained_value,
                retained_kind,
                retention_scope,
                retention_horizon,
                confidence,
                created_at,
            ),
        )
        conn.commit()


def get_private_retained_memory_record() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                record_id,
                source,
                run_id,
                work_id,
                retained_value,
                retained_kind,
                retention_scope,
                retention_horizon,
                confidence,
                created_at
            FROM private_retained_memory_records
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return {
        "record_id": row["record_id"],
        "source": row["source"],
        "run_id": row["run_id"],
        "work_id": row["work_id"],
        "retained_value": row["retained_value"],
        "retained_kind": row["retained_kind"],
        "retention_scope": row["retention_scope"],
        "retention_horizon": row["retention_horizon"],
        "confidence": row["confidence"],
        "created_at": row["created_at"],
    }


def recent_private_retained_memory_records(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                record_id,
                source,
                run_id,
                work_id,
                retained_value,
                retained_kind,
                retention_scope,
                retention_horizon,
                confidence,
                created_at
            FROM private_retained_memory_records
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "record_id": row["record_id"],
            "source": row["source"],
            "run_id": row["run_id"],
            "work_id": row["work_id"],
            "retained_value": row["retained_value"],
            "retained_kind": row["retained_kind"],
            "retention_scope": row["retention_scope"],
            "retention_horizon": row["retention_horizon"],
            "confidence": row["confidence"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def recent_capability_invocations(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                capability_id,
                capability_name,
                capability_kind,
                status,
                execution_mode,
                invoked_at,
                finished_at,
                result_preview,
                detail,
                approval_policy,
                approval_required,
                approved,
                granted,
                run_id
            FROM capability_invocations
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "capability_id": row["capability_id"],
            "capability_name": row["capability_name"],
            "capability_kind": row["capability_kind"],
            "status": row["status"],
            "execution_mode": row["execution_mode"],
            "invoked_at": row["invoked_at"],
            "finished_at": row["finished_at"],
            "result_preview": row["result_preview"],
            "detail": row["detail"],
            "approval": {
                "policy": row["approval_policy"],
                "required": bool(row["approval_required"]),
                "approved": bool(row["approved"]),
                "granted": bool(row["granted"]),
            },
            "run_id": row["run_id"],
        }
        for row in rows
    ]


def _ensure_capability_invocation_approval_columns(conn: sqlite3.Connection) -> None:
    rows = conn.execute("PRAGMA table_info(capability_invocations)").fetchall()
    existing = {str(row["name"]) for row in rows}
    required_columns = {
        "approval_policy": "TEXT",
        "approval_required": "INTEGER NOT NULL DEFAULT 0",
        "approved": "INTEGER NOT NULL DEFAULT 0",
        "granted": "INTEGER NOT NULL DEFAULT 0",
    }
    for name, spec in required_columns.items():
        if name in existing:
            continue
        conn.execute(f"ALTER TABLE capability_invocations ADD COLUMN {name} {spec}")


def _ensure_private_inner_note_columns(conn: sqlite3.Connection) -> None:
    rows = conn.execute("PRAGMA table_info(private_inner_notes)").fetchall()
    existing = {str(row["name"]) for row in rows}
    required_columns = {
        "note_kind": "TEXT NOT NULL DEFAULT ''",
        "focus": "TEXT NOT NULL DEFAULT ''",
        "uncertainty": "TEXT NOT NULL DEFAULT ''",
        "identity_alignment": "TEXT NOT NULL DEFAULT ''",
        "work_signal": "TEXT NOT NULL DEFAULT ''",
    }
    for name, spec in required_columns.items():
        if name in existing:
            continue
        conn.execute(f"ALTER TABLE private_inner_notes ADD COLUMN {name} {spec}")


def visible_session_continuity() -> dict[str, object]:
    recent_runs = recent_visible_runs(limit=1)
    recent_invocations = recent_capability_invocations(limit=2)
    latest_run = recent_runs[0] if recent_runs else {}
    recent_capability_ids = [
        capability_id
        for item in recent_invocations
        if (capability_id := str(item.get("capability_id") or "").strip())
    ]
    return {
        "active": bool(latest_run or recent_invocations),
        "source": "persisted-visible-runs+capability-invocations",
        "latest_run_id": latest_run.get("run_id"),
        "latest_status": latest_run.get("status"),
        "latest_finished_at": latest_run.get("finished_at"),
        "latest_text_preview": latest_run.get("text_preview"),
        "latest_capability_id": latest_run.get("capability_id"),
        "recent_capability_ids": recent_capability_ids,
        "included_run_rows": len(recent_runs),
        "included_capability_rows": len(recent_invocations),
    }


def recent_capability_approval_requests(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                request_id,
                capability_id,
                capability_name,
                capability_kind,
                execution_mode,
                approval_policy,
                run_id,
                requested_at,
                status,
                approved_at,
                executed,
                executed_at,
                invocation_status,
                invocation_execution_mode
            FROM capability_approval_requests
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [_capability_approval_request_from_row(row) for row in rows]


def get_capability_approval_request(request_id: str) -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                request_id,
                capability_id,
                capability_name,
                capability_kind,
                execution_mode,
                approval_policy,
                run_id,
                requested_at,
                status,
                approved_at,
                executed,
                executed_at,
                invocation_status,
                invocation_execution_mode
            FROM capability_approval_requests
            WHERE request_id = ?
            """,
            (request_id,),
        ).fetchone()
    if row is None:
        return None
    return _capability_approval_request_from_row(row)


def approve_capability_approval_request(
    request_id: str, *, approved_at: str
) -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                request_id,
                capability_id,
                capability_name,
                capability_kind,
                execution_mode,
                approval_policy,
                run_id,
                requested_at,
                status,
                approved_at,
                executed,
                executed_at,
                invocation_status,
                invocation_execution_mode
            FROM capability_approval_requests
            WHERE request_id = ?
            """,
            (request_id,),
        ).fetchone()
        if row is None:
            return None

        status = str(row["status"] or "")
        final_approved_at = row["approved_at"]
        if status == "pending":
            conn.execute(
                """
                UPDATE capability_approval_requests
                SET status = ?, approved_at = ?
                WHERE request_id = ?
                """,
                ("approved", approved_at, request_id),
            )
            conn.commit()
            status = "approved"
            final_approved_at = approved_at

    return _capability_approval_request_from_row(
        row,
        status=status,
        approved_at=final_approved_at,
    )


def record_capability_approval_request_execution(
    request_id: str,
    *,
    executed_at: str,
    invocation_status: str,
    invocation_execution_mode: str,
) -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                request_id,
                capability_id,
                capability_name,
                capability_kind,
                execution_mode,
                approval_policy,
                run_id,
                requested_at,
                status,
                approved_at,
                executed,
                executed_at,
                invocation_status,
                invocation_execution_mode
            FROM capability_approval_requests
            WHERE request_id = ?
            """,
            (request_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE capability_approval_requests
            SET
                executed = ?,
                executed_at = ?,
                invocation_status = ?,
                invocation_execution_mode = ?
            WHERE request_id = ?
            """,
            (1, executed_at, invocation_status, invocation_execution_mode, request_id),
        )
        conn.commit()
    return _capability_approval_request_from_row(
        row,
        executed=True,
        executed_at=executed_at,
        invocation_status=invocation_status,
        invocation_execution_mode=invocation_execution_mode,
    )


def _capability_approval_request_from_row(
    row: sqlite3.Row,
    *,
    status: str | None = None,
    approved_at: str | None = None,
    executed: bool | None = None,
    executed_at: str | None = None,
    invocation_status: str | None = None,
    invocation_execution_mode: str | None = None,
) -> dict[str, object]:
    return {
        "request_id": row["request_id"],
        "capability_id": row["capability_id"],
        "capability_name": row["capability_name"],
        "capability_kind": row["capability_kind"],
        "execution_mode": row["execution_mode"],
        "approval_policy": row["approval_policy"],
        "run_id": row["run_id"],
        "requested_at": row["requested_at"],
        "status": status if status is not None else row["status"],
        "approved_at": approved_at if approved_at is not None else row["approved_at"],
        "executed": executed if executed is not None else bool(row["executed"]),
        "executed_at": executed_at if executed_at is not None else row["executed_at"],
        "invocation_status": (
            invocation_status
            if invocation_status is not None
            else row["invocation_status"]
        ),
        "invocation_execution_mode": (
            invocation_execution_mode
            if invocation_execution_mode is not None
            else row["invocation_execution_mode"]
        ),
    }


def _ensure_capability_approval_request_columns(conn: sqlite3.Connection) -> None:
    rows = conn.execute("PRAGMA table_info(capability_approval_requests)").fetchall()
    existing = {str(row["name"]) for row in rows}
    required_columns = {
        "approved_at": "TEXT",
        "executed": "INTEGER NOT NULL DEFAULT 0",
        "executed_at": "TEXT",
        "invocation_status": "TEXT",
        "invocation_execution_mode": "TEXT",
    }
    for name, spec in required_columns.items():
        if name in existing:
            continue
        conn.execute(
            f"ALTER TABLE capability_approval_requests ADD COLUMN {name} {spec}"
        )


def upsert_runtime_contract_candidate(
    *,
    candidate_id: str,
    candidate_type: str,
    target_file: str,
    status: str,
    source_kind: str,
    source_mode: str,
    actor: str,
    session_id: str,
    run_id: str,
    canonical_key: str,
    summary: str,
    reason: str,
    evidence_summary: str,
    support_summary: str,
    confidence: str,
    evidence_class: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    proposed_value: str = "",
    write_section: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_contract_candidate_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    candidate_id,
                    status,
                    source_kind,
                    source_mode,
                    actor,
                    session_id,
                    run_id,
                    summary,
                    reason,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    proposed_value,
                    write_section,
                    confidence,
                    evidence_class,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_contract_candidates
                WHERE candidate_type = ?
                  AND target_file = ?
                  AND canonical_key = ?
                  AND status IN ('proposed', 'approved')
                ORDER BY id DESC
                LIMIT 1
                """,
                (candidate_type, target_file, canonical_key),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_contract_candidates (
                    candidate_id,
                    candidate_type,
                    target_file,
                    status,
                    source_kind,
                    source_mode,
                    actor,
                    session_id,
                    run_id,
                    canonical_key,
                    summary,
                    reason,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    proposed_value,
                    write_section,
                    confidence,
                    evidence_class,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id,
                    candidate_type,
                    target_file,
                    status,
                    source_kind,
                    source_mode,
                    actor,
                    session_id,
                    run_id,
                    canonical_key,
                    summary,
                    reason,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    proposed_value,
                    write_section,
                    confidence,
                    evidence_class,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = candidate_id
            upsert_meta = {
                "was_created": True,
                "was_updated": True,
                "merge_state": "created",
            }
        else:
            resolved_id = str(existing["candidate_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_class = _stronger_ranked_value(
                str(existing["evidence_class"] or ""),
                evidence_class,
                _EVIDENCE_CLASS_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0),
                max(int(support_count or 0), 1),
            )
            merged_session_count = max(
                int(existing["session_count"] or 0),
                max(int(session_count or 0), 1),
            )
            merged_summary = summary
            merged_reason = reason
            if _rank_for(_EVIDENCE_CLASS_RANKS, evidence_class) < _rank_for(
                _EVIDENCE_CLASS_RANKS,
                str(existing["evidence_class"] or ""),
            ):
                merged_summary = str(existing["summary"] or "")
                merged_reason = str(existing["reason"] or "")
            merged_status = (
                str(existing["status"] or "")
                if str(existing["status"] or "") == "approved"
                else status
            )
            same_payload = (
                merged_status == str(existing["status"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and source_mode == str(existing["source_mode"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_summary == str(existing["summary"] or "")
                and merged_reason == str(existing["reason"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and proposed_value == str(existing["proposed_value"] or "")
                and write_section == str(existing["write_section"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_class == str(existing["evidence_class"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                upsert_meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_contract_candidates
                    SET
                        status = ?,
                        source_kind = ?,
                        source_mode = ?,
                        actor = ?,
                        session_id = ?,
                        run_id = ?,
                        summary = ?,
                        reason = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        proposed_value = ?,
                        write_section = ?,
                        confidence = ?,
                        evidence_class = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE candidate_id = ?
                    """,
                    (
                        merged_status,
                        merged_source_kind,
                        source_mode,
                        actor,
                        session_id,
                        run_id,
                        merged_summary,
                        merged_reason,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        proposed_value,
                        write_section,
                        merged_confidence,
                        merged_evidence_class,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                upsert_meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    candidate = get_runtime_contract_candidate(resolved_id)
    if candidate is None:
        raise RuntimeError("runtime contract candidate was not persisted")
    candidate.update(upsert_meta)
    return candidate


def list_runtime_contract_candidates(
    *,
    candidate_type: str | None = None,
    target_file: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_contract_candidate_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if candidate_type:
            clauses.append("candidate_type = ?")
            params.append(candidate_type)
        if target_file:
            clauses.append("target_file = ?")
            params.append(target_file)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                candidate_id,
                candidate_type,
                target_file,
                status,
                source_kind,
                source_mode,
                actor,
                session_id,
                run_id,
                canonical_key,
                summary,
                reason,
                evidence_summary,
                support_summary,
                status_reason,
                proposed_value,
                write_section,
                confidence,
                evidence_class,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_contract_candidates
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_contract_candidate_from_row(row) for row in rows]


def get_runtime_contract_candidate(candidate_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_contract_candidate_table(conn)
        row = conn.execute(
            """
            SELECT
                candidate_id,
                candidate_type,
                target_file,
                status,
                source_kind,
                source_mode,
                actor,
                session_id,
                run_id,
                canonical_key,
                summary,
                reason,
                evidence_summary,
                support_summary,
                status_reason,
                proposed_value,
                write_section,
                confidence,
                evidence_class,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_contract_candidates
            WHERE candidate_id = ?
            LIMIT 1
            """,
            (candidate_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_contract_candidate_from_row(row)


def runtime_contract_candidate_counts() -> dict[str, int]:
    with connect() as conn:
        _ensure_runtime_contract_candidate_table(conn)
        rows = conn.execute(
            """
            SELECT candidate_type, status, COUNT(*) AS n
            FROM runtime_contract_candidates
            GROUP BY candidate_type, status
            """
        ).fetchall()
    counts: dict[str, int] = {}
    for row in rows:
        key = f"{row['candidate_type']}:{row['status']}"
        counts[key] = int(row["n"] or 0)
    return counts


def update_runtime_contract_candidate_status(
    candidate_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_contract_candidate_table(conn)
        row = conn.execute(
            """
            SELECT candidate_id
            FROM runtime_contract_candidates
            WHERE candidate_id = ?
            LIMIT 1
            """,
            (candidate_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_contract_candidates
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE candidate_id = ?
            """,
            (status, status_reason, updated_at, candidate_id),
        )
        conn.commit()
    return get_runtime_contract_candidate(candidate_id)


def supersede_runtime_contract_candidates(
    *,
    candidate_type: str,
    target_file: str,
    canonical_key: str,
    exclude_candidate_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    if not canonical_key:
        return 0
    with connect() as conn:
        _ensure_runtime_contract_candidate_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_contract_candidates
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE candidate_type = ?
              AND target_file = ?
              AND canonical_key = ?
              AND candidate_id != ?
              AND status IN ('proposed', 'approved')
            """,
            (
                status_reason,
                updated_at,
                candidate_type,
                target_file,
                canonical_key,
                exclude_candidate_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def record_runtime_contract_file_write(
    *,
    write_id: str,
    candidate_id: str,
    target_file: str,
    canonical_key: str,
    write_status: str,
    actor: str,
    summary: str,
    content_line: str,
    created_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_contract_file_write_table(conn)
        conn.execute(
            """
            INSERT INTO runtime_contract_file_writes (
                write_id,
                candidate_id,
                target_file,
                canonical_key,
                write_status,
                actor,
                summary,
                content_line,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                write_id,
                candidate_id,
                target_file,
                canonical_key,
                write_status,
                actor,
                summary,
                content_line,
                created_at,
            ),
        )
        conn.commit()
    write = get_runtime_contract_file_write(write_id)
    if write is None:
        raise RuntimeError("runtime contract file write was not persisted")
    return write


def get_runtime_contract_file_write(write_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_contract_file_write_table(conn)
        row = conn.execute(
            """
            SELECT
                write_id,
                candidate_id,
                target_file,
                canonical_key,
                write_status,
                actor,
                summary,
                content_line,
                created_at
            FROM runtime_contract_file_writes
            WHERE write_id = ?
            LIMIT 1
            """,
            (write_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_contract_file_write_from_row(row)


def recent_runtime_contract_file_writes(limit: int = 10) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_contract_file_write_table(conn)
        rows = conn.execute(
            """
            SELECT
                write_id,
                candidate_id,
                target_file,
                canonical_key,
                write_status,
                actor,
                summary,
                content_line,
                created_at
            FROM runtime_contract_file_writes
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [_runtime_contract_file_write_from_row(row) for row in rows]


def runtime_contract_file_write_counts() -> dict[str, int]:
    with connect() as conn:
        _ensure_runtime_contract_file_write_table(conn)
        rows = conn.execute(
            """
            SELECT target_file, write_status, COUNT(*) AS n
            FROM runtime_contract_file_writes
            GROUP BY target_file, write_status
            """
        ).fetchall()
    counts: dict[str, int] = {}
    for row in rows:
        key = f"{row['target_file']}:{row['write_status']}"
        counts[key] = int(row["n"] or 0)
    return counts


def upsert_runtime_development_focus(
    *,
    focus_id: str,
    focus_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_development_focus_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    focus_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_development_focuses
                WHERE canonical_key = ?
                  AND status IN ('active', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_development_focuses (
                    focus_id,
                    focus_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    focus_id,
                    focus_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = focus_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["focus_id"])
            merged_status = (
                "active"
                if status == "active"
                else str(status or existing["status"] or "active")
            )
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0),
                max(int(support_count or 0), 1),
            )
            merged_session_count = max(
                int(existing["session_count"] or 0),
                max(int(session_count or 0), 1),
            )
            same_payload = (
                merged_status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_development_focuses
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE focus_id = ?
                    """,
                    (
                        merged_status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    focus = get_runtime_development_focus(resolved_id)
    if focus is None:
        raise RuntimeError("runtime development focus was not persisted")
    focus.update(meta)
    return focus


def list_runtime_development_focuses(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_development_focus_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                focus_id,
                focus_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_development_focuses
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_development_focus_from_row(row) for row in rows]


def get_runtime_development_focus(focus_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_development_focus_table(conn)
        row = conn.execute(
            """
            SELECT
                focus_id,
                focus_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_development_focuses
            WHERE focus_id = ?
            LIMIT 1
            """,
            (focus_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_development_focus_from_row(row)


def update_runtime_development_focus_status(
    focus_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_development_focus_table(conn)
        row = conn.execute(
            """
            SELECT focus_id
            FROM runtime_development_focuses
            WHERE focus_id = ?
            LIMIT 1
            """,
            (focus_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_development_focuses
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE focus_id = ?
            """,
            (status, status_reason, updated_at, focus_id),
        )
        conn.commit()
    return get_runtime_development_focus(focus_id)


def supersede_runtime_development_focuses(
    *,
    focus_type: str,
    exclude_focus_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_development_focus_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_development_focuses
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE focus_type = ?
              AND focus_id != ?
              AND status IN ('active', 'stale')
            """,
            (
                status_reason,
                updated_at,
                focus_type,
                exclude_focus_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_reflective_critic(
    *,
    critic_id: str,
    critic_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_reflective_critic_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    critic_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_reflective_critics
                WHERE canonical_key = ?
                  AND status IN ('active', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_reflective_critics (
                    critic_id,
                    critic_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    critic_id,
                    critic_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = critic_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["critic_id"])
            merged_status = (
                "active"
                if status == "active"
                else str(status or existing["status"] or "active")
            )
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                merged_status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_reflective_critics
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE critic_id = ?
                    """,
                    (
                        merged_status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    critic = get_runtime_reflective_critic(resolved_id)
    if critic is None:
        raise RuntimeError("runtime reflective critic was not persisted")
    critic.update(meta)
    return critic


def list_runtime_reflective_critics(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_reflective_critic_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                critic_id,
                critic_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_reflective_critics
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_reflective_critic_from_row(row) for row in rows]


def get_runtime_reflective_critic(critic_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_reflective_critic_table(conn)
        row = conn.execute(
            """
            SELECT
                critic_id,
                critic_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_reflective_critics
            WHERE critic_id = ?
            LIMIT 1
            """,
            (critic_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_reflective_critic_from_row(row)


def update_runtime_reflective_critic_status(
    critic_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_reflective_critic_table(conn)
        row = conn.execute(
            """
            SELECT critic_id
            FROM runtime_reflective_critics
            WHERE critic_id = ?
            LIMIT 1
            """,
            (critic_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_reflective_critics
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE critic_id = ?
            """,
            (status, status_reason, updated_at, critic_id),
        )
        conn.commit()
    return get_runtime_reflective_critic(critic_id)


def supersede_runtime_reflective_critics(
    *,
    critic_type: str,
    exclude_critic_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_reflective_critic_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_reflective_critics
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE critic_type = ?
              AND critic_id != ?
              AND status IN ('active', 'stale')
            """,
            (
                status_reason,
                updated_at,
                critic_type,
                exclude_critic_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_world_model_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_world_model_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_world_model_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'uncertain', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_world_model_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_status = (
                status
                if status == "active"
                else str(status or existing["status"] or "uncertain")
            )
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                merged_status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_world_model_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        merged_status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_world_model_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime world-model signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_world_model_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_world_model_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_world_model_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_world_model_signal_from_row(row) for row in rows]


def get_runtime_world_model_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_world_model_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_world_model_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_world_model_signal_from_row(row)


def update_runtime_world_model_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_world_model_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_world_model_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_world_model_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_world_model_signal(signal_id)


def supersede_runtime_world_model_signals(
    *,
    signal_type: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_world_model_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_world_model_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE signal_type = ?
              AND signal_id != ?
              AND status IN ('active', 'uncertain', 'stale')
            """,
            (
                status_reason,
                updated_at,
                signal_type,
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_self_model_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_self_model_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_self_model_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'uncertain', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_self_model_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_status = (
                status
                if status == "active"
                else str(status or existing["status"] or "uncertain")
            )
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                merged_status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_self_model_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        merged_status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_self_model_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime self-model signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_self_model_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_self_model_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_model_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_self_model_signal_from_row(row) for row in rows]


def get_runtime_self_model_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_model_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_model_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_self_model_signal_from_row(row)


def update_runtime_self_model_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_model_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_self_model_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_self_model_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_self_model_signal(signal_id)


def supersede_runtime_self_model_signals(
    *,
    signal_type: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_self_model_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_self_model_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE signal_type = ?
              AND signal_id != ?
              AND status IN ('active', 'uncertain', 'stale')
            """,
            (
                status_reason,
                updated_at,
                signal_type,
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_goal_signal(
    *,
    goal_id: str,
    goal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_goal_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    goal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_goal_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'blocked', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_goal_signals (
                    goal_id,
                    goal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    goal_id,
                    goal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = goal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["goal_id"])
            merged_status = (
                status
                if status in {"active", "blocked"}
                else str(status or existing["status"] or "active")
            )
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                merged_status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_goal_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE goal_id = ?
                    """,
                    (
                        merged_status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    goal = get_runtime_goal_signal(resolved_id)
    if goal is None:
        raise RuntimeError("runtime goal signal was not persisted")
    goal.update(meta)
    return goal


def list_runtime_goal_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_goal_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                goal_id,
                goal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_goal_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_goal_signal_from_row(row) for row in rows]


def get_runtime_goal_signal(goal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_goal_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                goal_id,
                goal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_goal_signals
            WHERE goal_id = ?
            LIMIT 1
            """,
            (goal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_goal_signal_from_row(row)


def update_runtime_goal_signal_status(
    goal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_goal_signal_table(conn)
        row = conn.execute(
            """
            SELECT goal_id
            FROM runtime_goal_signals
            WHERE goal_id = ?
            LIMIT 1
            """,
            (goal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_goal_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE goal_id = ?
            """,
            (status, status_reason, updated_at, goal_id),
        )
        conn.commit()
    return get_runtime_goal_signal(goal_id)


def supersede_runtime_goal_signals(
    *,
    goal_type: str,
    exclude_goal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_goal_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_goal_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE goal_type = ?
              AND goal_id != ?
              AND status IN ('active', 'blocked', 'stale')
            """,
            (
                status_reason,
                updated_at,
                goal_type,
                exclude_goal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_awareness_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_awareness_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_awareness_signals
                WHERE canonical_key = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_awareness_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_awareness_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_awareness_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime awareness signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_awareness_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_awareness_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_awareness_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_awareness_signal_from_row(row) for row in rows]


def get_runtime_awareness_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_awareness_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_awareness_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_awareness_signal_from_row(row)


def update_runtime_awareness_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_awareness_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_awareness_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_awareness_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_awareness_signal(signal_id)


def supersede_runtime_awareness_signals(
    *,
    signal_type: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_awareness_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_awareness_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE signal_type = ?
              AND signal_id != ?
              AND status IN ('active', 'constrained', 'recovered', 'stale')
            """,
            (
                status_reason,
                updated_at,
                signal_type,
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_reflection_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_reflection_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_reflection_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'integrating', 'settled', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_reflection_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_reflection_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_reflection_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime reflection signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_reflection_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_reflection_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_reflection_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_reflection_signal_from_row(row) for row in rows]


def get_runtime_reflection_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_reflection_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_reflection_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_reflection_signal_from_row(row)


def update_runtime_reflection_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_reflection_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_reflection_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_reflection_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_reflection_signal(signal_id)


def supersede_runtime_reflection_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_reflection_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_reflection_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'integrating', 'settled', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"reflection-signal:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_temporal_recurrence_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_temporal_recurrence_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_temporal_recurrence_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_temporal_recurrence_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_temporal_recurrence_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_temporal_recurrence_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime temporal recurrence signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_temporal_recurrence_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_temporal_recurrence_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_temporal_recurrence_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_temporal_recurrence_signal_from_row(row) for row in rows]


def get_runtime_temporal_recurrence_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_temporal_recurrence_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_temporal_recurrence_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_temporal_recurrence_signal_from_row(row)


def update_runtime_temporal_recurrence_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_temporal_recurrence_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_temporal_recurrence_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_temporal_recurrence_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_temporal_recurrence_signal(signal_id)


def supersede_runtime_temporal_recurrence_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_temporal_recurrence_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_temporal_recurrence_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"temporal-recurrence:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_witness_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_witness_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_witness_signals
                WHERE canonical_key = ?
                  AND status IN ('fresh', 'carried', 'fading')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_witness_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_witness_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_witness_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime witness signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_witness_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_witness_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_witness_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_witness_signal_from_row(row) for row in rows]


def get_runtime_witness_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_witness_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_witness_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_witness_signal_from_row(row)


def update_runtime_witness_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_witness_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_witness_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_witness_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_witness_signal(signal_id)


def supersede_runtime_witness_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_witness_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_witness_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('fresh', 'carried', 'fading')
            """,
            (
                status_reason,
                updated_at,
                f"witness-signal:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_open_loop_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_open_loop_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_open_loop_signals
                WHERE canonical_key = ?
                  AND status IN ('open', 'softening', 'closed', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_open_loop_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_open_loop_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_open_loop_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime open loop signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_open_loop_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_open_loop_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_open_loop_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_open_loop_signal_from_row(row) for row in rows]


def get_runtime_open_loop_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_open_loop_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_open_loop_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_open_loop_signal_from_row(row)


def update_runtime_open_loop_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_open_loop_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_open_loop_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_open_loop_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_open_loop_signal(signal_id)


def supersede_runtime_open_loop_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_open_loop_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_open_loop_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('open', 'softening', 'closed', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"open-loop:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_internal_opposition_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_internal_opposition_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_internal_opposition_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_internal_opposition_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_internal_opposition_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_internal_opposition_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime internal opposition signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_internal_opposition_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_internal_opposition_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_internal_opposition_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_internal_opposition_signal_from_row(row) for row in rows]


def get_runtime_internal_opposition_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_internal_opposition_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_internal_opposition_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_internal_opposition_signal_from_row(row)


def update_runtime_internal_opposition_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_internal_opposition_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_internal_opposition_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_internal_opposition_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_internal_opposition_signal(signal_id)


def supersede_runtime_internal_opposition_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_internal_opposition_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_internal_opposition_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"internal-opposition:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_self_review_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_self_review_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_self_review_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_self_review_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_self_review_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_self_review_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime self-review signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_self_review_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_self_review_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_review_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_self_review_signal_from_row(row) for row in rows]


def get_runtime_self_review_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_review_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_self_review_signal_from_row(row)


def update_runtime_self_review_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_self_review_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_self_review_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_self_review_signal(signal_id)


def supersede_runtime_self_review_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_self_review_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_self_review_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"self-review:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_self_review_record(
    *,
    record_id: str,
    record_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_self_review_record_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    record_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_self_review_records
                WHERE canonical_key = ?
                  AND status IN ('fresh', 'active', 'fading', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_self_review_records (
                    record_id,
                    record_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    record_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = record_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["record_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_self_review_records
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE record_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    record = get_runtime_self_review_record(resolved_id)
    if record is None:
        raise RuntimeError("runtime self-review record was not persisted")
    record.update(meta)
    return record


def list_runtime_self_review_records(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_self_review_record_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                record_id,
                record_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_review_records
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_self_review_record_from_row(row) for row in rows]


def get_runtime_self_review_record(record_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_record_table(conn)
        row = conn.execute(
            """
            SELECT
                record_id,
                record_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_review_records
            WHERE record_id = ?
            LIMIT 1
            """,
            (record_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_self_review_record_from_row(row)


def update_runtime_self_review_record_status(
    record_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_record_table(conn)
        row = conn.execute(
            """
            SELECT record_id
            FROM runtime_self_review_records
            WHERE record_id = ?
            LIMIT 1
            """,
            (record_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_self_review_records
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE record_id = ?
            """,
            (status, status_reason, updated_at, record_id),
        )
        conn.commit()
    return get_runtime_self_review_record(record_id)


def supersede_runtime_self_review_records_for_domain(
    *,
    domain_key: str,
    exclude_record_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_self_review_record_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_self_review_records
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND record_id != ?
              AND status IN ('fresh', 'active', 'fading', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"self-review-record:%:{domain_key}",
                exclude_record_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_self_review_run(
    *,
    run_id: str,
    run_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    record_run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_self_review_run_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    run_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    record_run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_self_review_runs
                WHERE canonical_key = ?
                  AND status IN ('fresh', 'active', 'fading', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_self_review_runs (
                    run_id,
                    run_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    record_run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    run_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    record_run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = run_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["run_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and record_run_id == str(existing["record_run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_self_review_runs
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        record_run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE run_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        record_run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    run = get_runtime_self_review_run(resolved_id)
    if run is None:
        raise RuntimeError("runtime self-review run was not persisted")
    run.update(meta)
    return run


def list_runtime_self_review_runs(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_self_review_run_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                run_id,
                run_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                record_run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_review_runs
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_self_review_run_from_row(row) for row in rows]


def get_runtime_self_review_run(run_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_run_table(conn)
        row = conn.execute(
            """
            SELECT
                run_id,
                run_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                record_run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_review_runs
            WHERE run_id = ?
            LIMIT 1
            """,
            (run_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_self_review_run_from_row(row)


def update_runtime_self_review_run_status(
    run_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_run_table(conn)
        row = conn.execute(
            """
            SELECT run_id
            FROM runtime_self_review_runs
            WHERE run_id = ?
            LIMIT 1
            """,
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_self_review_runs
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE run_id = ?
            """,
            (status, status_reason, updated_at, run_id),
        )
        conn.commit()
    return get_runtime_self_review_run(run_id)


def supersede_runtime_self_review_runs_for_domain(
    *,
    domain_key: str,
    exclude_run_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_self_review_run_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_self_review_runs
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND run_id != ?
              AND status IN ('fresh', 'active', 'fading', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"self-review-run:%:{domain_key}",
                exclude_run_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_self_review_outcome(
    *,
    outcome_id: str,
    outcome_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    review_run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_self_review_outcome_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    outcome_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    review_run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_self_review_outcomes
                WHERE canonical_key = ?
                  AND status IN ('fresh', 'active', 'fading', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_self_review_outcomes (
                    outcome_id,
                    outcome_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    review_run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    outcome_id,
                    outcome_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    review_run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = outcome_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["outcome_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and review_run_id == str(existing["review_run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_self_review_outcomes
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        review_run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE outcome_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        review_run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    outcome = get_runtime_self_review_outcome(resolved_id)
    if outcome is None:
        raise RuntimeError("runtime self-review outcome was not persisted")
    outcome.update(meta)
    return outcome


def list_runtime_self_review_outcomes(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_self_review_outcome_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                outcome_id,
                outcome_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                review_run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_review_outcomes
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_self_review_outcome_from_row(row) for row in rows]


def get_runtime_self_review_outcome(outcome_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_outcome_table(conn)
        row = conn.execute(
            """
            SELECT
                outcome_id,
                outcome_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                review_run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_review_outcomes
            WHERE outcome_id = ?
            LIMIT 1
            """,
            (outcome_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_self_review_outcome_from_row(row)


def update_runtime_self_review_outcome_status(
    outcome_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_outcome_table(conn)
        row = conn.execute(
            """
            SELECT outcome_id
            FROM runtime_self_review_outcomes
            WHERE outcome_id = ?
            LIMIT 1
            """,
            (outcome_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_self_review_outcomes
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE outcome_id = ?
            """,
            (status, status_reason, updated_at, outcome_id),
        )
        conn.commit()
    return get_runtime_self_review_outcome(outcome_id)


def supersede_runtime_self_review_outcomes_for_domain(
    *,
    domain_key: str,
    exclude_outcome_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_self_review_outcome_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_self_review_outcomes
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND outcome_id != ?
              AND status IN ('fresh', 'active', 'fading', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"self-review-outcome:%:{domain_key}",
                exclude_outcome_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_self_review_cadence_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_self_review_cadence_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_self_review_cadence_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_self_review_cadence_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_self_review_cadence_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_self_review_cadence_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime self-review cadence signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_self_review_cadence_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_self_review_cadence_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_review_cadence_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_self_review_cadence_signal_from_row(row) for row in rows]


def get_runtime_self_review_cadence_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_cadence_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_review_cadence_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_self_review_cadence_signal_from_row(row)


def update_runtime_self_review_cadence_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_review_cadence_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_self_review_cadence_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_self_review_cadence_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_self_review_cadence_signal(signal_id)


def supersede_runtime_self_review_cadence_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_self_review_cadence_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_self_review_cadence_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"self-review-cadence:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_open_loop_closure_proposal(
    *,
    proposal_id: str,
    proposal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_open_loop_closure_proposal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    proposal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_open_loop_closure_proposals
                WHERE canonical_key = ?
                  AND status IN ('fresh', 'active', 'fading', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_open_loop_closure_proposals (
                    proposal_id,
                    proposal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal_id,
                    proposal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = proposal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["proposal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_open_loop_closure_proposals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE proposal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    proposal = get_runtime_open_loop_closure_proposal(resolved_id)
    if proposal is None:
        raise RuntimeError("runtime open-loop closure proposal was not persisted")
    proposal.update(meta)
    return proposal


def list_runtime_open_loop_closure_proposals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_open_loop_closure_proposal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                proposal_id,
                proposal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_open_loop_closure_proposals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_open_loop_closure_proposal_from_row(row) for row in rows]


def get_runtime_open_loop_closure_proposal(
    proposal_id: str,
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_open_loop_closure_proposal_table(conn)
        row = conn.execute(
            """
            SELECT
                proposal_id,
                proposal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_open_loop_closure_proposals
            WHERE proposal_id = ?
            LIMIT 1
            """,
            (proposal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_open_loop_closure_proposal_from_row(row)


def update_runtime_open_loop_closure_proposal_status(
    proposal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_open_loop_closure_proposal_table(conn)
        row = conn.execute(
            """
            SELECT proposal_id
            FROM runtime_open_loop_closure_proposals
            WHERE proposal_id = ?
            LIMIT 1
            """,
            (proposal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_open_loop_closure_proposals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE proposal_id = ?
            """,
            (status, status_reason, updated_at, proposal_id),
        )
        conn.commit()
    return get_runtime_open_loop_closure_proposal(proposal_id)


def supersede_runtime_open_loop_closure_proposals_for_domain(
    *,
    domain_key: str,
    exclude_proposal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_open_loop_closure_proposal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_open_loop_closure_proposals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND proposal_id != ?
              AND status IN ('fresh', 'active', 'fading', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"open-loop-closure-proposal:%:{domain_key}",
                exclude_proposal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_dream_hypothesis_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_dream_hypothesis_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_dream_hypothesis_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'integrating', 'fading', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_dream_hypothesis_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_dream_hypothesis_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_dream_hypothesis_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime dream hypothesis signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_dream_hypothesis_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_dream_hypothesis_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_dream_hypothesis_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_dream_hypothesis_signal_from_row(row) for row in rows]


def get_runtime_dream_hypothesis_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_dream_hypothesis_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_dream_hypothesis_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_dream_hypothesis_signal_from_row(row)


def update_runtime_dream_hypothesis_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_dream_hypothesis_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_dream_hypothesis_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_dream_hypothesis_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_dream_hypothesis_signal(signal_id)


def supersede_runtime_dream_hypothesis_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_dream_hypothesis_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_dream_hypothesis_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'integrating', 'fading', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"dream-hypothesis:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_dream_adoption_candidate(
    *,
    candidate_id: str,
    candidate_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_dream_adoption_candidate_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    candidate_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_dream_adoption_candidates
                WHERE canonical_key = ?
                  AND status IN ('fresh', 'active', 'fading', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_dream_adoption_candidates (
                    candidate_id,
                    candidate_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id,
                    candidate_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = candidate_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["candidate_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_dream_adoption_candidates
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE candidate_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    candidate = get_runtime_dream_adoption_candidate(resolved_id)
    if candidate is None:
        raise RuntimeError("runtime dream adoption candidate was not persisted")
    candidate.update(meta)
    return candidate


def list_runtime_dream_adoption_candidates(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_dream_adoption_candidate_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                candidate_id,
                candidate_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_dream_adoption_candidates
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_dream_adoption_candidate_from_row(row) for row in rows]


def get_runtime_dream_adoption_candidate(candidate_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_dream_adoption_candidate_table(conn)
        row = conn.execute(
            """
            SELECT
                candidate_id,
                candidate_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_dream_adoption_candidates
            WHERE candidate_id = ?
            LIMIT 1
            """,
            (candidate_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_dream_adoption_candidate_from_row(row)


def update_runtime_dream_adoption_candidate_status(
    candidate_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_dream_adoption_candidate_table(conn)
        row = conn.execute(
            """
            SELECT candidate_id
            FROM runtime_dream_adoption_candidates
            WHERE candidate_id = ?
            LIMIT 1
            """,
            (candidate_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_dream_adoption_candidates
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE candidate_id = ?
            """,
            (status, status_reason, updated_at, candidate_id),
        )
        conn.commit()
    return get_runtime_dream_adoption_candidate(candidate_id)


def supersede_runtime_dream_adoption_candidates_for_domain(
    *,
    domain_key: str,
    exclude_candidate_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_dream_adoption_candidate_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_dream_adoption_candidates
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND candidate_id != ?
              AND status IN ('fresh', 'active', 'fading', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"dream-adoption-candidate:%:{domain_key}",
                exclude_candidate_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_dream_influence_proposal(
    *,
    proposal_id: str,
    proposal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_dream_influence_proposal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    proposal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_dream_influence_proposals
                WHERE canonical_key = ?
                  AND status IN ('fresh', 'active', 'fading', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_dream_influence_proposals (
                    proposal_id,
                    proposal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal_id,
                    proposal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = proposal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["proposal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_dream_influence_proposals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE proposal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    proposal = get_runtime_dream_influence_proposal(resolved_id)
    if proposal is None:
        raise RuntimeError("runtime dream influence proposal was not persisted")
    proposal.update(meta)
    return proposal


def list_runtime_dream_influence_proposals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_dream_influence_proposal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                proposal_id,
                proposal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_dream_influence_proposals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_dream_influence_proposal_from_row(row) for row in rows]


def get_runtime_dream_influence_proposal(proposal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_dream_influence_proposal_table(conn)
        row = conn.execute(
            """
            SELECT
                proposal_id,
                proposal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_dream_influence_proposals
            WHERE proposal_id = ?
            LIMIT 1
            """,
            (proposal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_dream_influence_proposal_from_row(row)


def update_runtime_dream_influence_proposal_status(
    proposal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_dream_influence_proposal_table(conn)
        row = conn.execute(
            """
            SELECT proposal_id
            FROM runtime_dream_influence_proposals
            WHERE proposal_id = ?
            LIMIT 1
            """,
            (proposal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_dream_influence_proposals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE proposal_id = ?
            """,
            (status, status_reason, updated_at, proposal_id),
        )
        conn.commit()
    return get_runtime_dream_influence_proposal(proposal_id)


def supersede_runtime_dream_influence_proposals_for_domain(
    *,
    domain_key: str,
    exclude_proposal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_dream_influence_proposal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_dream_influence_proposals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND proposal_id != ?
              AND status IN ('fresh', 'active', 'fading', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"dream-influence-proposal:%:{domain_key}",
                exclude_proposal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_self_authored_prompt_proposal(
    *,
    proposal_id: str,
    proposal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_self_authored_prompt_proposal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    proposal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_self_authored_prompt_proposals
                WHERE canonical_key = ?
                  AND status IN ('fresh', 'active', 'fading', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_self_authored_prompt_proposals (
                    proposal_id,
                    proposal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal_id,
                    proposal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = proposal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["proposal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_self_authored_prompt_proposals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE proposal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    proposal = get_runtime_self_authored_prompt_proposal(resolved_id)
    if proposal is None:
        raise RuntimeError("runtime self authored prompt proposal was not persisted")
    proposal.update(meta)
    return proposal


def list_runtime_self_authored_prompt_proposals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_self_authored_prompt_proposal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                proposal_id,
                proposal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_authored_prompt_proposals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_self_authored_prompt_proposal_from_row(row) for row in rows]


def get_runtime_self_authored_prompt_proposal(
    proposal_id: str,
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_authored_prompt_proposal_table(conn)
        row = conn.execute(
            """
            SELECT
                proposal_id,
                proposal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_authored_prompt_proposals
            WHERE proposal_id = ?
            LIMIT 1
            """,
            (proposal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_self_authored_prompt_proposal_from_row(row)


def update_runtime_self_authored_prompt_proposal_status(
    proposal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_authored_prompt_proposal_table(conn)
        row = conn.execute(
            """
            SELECT proposal_id
            FROM runtime_self_authored_prompt_proposals
            WHERE proposal_id = ?
            LIMIT 1
            """,
            (proposal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_self_authored_prompt_proposals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE proposal_id = ?
            """,
            (status, status_reason, updated_at, proposal_id),
        )
        conn.commit()
    return get_runtime_self_authored_prompt_proposal(proposal_id)


def supersede_runtime_self_authored_prompt_proposals_for_domain(
    *,
    domain_key: str,
    exclude_proposal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_self_authored_prompt_proposal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_self_authored_prompt_proposals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND proposal_id != ?
              AND status IN ('fresh', 'active', 'fading', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"self-authored-prompt-proposal:%:{domain_key}",
                exclude_proposal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_user_md_update_proposal(
    *,
    proposal_id: str,
    proposal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_user_md_update_proposal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    proposal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_user_md_update_proposals
                WHERE canonical_key = ?
                  AND status IN ('fresh', 'active', 'fading', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_user_md_update_proposals (
                    proposal_id,
                    proposal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal_id,
                    proposal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = proposal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["proposal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_user_md_update_proposals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE proposal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    proposal = get_runtime_user_md_update_proposal(resolved_id)
    if proposal is None:
        raise RuntimeError("runtime user md update proposal was not persisted")
    proposal.update(meta)
    return proposal


def list_runtime_user_md_update_proposals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_user_md_update_proposal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                proposal_id,
                proposal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_user_md_update_proposals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_user_md_update_proposal_from_row(row) for row in rows]


def get_runtime_user_md_update_proposal(proposal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_user_md_update_proposal_table(conn)
        row = conn.execute(
            """
            SELECT
                proposal_id,
                proposal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_user_md_update_proposals
            WHERE proposal_id = ?
            LIMIT 1
            """,
            (proposal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_user_md_update_proposal_from_row(row)


def update_runtime_user_md_update_proposal_status(
    proposal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_user_md_update_proposal_table(conn)
        row = conn.execute(
            """
            SELECT proposal_id
            FROM runtime_user_md_update_proposals
            WHERE proposal_id = ?
            LIMIT 1
            """,
            (proposal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_user_md_update_proposals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE proposal_id = ?
            """,
            (status, status_reason, updated_at, proposal_id),
        )
        conn.commit()
    return get_runtime_user_md_update_proposal(proposal_id)


def supersede_runtime_user_md_update_proposals_for_dimension(
    *,
    dimension_key: str,
    exclude_proposal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_user_md_update_proposal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_user_md_update_proposals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND proposal_id != ?
              AND status IN ('fresh', 'active', 'fading', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"user-md-update-proposal:%:{dimension_key}",
                exclude_proposal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_memory_md_update_proposal(
    *,
    proposal_id: str,
    proposal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_memory_md_update_proposal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    proposal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_memory_md_update_proposals
                WHERE canonical_key = ?
                  AND status IN ('fresh', 'active', 'fading', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_memory_md_update_proposals (
                    proposal_id,
                    proposal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal_id,
                    proposal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = proposal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["proposal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_memory_md_update_proposals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE proposal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    proposal = get_runtime_memory_md_update_proposal(resolved_id)
    if proposal is None:
        raise RuntimeError("runtime memory md update proposal was not persisted")
    proposal.update(meta)
    return proposal


def list_runtime_memory_md_update_proposals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_memory_md_update_proposal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                proposal_id,
                proposal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_memory_md_update_proposals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_memory_md_update_proposal_from_row(row) for row in rows]


def get_runtime_memory_md_update_proposal(proposal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_memory_md_update_proposal_table(conn)
        row = conn.execute(
            """
            SELECT
                proposal_id,
                proposal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_memory_md_update_proposals
            WHERE proposal_id = ?
            LIMIT 1
            """,
            (proposal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_memory_md_update_proposal_from_row(row)


def update_runtime_memory_md_update_proposal_status(
    proposal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_memory_md_update_proposal_table(conn)
        row = conn.execute(
            """
            SELECT proposal_id
            FROM runtime_memory_md_update_proposals
            WHERE proposal_id = ?
            LIMIT 1
            """,
            (proposal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_memory_md_update_proposals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE proposal_id = ?
            """,
            (status, status_reason, updated_at, proposal_id),
        )
        conn.commit()
    return get_runtime_memory_md_update_proposal(proposal_id)


def supersede_runtime_memory_md_update_proposals_for_dimension(
    *,
    dimension_key: str,
    exclude_proposal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_memory_md_update_proposal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_memory_md_update_proposals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND proposal_id != ?
              AND status IN ('fresh', 'active', 'fading', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"memory-md-update-proposal:{dimension_key}",
                exclude_proposal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_user_understanding_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_user_understanding_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_user_understanding_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_user_understanding_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_user_understanding_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_user_understanding_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime user understanding signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_user_understanding_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_user_understanding_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_user_understanding_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_user_understanding_signal_from_row(row) for row in rows]


def get_runtime_user_understanding_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_user_understanding_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_user_understanding_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_user_understanding_signal_from_row(row)


def update_runtime_user_understanding_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_user_understanding_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_user_understanding_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_user_understanding_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_user_understanding_signal(signal_id)


def supersede_runtime_user_understanding_signals_for_dimension(
    *,
    dimension_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_user_understanding_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_user_understanding_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"user-understanding:%:{dimension_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_remembered_fact_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_remembered_fact_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_remembered_fact_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_remembered_fact_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_remembered_fact_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_remembered_fact_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime remembered fact signal was not persisted")
    signal.update(meta)
    return signal


def upsert_runtime_private_inner_note_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_private_inner_note_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_private_inner_note_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_private_inner_note_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_private_inner_note_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_private_inner_note_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime private inner note signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_private_inner_note_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_private_inner_note_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_private_inner_note_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_private_inner_note_signal_from_row(row) for row in rows]


def get_runtime_private_inner_note_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_private_inner_note_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_private_inner_note_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_private_inner_note_signal_from_row(row)


def update_runtime_private_inner_note_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_private_inner_note_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_private_inner_note_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_private_inner_note_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_private_inner_note_signal(signal_id)


def supersede_runtime_private_inner_note_signals_for_focus(
    *,
    focus_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_private_inner_note_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_private_inner_note_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"private-inner-note:%:{focus_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_private_initiative_tension_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_private_initiative_tension_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_private_initiative_tension_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_private_initiative_tension_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_private_initiative_tension_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_private_initiative_tension_signal(resolved_id)
    if signal is None:
        raise RuntimeError(
            "runtime private initiative tension signal was not persisted"
        )
    signal.update(meta)
    return signal


def list_runtime_private_initiative_tension_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_private_initiative_tension_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_private_initiative_tension_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_private_initiative_tension_signal_from_row(row) for row in rows]


def get_runtime_private_initiative_tension_signal(
    signal_id: str,
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_private_initiative_tension_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_private_initiative_tension_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_private_initiative_tension_signal_from_row(row)


def update_runtime_private_initiative_tension_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_private_initiative_tension_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_private_initiative_tension_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_private_initiative_tension_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_private_initiative_tension_signal(signal_id)


def supersede_runtime_private_initiative_tension_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_private_initiative_tension_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_private_initiative_tension_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"private-initiative-tension:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_private_inner_interplay_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_private_inner_interplay_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_private_inner_interplay_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_private_inner_interplay_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_private_inner_interplay_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_private_inner_interplay_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime private inner interplay signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_private_inner_interplay_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_private_inner_interplay_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_private_inner_interplay_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_private_inner_interplay_signal_from_row(row) for row in rows]


def get_runtime_private_inner_interplay_signal(
    signal_id: str,
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_private_inner_interplay_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_private_inner_interplay_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_private_inner_interplay_signal_from_row(row)


def update_runtime_private_inner_interplay_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_private_inner_interplay_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_private_inner_interplay_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_private_inner_interplay_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_private_inner_interplay_signal(signal_id)


def supersede_runtime_private_inner_interplay_signals_for_relation(
    *,
    relation_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_private_inner_interplay_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_private_inner_interplay_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"private-inner-interplay:%:{relation_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_private_state_snapshot(
    *,
    snapshot_id: str,
    snapshot_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_private_state_snapshot_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    snapshot_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_private_state_snapshots
                WHERE canonical_key = ?
                  AND status IN ('active', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_private_state_snapshots (
                    snapshot_id,
                    snapshot_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    snapshot_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = snapshot_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["snapshot_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_private_state_snapshots
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE snapshot_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    snapshot = get_runtime_private_state_snapshot(resolved_id)
    if snapshot is None:
        raise RuntimeError("runtime private state snapshot was not persisted")
    snapshot.update(meta)
    return snapshot


def list_runtime_private_state_snapshots(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_private_state_snapshot_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                snapshot_id,
                snapshot_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_private_state_snapshots
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_private_state_snapshot_from_row(row) for row in rows]


def get_runtime_private_state_snapshot(snapshot_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_private_state_snapshot_table(conn)
        row = conn.execute(
            """
            SELECT
                snapshot_id,
                snapshot_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_private_state_snapshots
            WHERE snapshot_id = ?
            LIMIT 1
            """,
            (snapshot_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_private_state_snapshot_from_row(row)


def update_runtime_private_state_snapshot_status(
    snapshot_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_private_state_snapshot_table(conn)
        row = conn.execute(
            """
            SELECT snapshot_id
            FROM runtime_private_state_snapshots
            WHERE snapshot_id = ?
            LIMIT 1
            """,
            (snapshot_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_private_state_snapshots
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE snapshot_id = ?
            """,
            (status, status_reason, updated_at, snapshot_id),
        )
        conn.commit()
    return get_runtime_private_state_snapshot(snapshot_id)


def supersede_runtime_private_state_snapshots_for_focus(
    *,
    focus_key: str,
    exclude_snapshot_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_private_state_snapshot_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_private_state_snapshots
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND snapshot_id != ?
              AND status IN ('active', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"private-state-snapshot:%:{focus_key}",
                exclude_snapshot_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def list_runtime_diary_synthesis_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_diary_synthesis_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_diary_synthesis_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_diary_synthesis_signal_from_row(row) for row in rows]


def get_diary_synthesis_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_diary_synthesis_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_diary_synthesis_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_diary_synthesis_signal_from_row(row)


def update_diary_synthesis_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_diary_synthesis_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_diary_synthesis_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_diary_synthesis_signals
            SET status = ?,
                updated_at = ?,
                status_reason = ?
            WHERE signal_id = ?
            """,
            (status, updated_at, status_reason, signal_id),
        )
        conn.commit()
        return get_diary_synthesis_signal(signal_id)


def supersede_diary_synthesis_signals_for_focus(
    *,
    focus_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_diary_synthesis_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_diary_synthesis_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"diary-synthesis:%:{focus_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_diary_synthesis_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_diary_synthesis_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_diary_synthesis_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_diary_synthesis_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            return {
                "was_created": True,
                "was_updated": False,
                **get_diary_synthesis_signal(signal_id),
            }

        was_created = False
        old_merge_count = existing[15] if len(existing) > 15 else 0
        conn.execute(
            """
            UPDATE runtime_diary_synthesis_signals
            SET status = ?,
                title = ?,
                summary = ?,
                rationale = ?,
                source_kind = ?,
                confidence = ?,
                evidence_summary = ?,
                support_summary = ?,
                status_reason = ?,
                run_id = ?,
                session_id = ?,
                support_count = ?,
                session_count = ?,
                merge_count = ?,
                updated_at = ?
            WHERE signal_id = ?
            """,
            (
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                old_merge_count + 1,
                updated_at,
                existing[0],
            ),
        )
        conn.commit()
        return {
            "was_created": was_created,
            "was_updated": True,
            **get_diary_synthesis_signal(existing[0]),
        }


def _runtime_diary_synthesis_signal_from_row(
    row: tuple[object, ...],
) -> dict[str, object]:
    return {
        "signal_id": str(row[0]),
        "signal_type": str(row[1]),
        "canonical_key": str(row[2]),
        "status": str(row[3]),
        "title": str(row[4]),
        "summary": str(row[5]),
        "rationale": str(row[6]),
        "source_kind": str(row[7]),
        "confidence": str(row[8]),
        "evidence_summary": str(row[9]),
        "support_summary": str(row[10]),
        "status_reason": str(row[11]),
        "run_id": str(row[12]),
        "session_id": str(row[13]),
        "support_count": int(row[14]) if row[14] else 1,
        "session_count": int(row[15]) if row[15] else 1,
        "merge_count": int(row[16]) if row[16] else 0,
        "created_at": str(row[17]),
        "updated_at": str(row[18]),
    }


def _ensure_runtime_diary_synthesis_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_diary_synthesis_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_diary_synthesis_signals_status
        ON runtime_diary_synthesis_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_diary_synthesis_signals_canonical_key
        ON runtime_diary_synthesis_signals(canonical_key, id DESC)
        """
    )


def upsert_runtime_private_temporal_curiosity_state(
    *,
    state_id: str,
    state_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_private_temporal_curiosity_state_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    state_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_private_temporal_curiosity_states
                WHERE canonical_key = ?
                  AND status IN ('active', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_private_temporal_curiosity_states (
                    state_id,
                    state_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state_id,
                    state_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = state_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["state_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_private_temporal_curiosity_states
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE state_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    state = get_runtime_private_temporal_curiosity_state(resolved_id)
    if state is None:
        raise RuntimeError("runtime private temporal curiosity state was not persisted")
    state.update(meta)
    return state


def list_runtime_private_temporal_curiosity_states(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_private_temporal_curiosity_state_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                state_id,
                state_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_private_temporal_curiosity_states
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_private_temporal_curiosity_state_from_row(row) for row in rows]


def get_runtime_private_temporal_curiosity_state(
    state_id: str,
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_private_temporal_curiosity_state_table(conn)
        row = conn.execute(
            """
            SELECT
                state_id,
                state_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_private_temporal_curiosity_states
            WHERE state_id = ?
            LIMIT 1
            """,
            (state_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_private_temporal_curiosity_state_from_row(row)


def update_runtime_private_temporal_curiosity_state_status(
    state_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_private_temporal_curiosity_state_table(conn)
        row = conn.execute(
            """
            SELECT state_id
            FROM runtime_private_temporal_curiosity_states
            WHERE state_id = ?
            LIMIT 1
            """,
            (state_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_private_temporal_curiosity_states
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE state_id = ?
            """,
            (status, status_reason, updated_at, state_id),
        )
        conn.commit()
    return get_runtime_private_temporal_curiosity_state(state_id)


def supersede_runtime_private_temporal_curiosity_states_for_focus(
    *,
    focus_key: str,
    exclude_state_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_private_temporal_curiosity_state_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_private_temporal_curiosity_states
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND state_id != ?
              AND status IN ('active', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"private-temporal-curiosity:%:{focus_key}",
                exclude_state_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_private_temporal_promotion_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_private_temporal_promotion_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_private_temporal_promotion_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_private_temporal_promotion_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_private_temporal_promotion_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_private_temporal_promotion_signal(resolved_id)
    if signal is None:
        raise RuntimeError(
            "runtime private temporal promotion signal was not persisted"
        )
    signal.update(meta)
    return signal


def list_runtime_private_temporal_promotion_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_private_temporal_promotion_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_private_temporal_promotion_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_private_temporal_promotion_signal_from_row(row) for row in rows]


def get_runtime_private_temporal_promotion_signal(
    signal_id: str,
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_private_temporal_promotion_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_private_temporal_promotion_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_private_temporal_promotion_signal_from_row(row)


def update_runtime_private_temporal_promotion_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_private_temporal_promotion_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_private_temporal_promotion_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_private_temporal_promotion_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_private_temporal_promotion_signal(signal_id)


def supersede_runtime_private_temporal_promotion_signals_for_focus(
    *,
    focus_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_private_temporal_promotion_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_private_temporal_promotion_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"private-temporal-promotion:%:{focus_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_inner_visible_support_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_inner_visible_support_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_inner_visible_support_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_inner_visible_support_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_inner_visible_support_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_inner_visible_support_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime inner visible support signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_inner_visible_support_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_inner_visible_support_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_inner_visible_support_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_inner_visible_support_signal_from_row(row) for row in rows]


def get_runtime_inner_visible_support_signal(
    signal_id: str,
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_inner_visible_support_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_inner_visible_support_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_inner_visible_support_signal_from_row(row)


def update_runtime_inner_visible_support_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_inner_visible_support_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_inner_visible_support_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_inner_visible_support_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_inner_visible_support_signal(signal_id)


def supersede_runtime_inner_visible_support_signals_for_focus(
    *,
    focus_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_inner_visible_support_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_inner_visible_support_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"inner-visible-support:%:{focus_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_regulation_homeostasis_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_regulation_homeostasis_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_regulation_homeostasis_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_regulation_homeostasis_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_regulation_homeostasis_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_regulation_homeostasis_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime regulation homeostasis signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_regulation_homeostasis_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_regulation_homeostasis_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_regulation_homeostasis_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_regulation_homeostasis_signal_from_row(row) for row in rows]


def get_runtime_regulation_homeostasis_signal(
    signal_id: str,
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_regulation_homeostasis_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_regulation_homeostasis_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_regulation_homeostasis_signal_from_row(row)


def update_runtime_regulation_homeostasis_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_regulation_homeostasis_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_regulation_homeostasis_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_regulation_homeostasis_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_regulation_homeostasis_signal(signal_id)


def supersede_runtime_regulation_homeostasis_signals_for_focus(
    *,
    focus_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_regulation_homeostasis_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_regulation_homeostasis_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"regulation-homeostasis:%:{focus_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_relation_state_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_relation_state_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_relation_state_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_relation_state_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_relation_state_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_relation_state_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime relation state signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_relation_state_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_relation_state_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_relation_state_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_relation_state_signal_from_row(row) for row in rows]


def get_runtime_relation_state_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_relation_state_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_relation_state_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_relation_state_signal_from_row(row)


def update_runtime_relation_state_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_relation_state_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_relation_state_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_relation_state_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_relation_state_signal(signal_id)


def supersede_runtime_relation_state_signals_for_focus(
    *,
    focus_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_relation_state_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_relation_state_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"relation-state:%:{focus_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_relation_continuity_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_relation_continuity_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_relation_continuity_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_relation_continuity_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_relation_continuity_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_relation_continuity_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime relation continuity signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_relation_continuity_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_relation_continuity_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_relation_continuity_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_relation_continuity_signal_from_row(row) for row in rows]


def get_runtime_relation_continuity_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_relation_continuity_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_relation_continuity_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_relation_continuity_signal_from_row(row)


def update_runtime_relation_continuity_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_relation_continuity_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_relation_continuity_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_relation_continuity_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_relation_continuity_signal(signal_id)


def supersede_runtime_relation_continuity_signals_for_focus(
    *,
    focus_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_relation_continuity_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_relation_continuity_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"relation-continuity:%:{focus_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_meaning_significance_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_meaning_significance_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_meaning_significance_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_meaning_significance_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_meaning_significance_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_meaning_significance_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime meaning significance signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_meaning_significance_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_meaning_significance_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_meaning_significance_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_meaning_significance_signal_from_row(row) for row in rows]


def get_runtime_meaning_significance_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_meaning_significance_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_meaning_significance_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_meaning_significance_signal_from_row(row)


def update_runtime_meaning_significance_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_meaning_significance_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_meaning_significance_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_meaning_significance_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_meaning_significance_signal(signal_id)


def supersede_runtime_meaning_significance_signals_for_focus(
    *,
    focus_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_meaning_significance_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_meaning_significance_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"meaning-significance:%:{focus_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_temperament_tendency_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_temperament_tendency_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_temperament_tendency_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_temperament_tendency_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_temperament_tendency_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_temperament_tendency_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime temperament tendency signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_temperament_tendency_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_temperament_tendency_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_temperament_tendency_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_temperament_tendency_signal_from_row(row) for row in rows]


def get_runtime_temperament_tendency_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_temperament_tendency_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_temperament_tendency_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_temperament_tendency_signal_from_row(row)


def update_runtime_temperament_tendency_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_temperament_tendency_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_temperament_tendency_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_temperament_tendency_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_temperament_tendency_signal(signal_id)


def supersede_runtime_temperament_tendency_signals_for_focus(
    *,
    focus_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_temperament_tendency_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_temperament_tendency_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"temperament-tendency:%:{focus_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_self_narrative_continuity_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_self_narrative_continuity_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_self_narrative_continuity_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_self_narrative_continuity_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_self_narrative_continuity_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_self_narrative_continuity_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime self narrative continuity signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_self_narrative_continuity_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_self_narrative_continuity_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_narrative_continuity_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_self_narrative_continuity_signal_from_row(row) for row in rows]


def get_runtime_self_narrative_continuity_signal(
    signal_id: str,
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_narrative_continuity_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_self_narrative_continuity_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_self_narrative_continuity_signal_from_row(row)


def update_runtime_self_narrative_continuity_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_self_narrative_continuity_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_self_narrative_continuity_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_self_narrative_continuity_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_self_narrative_continuity_signal(signal_id)


def supersede_runtime_self_narrative_continuity_signals_for_focus(
    *,
    focus_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_self_narrative_continuity_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_self_narrative_continuity_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"self-narrative-continuity:%:{focus_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_metabolism_state_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_metabolism_state_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_metabolism_state_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_metabolism_state_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_metabolism_state_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_metabolism_state_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime metabolism-state signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_metabolism_state_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_metabolism_state_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_metabolism_state_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_metabolism_state_signal_from_row(row) for row in rows]


def get_runtime_metabolism_state_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_metabolism_state_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_metabolism_state_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_metabolism_state_signal_from_row(row)


def update_runtime_metabolism_state_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_metabolism_state_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_metabolism_state_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_metabolism_state_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_metabolism_state_signal(signal_id)


def supersede_runtime_metabolism_state_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_metabolism_state_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_metabolism_state_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"metabolism-state:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_release_marker_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_release_marker_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_release_marker_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_release_marker_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_release_marker_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_release_marker_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime release-marker signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_release_marker_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_release_marker_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_release_marker_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_release_marker_signal_from_row(row) for row in rows]


def get_runtime_release_marker_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_release_marker_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_release_marker_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_release_marker_signal_from_row(row)


def update_runtime_release_marker_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_release_marker_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_release_marker_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_release_marker_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_release_marker_signal(signal_id)


def supersede_runtime_release_marker_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_release_marker_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_release_marker_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"release-marker:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_consolidation_target_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_consolidation_target_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_consolidation_target_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_consolidation_target_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_consolidation_target_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_consolidation_target_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime consolidation-target signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_consolidation_target_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_consolidation_target_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_consolidation_target_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_consolidation_target_signal_from_row(row) for row in rows]


def get_runtime_consolidation_target_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_consolidation_target_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_consolidation_target_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_consolidation_target_signal_from_row(row)


def update_runtime_consolidation_target_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_consolidation_target_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_consolidation_target_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_consolidation_target_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_consolidation_target_signal(signal_id)


def supersede_runtime_consolidation_target_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_consolidation_target_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_consolidation_target_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"consolidation-target:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_selective_forgetting_candidate(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_selective_forgetting_candidate_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_selective_forgetting_candidates
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_selective_forgetting_candidates (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_selective_forgetting_candidates
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_selective_forgetting_candidate(resolved_id)
    if signal is None:
        raise RuntimeError("runtime selective-forgetting candidate was not persisted")
    signal.update(meta)
    return signal


def list_runtime_selective_forgetting_candidates(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_selective_forgetting_candidate_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_selective_forgetting_candidates
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_selective_forgetting_candidate_from_row(row) for row in rows]


def get_runtime_selective_forgetting_candidate(
    signal_id: str,
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_selective_forgetting_candidate_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_selective_forgetting_candidates
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_selective_forgetting_candidate_from_row(row)


def update_runtime_selective_forgetting_candidate_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_selective_forgetting_candidate_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_selective_forgetting_candidates
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_selective_forgetting_candidates
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_selective_forgetting_candidate(signal_id)


def supersede_runtime_selective_forgetting_candidates_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_selective_forgetting_candidate_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_selective_forgetting_candidates
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"selective-forgetting-candidate:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_attachment_topology_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_attachment_topology_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_attachment_topology_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_attachment_topology_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_attachment_topology_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_attachment_topology_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime attachment-topology signal was not persisted")
    signal.update(meta)
    return signal


def upsert_runtime_loyalty_gradient_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_loyalty_gradient_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_loyalty_gradient_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_loyalty_gradient_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=6,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_loyalty_gradient_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_loyalty_gradient_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime loyalty-gradient signal was not persisted")
    signal.update(meta)
    return signal


def upsert_runtime_autonomy_pressure_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_autonomy_pressure_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_autonomy_pressure_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_autonomy_pressure_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=6,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_autonomy_pressure_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_autonomy_pressure_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime autonomy-pressure signal was not persisted")
    signal.update(meta)
    return signal


def upsert_runtime_proactive_loop_lifecycle_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_proactive_loop_lifecycle_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_proactive_loop_lifecycle_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_proactive_loop_lifecycle_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=8,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_proactive_loop_lifecycle_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_proactive_loop_lifecycle_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime proactive-loop lifecycle signal was not persisted")
    signal.update(meta)
    return signal


def upsert_runtime_proactive_question_gate(
    *,
    gate_id: str,
    gate_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_proactive_question_gate_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    gate_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_proactive_question_gates
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_proactive_question_gates (
                    gate_id,
                    gate_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    gate_id,
                    gate_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = gate_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["gate_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=8,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_proactive_question_gates
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE gate_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    gate = get_runtime_proactive_question_gate(resolved_id)
    if gate is None:
        raise RuntimeError("runtime proactive-question gate was not persisted")
    gate.update(meta)
    return gate


def record_runtime_webchat_execution_pilot(
    *,
    pilot_id: str,
    canonical_key: str,
    status: str,
    execution_type: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 0,
    delivery_channel: str = "webchat",
    delivery_state: str = "blocked",
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_webchat_execution_pilot_table(conn)
        conn.execute(
            """
            INSERT INTO runtime_webchat_execution_pilots (
                pilot_id,
                canonical_key,
                status,
                execution_type,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                delivery_channel,
                delivery_state,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pilot_id,
                canonical_key,
                status,
                execution_type,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                max(int(support_count or 0), 1),
                max(int(session_count or 0), 0),
                delivery_channel,
                delivery_state,
                created_at,
                updated_at,
            ),
        )
        conn.commit()
    pilot = get_runtime_webchat_execution_pilot(pilot_id)
    if pilot is None:
        raise RuntimeError("runtime webchat execution pilot was not persisted")
    return pilot


def list_runtime_attachment_topology_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_attachment_topology_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_attachment_topology_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_attachment_topology_signal_from_row(row) for row in rows]


def list_runtime_loyalty_gradient_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_loyalty_gradient_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_loyalty_gradient_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_loyalty_gradient_signal_from_row(row) for row in rows]


def list_runtime_autonomy_pressure_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_autonomy_pressure_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_autonomy_pressure_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_autonomy_pressure_signal_from_row(row) for row in rows]


def list_runtime_proactive_loop_lifecycle_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_proactive_loop_lifecycle_signal_table(conn)
        params: list[object] = []
        where = ""
        if status:
            where = "WHERE status = ?"
            params.append(status)
        params.append(max(int(limit or 0), 1))
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_proactive_loop_lifecycle_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [_runtime_proactive_loop_lifecycle_signal_from_row(row) for row in rows]


def list_runtime_proactive_question_gates(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_proactive_question_gate_table(conn)
        params: list[object] = []
        where = ""
        if status:
            where = "WHERE status = ?"
            params.append(status)
        params.append(max(int(limit or 0), 1))
        rows = conn.execute(
            f"""
            SELECT
                gate_id,
                gate_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_proactive_question_gates
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [_runtime_proactive_question_gate_from_row(row) for row in rows]


def list_runtime_webchat_execution_pilots(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_webchat_execution_pilot_table(conn)
        params: list[object] = []
        where = ""
        if status:
            where = "WHERE status = ?"
            params.append(status)
        params.append(max(int(limit or 0), 1))
        rows = conn.execute(
            f"""
            SELECT
                pilot_id,
                canonical_key,
                status,
                execution_type,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                delivery_channel,
                delivery_state,
                created_at,
                updated_at
            FROM runtime_webchat_execution_pilots
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()
    return [_runtime_webchat_execution_pilot_from_row(row) for row in rows]


def get_runtime_attachment_topology_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_attachment_topology_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_attachment_topology_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_attachment_topology_signal_from_row(row)


def get_runtime_loyalty_gradient_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_loyalty_gradient_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_loyalty_gradient_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_loyalty_gradient_signal_from_row(row)


def get_runtime_autonomy_pressure_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_autonomy_pressure_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_autonomy_pressure_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_autonomy_pressure_signal_from_row(row)


def get_runtime_proactive_loop_lifecycle_signal(
    signal_id: str,
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_proactive_loop_lifecycle_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_proactive_loop_lifecycle_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_proactive_loop_lifecycle_signal_from_row(row)


def get_runtime_proactive_question_gate(gate_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_proactive_question_gate_table(conn)
        row = conn.execute(
            """
            SELECT
                gate_id,
                gate_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_proactive_question_gates
            WHERE gate_id = ?
            LIMIT 1
            """,
            (gate_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_proactive_question_gate_from_row(row)


def get_runtime_webchat_execution_pilot(pilot_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_webchat_execution_pilot_table(conn)
        row = conn.execute(
            """
            SELECT
                pilot_id,
                canonical_key,
                status,
                execution_type,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                delivery_channel,
                delivery_state,
                created_at,
                updated_at
            FROM runtime_webchat_execution_pilots
            WHERE pilot_id = ?
            LIMIT 1
            """,
            (pilot_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_webchat_execution_pilot_from_row(row)


def update_runtime_attachment_topology_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_attachment_topology_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_attachment_topology_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_attachment_topology_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_attachment_topology_signal(signal_id)


def update_runtime_loyalty_gradient_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_loyalty_gradient_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_loyalty_gradient_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_loyalty_gradient_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_loyalty_gradient_signal(signal_id)


def update_runtime_autonomy_pressure_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_autonomy_pressure_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_autonomy_pressure_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_autonomy_pressure_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_autonomy_pressure_signal(signal_id)


def update_runtime_proactive_loop_lifecycle_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_proactive_loop_lifecycle_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_proactive_loop_lifecycle_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_proactive_loop_lifecycle_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_proactive_loop_lifecycle_signal(signal_id)


def update_runtime_proactive_question_gate_status(
    gate_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_proactive_question_gate_table(conn)
        row = conn.execute(
            """
            SELECT gate_id
            FROM runtime_proactive_question_gates
            WHERE gate_id = ?
            LIMIT 1
            """,
            (gate_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_proactive_question_gates
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE gate_id = ?
            """,
            (status, status_reason, updated_at, gate_id),
        )
        conn.commit()
    return get_runtime_proactive_question_gate(gate_id)


def supersede_runtime_attachment_topology_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_attachment_topology_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_attachment_topology_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"attachment-topology:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def supersede_runtime_loyalty_gradient_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_loyalty_gradient_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_loyalty_gradient_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"loyalty-gradient:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def supersede_runtime_autonomy_pressure_signals_for_type(
    *,
    pressure_type: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_autonomy_pressure_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_autonomy_pressure_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key = ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"autonomy-pressure:{pressure_type}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def supersede_runtime_proactive_loop_lifecycle_signals_for_kind(
    *,
    loop_kind: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_proactive_loop_lifecycle_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_proactive_loop_lifecycle_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"proactive-loop-lifecycle:{loop_kind}:%",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def supersede_runtime_proactive_question_gates_for_kind(
    *,
    gate_type: str,
    exclude_gate_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_proactive_question_gate_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_proactive_question_gates
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND gate_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"proactive-question-gate:%",
                exclude_gate_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_executive_contradiction_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_executive_contradiction_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_executive_contradiction_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_executive_contradiction_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_executive_contradiction_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_executive_contradiction_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime executive contradiction signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_executive_contradiction_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_executive_contradiction_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_executive_contradiction_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_executive_contradiction_signal_from_row(row) for row in rows]


def get_runtime_executive_contradiction_signal(
    signal_id: str,
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_executive_contradiction_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_executive_contradiction_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_executive_contradiction_signal_from_row(row)


def update_runtime_executive_contradiction_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_executive_contradiction_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_executive_contradiction_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_executive_contradiction_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_executive_contradiction_signal(signal_id)


def supersede_runtime_executive_contradiction_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_executive_contradiction_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_executive_contradiction_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"executive-contradiction:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_chronicle_consolidation_signal(
    *,
    signal_id: str,
    signal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_signal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    signal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_chronicle_consolidation_signals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_chronicle_consolidation_signals (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = signal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["signal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_chronicle_consolidation_signals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE signal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    signal = get_runtime_chronicle_consolidation_signal(resolved_id)
    if signal is None:
        raise RuntimeError("runtime chronicle consolidation signal was not persisted")
    signal.update(meta)
    return signal


def list_runtime_chronicle_consolidation_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_chronicle_consolidation_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_chronicle_consolidation_signal_from_row(row) for row in rows]


def get_runtime_chronicle_consolidation_signal(
    signal_id: str,
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_chronicle_consolidation_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_chronicle_consolidation_signal_from_row(row)


def update_runtime_chronicle_consolidation_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_chronicle_consolidation_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_chronicle_consolidation_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_chronicle_consolidation_signal(signal_id)


def supersede_runtime_chronicle_consolidation_signals_for_domain(
    *,
    domain_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_chronicle_consolidation_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"chronicle-consolidation:%:{domain_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_chronicle_consolidation_brief(
    *,
    brief_id: str,
    brief_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_brief_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    brief_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_chronicle_consolidation_briefs
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_chronicle_consolidation_briefs (
                    brief_id,
                    brief_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    brief_id,
                    brief_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = brief_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["brief_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_chronicle_consolidation_briefs
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE brief_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    brief = get_runtime_chronicle_consolidation_brief(resolved_id)
    if brief is None:
        raise RuntimeError("runtime chronicle consolidation brief was not persisted")
    brief.update(meta)
    return brief


def list_runtime_chronicle_consolidation_briefs(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_brief_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                brief_id,
                brief_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_chronicle_consolidation_briefs
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_chronicle_consolidation_brief_from_row(row) for row in rows]


def get_runtime_chronicle_consolidation_brief(
    brief_id: str,
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_brief_table(conn)
        row = conn.execute(
            """
            SELECT
                brief_id,
                brief_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_chronicle_consolidation_briefs
            WHERE brief_id = ?
            LIMIT 1
            """,
            (brief_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_chronicle_consolidation_brief_from_row(row)


def update_runtime_chronicle_consolidation_brief_status(
    brief_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_brief_table(conn)
        row = conn.execute(
            """
            SELECT brief_id
            FROM runtime_chronicle_consolidation_briefs
            WHERE brief_id = ?
            LIMIT 1
            """,
            (brief_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_chronicle_consolidation_briefs
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE brief_id = ?
            """,
            (status, status_reason, updated_at, brief_id),
        )
        conn.commit()
    return get_runtime_chronicle_consolidation_brief(brief_id)


def supersede_runtime_chronicle_consolidation_briefs_for_domain(
    *,
    domain_key: str,
    exclude_brief_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_brief_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_chronicle_consolidation_briefs
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND brief_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"chronicle-consolidation-brief:%:{domain_key}",
                exclude_brief_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_chronicle_consolidation_proposal(
    *,
    proposal_id: str,
    proposal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
    support_count: int = 1,
    session_count: int = 1,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_proposal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    proposal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_chronicle_consolidation_proposals
                WHERE canonical_key = ?
                  AND status IN ('active', 'softening', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_chronicle_consolidation_proposals (
                    proposal_id,
                    proposal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal_id,
                    proposal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = proposal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["proposal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_chronicle_consolidation_proposals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE proposal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    proposal = get_runtime_chronicle_consolidation_proposal(resolved_id)
    if proposal is None:
        raise RuntimeError("runtime chronicle consolidation proposal was not persisted")
    proposal.update(meta)
    return proposal


def list_runtime_chronicle_consolidation_proposals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_proposal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                proposal_id,
                proposal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_chronicle_consolidation_proposals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_chronicle_consolidation_proposal_from_row(row) for row in rows]


def get_runtime_chronicle_consolidation_proposal(
    proposal_id: str,
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_proposal_table(conn)
        row = conn.execute(
            """
            SELECT
                proposal_id,
                proposal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_chronicle_consolidation_proposals
            WHERE proposal_id = ?
            LIMIT 1
            """,
            (proposal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_chronicle_consolidation_proposal_from_row(row)


def update_runtime_chronicle_consolidation_proposal_status(
    proposal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_proposal_table(conn)
        row = conn.execute(
            """
            SELECT proposal_id
            FROM runtime_chronicle_consolidation_proposals
            WHERE proposal_id = ?
            LIMIT 1
            """,
            (proposal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_chronicle_consolidation_proposals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE proposal_id = ?
            """,
            (status, status_reason, updated_at, proposal_id),
        )
        conn.commit()
    return get_runtime_chronicle_consolidation_proposal(proposal_id)


def supersede_runtime_chronicle_consolidation_proposals_for_domain(
    *,
    domain_key: str,
    exclude_proposal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_chronicle_consolidation_proposal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_chronicle_consolidation_proposals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND proposal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"chronicle-consolidation-proposal:%:{domain_key}",
                exclude_proposal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def list_runtime_remembered_fact_signals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_remembered_fact_signal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_remembered_fact_signals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_remembered_fact_signal_from_row(row) for row in rows]


def get_runtime_remembered_fact_signal(signal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_remembered_fact_signal_table(conn)
        row = conn.execute(
            """
            SELECT
                signal_id,
                signal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_remembered_fact_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_remembered_fact_signal_from_row(row)


def update_runtime_remembered_fact_signal_status(
    signal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_remembered_fact_signal_table(conn)
        row = conn.execute(
            """
            SELECT signal_id
            FROM runtime_remembered_fact_signals
            WHERE signal_id = ?
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_remembered_fact_signals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE signal_id = ?
            """,
            (status, status_reason, updated_at, signal_id),
        )
        conn.commit()
    return get_runtime_remembered_fact_signal(signal_id)


def supersede_runtime_remembered_fact_signals_for_dimension(
    *,
    dimension_key: str,
    exclude_signal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_remembered_fact_signal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_remembered_fact_signals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND signal_id != ?
              AND status IN ('active', 'softening', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"remembered-fact:%:{dimension_key}",
                exclude_signal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def upsert_runtime_selfhood_proposal(
    *,
    proposal_id: str,
    proposal_type: str,
    canonical_key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    source_kind: str,
    confidence: str,
    evidence_summary: str,
    support_summary: str,
    support_count: int,
    session_count: int,
    created_at: str,
    updated_at: str,
    status_reason: str = "",
    run_id: str = "",
    session_id: str = "",
) -> dict[str, object]:
    with connect() as conn:
        _ensure_runtime_selfhood_proposal_table(conn)
        existing = None
        if canonical_key:
            existing = conn.execute(
                """
                SELECT
                    proposal_id,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                FROM runtime_selfhood_proposals
                WHERE canonical_key = ?
                  AND status IN ('fresh', 'active', 'fading', 'stale')
                ORDER BY id DESC
                LIMIT 1
                """,
                (canonical_key,),
            ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO runtime_selfhood_proposals (
                    proposal_id,
                    proposal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    support_count,
                    session_count,
                    merge_count,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal_id,
                    proposal_type,
                    canonical_key,
                    status,
                    title,
                    summary,
                    rationale,
                    source_kind,
                    confidence,
                    evidence_summary,
                    support_summary,
                    status_reason,
                    run_id,
                    session_id,
                    max(int(support_count or 0), 1),
                    max(int(session_count or 0), 1),
                    0,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            resolved_id = proposal_id
            meta = {"was_created": True, "was_updated": True, "merge_state": "created"}
        else:
            resolved_id = str(existing["proposal_id"])
            merged_source_kind = _stronger_ranked_value(
                str(existing["source_kind"] or ""),
                source_kind,
                _SOURCE_KIND_RANKS,
            )
            merged_confidence = _stronger_ranked_value(
                str(existing["confidence"] or ""),
                confidence,
                _CONFIDENCE_RANKS,
            )
            merged_evidence_summary = _merge_text_fragments(
                str(existing["evidence_summary"] or ""),
                evidence_summary,
                limit=4,
            )
            merged_support_summary = _merge_text_fragments(
                str(existing["support_summary"] or ""),
                support_summary,
                limit=4,
            )
            merged_status_reason = _merge_text_fragments(
                str(existing["status_reason"] or ""),
                status_reason,
                limit=4,
            )
            merged_support_count = max(
                int(existing["support_count"] or 0), max(int(support_count or 0), 1)
            )
            merged_session_count = max(
                int(existing["session_count"] or 0), max(int(session_count or 0), 1)
            )
            same_payload = (
                status == str(existing["status"] or "")
                and title == str(existing["title"] or "")
                and summary == str(existing["summary"] or "")
                and rationale == str(existing["rationale"] or "")
                and merged_source_kind == str(existing["source_kind"] or "")
                and merged_confidence == str(existing["confidence"] or "")
                and merged_evidence_summary == str(existing["evidence_summary"] or "")
                and merged_support_summary == str(existing["support_summary"] or "")
                and merged_status_reason == str(existing["status_reason"] or "")
                and run_id == str(existing["run_id"] or "")
                and session_id == str(existing["session_id"] or "")
                and merged_support_count == int(existing["support_count"] or 0)
                and merged_session_count == int(existing["session_count"] or 0)
            )
            if same_payload:
                meta = {
                    "was_created": False,
                    "was_updated": False,
                    "merge_state": "unchanged",
                }
            else:
                conn.execute(
                    """
                    UPDATE runtime_selfhood_proposals
                    SET
                        status = ?,
                        title = ?,
                        summary = ?,
                        rationale = ?,
                        source_kind = ?,
                        confidence = ?,
                        evidence_summary = ?,
                        support_summary = ?,
                        status_reason = ?,
                        run_id = ?,
                        session_id = ?,
                        support_count = ?,
                        session_count = ?,
                        merge_count = COALESCE(merge_count, 0) + 1,
                        updated_at = ?
                    WHERE proposal_id = ?
                    """,
                    (
                        status,
                        title,
                        summary,
                        rationale,
                        merged_source_kind,
                        merged_confidence,
                        merged_evidence_summary,
                        merged_support_summary,
                        merged_status_reason,
                        run_id,
                        session_id,
                        merged_support_count,
                        merged_session_count,
                        updated_at,
                        resolved_id,
                    ),
                )
                conn.commit()
                meta = {
                    "was_created": False,
                    "was_updated": True,
                    "merge_state": "merged",
                }

    proposal = get_runtime_selfhood_proposal(resolved_id)
    if proposal is None:
        raise RuntimeError("runtime selfhood proposal was not persisted")
    proposal.update(meta)
    return proposal


def list_runtime_selfhood_proposals(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_selfhood_proposal_table(conn)
        clauses: list[str] = []
        params: list[object] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"""
            SELECT
                proposal_id,
                proposal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_selfhood_proposals
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_selfhood_proposal_from_row(row) for row in rows]


def get_runtime_selfhood_proposal(proposal_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_selfhood_proposal_table(conn)
        row = conn.execute(
            """
            SELECT
                proposal_id,
                proposal_type,
                canonical_key,
                status,
                title,
                summary,
                rationale,
                source_kind,
                confidence,
                evidence_summary,
                support_summary,
                status_reason,
                run_id,
                session_id,
                support_count,
                session_count,
                merge_count,
                created_at,
                updated_at
            FROM runtime_selfhood_proposals
            WHERE proposal_id = ?
            LIMIT 1
            """,
            (proposal_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_selfhood_proposal_from_row(row)


def update_runtime_selfhood_proposal_status(
    proposal_id: str,
    *,
    status: str,
    updated_at: str,
    status_reason: str = "",
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_selfhood_proposal_table(conn)
        row = conn.execute(
            """
            SELECT proposal_id
            FROM runtime_selfhood_proposals
            WHERE proposal_id = ?
            LIMIT 1
            """,
            (proposal_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_selfhood_proposals
            SET status = ?, status_reason = ?, updated_at = ?
            WHERE proposal_id = ?
            """,
            (status, status_reason, updated_at, proposal_id),
        )
        conn.commit()
    return get_runtime_selfhood_proposal(proposal_id)


def supersede_runtime_selfhood_proposals_for_domain(
    *,
    domain_key: str,
    exclude_proposal_id: str,
    updated_at: str,
    status_reason: str,
) -> int:
    with connect() as conn:
        _ensure_runtime_selfhood_proposal_table(conn)
        cursor = conn.execute(
            """
            UPDATE runtime_selfhood_proposals
            SET status = 'superseded',
                status_reason = ?,
                updated_at = ?
            WHERE canonical_key LIKE ?
              AND proposal_id != ?
              AND status IN ('fresh', 'active', 'fading', 'stale')
            """,
            (
                status_reason,
                updated_at,
                f"selfhood-proposal:%:{domain_key}",
                exclude_proposal_id,
            ),
        )
        conn.commit()
        return int(cursor.rowcount or 0)


def get_heartbeat_runtime_state() -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                state_id,
                last_tick_id,
                last_tick_at,
                next_tick_at,
                schedule_state,
                due,
                last_decision_type,
                last_result,
                blocked_reason,
                currently_ticking,
                last_trigger_source,
                scheduler_active,
                scheduler_started_at,
                scheduler_stopped_at,
                scheduler_health,
                recovery_status,
                last_recovery_at,
                provider,
                model,
                lane,
                model_source,
                resolution_status,
                fallback_used,
                execution_status,
                parse_status,
                budget_status,
                last_ping_eligible,
                last_ping_result,
                last_action_type,
                last_action_status,
                last_action_summary,
                last_action_artifact,
                updated_at
            FROM heartbeat_runtime_state
            WHERE id = 1
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        return None
    return _heartbeat_runtime_state_from_row(row)


def upsert_heartbeat_runtime_state(
    *,
    state_id: str,
    last_tick_id: str,
    last_tick_at: str,
    next_tick_at: str,
    schedule_state: str,
    due: bool,
    last_decision_type: str,
    last_result: str,
    blocked_reason: str,
    currently_ticking: bool,
    last_trigger_source: str,
    scheduler_active: bool,
    scheduler_started_at: str,
    scheduler_stopped_at: str,
    scheduler_health: str,
    recovery_status: str,
    last_recovery_at: str,
    provider: str,
    model: str,
    lane: str,
    model_source: str,
    resolution_status: str,
    fallback_used: bool,
    execution_status: str,
    parse_status: str,
    budget_status: str,
    last_ping_eligible: bool,
    last_ping_result: str,
    last_action_type: str,
    last_action_status: str,
    last_action_summary: str,
    last_action_artifact: str,
    updated_at: str,
) -> dict[str, object]:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO heartbeat_runtime_state (
                id,
                state_id,
                last_tick_id,
                last_tick_at,
                next_tick_at,
                schedule_state,
                due,
                last_decision_type,
                last_result,
                blocked_reason,
                currently_ticking,
                last_trigger_source,
                scheduler_active,
                scheduler_started_at,
                scheduler_stopped_at,
                scheduler_health,
                recovery_status,
                last_recovery_at,
                provider,
                model,
                lane,
                model_source,
                resolution_status,
                fallback_used,
                execution_status,
                parse_status,
                budget_status,
                last_ping_eligible,
                last_ping_result,
                last_action_type,
                last_action_status,
                last_action_summary,
                last_action_artifact,
                updated_at
            )
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                state_id = excluded.state_id,
                last_tick_id = excluded.last_tick_id,
                last_tick_at = excluded.last_tick_at,
                next_tick_at = excluded.next_tick_at,
                schedule_state = excluded.schedule_state,
                due = excluded.due,
                last_decision_type = excluded.last_decision_type,
                last_result = excluded.last_result,
                blocked_reason = excluded.blocked_reason,
                currently_ticking = excluded.currently_ticking,
                last_trigger_source = excluded.last_trigger_source,
                scheduler_active = excluded.scheduler_active,
                scheduler_started_at = excluded.scheduler_started_at,
                scheduler_stopped_at = excluded.scheduler_stopped_at,
                scheduler_health = excluded.scheduler_health,
                recovery_status = excluded.recovery_status,
                last_recovery_at = excluded.last_recovery_at,
                provider = excluded.provider,
                model = excluded.model,
                lane = excluded.lane,
                model_source = excluded.model_source,
                resolution_status = excluded.resolution_status,
                fallback_used = excluded.fallback_used,
                execution_status = excluded.execution_status,
                parse_status = excluded.parse_status,
                budget_status = excluded.budget_status,
                last_ping_eligible = excluded.last_ping_eligible,
                last_ping_result = excluded.last_ping_result,
                last_action_type = excluded.last_action_type,
                last_action_status = excluded.last_action_status,
                last_action_summary = excluded.last_action_summary,
                last_action_artifact = excluded.last_action_artifact,
                updated_at = excluded.updated_at
            """,
            (
                state_id,
                last_tick_id,
                last_tick_at,
                next_tick_at,
                schedule_state,
                1 if due else 0,
                last_decision_type,
                last_result,
                blocked_reason,
                1 if currently_ticking else 0,
                last_trigger_source,
                1 if scheduler_active else 0,
                scheduler_started_at,
                scheduler_stopped_at,
                scheduler_health,
                recovery_status,
                last_recovery_at,
                provider,
                model,
                lane,
                model_source,
                resolution_status,
                1 if fallback_used else 0,
                execution_status,
                parse_status,
                budget_status,
                1 if last_ping_eligible else 0,
                last_ping_result,
                last_action_type,
                last_action_status,
                last_action_summary,
                last_action_artifact,
                updated_at,
            ),
        )
        conn.commit()
    state = get_heartbeat_runtime_state()
    if state is None:
        raise RuntimeError("heartbeat runtime state was not persisted")
    return state


def record_heartbeat_runtime_tick(
    *,
    tick_id: str,
    trigger: str,
    tick_status: str,
    decision_type: str,
    decision_summary: str,
    decision_reason: str,
    blocked_reason: str,
    provider: str,
    model: str,
    lane: str,
    model_source: str,
    resolution_status: str,
    fallback_used: bool,
    execution_status: str,
    parse_status: str,
    budget_status: str,
    ping_eligible: bool,
    ping_result: str,
    action_status: str,
    action_summary: str,
    action_type: str,
    action_artifact: str,
    raw_response: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    started_at: str,
    finished_at: str,
) -> dict[str, object]:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO heartbeat_runtime_ticks (
                tick_id,
                trigger,
                tick_status,
                decision_type,
                decision_summary,
                decision_reason,
                blocked_reason,
                provider,
                model,
                lane,
                model_source,
                resolution_status,
                fallback_used,
                execution_status,
                parse_status,
                budget_status,
                ping_eligible,
                ping_result,
                action_status,
                action_summary,
                action_type,
                action_artifact,
                raw_response,
                input_tokens,
                output_tokens,
                cost_usd,
                started_at,
                finished_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tick_id,
                trigger,
                tick_status,
                decision_type,
                decision_summary,
                decision_reason,
                blocked_reason,
                provider,
                model,
                lane,
                model_source,
                resolution_status,
                1 if fallback_used else 0,
                execution_status,
                parse_status,
                budget_status,
                1 if ping_eligible else 0,
                ping_result,
                action_status,
                action_summary,
                action_type,
                action_artifact,
                raw_response,
                int(input_tokens or 0),
                int(output_tokens or 0),
                float(cost_usd or 0.0),
                started_at,
                finished_at,
            ),
        )
        conn.commit()
    tick = get_heartbeat_runtime_tick(tick_id)
    if tick is None:
        raise RuntimeError("heartbeat runtime tick was not persisted")
    return tick


def get_heartbeat_runtime_tick(tick_id: str) -> dict[str, object] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                tick_id,
                trigger,
                tick_status,
                decision_type,
                decision_summary,
                decision_reason,
                blocked_reason,
                provider,
                model,
                lane,
                model_source,
                resolution_status,
                fallback_used,
                execution_status,
                parse_status,
                budget_status,
                ping_eligible,
                ping_result,
                action_status,
                action_summary,
                action_type,
                action_artifact,
                raw_response,
                input_tokens,
                output_tokens,
                cost_usd,
                started_at,
                finished_at
            FROM heartbeat_runtime_ticks
            WHERE tick_id = ?
            LIMIT 1
            """,
            (tick_id,),
        ).fetchone()
    if row is None:
        return None
    return _heartbeat_runtime_tick_from_row(row)


def recent_heartbeat_runtime_ticks(limit: int = 10) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                tick_id,
                trigger,
                tick_status,
                decision_type,
                decision_summary,
                decision_reason,
                blocked_reason,
                provider,
                model,
                lane,
                model_source,
                resolution_status,
                fallback_used,
                execution_status,
                parse_status,
                budget_status,
                ping_eligible,
                ping_result,
                action_status,
                action_summary,
                action_type,
                action_artifact,
                raw_response,
                input_tokens,
                output_tokens,
                cost_usd,
                started_at,
                finished_at
            FROM heartbeat_runtime_ticks
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [_heartbeat_runtime_tick_from_row(row) for row in rows]


def _runtime_contract_candidate_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "candidate_id": row["candidate_id"],
        "candidate_type": row["candidate_type"],
        "target_file": row["target_file"],
        "status": row["status"],
        "source_kind": row["source_kind"],
        "source_mode": row["source_mode"],
        "actor": row["actor"],
        "session_id": row["session_id"],
        "run_id": row["run_id"],
        "canonical_key": row["canonical_key"],
        "summary": row["summary"],
        "reason": row["reason"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "proposed_value": row["proposed_value"],
        "write_section": row["write_section"],
        "confidence": row["confidence"],
        "evidence_class": row["evidence_class"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _heartbeat_runtime_state_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "state_id": row["state_id"],
        "last_tick_id": row["last_tick_id"],
        "last_tick_at": row["last_tick_at"],
        "next_tick_at": row["next_tick_at"],
        "schedule_state": row["schedule_state"],
        "due": bool(row["due"]),
        "last_decision_type": row["last_decision_type"],
        "last_result": row["last_result"],
        "blocked_reason": row["blocked_reason"],
        "currently_ticking": bool(row["currently_ticking"]),
        "last_trigger_source": row["last_trigger_source"],
        "scheduler_active": bool(row["scheduler_active"]),
        "scheduler_started_at": row["scheduler_started_at"],
        "scheduler_stopped_at": row["scheduler_stopped_at"],
        "scheduler_health": row["scheduler_health"],
        "recovery_status": row["recovery_status"],
        "last_recovery_at": row["last_recovery_at"],
        "provider": row["provider"],
        "model": row["model"],
        "lane": row["lane"],
        "model_source": row["model_source"],
        "resolution_status": row["resolution_status"],
        "fallback_used": bool(row["fallback_used"]),
        "execution_status": row["execution_status"],
        "parse_status": row["parse_status"],
        "budget_status": row["budget_status"],
        "last_ping_eligible": bool(row["last_ping_eligible"]),
        "last_ping_result": row["last_ping_result"],
        "last_action_type": row["last_action_type"],
        "last_action_status": row["last_action_status"],
        "last_action_summary": row["last_action_summary"],
        "last_action_artifact": row["last_action_artifact"],
        "updated_at": row["updated_at"],
    }


def _heartbeat_runtime_tick_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "tick_id": row["tick_id"],
        "trigger": row["trigger"],
        "tick_status": row["tick_status"],
        "decision_type": row["decision_type"],
        "decision_summary": row["decision_summary"],
        "decision_reason": row["decision_reason"],
        "blocked_reason": row["blocked_reason"],
        "provider": row["provider"],
        "model": row["model"],
        "lane": row["lane"],
        "model_source": row["model_source"],
        "resolution_status": row["resolution_status"],
        "fallback_used": bool(row["fallback_used"]),
        "execution_status": row["execution_status"],
        "parse_status": row["parse_status"],
        "budget_status": row["budget_status"],
        "ping_eligible": bool(row["ping_eligible"]),
        "ping_result": row["ping_result"],
        "action_status": row["action_status"],
        "action_summary": row["action_summary"],
        "action_type": row["action_type"],
        "action_artifact": row["action_artifact"],
        "raw_response": row["raw_response"],
        "input_tokens": int(row["input_tokens"] or 0),
        "output_tokens": int(row["output_tokens"] or 0),
        "cost_usd": float(row["cost_usd"] or 0.0),
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
    }


def _ensure_heartbeat_runtime_state_columns(conn: sqlite3.Connection) -> None:
    rows = conn.execute("PRAGMA table_info(heartbeat_runtime_state)").fetchall()
    existing = {str(row["name"]) for row in rows}
    if "currently_ticking" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN currently_ticking INTEGER NOT NULL DEFAULT 0
            """
        )
    if "last_trigger_source" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN last_trigger_source TEXT NOT NULL DEFAULT ''
            """
        )
    if "schedule_state" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN schedule_state TEXT NOT NULL DEFAULT ''
            """
        )
    if "due" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN due INTEGER NOT NULL DEFAULT 0
            """
        )
    if "scheduler_active" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN scheduler_active INTEGER NOT NULL DEFAULT 0
            """
        )
    if "scheduler_started_at" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN scheduler_started_at TEXT NOT NULL DEFAULT ''
            """
        )
    if "scheduler_stopped_at" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN scheduler_stopped_at TEXT NOT NULL DEFAULT ''
            """
        )
    if "scheduler_health" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN scheduler_health TEXT NOT NULL DEFAULT ''
            """
        )
    if "recovery_status" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN recovery_status TEXT NOT NULL DEFAULT ''
            """
        )
    if "last_recovery_at" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN last_recovery_at TEXT NOT NULL DEFAULT ''
            """
        )
    if "last_action_type" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN last_action_type TEXT NOT NULL DEFAULT ''
            """
        )
    if "last_action_status" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN last_action_status TEXT NOT NULL DEFAULT ''
            """
        )
    if "last_action_summary" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN last_action_summary TEXT NOT NULL DEFAULT ''
            """
        )
    if "last_action_artifact" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN last_action_artifact TEXT NOT NULL DEFAULT ''
            """
        )
    if "model_source" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN model_source TEXT NOT NULL DEFAULT ''
            """
        )
    if "resolution_status" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN resolution_status TEXT NOT NULL DEFAULT ''
            """
        )
    if "fallback_used" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN fallback_used INTEGER NOT NULL DEFAULT 0
            """
        )
    if "execution_status" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN execution_status TEXT NOT NULL DEFAULT ''
            """
        )
    if "parse_status" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_state
            ADD COLUMN parse_status TEXT NOT NULL DEFAULT ''
            """
        )


def _ensure_heartbeat_runtime_tick_columns(conn: sqlite3.Connection) -> None:
    rows = conn.execute("PRAGMA table_info(heartbeat_runtime_ticks)").fetchall()
    existing = {str(row["name"]) for row in rows}
    if "action_type" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_ticks
            ADD COLUMN action_type TEXT NOT NULL DEFAULT ''
            """
        )
    if "action_artifact" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_ticks
            ADD COLUMN action_artifact TEXT NOT NULL DEFAULT ''
            """
        )
    if "model_source" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_ticks
            ADD COLUMN model_source TEXT NOT NULL DEFAULT ''
            """
        )
    if "resolution_status" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_ticks
            ADD COLUMN resolution_status TEXT NOT NULL DEFAULT ''
            """
        )
    if "fallback_used" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_ticks
            ADD COLUMN fallback_used INTEGER NOT NULL DEFAULT 0
            """
        )
    if "execution_status" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_ticks
            ADD COLUMN execution_status TEXT NOT NULL DEFAULT ''
            """
        )
    if "parse_status" not in existing:
        conn.execute(
            """
            ALTER TABLE heartbeat_runtime_ticks
            ADD COLUMN parse_status TEXT NOT NULL DEFAULT ''
            """
        )


def _ensure_runtime_contract_candidate_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_contract_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id TEXT NOT NULL UNIQUE,
            candidate_type TEXT NOT NULL,
            target_file TEXT NOT NULL,
            status TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            source_mode TEXT NOT NULL,
            actor TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            canonical_key TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            proposed_value TEXT NOT NULL DEFAULT '',
            write_section TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_class TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_contract_candidates_status_target
        ON runtime_contract_candidates(status, target_file, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_contract_candidates_canonical_key
        ON runtime_contract_candidates(candidate_type, target_file, canonical_key, id DESC)
        """
    )
    rows = conn.execute("PRAGMA table_info(runtime_contract_candidates)").fetchall()
    existing = {str(row["name"]) for row in rows}
    required_columns = {
        "status_reason": "TEXT NOT NULL DEFAULT ''",
        "proposed_value": "TEXT NOT NULL DEFAULT ''",
        "write_section": "TEXT NOT NULL DEFAULT ''",
        "evidence_class": "TEXT NOT NULL DEFAULT ''",
        "support_count": "INTEGER NOT NULL DEFAULT 1",
        "session_count": "INTEGER NOT NULL DEFAULT 1",
        "merge_count": "INTEGER NOT NULL DEFAULT 0",
    }
    for name, spec in required_columns.items():
        if name in existing:
            continue
        conn.execute(
            f"ALTER TABLE runtime_contract_candidates ADD COLUMN {name} {spec}"
        )


def _ensure_runtime_contract_file_write_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_contract_file_writes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            write_id TEXT NOT NULL UNIQUE,
            candidate_id TEXT NOT NULL,
            target_file TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            write_status TEXT NOT NULL,
            actor TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL,
            content_line TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_contract_file_writes_target
        ON runtime_contract_file_writes(target_file, id DESC)
        """
    )


def _runtime_contract_file_write_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "write_id": row["write_id"],
        "candidate_id": row["candidate_id"],
        "target_file": row["target_file"],
        "canonical_key": row["canonical_key"],
        "write_status": row["write_status"],
        "actor": row["actor"],
        "summary": row["summary"],
        "content_line": row["content_line"],
        "created_at": row["created_at"],
    }


def _ensure_runtime_development_focus_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_development_focuses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            focus_id TEXT NOT NULL UNIQUE,
            focus_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_development_focuses_status
        ON runtime_development_focuses(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_development_focuses_canonical_key
        ON runtime_development_focuses(canonical_key, id DESC)
        """
    )


def _ensure_runtime_reflective_critic_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_reflective_critics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            critic_id TEXT NOT NULL UNIQUE,
            critic_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_reflective_critics_status
        ON runtime_reflective_critics(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_reflective_critics_canonical_key
        ON runtime_reflective_critics(canonical_key, id DESC)
        """
    )


def _ensure_runtime_world_model_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_world_model_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_world_model_signals_status
        ON runtime_world_model_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_world_model_signals_canonical_key
        ON runtime_world_model_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_self_model_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_self_model_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_model_signals_status
        ON runtime_self_model_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_model_signals_canonical_key
        ON runtime_self_model_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_goal_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_goal_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id TEXT NOT NULL UNIQUE,
            goal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_goal_signals_status
        ON runtime_goal_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_goal_signals_canonical_key
        ON runtime_goal_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_awareness_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_awareness_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL,
            status TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            rationale TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            confidence TEXT NOT NULL,
            evidence_summary TEXT NOT NULL,
            support_summary TEXT NOT NULL,
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 0,
            session_count INTEGER NOT NULL DEFAULT 0,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_awareness_signals_status
        ON runtime_awareness_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_awareness_signals_canonical_key
        ON runtime_awareness_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_reflection_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_reflection_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_reflection_signals_status
        ON runtime_reflection_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_reflection_signals_canonical_key
        ON runtime_reflection_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_temporal_recurrence_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_temporal_recurrence_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_temporal_recurrence_signals_status
        ON runtime_temporal_recurrence_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_temporal_recurrence_signals_canonical_key
        ON runtime_temporal_recurrence_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_witness_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_witness_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'fresh',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_witness_signals_status
        ON runtime_witness_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_witness_signals_canonical_key
        ON runtime_witness_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_open_loop_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_open_loop_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'open',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_open_loop_signals_status
        ON runtime_open_loop_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_open_loop_signals_canonical_key
        ON runtime_open_loop_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_internal_opposition_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_internal_opposition_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_internal_opposition_signals_status
        ON runtime_internal_opposition_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_internal_opposition_signals_canonical_key
        ON runtime_internal_opposition_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_self_review_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_self_review_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_signals_status
        ON runtime_self_review_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_signals_canonical_key
        ON runtime_self_review_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_self_review_record_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_self_review_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT NOT NULL UNIQUE,
            record_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'fresh',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_records_status
        ON runtime_self_review_records(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_records_canonical_key
        ON runtime_self_review_records(canonical_key, id DESC)
        """
    )


def _ensure_runtime_self_review_run_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_self_review_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL UNIQUE,
            run_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'fresh',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            record_run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_runs_status
        ON runtime_self_review_runs(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_runs_canonical_key
        ON runtime_self_review_runs(canonical_key, id DESC)
        """
    )


def _ensure_runtime_self_review_outcome_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_self_review_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            outcome_id TEXT NOT NULL UNIQUE,
            outcome_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'fresh',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            review_run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_outcomes_status
        ON runtime_self_review_outcomes(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_outcomes_canonical_key
        ON runtime_self_review_outcomes(canonical_key, id DESC)
        """
    )


def _ensure_runtime_self_review_cadence_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_self_review_cadence_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_cadence_signals_status
        ON runtime_self_review_cadence_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_review_cadence_signals_canonical_key
        ON runtime_self_review_cadence_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_open_loop_closure_proposal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_open_loop_closure_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT NOT NULL UNIQUE,
            proposal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'fresh',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_open_loop_closure_proposals_status
        ON runtime_open_loop_closure_proposals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_open_loop_closure_proposals_canonical_key
        ON runtime_open_loop_closure_proposals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_dream_hypothesis_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_dream_hypothesis_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_dream_hypothesis_signals_status
        ON runtime_dream_hypothesis_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_dream_hypothesis_signals_canonical_key
        ON runtime_dream_hypothesis_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_dream_adoption_candidate_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_dream_adoption_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id TEXT NOT NULL UNIQUE,
            candidate_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'fresh',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_dream_adoption_candidates_status
        ON runtime_dream_adoption_candidates(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_dream_adoption_candidates_canonical_key
        ON runtime_dream_adoption_candidates(canonical_key, id DESC)
        """
    )


def _ensure_runtime_dream_influence_proposal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_dream_influence_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT NOT NULL UNIQUE,
            proposal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'fresh',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_dream_influence_proposals_status
        ON runtime_dream_influence_proposals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_dream_influence_proposals_canonical_key
        ON runtime_dream_influence_proposals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_self_authored_prompt_proposal_table(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_self_authored_prompt_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT NOT NULL UNIQUE,
            proposal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'fresh',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_authored_prompt_proposals_status
        ON runtime_self_authored_prompt_proposals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_authored_prompt_proposals_canonical_key
        ON runtime_self_authored_prompt_proposals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_user_md_update_proposal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_user_md_update_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT NOT NULL UNIQUE,
            proposal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'fresh',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_user_md_update_proposals_status
        ON runtime_user_md_update_proposals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_user_md_update_proposals_canonical_key
        ON runtime_user_md_update_proposals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_user_understanding_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_user_understanding_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_user_understanding_signals_status
        ON runtime_user_understanding_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_user_understanding_signals_canonical_key
        ON runtime_user_understanding_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_remembered_fact_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_remembered_fact_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_remembered_fact_signals_status
        ON runtime_remembered_fact_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_remembered_fact_signals_canonical_key
        ON runtime_remembered_fact_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_private_inner_note_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_private_inner_note_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_private_inner_note_signals_status
        ON runtime_private_inner_note_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_private_inner_note_signals_canonical_key
        ON runtime_private_inner_note_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_private_initiative_tension_signal_table(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_private_initiative_tension_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_private_initiative_tension_signals_status
        ON runtime_private_initiative_tension_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_private_initiative_tension_signals_canonical_key
        ON runtime_private_initiative_tension_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_private_inner_interplay_signal_table(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_private_inner_interplay_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_private_inner_interplay_signals_status
        ON runtime_private_inner_interplay_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_private_inner_interplay_signals_canonical_key
        ON runtime_private_inner_interplay_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_private_state_snapshot_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_private_state_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id TEXT NOT NULL UNIQUE,
            snapshot_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_private_state_snapshots_status
        ON runtime_private_state_snapshots(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_private_state_snapshots_canonical_key
        ON runtime_private_state_snapshots(canonical_key, id DESC)
        """
    )


def _ensure_runtime_private_temporal_curiosity_state_table(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_private_temporal_curiosity_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_id TEXT NOT NULL UNIQUE,
            state_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_private_temporal_curiosity_states_status
        ON runtime_private_temporal_curiosity_states(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_private_temporal_curiosity_states_canonical_key
        ON runtime_private_temporal_curiosity_states(canonical_key, id DESC)
        """
    )


def _ensure_runtime_private_temporal_promotion_signal_table(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_private_temporal_promotion_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_private_temporal_promotion_signals_status
        ON runtime_private_temporal_promotion_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_private_temporal_promotion_signals_canonical_key
        ON runtime_private_temporal_promotion_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_inner_visible_support_signal_table(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_inner_visible_support_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_inner_visible_support_signals_status
        ON runtime_inner_visible_support_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_inner_visible_support_signals_canonical_key
        ON runtime_inner_visible_support_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_regulation_homeostasis_signal_table(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_regulation_homeostasis_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_regulation_homeostasis_signals_status
        ON runtime_regulation_homeostasis_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_regulation_homeostasis_signals_canonical_key
        ON runtime_regulation_homeostasis_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_relation_state_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_relation_state_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_relation_state_signals_status
        ON runtime_relation_state_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_relation_state_signals_canonical_key
        ON runtime_relation_state_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_relation_continuity_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_relation_continuity_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_relation_continuity_signals_status
        ON runtime_relation_continuity_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_relation_continuity_signals_canonical_key
        ON runtime_relation_continuity_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_meaning_significance_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_meaning_significance_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_meaning_significance_signals_status
        ON runtime_meaning_significance_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_meaning_significance_signals_canonical_key
        ON runtime_meaning_significance_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_temperament_tendency_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_temperament_tendency_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_temperament_tendency_signals_status
        ON runtime_temperament_tendency_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_temperament_tendency_signals_canonical_key
        ON runtime_temperament_tendency_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_self_narrative_continuity_signal_table(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_self_narrative_continuity_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_narrative_continuity_signals_status
        ON runtime_self_narrative_continuity_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_self_narrative_continuity_signals_canonical_key
        ON runtime_self_narrative_continuity_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_metabolism_state_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_metabolism_state_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_metabolism_state_signals_status
        ON runtime_metabolism_state_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_metabolism_state_signals_canonical_key
        ON runtime_metabolism_state_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_release_marker_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_release_marker_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_release_marker_signals_status
        ON runtime_release_marker_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_release_marker_signals_canonical_key
        ON runtime_release_marker_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_consolidation_target_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_consolidation_target_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_consolidation_target_signals_status
        ON runtime_consolidation_target_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_consolidation_target_signals_canonical_key
        ON runtime_consolidation_target_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_selective_forgetting_candidate_table(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_selective_forgetting_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_selective_forgetting_candidates_status
        ON runtime_selective_forgetting_candidates(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_selective_forgetting_candidates_canonical_key
        ON runtime_selective_forgetting_candidates(canonical_key, id DESC)
        """
    )


def _ensure_runtime_attachment_topology_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_attachment_topology_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL,
            status TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            rationale TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            confidence TEXT NOT NULL,
            evidence_summary TEXT NOT NULL,
            support_summary TEXT NOT NULL,
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_attachment_topology_signals_status
        ON runtime_attachment_topology_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_attachment_topology_signals_canonical_key
        ON runtime_attachment_topology_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_loyalty_gradient_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_loyalty_gradient_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL,
            status TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            rationale TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            confidence TEXT NOT NULL,
            evidence_summary TEXT NOT NULL,
            support_summary TEXT NOT NULL,
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_loyalty_gradient_signals_status
        ON runtime_loyalty_gradient_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_loyalty_gradient_signals_canonical_key
        ON runtime_loyalty_gradient_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_autonomy_pressure_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_autonomy_pressure_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL,
            status TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            rationale TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            confidence TEXT NOT NULL,
            evidence_summary TEXT NOT NULL,
            support_summary TEXT NOT NULL,
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_autonomy_pressure_signals_status
        ON runtime_autonomy_pressure_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_autonomy_pressure_signals_canonical_key
        ON runtime_autonomy_pressure_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_proactive_loop_lifecycle_signal_table(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_proactive_loop_lifecycle_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL,
            status TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            rationale TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            confidence TEXT NOT NULL,
            evidence_summary TEXT NOT NULL,
            support_summary TEXT NOT NULL,
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_proactive_loop_lifecycle_signals_status
        ON runtime_proactive_loop_lifecycle_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_proactive_loop_lifecycle_signals_canonical_key
        ON runtime_proactive_loop_lifecycle_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_proactive_question_gate_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_proactive_question_gates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gate_id TEXT NOT NULL UNIQUE,
            gate_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL,
            status TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            rationale TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            confidence TEXT NOT NULL,
            evidence_summary TEXT NOT NULL,
            support_summary TEXT NOT NULL,
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_proactive_question_gates_status
        ON runtime_proactive_question_gates(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_proactive_question_gates_canonical_key
        ON runtime_proactive_question_gates(canonical_key, id DESC)
        """
    )


def _ensure_runtime_webchat_execution_pilot_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_webchat_execution_pilots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pilot_id TEXT NOT NULL UNIQUE,
            canonical_key TEXT NOT NULL,
            status TEXT NOT NULL,
            execution_type TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            rationale TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            confidence TEXT NOT NULL,
            evidence_summary TEXT NOT NULL,
            support_summary TEXT NOT NULL,
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 0,
            delivery_channel TEXT NOT NULL DEFAULT 'webchat',
            delivery_state TEXT NOT NULL DEFAULT 'blocked',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_webchat_execution_pilots_status
        ON runtime_webchat_execution_pilots(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_webchat_execution_pilots_canonical_key
        ON runtime_webchat_execution_pilots(canonical_key, id DESC)
        """
    )


def _ensure_runtime_executive_contradiction_signal_table(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_executive_contradiction_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_executive_contradiction_signals_status
        ON runtime_executive_contradiction_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_executive_contradiction_signals_canonical_key
        ON runtime_executive_contradiction_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_chronicle_consolidation_signal_table(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_chronicle_consolidation_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_chronicle_consolidation_signals_status
        ON runtime_chronicle_consolidation_signals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_chronicle_consolidation_signals_canonical_key
        ON runtime_chronicle_consolidation_signals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_chronicle_consolidation_brief_table(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_chronicle_consolidation_briefs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brief_id TEXT NOT NULL UNIQUE,
            brief_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_chronicle_consolidation_briefs_status
        ON runtime_chronicle_consolidation_briefs(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_chronicle_consolidation_briefs_canonical_key
        ON runtime_chronicle_consolidation_briefs(canonical_key, id DESC)
        """
    )


def _ensure_runtime_chronicle_consolidation_proposal_table(
    conn: sqlite3.Connection,
) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_chronicle_consolidation_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT NOT NULL UNIQUE,
            proposal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '',
            confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '',
            support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_chronicle_consolidation_proposals_status
        ON runtime_chronicle_consolidation_proposals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_chronicle_consolidation_proposals_canonical_key
        ON runtime_chronicle_consolidation_proposals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_memory_md_update_proposal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_memory_md_update_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT NOT NULL UNIQUE,
            proposal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL,
            status TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            rationale TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            confidence TEXT NOT NULL,
            evidence_summary TEXT NOT NULL,
            support_summary TEXT NOT NULL,
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_memory_md_update_proposals_status
        ON runtime_memory_md_update_proposals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_memory_md_update_proposals_canonical_key
        ON runtime_memory_md_update_proposals(canonical_key, id DESC)
        """
    )


def _ensure_runtime_selfhood_proposal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_selfhood_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT NOT NULL UNIQUE,
            proposal_type TEXT NOT NULL,
            canonical_key TEXT NOT NULL,
            status TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            rationale TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            confidence TEXT NOT NULL,
            evidence_summary TEXT NOT NULL,
            support_summary TEXT NOT NULL,
            status_reason TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1,
            merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_selfhood_proposals_status
        ON runtime_selfhood_proposals(status, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_selfhood_proposals_canonical_key
        ON runtime_selfhood_proposals(canonical_key, id DESC)
        """
    )


def _runtime_development_focus_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "focus_id": row["focus_id"],
        "focus_type": row["focus_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_user_understanding_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_remembered_fact_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_private_inner_note_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_private_initiative_tension_signal_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_private_inner_interplay_signal_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_private_state_snapshot_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "snapshot_id": row["snapshot_id"],
        "snapshot_type": row["snapshot_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_private_temporal_curiosity_state_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "state_id": row["state_id"],
        "state_type": row["state_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_private_temporal_promotion_signal_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_inner_visible_support_signal_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_regulation_homeostasis_signal_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_relation_state_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_relation_continuity_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_meaning_significance_signal_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_temperament_tendency_signal_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_self_narrative_continuity_signal_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_metabolism_state_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_release_marker_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_consolidation_target_signal_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_selective_forgetting_candidate_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_attachment_topology_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": row["support_count"],
        "session_count": row["session_count"],
        "merge_count": row["merge_count"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_loyalty_gradient_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_autonomy_pressure_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_proactive_loop_lifecycle_signal_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_proactive_question_gate_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "gate_id": row["gate_id"],
        "gate_type": row["gate_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_webchat_execution_pilot_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "pilot_id": row["pilot_id"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "execution_type": row["execution_type"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "delivery_channel": row["delivery_channel"],
        "delivery_state": row["delivery_state"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_executive_contradiction_signal_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_chronicle_consolidation_signal_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_chronicle_consolidation_brief_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "brief_id": row["brief_id"],
        "brief_type": row["brief_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_chronicle_consolidation_proposal_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "proposal_id": row["proposal_id"],
        "proposal_type": row["proposal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_reflective_critic_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "critic_id": row["critic_id"],
        "critic_type": row["critic_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_world_model_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_self_model_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_goal_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "goal_id": row["goal_id"],
        "goal_type": row["goal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_awareness_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_reflection_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_temporal_recurrence_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_witness_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_open_loop_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_internal_opposition_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_self_review_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_self_review_record_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "record_id": row["record_id"],
        "record_type": row["record_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_self_review_run_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "run_id": row["run_id"],
        "run_type": row["run_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "record_run_id": row["record_run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_self_review_outcome_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "outcome_id": row["outcome_id"],
        "outcome_type": row["outcome_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "review_run_id": row["review_run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_self_review_cadence_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_open_loop_closure_proposal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "proposal_id": row["proposal_id"],
        "proposal_type": row["proposal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_dream_hypothesis_signal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "signal_id": row["signal_id"],
        "signal_type": row["signal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_dream_adoption_candidate_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "candidate_id": row["candidate_id"],
        "candidate_type": row["candidate_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_dream_influence_proposal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "proposal_id": row["proposal_id"],
        "proposal_type": row["proposal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_self_authored_prompt_proposal_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "proposal_id": row["proposal_id"],
        "proposal_type": row["proposal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_user_md_update_proposal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "proposal_id": row["proposal_id"],
        "proposal_type": row["proposal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_memory_md_update_proposal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "proposal_id": row["proposal_id"],
        "proposal_type": row["proposal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _runtime_selfhood_proposal_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "proposal_id": row["proposal_id"],
        "proposal_type": row["proposal_type"],
        "canonical_key": row["canonical_key"],
        "status": row["status"],
        "title": row["title"],
        "summary": row["summary"],
        "rationale": row["rationale"],
        "source_kind": row["source_kind"],
        "confidence": row["confidence"],
        "evidence_summary": row["evidence_summary"],
        "support_summary": row["support_summary"],
        "status_reason": row["status_reason"],
        "run_id": row["run_id"],
        "session_id": row["session_id"],
        "support_count": int(row["support_count"] or 0),
        "session_count": int(row["session_count"] or 0),
        "merge_count": int(row["merge_count"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
