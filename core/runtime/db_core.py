"""Core infrastructure for core.runtime.db modulet.

Indeholder:
- DB_PATH konstant
- ClosingConnection (context-manager wrapper)
- connect() — primær DB-forbindelse
- Konstant-ranks (_CONFIDENCE_RANKS, _EVIDENCE_CLASS_RANKS, _SOURCE_KIND_RANKS)
- Helper-funktioner (_rank_for, _stronger_ranked_value, _merge_text_fragments)
- init_db() — schema bootstrap for hele DB'en
- Runtime-state KV (set/get_runtime_state_value)
- _now_iso() helper
- _SIGNAL_TABLES_WITH_STATUS — liste af signal-tabeller med status-felt
- _ensure-once cache infrastructure (_ENSURED_TABLES, _install_ensure_once_cache,
  _install_ensure_once_cache_for, _conn_db_id, invalidate_ensure_once_cache)

Andre db_*.py submoduler må KUN importere fra dette modul (forhindrer
cirkulære imports). Alle public symboler re-eksporteres fra
core.runtime.db facaden for bagudkompat.

Split-spec: docs/superpowers/specs/2026-05-15-db-split-design.md
"""
from __future__ import annotations

import json as _json
import sqlite3
import sys as _sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from core.runtime.config import STATE_DIR


# === Constants, ClosingConnection, connect, helpers, KV, init_db (verbatim from db.py L11-1128) ===
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


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, factory=ClosingConnection)
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


def set_runtime_state_value(key: str, value: object, *, updated_at: str = "") -> None:
    normalized_key = str(key or "").strip()
    if not normalized_key:
        raise ValueError("key must not be empty")
    timestamp = updated_at or datetime.now(UTC).isoformat()
    payload = _json.dumps(value, ensure_ascii=False)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO runtime_state_kv (key, value_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value_json = excluded.value_json,
                updated_at = excluded.updated_at
            """,
            (normalized_key, payload, timestamp),
        )


def get_runtime_state_value(key: str, default: object = None) -> object:
    normalized_key = str(key or "").strip()
    if not normalized_key:
        return default
    with connect() as conn:
        row = conn.execute(
            "SELECT value_json FROM runtime_state_kv WHERE key = ?",
            (normalized_key,),
        ).fetchone()
    if row is None:
        return default
    try:
        return _json.loads(str(row["value_json"]))
    except Exception:
        return default


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
            CREATE TABLE IF NOT EXISTS runtime_state_kv (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL
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
            CREATE TABLE IF NOT EXISTS cheap_provider_runtime_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                lane TEXT NOT NULL DEFAULT 'cheap',
                status TEXT NOT NULL DEFAULT '',
                auth_ready INTEGER NOT NULL DEFAULT 0,
                quota_limited INTEGER NOT NULL DEFAULT 0,
                cooldown_until TEXT,
                last_error_code TEXT NOT NULL DEFAULT '',
                last_error_message TEXT NOT NULL DEFAULT '',
                last_success_at TEXT,
                last_failure_at TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL,
                UNIQUE(provider, model, lane)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cheap_provider_invocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lane TEXT NOT NULL DEFAULT 'cheap',
                provider TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                error_code TEXT NOT NULL DEFAULT '',
                error_message TEXT NOT NULL DEFAULT '',
                retry_after_seconds INTEGER NOT NULL DEFAULT 0,
                latency_ms INTEGER NOT NULL DEFAULT 0,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                cost_usd REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cheap_provider_invocations_lookup
            ON cheap_provider_invocations(provider, lane, created_at DESC)
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
            CREATE TABLE IF NOT EXISTS runtime_action_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                outcome_id TEXT NOT NULL UNIQUE,
                action_id TEXT NOT NULL,
                decision_mode TEXT NOT NULL,
                decision_reason TEXT NOT NULL DEFAULT '',
                decision_score REAL NOT NULL DEFAULT 0,
                payload_json TEXT NOT NULL DEFAULT '{}',
                result_status TEXT NOT NULL,
                result_summary TEXT NOT NULL DEFAULT '',
                result_json TEXT NOT NULL DEFAULT '{}',
                recorded_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_action_outcomes_lookup
            ON runtime_action_outcomes(action_id, recorded_at DESC)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_learning_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT NOT NULL UNIQUE,
                outcome_id TEXT NOT NULL,
                source_action_id TEXT NOT NULL,
                target_action_id TEXT NOT NULL DEFAULT '',
                target_family TEXT NOT NULL DEFAULT '',
                target_domain TEXT NOT NULL DEFAULT '',
                signal_key TEXT NOT NULL,
                signal_weight REAL NOT NULL DEFAULT 0,
                signal_count INTEGER NOT NULL DEFAULT 1,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                recorded_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_learning_signals_lookup
            ON runtime_learning_signals(signal_key, target_family, target_action_id, recorded_at DESC)
            """
        )
        try:
            conn.execute(
                """
                ALTER TABLE runtime_learning_signals
                ADD COLUMN target_domain TEXT NOT NULL DEFAULT ''
                """
            )
        except sqlite3.OperationalError:
            pass
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL UNIQUE,
                kind TEXT NOT NULL,
                origin TEXT NOT NULL,
                status TEXT NOT NULL,
                goal TEXT NOT NULL,
                scope TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'medium',
                flow_id TEXT NOT NULL DEFAULT '',
                session_id TEXT NOT NULL DEFAULT '',
                run_id TEXT NOT NULL DEFAULT '',
                owner TEXT NOT NULL DEFAULT '',
                retry_at TEXT NOT NULL DEFAULT '',
                blocked_reason TEXT NOT NULL DEFAULT '',
                result_summary TEXT NOT NULL DEFAULT '',
                artifact_ref TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_tasks_status_priority
            ON runtime_tasks(status, priority, id DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_tasks_kind_origin
            ON runtime_tasks(kind, origin, id DESC)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_flows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flow_id TEXT NOT NULL UNIQUE,
                task_id TEXT NOT NULL,
                status TEXT NOT NULL,
                current_step TEXT NOT NULL DEFAULT '',
                step_state TEXT NOT NULL DEFAULT '',
                plan_json TEXT NOT NULL DEFAULT '[]',
                next_action TEXT NOT NULL DEFAULT '',
                last_error TEXT NOT NULL DEFAULT '',
                attempt_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_flows_task_status
            ON runtime_flows(task_id, status, id DESC)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_hook_dispatches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL UNIQUE,
                event_kind TEXT NOT NULL,
                status TEXT NOT NULL,
                task_id TEXT NOT NULL DEFAULT '',
                flow_id TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_hook_dispatches_status
            ON runtime_hook_dispatches(status, id DESC)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runtime_browser_bodies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                body_id TEXT NOT NULL UNIQUE,
                profile_name TEXT NOT NULL,
                status TEXT NOT NULL,
                active_task_id TEXT NOT NULL DEFAULT '',
                active_flow_id TEXT NOT NULL DEFAULT '',
                focused_tab_id TEXT NOT NULL DEFAULT '',
                tabs_json TEXT NOT NULL DEFAULT '[]',
                last_url TEXT NOT NULL DEFAULT '',
                last_title TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_runtime_browser_bodies_profile
            ON runtime_browser_bodies(profile_name, id DESC)
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
                user_id TEXT NOT NULL DEFAULT '',
                workspace_name TEXT NOT NULL DEFAULT '',
                reasoning_content TEXT NOT NULL DEFAULT '',
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
                last_successful_ping_at TEXT NOT NULL DEFAULT '',
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
        # chat_messages table already has all columns from CREATE TABLE above
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
                created_at TEXT NOT NULL,
                enriched INTEGER NOT NULL DEFAULT 0
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
                created_at TEXT NOT NULL,
                enriched INTEGER NOT NULL DEFAULT 0
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
                created_at TEXT NOT NULL,
                enriched INTEGER NOT NULL DEFAULT 0
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
                proposal_target_path TEXT,
                proposal_content TEXT,
                proposal_content_summary TEXT,
                proposal_content_fingerprint TEXT,
                proposal_content_source TEXT,
                proposal_reason TEXT,
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tool_intent_approval_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                approval_id TEXT NOT NULL UNIQUE,
                intent_key TEXT NOT NULL UNIQUE,
                intent_type TEXT NOT NULL,
                intent_target TEXT NOT NULL,
                approval_scope TEXT NOT NULL,
                approval_required INTEGER NOT NULL DEFAULT 1,
                approval_state TEXT NOT NULL,
                approval_source TEXT NOT NULL DEFAULT 'none',
                approval_reason TEXT NOT NULL DEFAULT '',
                requested_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                resolved_at TEXT,
                resolution_reason TEXT NOT NULL DEFAULT '',
                resolution_message TEXT NOT NULL DEFAULT '',
                session_id TEXT NOT NULL DEFAULT '',
                execution_state TEXT NOT NULL DEFAULT 'not-executed'
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tool_intent_approval_requests_state
            ON tool_intent_approval_requests(approval_state, id DESC)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS approval_feedback_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at TEXT NOT NULL,
                intent_key TEXT NOT NULL,
                approval_state TEXT NOT NULL,
                approval_source TEXT NOT NULL,
                tool_name TEXT,
                resolution_reason TEXT,
                resolution_message TEXT,
                session_id TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_approval_feedback_recorded_at
            ON approval_feedback_log(recorded_at DESC)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bounded_action_continuity_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                continuity_id TEXT NOT NULL,
                action_continuity_state TEXT NOT NULL,
                last_action_type TEXT NOT NULL,
                last_action_target TEXT NOT NULL,
                last_action_summary TEXT NOT NULL,
                last_action_outcome TEXT NOT NULL,
                last_action_at TEXT NOT NULL,
                action_mode TEXT NOT NULL,
                read_only INTEGER NOT NULL DEFAULT 1,
                mutation_permitted INTEGER NOT NULL DEFAULT 0,
                followup_state TEXT NOT NULL,
                followup_hint TEXT NOT NULL,
                post_action_understanding TEXT NOT NULL,
                post_action_concern TEXT NOT NULL,
                confidence TEXT NOT NULL,
                source_contributors TEXT NOT NULL DEFAULT '',
                boundary TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        _ensure_private_inner_note_columns(conn)
        _ensure_enriched_columns(conn)
        _ensure_private_retained_memory_record_columns(conn)
        _ensure_capability_invocation_approval_columns(conn)
        _ensure_capability_approval_request_columns(conn)
        _ensure_tool_intent_approval_request_columns(conn)
        _ensure_runtime_user_understanding_signal_table(conn)
        _ensure_runtime_remembered_fact_signal_table(conn)
        _ensure_runtime_memory_md_update_proposal_table(conn)
        _ensure_runtime_selfhood_proposal_table(conn)
        _ensure_runtime_initiatives_table(conn)
        _ensure_autonomy_proposals_table(conn)
        _ensure_scheduled_tasks_table(conn)
        _ensure_tool_router_tables(conn)
        _ensure_decision_trigger_column(conn)
        _ensure_chat_messages_reasoning_column(conn)
        _ensure_counterfactuals_table(conn)
        _ensure_absence_traces_table(conn)
        _ensure_reasoning_conclusions_table(conn)
        _ensure_soft_deleted_at_columns(conn)
        _ensure_dream_bias_active_table(conn)
        _ensure_user_temperature_active_table(conn)
        # Generalized policies schema lives in policy_abstraction.py to keep
        # db.py from growing. Delegate the ensure-call here.
        # Added 2026-05-11 by Jarvis; the init_db call referenced a
        # function name that was never defined in db.py — fixed by
        # delegating to the real _ensure_table.
        from core.services.policy_abstraction import _ensure_table as _ensure_generalized_policies
        _ensure_generalized_policies(conn)
        _ensure_experience_episodes_table(conn)
        _ensure_causal_edges_table(conn)
        from core.runtime.db_claude_dispatch import ensure_claude_dispatch_tables
        ensure_claude_dispatch_tables(conn)
        conn.commit()


# === _now_iso helper (verbatim from db.py L29797-29799) ===
def _now_iso() -> str:
    from datetime import UTC, datetime
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


# === _SIGNAL_TABLES_WITH_STATUS (verbatim from db.py L33554-33590) ===
_SIGNAL_TABLES_WITH_STATUS: list[str] = [
    "runtime_attachment_topology_signals",
    "runtime_autonomy_pressure_signals",
    "runtime_awareness_signals",
    "runtime_chronicle_consolidation_signals",
    "runtime_consolidation_target_signals",
    "runtime_diary_synthesis_signals",
    "runtime_dream_hypothesis_signals",
    "runtime_executive_contradiction_signals",
    "runtime_goal_signals",
    "runtime_inner_visible_support_signals",
    "runtime_internal_opposition_signals",
    "runtime_loyalty_gradient_signals",
    "runtime_meaning_significance_signals",
    "runtime_metabolism_state_signals",
    "runtime_open_loop_signals",
    "runtime_private_initiative_tension_signals",
    "runtime_private_inner_interplay_signals",
    "runtime_private_inner_note_signals",
    "runtime_private_temporal_promotion_signals",
    "runtime_proactive_loop_lifecycle_signals",
    "runtime_reflection_signals",
    "runtime_regulation_homeostasis_signals",
    "runtime_relation_continuity_signals",
    "runtime_relation_state_signals",
    "runtime_release_marker_signals",
    "runtime_remembered_fact_signals",
    "runtime_self_model_signals",
    "runtime_self_narrative_continuity_signals",
    "runtime_self_review_cadence_signals",
    "runtime_self_review_signals",
    "runtime_temperament_tendency_signals",
    "runtime_temporal_recurrence_signals",
    "runtime_user_understanding_signals",
    "runtime_witness_signals",
    "runtime_world_model_signals",
]


# === Ensure-once cache infrastructure (modified from db.py L33998-34070) ===
_ENSURED_TABLES: set[tuple[str, str]] = set()


def _conn_db_id(conn: sqlite3.Connection) -> str:
    """Stable identifier for a sqlite connection's underlying database.

    For file-backed DBs this is the file path — same across all
    connect() calls in production. For :memory: DBs each connection
    has its own private database, so we use id(conn) as the discriminator
    to force per-connection re-ensure (which is what tests need).
    """
    try:
        rows = conn.execute("PRAGMA database_list").fetchall()
        for row in rows:
            # PRAGMA database_list yields (seq, name, file). Look for 'main'.
            name = row[1] if len(row) > 1 else ""
            path = row[2] if len(row) > 2 else ""
            if str(name) == "main":
                if path:
                    return str(path)
                # In-memory: per-connection identity so tests get fresh ensure
                return f"memory:{id(conn)}"
    except Exception:
        pass
    return f"unknown:{id(conn)}"


def _install_ensure_once_cache() -> None:
    """Bagudkompat-shim: wrapper _ensure_*_table funcs på core.runtime.db
    (facaden). Kaldes fra db.py i bunden EFTER alle re-eksporter, så
    også flyttede _ensure_*-funcs fra submoduler dækkes på facade-niveau.

    Implementation delegerer til _install_ensure_once_cache_for("core.runtime.db").
    """
    _install_ensure_once_cache_for("core.runtime.db")


def invalidate_ensure_once_cache(table_name: str | None = None) -> None:
    """Force re-run of `_ensure_*_table` on next call.

    Pass None to clear all (e.g. after switching DB files in tests).
    Pass a specific table name to re-ensure that one table (matches by
    function-name prefix across all DB paths).
    """
    if table_name is None:
        _ENSURED_TABLES.clear()
    else:
        # Remove all cache entries whose function name matches.
        to_remove = {key for key in _ENSURED_TABLES if key[0] == table_name}
        for key in to_remove:
            _ENSURED_TABLES.discard(key)




def _install_ensure_once_cache_for(module_name: str) -> None:
    """Wrap _ensure_*_table funcs i target-modul med once-cache.

    Tidligere version (_install_ensure_once_cache) scannede kun sit eget
    namespace (sys.modules[__name__]). Denne nye signatur tager target-
    modulnavn så hvert domæne-submodul kan kalde det på sig selv efter
    at have defineret sine _ensure_*_table-funktioner.

    Bagudkompat: _install_ensure_once_cache() shimmer dette ved at kalde
    _install_ensure_once_cache_for("core.runtime.db").
    """
    _mod = _sys.modules[module_name]
    _names = [
        _n for _n in vars(_mod).keys()
        if _n.startswith("_ensure_") and _n.endswith("_table") and callable(getattr(_mod, _n, None))
    ]
    for _name in _names:
        _orig = getattr(_mod, _name)
        if getattr(_orig, "_ensure_once_wrapped", False):
            continue

        def _make_wrapped(_fn, _fname):
            def _wrapped(*args, **kwargs):
                conn = args[0] if args else kwargs.get("conn")
                db_id = _conn_db_id(conn) if conn is not None else "no-conn"
                cache_key = (_fname, db_id)
                if cache_key in _ENSURED_TABLES:
                    return None
                _result = _fn(*args, **kwargs)
                _ENSURED_TABLES.add(cache_key)
                return _result
            _wrapped.__name__ = _fn.__name__
            _wrapped.__qualname__ = _fn.__qualname__
            _wrapped.__doc__ = _fn.__doc__
            _wrapped._ensure_once_wrapped = True  # type: ignore[attr-defined]
            _wrapped._ensure_once_orig = _fn  # type: ignore[attr-defined]
            return _wrapped
        setattr(_mod, _name, _make_wrapped(_orig, _name))
