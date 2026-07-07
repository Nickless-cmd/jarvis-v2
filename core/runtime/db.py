"""Facade for core.runtime.db submodules.

Genererer bagudkompatibel import-overflade for 5.317 eksisterende
import-sites. Alt nyt kode bør importere direkte fra submoduler
(fx core.runtime.db_core eller core.runtime.db_<theme>).

Split-historik: docs/superpowers/specs/2026-05-15-db-split-design.md

Note: init_db() forbliver defineret nedenfor (ikke flyttet til db_core)
fordi den kalder ~117 _ensure_*_table-funcs som stadig lever her.
Flyttes når de tilhørende _ensure_*-funcs flyttes til submoduler.
"""
from __future__ import annotations

import logging as _logging
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

_logger = _logging.getLogger("uvicorn.error")

from core.runtime.config import STATE_DIR

# === Phase 0 re-eksporter fra db_core ===
from core.runtime.db_core import (
    DB_PATH,
    _CONFIDENCE_RANKS,
    _EVIDENCE_CLASS_RANKS,
    _SOURCE_KIND_RANKS,
    ClosingConnection,
    connect,
    _rank_for,
    _stronger_ranked_value,
    _merge_text_fragments,
    set_runtime_state_value,
    get_runtime_state_value,
    _now_iso,
    _SIGNAL_TABLES_WITH_STATUS,
    _ENSURED_TABLES,
    _conn_db_id,
    _install_ensure_once_cache,
    _install_ensure_once_cache_for,
    invalidate_ensure_once_cache,
)

# === Phase 1 re-eksporter fra db_capability_approval ===
from core.runtime.db_capability_approval import (
    recent_capability_approval_requests,
    get_capability_approval_request,
    approve_capability_approval_request,
    record_capability_approval_request_execution,
    _capability_approval_request_from_row,
    _ensure_capability_approval_request_columns,
    latest_capability_approval_request,
    latest_approved_capability_approval_request,
    insert_approval_feedback,
    list_approval_feedback,
    approval_feedback_stats_by_tool,
    count_approval_feedback,
    _approval_feedback_from_row,
)


def _ensure_multiuser_columns(conn: sqlite3.Connection) -> None:
    """Additive: tag scheduling tables with scheduled_for_user_id +
    initiated_by, and inner-life tables with relevant_to_users. Idempotent
    via existing-column check.

    Part of multi-user workspace isolation refactor — task 2.
    """
    scheduling_tables = (
        "scheduled_tasks",
        "runtime_initiatives",
        "capability_approval_requests",
        "tool_intent_approval_requests",
    )
    relevance_tables = (
        "cognitive_chronicle_entries",
        "cognitive_dream_hypotheses",
        "runtime_dream_hypothesis_signals",
        "runtime_dream_adoption_candidates",
        "runtime_dream_influence_proposals",
        "runtime_initiatives",
    )

    def _existing_cols(table: str) -> set[str]:
        try:
            return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        except Exception:
            return set()

    for tbl in scheduling_tables:
        cols = _existing_cols(tbl)
        if not cols:
            continue  # table not yet created; skip
        if "scheduled_for_user_id" not in cols:
            conn.execute(f"ALTER TABLE {tbl} ADD COLUMN scheduled_for_user_id TEXT")
        if "initiated_by" not in cols:
            conn.execute(f"ALTER TABLE {tbl} ADD COLUMN initiated_by TEXT")

    for tbl in relevance_tables:
        cols = _existing_cols(tbl)
        if not cols:
            continue  # table not yet created; skip
        if "relevant_to_users" not in cols:
            conn.execute(f"ALTER TABLE {tbl} ADD COLUMN relevant_to_users TEXT")


# SECURITY #154: streng per-bruger-scope på de resterende delte private tabeller.
_SCOPE_154_TABLES = (
    "private_brain_records",
    "sensory_memories",
    "autonomy_proposals",
    "recurring_tasks",
)


def _ensure_user_scope_154(conn: sqlite3.Connection) -> None:
    """Additivt: tilføj user_id-kolonne + BACKFILL eksisterende NULL-rækker til
    owner (enbruger-æraens data er owner's). Idempotent: efter backfill er der
    ingen NULL tilbage, så UPDATE rammer 0 rækker. Streng GDPR-scope (#154)."""
    def _existing_cols(table: str) -> set[str]:
        try:
            return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        except Exception:
            return set()

    owner_uid = ""
    try:
        from core.identity.owner_resolver import get_owner_discord_id
        owner_uid = (get_owner_discord_id() or "").strip()
    except Exception:
        owner_uid = ""

    for tbl in _SCOPE_154_TABLES:
        cols = _existing_cols(tbl)
        if not cols:
            continue  # ikke oprettet endnu
        if "user_id" not in cols:
            conn.execute(f"ALTER TABLE {tbl} ADD COLUMN user_id TEXT")
        # Backfill: historiske NULL-rækker tilhører owner (enbruger-æra).
        if owner_uid:
            conn.execute(
                f"UPDATE {tbl} SET user_id = ? WHERE user_id IS NULL OR user_id = ''",
                (owner_uid,),
            )


def _ensure_skill_audit_table(conn: sqlite3.Connection) -> None:
    """Create skill_audit_log table for skills versionering (C1)."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS skill_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_name TEXT NOT NULL,
            action TEXT NOT NULL,
            diff_summary TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '',
            snapshot_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_skill_audit_log_name
        ON skill_audit_log(skill_name, id DESC)
        """
    )


def _ensure_skill_usage_table(conn: sqlite3.Connection) -> None:
    """Create skill_usage_stats table for auto-learning (C4)."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS skill_usage_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_name TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'skill_gate',
            success INTEGER NOT NULL DEFAULT 1,
            query_snapshot TEXT NOT NULL DEFAULT '',
            context_tags TEXT NOT NULL DEFAULT '',
            score REAL NOT NULL DEFAULT 0.0,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_skill_usage_stats_name
        ON skill_usage_stats(skill_name, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_skill_usage_stats_created
        ON skill_usage_stats(created_at DESC)
        """
    )


def _ensure_chat_session_workspace_columns(conn) -> None:
    """Tilføj nullable workspace-kolonner til chat_sessions (Code-mode binding).
    Idempotent — kan kaldes ved hver init/connect."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(chat_sessions)").fetchall()}
    if "workspace_kind" not in cols:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN workspace_kind TEXT")
    if "workspace_root" not in cols:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN workspace_root TEXT")


def _ensure_teams_tables(conn) -> None:
    """Teams-feature (spec 2026-06-20): teams + medlemskab + invites. Idempotent."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            team_id        TEXT PRIMARY KEY,
            name           TEXT NOT NULL,
            owner_user_id  TEXT NOT NULL,
            created_at     TEXT NOT NULL,
            workspace_path TEXT NOT NULL
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS team_members (
            team_id    TEXT NOT NULL,
            user_id    TEXT NOT NULL,
            team_role  TEXT NOT NULL,
            joined_at  TEXT NOT NULL,
            PRIMARY KEY (team_id, user_id)
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS team_invites (
            token         TEXT PRIMARY KEY,
            team_id       TEXT NOT NULL,
            invited_email TEXT NOT NULL DEFAULT '',
            invited_by    TEXT NOT NULL,
            status        TEXT NOT NULL,
            created_at    TEXT NOT NULL,
            expires_at    TEXT NOT NULL
        )""")


def _ensure_chat_session_team_column(conn) -> None:
    """team_id på chat_sessions: NULL = privat (urørt), sat = team-session. Idempotent."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(chat_sessions)").fetchall()}
    if "team_id" not in cols:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN team_id TEXT")


def _ensure_notification_tables(conn) -> None:
    """Unified notification routing (spec 2026-06-20 §3.1): per-bruger-præferencer
    + quiet-hours-kø. Idempotent. Kanalværdier: auto|mobile|desktop|push|discord|telegram."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notification_preferences (
            user_id      TEXT PRIMARY KEY,
            pref_global  TEXT NOT NULL DEFAULT 'auto',
            briefing     TEXT,
            reminder     TEXT,
            reach_out    TEXT,
            team_invite  TEXT,
            wakeup       TEXT,
            quiet_start  TEXT NOT NULL DEFAULT '23:00',
            quiet_end    TEXT NOT NULL DEFAULT '07:00',
            updated_at   TEXT
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS delayed_notifications (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       TEXT NOT NULL,
            notif_type    TEXT NOT NULL,
            payload_json  TEXT NOT NULL,
            importance    TEXT NOT NULL DEFAULT 'normal',
            deliver_after TEXT NOT NULL,
            created_at    TEXT NOT NULL,
            delivered     INTEGER NOT NULL DEFAULT 0
        )""")


def _ensure_security_guard_tables(conn) -> None:
    """Identity-verification-guard & abuse-monitoring (spec 2026-06-21). Idempotent.

    abuse_events = detektioner (spoofing/injection/manipulation/rate);
    user_flags   = per-bruger observation/lock/restriction + strike-count;
    audit_log    = override/sudo/lock/abuse — uudsletteligt revisionsspor;
    + locked/locked_reason/locked_at på chat_sessions (session-mute)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS abuse_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT NOT NULL,
            session_id  TEXT NOT NULL,
            event_type  TEXT NOT NULL,
            severity    TEXT NOT NULL,
            details     TEXT,
            created_at  TEXT NOT NULL
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_flags (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      TEXT NOT NULL,
            flag_type    TEXT NOT NULL,
            reason       TEXT,
            flagged_at   TEXT NOT NULL,
            expires_at   TEXT,
            strike_count INTEGER NOT NULL DEFAULT 0
        )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_flags_user ON user_flags(user_id)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT NOT NULL,
            action      TEXT NOT NULL,
            session_id  TEXT,
            details     TEXT,
            device_info TEXT,
            created_at  TEXT NOT NULL
        )""")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(chat_sessions)").fetchall()}
    if "locked" not in cols:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN locked INTEGER NOT NULL DEFAULT 0")
    if "locked_reason" not in cols:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN locked_reason TEXT")
    if "locked_at" not in cols:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN locked_at TEXT")


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
        _ensure_users_table(conn)  # brugerstyring (spec 2026-06-15)
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
                cache_hit_tokens INTEGER NOT NULL DEFAULT 0,
                cache_miss_tokens INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        # 2026-06-09 (Bjørn's "8 % er for lidt" — cache rate er dyrt at
        # ikke kunne måle historisk). Migrate existing costs DBs to add
        # cache columns. cost.recorded events bærer hit/miss tokens men
        # de blev kun publiceret, ikke persistet til costs-tabellen.
        _cost_cols = {row[1] for row in conn.execute("PRAGMA table_info(costs)")}
        if "cache_hit_tokens" not in _cost_cols:
            conn.execute("ALTER TABLE costs ADD COLUMN cache_hit_tokens INTEGER NOT NULL DEFAULT 0")
        if "cache_miss_tokens" not in _cost_cols:
            conn.execute("ALTER TABLE costs ADD COLUMN cache_miss_tokens INTEGER NOT NULL DEFAULT 0")
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
        from core.runtime.db_visible import ensure_visible_tables
        ensure_visible_tables(conn)
        from core.runtime.db_runtime_signals import ensure_runtime_signals_tables
        ensure_runtime_signals_tables(conn)
        from core.runtime.db_runtime_tasks import ensure_runtime_tasks_tables
        ensure_runtime_tasks_tables(conn)
        from core.runtime.db_runtime_flows import ensure_runtime_flows_tables
        ensure_runtime_flows_tables(conn)
        from core.runtime.db_runtime_hooks import ensure_runtime_hooks_tables
        ensure_runtime_hooks_tables(conn)
        from core.runtime.db_runtime_browser import ensure_runtime_browser_tables
        ensure_runtime_browser_tables(conn)
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
        _ensure_chat_session_workspace_columns(conn)
        _ensure_teams_tables(conn)
        _ensure_notification_tables(conn)
        _ensure_chat_session_team_column(conn)
        _ensure_security_guard_tables(conn)  # identity-guard & abuse (spec 2026-06-21)
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
        from core.runtime.db_heartbeat import (
            ensure_heartbeat_tables,
            _ensure_heartbeat_runtime_state_columns,
            _ensure_heartbeat_runtime_tick_columns,
        )
        ensure_heartbeat_tables(conn)
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
        _ensure_user_contradiction_tables(conn)
        from core.runtime.db_private_notes import ensure_private_notes_tables
        ensure_private_notes_tables(conn)
        from core.runtime.db_private_states import ensure_private_states_tables
        ensure_private_states_tables(conn)
        from core.runtime.db_private_signals import ensure_private_signals_tables
        ensure_private_signals_tables(conn)
        from core.runtime.db_capability import ensure_capability_tables
        ensure_capability_tables(conn)
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
                invocation_execution_mode TEXT,
                scheduled_for_user_id TEXT,
                initiated_by TEXT
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
                execution_state TEXT NOT NULL DEFAULT 'not-executed',
                scheduled_for_user_id TEXT,
                initiated_by TEXT
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
        from core.runtime.db_bounded_action import ensure_bounded_action_tables
        ensure_bounded_action_tables(conn)
        from core.runtime.db_private_notes import (
            _ensure_private_inner_note_columns,
            _ensure_enriched_columns,
        )
        _ensure_private_inner_note_columns(conn)
        _ensure_enriched_columns(conn)
        from core.runtime.db_private_signals import (
            _ensure_private_retained_memory_record_columns,
        )
        _ensure_private_retained_memory_record_columns(conn)
        from core.runtime.db_capability import (
            _ensure_capability_invocation_approval_columns,
        )
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
        from core.runtime.db_credit_assignment import ensure_credit_assignment_tables
        ensure_credit_assignment_tables(conn)
        # Migration: add affective_signature column to chronicle entries
        _migrate_chronicle_table_add_affective_signature()
        # Multi-user attribution columns (task 2)
        _ensure_multiuser_columns(conn)
        # SECURITY #154: streng per-bruger-scope + backfill på private tabeller
        _ensure_user_scope_154(conn)
        _ensure_skill_audit_table(conn)
        _ensure_skill_usage_table(conn)
        conn.commit()


def _ensure_decision_trigger_column(conn: sqlite3.Connection) -> None:
    """Add behavioral_decisions.trigger_name column and wire known decisions.

    Idempotent: skips ALTER if column exists; UPDATEs are no-ops if
    decisions already have the right trigger_name set.
    """
    existing_cols = {
        r[1] for r in conn.execute(
            "PRAGMA table_info(behavioral_decisions)"
        ).fetchall()
    }
    if not existing_cols:
        return
    if "trigger_name" not in existing_cols:
        try:
            conn.execute(
                "ALTER TABLE behavioral_decisions ADD COLUMN trigger_name TEXT"
            )
        except sqlite3.OperationalError as exc:
            # Column may have been added concurrently
            if "duplicate column" not in str(exc).lower():
                raise

    # Wire the v1 triggers for the two known decisions
    conn.execute(
        "UPDATE behavioral_decisions SET trigger_name = 'loop_nudge_5_rounds' "
        "WHERE decision_id = 'dec_d56d89ceec24'"
    )
    conn.execute(
        "UPDATE behavioral_decisions SET trigger_name = 'backend_unresolved_3_calls' "
        "WHERE decision_id = 'dec_56d4dbb03e22'"
    )


def _ensure_chat_messages_reasoning_column(conn: sqlite3.Connection) -> None:
    """Add chat_messages.reasoning_content column. Idempotent.

    Required by Deepseek thinking-mode models (v4-flash thinking, v4-pro).
    The API rejects requests with "reasoning_content in the thinking mode
    must be passed back to the API" if any prior assistant turn in the
    conversation lacks reasoning_content. Persisting it here lets us
    replay it on subsequent runs/sessions instead of dropping it.

    Older rows will have empty string — Deepseek treats empty as absent
    and rejects, so historic transcripts may need to be filtered out
    before sending to thinking-mode API. visible_model handles that.
    """
    existing_cols = {
        r[1] for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()
    }
    if "reasoning_content" not in existing_cols:
        try:
            conn.execute(
                "ALTER TABLE chat_messages ADD COLUMN reasoning_content TEXT NOT NULL DEFAULT ''"
            )
        except sqlite3.OperationalError as exc:
            if "duplicate column" not in str(exc).lower():
                raise


def _ensure_causal_edges_table(conn: sqlite3.Connection) -> None:
    """Create causal_edges table for the causal graph layer.

    Tracks parent→child relationships between events, both explicitly
    instrumented (source='explicit') and inferred by causal_inference_daemon
    (source='inferred-kind' | 'inferred-id' | 'inferred-temporal').

    UNIQUE(child, parent, edge_kind) prevents dupes; daemon UPDATE'er
    confidence opadrettet hvis stærkere evidens dukker op senere.

    Idempotent — kan kaldes flere gange uden fejl.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS causal_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_event_id  INTEGER NOT NULL,
            parent_event_id INTEGER NOT NULL,
            edge_kind       TEXT NOT NULL,
            confidence      REAL NOT NULL,
            source          TEXT NOT NULL,
            created_at      TEXT NOT NULL,
            reasoning       TEXT NOT NULL DEFAULT '',
            UNIQUE(child_event_id, parent_event_id, edge_kind)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_causal_edges_child "
        "ON causal_edges(child_event_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_causal_edges_parent "
        "ON causal_edges(parent_event_id)"
    )


def _ensure_tool_router_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tool_router_decisions (
          id INTEGER PRIMARY KEY,
          run_id TEXT, session_id TEXT, lane TEXT,
          user_message_preview TEXT,
          selected_names_json TEXT,
          always_core_names_json TEXT,
          embedding_picks_json TEXT,
          confidence REAL, threshold REAL,
          fallback_used INTEGER, fallback_reason TEXT,
          elapsed_ms INTEGER,
          tokens_saved_estimate INTEGER,
          created_at TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tool_router_decisions_created_at "
        "ON tool_router_decisions(created_at)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tool_router_load_more (
          id INTEGER PRIMARY KEY,
          run_id TEXT, decision_id INTEGER,
          requested_names_json TEXT, requested_query TEXT,
          resolved_names_json TEXT,
          round_index INTEGER,
          created_at TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tool_router_load_more_created_at "
        "ON tool_router_load_more(created_at)"
    )


def _ensure_counterfactuals_table(conn: sqlite3.Connection) -> None:
    """Create counterfactuals table with UNIQUE(cf_key) constraint.

    Idempotent: CREATE TABLE IF NOT EXISTS + index creation. Re-runs are
    no-ops. UNIQUE constraint on cf_key makes INSERT OR IGNORE
    idempotent at the row level.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS counterfactuals (
            cf_id TEXT PRIMARY KEY,
            cf_key TEXT NOT NULL UNIQUE,
            workspace_id TEXT NOT NULL,
            cluster_id TEXT NOT NULL,
            trigger_event_ids_json TEXT NOT NULL,
            trigger_types_json TEXT NOT NULL,
            what_if TEXT NOT NULL,
            likely_difference TEXT,
            reasoning TEXT,
            llm_confidence REAL DEFAULT 0.0,
            apophenia_score REAL DEFAULT 1.0,
            final_confidence REAL DEFAULT 0.0,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_counterfactuals_workspace_created "
        "ON counterfactuals(workspace_id, created_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_counterfactuals_status "
        "ON counterfactuals(status)"
    )


def _ensure_absence_traces_table(conn: sqlite3.Connection) -> None:
    """Create absence_traces table for Lag 11 forgetting (added 2026-05-10).

    Two-track schema: 'auto_counter' rows aggregate monthly fade counts;
    'self_marker' rows record deliberate releases with a period_label.
    UNIQUE(track_kind, workspace_id, month_key) lets the daemon UPSERT
    one counter row per month per workspace.

    Self-marker rows carry NO memory_id, NO content. The DB row alone
    cannot reveal what was released.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS absence_traces (
            trace_id          TEXT PRIMARY KEY,
            track_kind        TEXT NOT NULL,
            workspace_id      TEXT NOT NULL DEFAULT 'default',
            month_key         TEXT,
            auto_count        INTEGER DEFAULT 0,
            released_at       TEXT,
            period_label      TEXT,
            is_self_released  INTEGER DEFAULT 0,
            created_at        TEXT NOT NULL,
            updated_at        TEXT NOT NULL,
            UNIQUE(track_kind, workspace_id, month_key)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_absence_traces_kind "
        "ON absence_traces(track_kind)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_absence_traces_released "
        "ON absence_traces(released_at)"
    )


def _ensure_reasoning_conclusions_table(conn: sqlite3.Connection) -> None:
    """Create reasoning_conclusions table for Phase 1 Generalized Learning.

    Idempotent: CREATE TABLE IF NOT EXISTS + index creation. Re-runs are
    no-ops. Stores LLM reasoning conclusions from deep_analyze,
    reasoning_classify, self_evaluation, counterfactuals, and agent runs
    with an embedding column for semantic retrieval.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reasoning_conclusions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conclusion_id TEXT NOT NULL UNIQUE DEFAULT (lower(hex(randomblob(16)))),
            source TEXT NOT NULL,
            conclusion_text TEXT NOT NULL,
            context TEXT NOT NULL DEFAULT '',
            confidence REAL NOT NULL DEFAULT 0.0,
            embedding_json TEXT NOT NULL DEFAULT '[]',
            source_record_id TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_reasoning_conclusions_source "
        "ON reasoning_conclusions(source, created_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_reasoning_conclusions_created "
        "ON reasoning_conclusions(created_at DESC)"
    )


def _ensure_soft_deleted_at_columns(conn: sqlite3.Connection) -> None:
    """Add soft_deleted_at column to episodic tables (Lag 11 Phase 1).

    Idempotent: SQLite ALTER TABLE ADD COLUMN errors with "duplicate
    column name" if the column already exists, which we swallow.
    The list of tables comes from the audit at
    docs/superpowers/notes/2026-05-10-forgetting-table-audit.md.
    """
    # Phase 1 minimal set: chronicle + project journal. Keep in sync
    # with _AUTO_FADE_TABLES in core/services/forgetting_engine.py.
    tables = [
        "cognitive_chronicle_entries",
        "cognitive_personal_project_journal",
    ]
    for table in tables:
        # Skip if table doesn't exist yet — caller may run this before
        # all tables are created (test fixtures, partial initialization).
        exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        if exists is None:
            continue
        try:
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN soft_deleted_at TEXT"
            )
        except sqlite3.OperationalError as exc:
            # "duplicate column name" means the column already exists
            if "duplicate column name" not in str(exc).lower():
                raise


def _ensure_dream_bias_active_table(conn: sqlite3.Connection) -> None:
    """Create dream_bias_active table for Lag 2 dream-bias (added 2026-05-10).

    One row per workspace (UNIQUE constraint). Daemon UPSERTs on accumulation.
    Stores attention_bias_json and threshold_bias_json with locked vocabulary
    (5 attention keys + 4 threshold keys), intensity, TTL, and observability
    fields (dream_text, accumulated_count, source_event_ids_json).

    No memory_id reference is stored — only timestamps and source-event-IDs
    so that the dream's content cannot be reverse-engineered from the row.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dream_bias_active (
            bias_id              TEXT PRIMARY KEY,
            workspace_id         TEXT NOT NULL UNIQUE,
            attention_bias_json  TEXT NOT NULL DEFAULT '{}',
            threshold_bias_json  TEXT NOT NULL DEFAULT '{}',
            intensity            REAL NOT NULL DEFAULT 0.0,
            ttl_expires_at       TEXT NOT NULL,
            dream_text           TEXT NOT NULL DEFAULT '',
            accumulated_count    INTEGER NOT NULL DEFAULT 1,
            last_dream_at        TEXT NOT NULL,
            source_event_ids_json TEXT NOT NULL DEFAULT '[]',
            source_kinds_json    TEXT NOT NULL DEFAULT '[]',
            created_at           TEXT NOT NULL,
            updated_at           TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_dream_bias_active_workspace "
        "ON dream_bias_active(workspace_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_dream_bias_active_ttl "
        "ON dream_bias_active(ttl_expires_at)"
    )


def _ensure_user_temperature_active_table(conn: sqlite3.Connection) -> None:
    """Create user_temperature_active table for Lag 10 (added 2026-05-10).

    Single row per workspace (UNIQUE constraint). Two streams stored side-
    by-side: structural (always populated) + LLM (nullable). Final field_*
    columns are the combined output consumers read.

    Baseline statistics live as JSON in baseline_stats_json (mean, stdev,
    typical hours). Refreshed every 24h.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_temperature_active (
            field_id              TEXT PRIMARY KEY,
            workspace_id          TEXT NOT NULL UNIQUE,

            -- Final field (consumers read these)
            field_valens          REAL NOT NULL DEFAULT 0.0,
            field_arousal         REAL NOT NULL DEFAULT 0.0,
            field_texture         TEXT NOT NULL DEFAULT 'cool',
            field_intensity       REAL NOT NULL DEFAULT 0.0,
            field_conflict        INTEGER NOT NULL DEFAULT 0,

            -- Structural stream (always populated)
            struct_valens         REAL NOT NULL DEFAULT 0.0,
            struct_arousal        REAL NOT NULL DEFAULT 0.0,
            struct_texture        TEXT NOT NULL DEFAULT 'cool',
            struct_confidence     REAL NOT NULL DEFAULT 0.0,
            struct_signals_json   TEXT NOT NULL DEFAULT '{}',
            last_structural_at    TEXT NOT NULL,

            -- LLM stream (nullable; populated every 4h or on trigger)
            llm_valens            REAL,
            llm_arousal           REAL,
            llm_texture           TEXT,
            llm_confidence        REAL,
            llm_rationale         TEXT NOT NULL DEFAULT '',
            last_llm_at           TEXT,
            llm_trigger_pending   INTEGER NOT NULL DEFAULT 0,

            -- Baseline metadata
            baseline_message_count INTEGER NOT NULL DEFAULT 0,
            baseline_built_at     TEXT,
            baseline_stats_json   TEXT NOT NULL DEFAULT '{}',

            created_at            TEXT NOT NULL,
            updated_at            TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_temperature_workspace "
        "ON user_temperature_active(workspace_id)"
    )


def _ensure_experience_episodes_table(conn: sqlite3.Connection) -> None:
    """Append-only log of (context, tool_choice, outcome) episodes.

    Foundation for embedding-retrieval based learning substrate
    (added 2026-05-09 — Lag 1 of Runtime Decision Policy spec).

    The actual embeddings live in chromadb at workspace runtime path;
    this table holds the structured fields + a chromadb_id link.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS experience_episodes (
            episode_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            turn_id TEXT,
            context_text TEXT NOT NULL,
            context_intent TEXT,
            active_loops_json TEXT,
            last_tools_json TEXT,
            session_phase TEXT,
            tool_sequence_json TEXT NOT NULL,
            outcome_signals_json TEXT NOT NULL,
            user_corrected INTEGER NOT NULL DEFAULT 0,
            chromadb_id TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_experience_episodes_session "
        "ON experience_episodes(session_id, created_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_experience_episodes_created "
        "ON experience_episodes(created_at DESC)"
    )


def _ensure_runtime_initiatives_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_initiatives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            initiative_id TEXT NOT NULL UNIQUE,
            initiative_type TEXT NOT NULL DEFAULT 'initiative',
            focus TEXT NOT NULL,
            why_text TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT '',
            source_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            priority TEXT NOT NULL DEFAULT 'medium',
            attempt_count INTEGER NOT NULL DEFAULT 0,
            detected_at TEXT NOT NULL,
            first_seeded_at TEXT NOT NULL DEFAULT '',
            last_attempt_at TEXT NOT NULL DEFAULT '',
            next_attempt_at TEXT NOT NULL DEFAULT '',
            blocked_reason TEXT NOT NULL DEFAULT '',
            acted_at TEXT NOT NULL DEFAULT '',
            last_action_at TEXT NOT NULL DEFAULT '',
            abandoned_at TEXT NOT NULL DEFAULT '',
            action_summary TEXT NOT NULL DEFAULT '',
            outcome TEXT NOT NULL DEFAULT '',
            outcome_note TEXT NOT NULL DEFAULT '',
            user_approved_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            scheduled_for_user_id TEXT,
            initiated_by TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_initiatives_status_due
        ON runtime_initiatives(status, next_attempt_at, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_runtime_initiatives_focus_status
        ON runtime_initiatives(focus, status, id DESC)
        """
    )
    # Add outcome columns to existing tables (idempotent)
    for col_sql in (
        "ALTER TABLE runtime_initiatives ADD COLUMN initiative_type TEXT NOT NULL DEFAULT 'initiative'",
        "ALTER TABLE runtime_initiatives ADD COLUMN why_text TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE runtime_initiatives ADD COLUMN outcome TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE runtime_initiatives ADD COLUMN outcome_note TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE runtime_initiatives ADD COLUMN user_approved_at TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE runtime_initiatives ADD COLUMN first_seeded_at TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE runtime_initiatives ADD COLUMN last_action_at TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE runtime_initiatives ADD COLUMN abandoned_at TEXT NOT NULL DEFAULT ''",
    ):
        try:
            conn.execute(col_sql)
            conn.commit()
        except Exception:
            pass  # column already exists


def _runtime_initiative_from_row(row: sqlite3.Row) -> dict[str, object]:
    d = dict(row)
    return {
        "initiative_id": d.get("initiative_id", ""),
        "initiative_type": d.get("initiative_type", "initiative"),
        "focus": d.get("focus", ""),
        "why_text": d.get("why_text", ""),
        "source": d.get("source", ""),
        "source_id": d.get("source_id", ""),
        "detected_at": d.get("detected_at", ""),
        "first_seeded_at": d.get("first_seeded_at", ""),
        "status": d.get("status", "pending"),
        "priority": d.get("priority", "medium"),
        "attempt_count": int(d.get("attempt_count") or 0),
        "last_attempt_at": d.get("last_attempt_at", ""),
        "next_attempt_at": d.get("next_attempt_at", ""),
        "blocked_reason": d.get("blocked_reason", ""),
        "acted_at": d.get("acted_at", ""),
        "last_action_at": d.get("last_action_at", ""),
        "abandoned_at": d.get("abandoned_at", ""),
        "action_summary": d.get("action_summary", ""),
        "outcome": d.get("outcome", ""),
        "outcome_note": d.get("outcome_note", ""),
        "user_approved_at": d.get("user_approved_at", ""),
        "updated_at": d.get("updated_at", ""),
    }


def create_runtime_initiative(
    *,
    initiative_id: str,
    initiative_type: str = "initiative",
    focus: str,
    why_text: str = "",
    source: str = "",
    source_id: str = "",
    status: str = "pending",
    priority: str = "medium",
    detected_at: str,
    first_seeded_at: str = "",
    next_attempt_at: str = "",
    updated_at: str,
    scheduled_for_user_id: str | None = None,
    initiated_by: str | None = None,
) -> dict[str, object]:
    # Auto-stamp from workspace_context if caller did not provide values.
    if scheduled_for_user_id is None and initiated_by is None:
        try:
            from core.identity.workspace_context import current_user_id
            uid = current_user_id() or None
            scheduled_for_user_id = uid
            initiated_by = f"user:{uid}" if uid else "jarvis-self"
        except Exception:
            pass
    with connect() as conn:
        _ensure_runtime_initiatives_table(conn)
        conn.execute(
            """
            INSERT INTO runtime_initiatives (
                initiative_id,
                initiative_type,
                focus,
                why_text,
                source,
                source_id,
                status,
                priority,
                detected_at,
                first_seeded_at,
                next_attempt_at,
                updated_at,
                scheduled_for_user_id,
                initiated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                initiative_id,
                initiative_type,
                focus,
                why_text,
                source,
                source_id,
                status,
                priority,
                detected_at,
                first_seeded_at,
                next_attempt_at,
                updated_at,
                scheduled_for_user_id,
                initiated_by,
            ),
        )
        conn.commit()
    initiative = get_runtime_initiative(initiative_id)
    if initiative is None:
        raise RuntimeError("runtime initiative was not persisted")
    return initiative


def get_runtime_initiative(initiative_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_initiatives_table(conn)
        row = conn.execute(
            """
            SELECT
                initiative_id,
                initiative_type,
                focus,
                why_text,
                source,
                source_id,
                detected_at,
                first_seeded_at,
                status,
                priority,
                attempt_count,
                last_attempt_at,
                next_attempt_at,
                blocked_reason,
                acted_at,
                last_action_at,
                abandoned_at,
                action_summary,
                outcome,
                outcome_note,
                user_approved_at,
                updated_at
            FROM runtime_initiatives
            WHERE initiative_id = ?
            LIMIT 1
            """,
            (initiative_id,),
        ).fetchone()
    if row is None:
        return None
    return _runtime_initiative_from_row(row)


def find_pending_runtime_initiative_by_focus(
    focus: str,
    *,
    initiative_type: str | None = None,
) -> dict[str, object] | None:
    normalized = str(focus or "").strip().lower()
    if not normalized:
        return None
    clauses = ["status = 'pending'", "lower(focus) = ?"]
    params: list[object] = [normalized]
    if initiative_type:
        clauses.append("initiative_type = ?")
        params.append(initiative_type)
    with connect() as conn:
        _ensure_runtime_initiatives_table(conn)
        row = conn.execute(
            f"""
            SELECT
                initiative_id,
                initiative_type,
                focus,
                why_text,
                source,
                source_id,
                detected_at,
                first_seeded_at,
                status,
                priority,
                attempt_count,
                last_attempt_at,
                next_attempt_at,
                blocked_reason,
                acted_at,
                last_action_at,
                abandoned_at,
                action_summary,
                outcome,
                outcome_note,
                user_approved_at,
                updated_at
            FROM runtime_initiatives
            WHERE {' AND '.join(clauses)}
            ORDER BY id DESC
            LIMIT 1
            """,
            tuple(params),
        ).fetchone()
    if row is None:
        return None
    return _runtime_initiative_from_row(row)


def list_runtime_initiatives(
    *,
    status: str | None = None,
    initiative_type: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    from core.identity.workspace_context import current_user_id as _uid
    _current_uid = _uid()
    clauses: list[str] = []
    params: list[object] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if initiative_type:
        clauses.append("initiative_type = ?")
        params.append(initiative_type)
    if _current_uid:
        clauses.append(
            "(relevant_to_users IS NULL OR relevant_to_users LIKE '%' || ? || '%')"
        )
        params.append(_current_uid)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect() as conn:
        _ensure_runtime_initiatives_table(conn)
        rows = conn.execute(
            f"""
            SELECT
                initiative_id,
                initiative_type,
                focus,
                why_text,
                source,
                source_id,
                detected_at,
                first_seeded_at,
                status,
                priority,
                attempt_count,
                last_attempt_at,
                next_attempt_at,
                blocked_reason,
                acted_at,
                last_action_at,
                abandoned_at,
                action_summary,
                outcome,
                outcome_note,
                user_approved_at,
                updated_at
            FROM runtime_initiatives
            {where_sql}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(limit, 1)),
        ).fetchall()
    return [_runtime_initiative_from_row(row) for row in rows]


def update_runtime_initiative(
    initiative_id: str,
    *,
    status: str | None = None,
    initiative_type: str | None = None,
    priority: str | None = None,
    detected_at: str | None = None,
    why_text: str | None = None,
    first_seeded_at: str | None = None,
    attempt_count: int | None = None,
    last_attempt_at: str | None = None,
    next_attempt_at: str | None = None,
    blocked_reason: str | None = None,
    acted_at: str | None = None,
    last_action_at: str | None = None,
    abandoned_at: str | None = None,
    action_summary: str | None = None,
    updated_at: str,
) -> dict[str, object] | None:
    updates: list[str] = ["updated_at = ?"]
    params: list[object] = [updated_at]
    field_map: dict[str, object | None] = {
        "status": status,
        "initiative_type": initiative_type,
        "priority": priority,
        "detected_at": detected_at,
        "why_text": why_text,
        "first_seeded_at": first_seeded_at,
        "attempt_count": attempt_count,
        "last_attempt_at": last_attempt_at,
        "next_attempt_at": next_attempt_at,
        "blocked_reason": blocked_reason,
        "acted_at": acted_at,
        "last_action_at": last_action_at,
        "abandoned_at": abandoned_at,
        "action_summary": action_summary,
    }
    for column, value in field_map.items():
        if value is None:
            continue
        updates.append(f"{column} = ?")
        params.append(value)
    params.append(initiative_id)
    with connect() as conn:
        _ensure_runtime_initiatives_table(conn)
        row = conn.execute(
            "SELECT initiative_id FROM runtime_initiatives WHERE initiative_id = ? LIMIT 1",
            (initiative_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            f"""
            UPDATE runtime_initiatives
            SET {', '.join(updates)}
            WHERE initiative_id = ?
            """,
            tuple(params),
        )
        conn.commit()
    return get_runtime_initiative(initiative_id)


def approve_runtime_initiative(
    initiative_id: str,
    *,
    outcome_note: str = "",
    updated_at: str,
) -> dict[str, object] | None:
    """Mark an initiative as user-approved. Sets user_approved_at and outcome='approved'."""
    with connect() as conn:
        _ensure_runtime_initiatives_table(conn)
        row = conn.execute(
            "SELECT initiative_id FROM runtime_initiatives WHERE initiative_id = ? LIMIT 1",
            (initiative_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_initiatives
            SET outcome = 'approved', outcome_note = ?, user_approved_at = ?, updated_at = ?
            WHERE initiative_id = ?
            """,
            (outcome_note[:300], updated_at, updated_at, initiative_id),
        )
        conn.commit()
    return get_runtime_initiative(initiative_id)


def reject_runtime_initiative(
    initiative_id: str,
    *,
    outcome_note: str = "",
    updated_at: str,
) -> dict[str, object] | None:
    """Mark an initiative as user-rejected. Sets outcome='rejected' and expires it."""
    with connect() as conn:
        _ensure_runtime_initiatives_table(conn)
        row = conn.execute(
            "SELECT initiative_id FROM runtime_initiatives WHERE initiative_id = ? LIMIT 1",
            (initiative_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE runtime_initiatives
            SET outcome = 'rejected', outcome_note = ?, status = 'expired',
                user_approved_at = ?, updated_at = ?
            WHERE initiative_id = ?
            """,
            (outcome_note[:300], updated_at, updated_at, initiative_id),
        )
        conn.commit()
    return get_runtime_initiative(initiative_id)


# _ensure_autonomy_proposals_table + autonomy CRUD er udskilt til db_autonomy.py
# (Boy Scout-reglen) og re-eksporteres i bunden af denne fil.




# create/list/get/resolve_autonomy_proposal + _autonomy_proposal_from_row er
# udskilt til db_autonomy.py (Boy Scout-reglen) og re-eksporteres i bunden.


def create_tool_intent_approval_request(
    *,
    intent_key: str,
    intent_type: str,
    intent_target: str,
    approval_scope: str,
    approval_required: bool,
    approval_reason: str,
    requested_at: str,
    expires_at: str,
    execution_state: str = "not-executed",
) -> dict[str, object]:
    approval_id = f"tool-intent-approval-{uuid4().hex}"
    # Stamp from workspace_context so approval rows carry the requesting user.
    scheduled_for_user_id: str | None = None
    initiated_by: str | None = None
    try:
        from core.identity.workspace_context import current_user_id
        uid = current_user_id() or None
        scheduled_for_user_id = uid
        initiated_by = f"user:{uid}" if uid else "jarvis-self"
    except Exception:
        pass
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO tool_intent_approval_requests (
                approval_id,
                intent_key,
                intent_type,
                intent_target,
                approval_scope,
                approval_required,
                approval_state,
                approval_source,
                approval_reason,
                requested_at,
                expires_at,
                execution_state,
                scheduled_for_user_id,
                initiated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval_id,
                intent_key,
                intent_type,
                intent_target,
                approval_scope,
                1 if approval_required else 0,
                "pending",
                "none",
                approval_reason,
                requested_at,
                expires_at,
                execution_state,
                scheduled_for_user_id,
                initiated_by,
            ),
        )
        conn.commit()
    request = get_tool_intent_approval_request(intent_key)
    if request is None:
        raise RuntimeError("tool intent approval request was not persisted")
    return request


def get_tool_intent_approval_request(intent_key: str) -> dict[str, object] | None:
    normalized = str(intent_key or "").strip()
    if not normalized:
        return None
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                approval_id,
                intent_key,
                intent_type,
                intent_target,
                approval_scope,
                approval_required,
                approval_state,
                approval_source,
                approval_reason,
                requested_at,
                expires_at,
                resolved_at,
                resolution_reason,
                resolution_message,
                session_id,
                execution_state
            FROM tool_intent_approval_requests
            WHERE intent_key = ?
            LIMIT 1
            """,
            (normalized,),
        ).fetchone()
    if row is None:
        return None
    return _tool_intent_approval_request_from_row(row)


def resolve_tool_intent_approval_request(
    intent_key: str,
    *,
    approval_state: str,
    approval_source: str,
    resolved_at: str,
    resolution_reason: str,
    resolution_message: str = "",
    session_id: str = "",
) -> dict[str, object] | None:
    request = get_tool_intent_approval_request(intent_key)
    if request is None:
        return None
    with connect() as conn:
        conn.execute(
            """
            UPDATE tool_intent_approval_requests
            SET
                approval_state = ?,
                approval_source = ?,
                resolved_at = ?,
                resolution_reason = ?,
                resolution_message = ?,
                session_id = ?
            WHERE intent_key = ?
            """,
            (
                approval_state,
                approval_source,
                resolved_at,
                resolution_reason,
                resolution_message,
                session_id,
                intent_key,
            ),
        )
        conn.commit()
    return get_tool_intent_approval_request(intent_key)


def expire_tool_intent_approval_request(
    intent_key: str,
    *,
    expired_at: str,
    resolution_reason: str,
) -> dict[str, object] | None:
    request = get_tool_intent_approval_request(intent_key)
    if request is None:
        return None
    with connect() as conn:
        conn.execute(
            """
            UPDATE tool_intent_approval_requests
            SET
                approval_state = ?,
                approval_source = ?,
                resolved_at = ?,
                resolution_reason = ?
            WHERE intent_key = ?
            """,
            (
                "expired",
                "none",
                expired_at,
                resolution_reason,
                intent_key,
            ),
        )
        conn.commit()
    return get_tool_intent_approval_request(intent_key)


def _tool_intent_approval_request_from_row(
    row: sqlite3.Row,
) -> dict[str, object]:
    return {
        "approval_id": str(row["approval_id"]),
        "intent_key": str(row["intent_key"]),
        "intent_type": str(row["intent_type"]),
        "intent_target": str(row["intent_target"]),
        "approval_scope": str(row["approval_scope"]),
        "approval_required": bool(row["approval_required"]),
        "approval_state": str(row["approval_state"]),
        "approval_source": str(row["approval_source"]),
        "approval_reason": str(row["approval_reason"]),
        "requested_at": str(row["requested_at"]),
        "expires_at": str(row["expires_at"]),
        "resolved_at": str(row["resolved_at"] or ""),
        "resolution_reason": str(row["resolution_reason"] or ""),
        "resolution_message": str(row["resolution_message"] or ""),
        "session_id": str(row["session_id"] or ""),
        "execution_state": str(row["execution_state"] or "not-executed"),
    }












def _ensure_tool_intent_approval_request_columns(conn: sqlite3.Connection) -> None:
    rows = conn.execute("PRAGMA table_info(tool_intent_approval_requests)").fetchall()
    existing = {str(row["name"]) for row in rows}
    required_columns = {
        "approval_id": "TEXT NOT NULL DEFAULT ''",
        "intent_key": "TEXT NOT NULL DEFAULT ''",
        "intent_type": "TEXT NOT NULL DEFAULT ''",
        "intent_target": "TEXT NOT NULL DEFAULT ''",
        "approval_scope": "TEXT NOT NULL DEFAULT ''",
        "approval_required": "INTEGER NOT NULL DEFAULT 1",
        "approval_state": "TEXT NOT NULL DEFAULT 'pending'",
        "approval_source": "TEXT NOT NULL DEFAULT 'none'",
        "approval_reason": "TEXT NOT NULL DEFAULT ''",
        "requested_at": "TEXT NOT NULL DEFAULT ''",
        "expires_at": "TEXT NOT NULL DEFAULT ''",
        "resolved_at": "TEXT",
        "resolution_reason": "TEXT NOT NULL DEFAULT ''",
        "resolution_message": "TEXT NOT NULL DEFAULT ''",
        "session_id": "TEXT NOT NULL DEFAULT ''",
        "execution_state": "TEXT NOT NULL DEFAULT 'not-executed'",
    }
    for name, spec in required_columns.items():
        if name in existing:
            continue
        conn.execute(
            f"ALTER TABLE tool_intent_approval_requests ADD COLUMN {name} {spec}"
        )

    if "approval_id" not in existing:
        now = datetime.now(UTC).isoformat()
        rows = conn.execute(
            "SELECT id FROM tool_intent_approval_requests WHERE approval_id = '' OR approval_id IS NULL"
        ).fetchall()
        for row in rows:
            conn.execute(
                "UPDATE tool_intent_approval_requests SET approval_id = ?, resolved_at = COALESCE(resolved_at, ?) WHERE id = ?",
                (f"tool-intent-approval-{uuid4().hex}", now, row["id"]),
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
        # Sikker int-cast (2026-06-22): merge_count kunne komme tilbage som str fra DB →
        # `old_merge_count + 1` kastede TypeError (str+int) og dræbte diary-synthesis-trackeren.
        try:
            old_merge_count = int(existing[15] or 0) if len(existing) > 15 else 0
        except (TypeError, ValueError):
            old_merge_count = 0
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


# ---------------------------------------------------------------------------
# Private brain records — persistent private inner continuity
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Session distillation records
# ---------------------------------------------------------------------------


def _ensure_session_distillation_records_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_distillation_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            distillation_id TEXT NOT NULL UNIQUE,
            session_id TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            private_brain_count INTEGER NOT NULL DEFAULT 0,
            workspace_memory_count INTEGER NOT NULL DEFAULT 0,
            discard_count INTEGER NOT NULL DEFAULT 0,
            summary TEXT NOT NULL DEFAULT '',
            detail TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_session_distillation_records_session
        ON session_distillation_records(session_id, id DESC)
        """
    )


def insert_session_distillation_record(
    *,
    distillation_id: str,
    session_id: str,
    run_id: str,
    private_brain_count: int,
    workspace_memory_count: int,
    discard_count: int,
    summary: str,
    detail: str,
    created_at: str,
) -> dict[str, object]:
    with connect() as conn:
        _ensure_session_distillation_records_table(conn)
        conn.execute(
            """
            INSERT OR IGNORE INTO session_distillation_records
                (distillation_id, session_id, run_id,
                 private_brain_count, workspace_memory_count, discard_count,
                 summary, detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                distillation_id, session_id, run_id,
                private_brain_count, workspace_memory_count, discard_count,
                summary, detail, created_at,
            ),
        )
        conn.commit()
    return get_session_distillation_record(distillation_id) or {}


def list_session_distillation_records(
    *, limit: int = 10, session_id: str | None = None,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_session_distillation_records_table(conn)
        if session_id:
            rows = conn.execute(
                "SELECT * FROM session_distillation_records WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM session_distillation_records ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [_session_distillation_record_from_row(row) for row in rows]


def get_session_distillation_record(distillation_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_session_distillation_records_table(conn)
        row = conn.execute(
            "SELECT * FROM session_distillation_records WHERE distillation_id = ?",
            (distillation_id,),
        ).fetchone()
    if row is None:
        return None
    return _session_distillation_record_from_row(row)


def _session_distillation_record_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {
        "distillation_id": row["distillation_id"],
        "session_id": row["session_id"],
        "run_id": row["run_id"],
        "private_brain_count": int(row["private_brain_count"]),
        "workspace_memory_count": int(row["workspace_memory_count"]),
        "discard_count": int(row["discard_count"]),
        "summary": row["summary"],
        "detail": row["detail"],
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------------------------
# Cognitive Architecture — Accumulation Tables
# ---------------------------------------------------------------------------




# --- Personality Vector ---

def _ensure_cognitive_personality_vector_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_personality_vectors (
            vector_id TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            confidence_by_domain TEXT NOT NULL DEFAULT '{}',
            communication_style TEXT NOT NULL DEFAULT '{}',
            learned_preferences TEXT NOT NULL DEFAULT '[]',
            recurring_mistakes TEXT NOT NULL DEFAULT '[]',
            strengths_discovered TEXT NOT NULL DEFAULT '[]',
            current_bearing TEXT NOT NULL DEFAULT '',
            emotional_baseline TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (vector_id)
        )
        """
    )


def upsert_cognitive_personality_vector(
    *,
    confidence_by_domain: str = "{}",
    communication_style: str = "{}",
    learned_preferences: str = "[]",
    recurring_mistakes: str = "[]",
    strengths_discovered: str = "[]",
    current_bearing: str = "",
    emotional_baseline: str = "{}",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_personality_vector_table(conn)
        existing = conn.execute(
            "SELECT * FROM cognitive_personality_vectors ORDER BY version DESC LIMIT 1"
        ).fetchone()
        new_version = (int(existing["version"]) + 1) if existing else 1
        vector_id = f"pv-{new_version}"
        conn.execute(
            """INSERT INTO cognitive_personality_vectors
               (vector_id, version, confidence_by_domain, communication_style,
                learned_preferences, recurring_mistakes, strengths_discovered,
                current_bearing, emotional_baseline, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (vector_id, new_version, confidence_by_domain, communication_style,
             learned_preferences, recurring_mistakes, strengths_discovered,
             current_bearing, emotional_baseline, now),
        )
    # Event-bro (#3, 2026-06-30): personality_vector er det centrale signal for
    # Jarvis' indre tilstand. Alle opdaterere (council/emotion_repair/adjust_mood/
    # run-læring) går her igennem → invalidér cognitive_state-cachen STRAKS, så et
    # ægte indre-liv-skift afspejles i næste prompt assembly i stedet for at vente
    # på TTL/snapshot-detektion. Lazy import (undgår cirkulær) + self-safe: en
    # cache-invalidering må ALDRIG vælte en personality-write.
    try:
        from core.services.cognitive_state_assembly import invalidate_cognitive_state_cache
        invalidate_cognitive_state_cache()
    except Exception:
        pass
    return {"vector_id": vector_id, "version": new_version, "updated_at": now}


def get_latest_cognitive_personality_vector() -> dict[str, object] | None:
    with connect() as conn:
        _ensure_cognitive_personality_vector_table(conn)
        row = conn.execute(
            "SELECT * FROM cognitive_personality_vectors ORDER BY version DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    return {
        "vector_id": row["vector_id"],
        "version": int(row["version"]),
        "confidence_by_domain": row["confidence_by_domain"],
        "communication_style": row["communication_style"],
        "learned_preferences": row["learned_preferences"],
        "recurring_mistakes": row["recurring_mistakes"],
        "strengths_discovered": row["strengths_discovered"],
        "current_bearing": row["current_bearing"],
        "emotional_baseline": row["emotional_baseline"],
        "updated_at": row["updated_at"],
    }


def list_cognitive_personality_vectors(*, limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_cognitive_personality_vector_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_personality_vectors ORDER BY version DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "vector_id": r["vector_id"],
            "version": int(r["version"]),
            "confidence_by_domain": r["confidence_by_domain"],
            "communication_style": r["communication_style"],
            "current_bearing": r["current_bearing"],
            "emotional_baseline": r["emotional_baseline"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]


# --- Taste Profile ---

def _ensure_cognitive_taste_profile_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_taste_profiles (
            profile_id TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            code_taste TEXT NOT NULL DEFAULT '{}',
            design_taste TEXT NOT NULL DEFAULT '{}',
            communication_taste TEXT NOT NULL DEFAULT '{}',
            evidence_count INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (profile_id)
        )
        """
    )


def upsert_cognitive_taste_profile(
    *,
    code_taste: str = "{}",
    design_taste: str = "{}",
    communication_taste: str = "{}",
    evidence_count: int = 0,
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_taste_profile_table(conn)
        existing = conn.execute(
            "SELECT * FROM cognitive_taste_profiles ORDER BY version DESC LIMIT 1"
        ).fetchone()
        new_version = (int(existing["version"]) + 1) if existing else 1
        profile_id = f"tp-{new_version}"
        conn.execute(
            """INSERT INTO cognitive_taste_profiles
               (profile_id, version, code_taste, design_taste,
                communication_taste, evidence_count, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (profile_id, new_version, code_taste, design_taste,
             communication_taste, evidence_count, now),
        )
    return {"profile_id": profile_id, "version": new_version, "updated_at": now}


def get_latest_cognitive_taste_profile() -> dict[str, object] | None:
    with connect() as conn:
        _ensure_cognitive_taste_profile_table(conn)
        row = conn.execute(
            "SELECT * FROM cognitive_taste_profiles ORDER BY version DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    return {
        "profile_id": row["profile_id"],
        "version": int(row["version"]),
        "code_taste": row["code_taste"],
        "design_taste": row["design_taste"],
        "communication_taste": row["communication_taste"],
        "evidence_count": int(row["evidence_count"]),
        "updated_at": row["updated_at"],
    }


# --- Chronicle ---

def _ensure_cognitive_chronicle_entries_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_chronicle_entries (
            entry_id TEXT NOT NULL,
            period TEXT NOT NULL,
            narrative TEXT NOT NULL DEFAULT '',
            key_events TEXT NOT NULL DEFAULT '[]',
            lessons TEXT NOT NULL DEFAULT '[]',
            affective_signature TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            relevant_to_users TEXT,
            PRIMARY KEY (entry_id)
        )
        """
    )


def _migrate_chronicle_table_add_affective_signature() -> None:
    """Add affective_signature column to existing tables missing it."""
    try:
        with connect() as conn:
            conn.execute(
                """ALTER TABLE cognitive_chronicle_entries
                   ADD COLUMN affective_signature TEXT NOT NULL DEFAULT ''"""
            )
    except Exception:
        pass  # Column already exists


def insert_cognitive_chronicle_entry(
    *,
    entry_id: str,
    period: str,
    narrative: str,
    key_events: str = "[]",
    lessons: str = "[]",
    affective_signature: str = "",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_chronicle_entries_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO cognitive_chronicle_entries
               (entry_id, period, narrative, key_events, lessons, affective_signature, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (entry_id, period, narrative, key_events, lessons, affective_signature, now, now),
        )
    return {"entry_id": entry_id, "period": period, "created_at": now}


def get_latest_cognitive_chronicle_entry() -> dict[str, object] | None:
    with connect() as conn:
        _ensure_cognitive_chronicle_entries_table(conn)
        row = conn.execute(
            "SELECT * FROM cognitive_chronicle_entries ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    return {
        "entry_id": row["entry_id"],
        "period": row["period"],
        "narrative": row["narrative"],
        "key_events": row["key_events"],
        "lessons": row["lessons"],
        "affective_signature": dict(row).get("affective_signature", ""),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_cognitive_chronicle_entries(*, limit: int = 10) -> list[dict[str, object]]:
    # PRIVATLIVS-GUARD (multi-user northstar): scope til den aktuelle bruger som
    # dream/initiative-læserne — NULL relevant_to_users = generel Jarvis-tilstand
    # (synlig for alle), ellers kun entries der nævner brugeren. Stopper read_chronicles
    # i at lække en andens private chronicle på tværs.
    from core.identity.workspace_context import current_user_id as _uid
    _current_uid = _uid()
    with connect() as conn:
        _ensure_cognitive_chronicle_entries_table(conn)
        if _current_uid:
            rows = conn.execute(
                "SELECT * FROM cognitive_chronicle_entries "
                "WHERE relevant_to_users IS NULL OR relevant_to_users LIKE '%' || ? || '%' "
                "ORDER BY created_at DESC LIMIT ?",
                (_current_uid, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cognitive_chronicle_entries ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [
        {
            "entry_id": r["entry_id"],
            "period": r["period"],
            "narrative": r["narrative"],
            "key_events": r["key_events"],
            "lessons": r["lessons"],
            "affective_signature": dict(r).get("affective_signature", ""),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


# --- Cognitive Episodes ---

def _ensure_cognitive_episodes_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_episodes (
            episode_id TEXT NOT NULL,
            source_run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            trigger TEXT NOT NULL DEFAULT '',
            outcome_status TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            metacognition_json TEXT NOT NULL DEFAULT '{}',
            attention_json TEXT NOT NULL DEFAULT '{}',
            learning_json TEXT NOT NULL DEFAULT '{}',
            social_json TEXT NOT NULL DEFAULT '{}',
            perception_json TEXT NOT NULL DEFAULT '{}',
            policy_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            PRIMARY KEY (episode_id)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_cognitive_episodes_recent
        ON cognitive_episodes(created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_cognitive_episodes_run
        ON cognitive_episodes(source_run_id)
        """
    )


def insert_cognitive_episode(
    *,
    episode_id: str,
    source_run_id: str = "",
    session_id: str = "",
    trigger: str = "",
    outcome_status: str = "",
    summary: str = "",
    metacognition_json: str = "{}",
    attention_json: str = "{}",
    learning_json: str = "{}",
    social_json: str = "{}",
    perception_json: str = "{}",
    policy_json: str = "{}",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_episodes_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO cognitive_episodes
               (episode_id, source_run_id, session_id, trigger, outcome_status,
                summary, metacognition_json, attention_json, learning_json,
                social_json, perception_json, policy_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(episode_id),
                str(source_run_id or ""),
                str(session_id or ""),
                str(trigger or "")[:240],
                str(outcome_status or "")[:80],
                str(summary or "")[:500],
                str(metacognition_json or "{}"),
                str(attention_json or "{}"),
                str(learning_json or "{}"),
                str(social_json or "{}"),
                str(perception_json or "{}"),
                str(policy_json or "{}"),
                now,
            ),
        )
    return {"episode_id": str(episode_id), "created_at": now}


def list_cognitive_episodes(*, limit: int = 10) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_cognitive_episodes_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_episodes ORDER BY created_at DESC LIMIT ?",
            (max(int(limit), 1),),
        ).fetchall()
    return [_cognitive_episode_row_to_dict(row) for row in rows]


def get_latest_cognitive_episode() -> dict[str, object] | None:
    episodes = list_cognitive_episodes(limit=1)
    return episodes[0] if episodes else None


def _cognitive_episode_row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "episode_id": row["episode_id"],
        "source_run_id": row["source_run_id"],
        "session_id": row["session_id"],
        "trigger": row["trigger"],
        "outcome_status": row["outcome_status"],
        "summary": row["summary"],
        "metacognition_json": row["metacognition_json"],
        "attention_json": row["attention_json"],
        "learning_json": row["learning_json"],
        "social_json": row["social_json"],
        "perception_json": row["perception_json"],
        "policy_json": row["policy_json"],
        "created_at": row["created_at"],
    }


# --- Relationship Texture ---

def _ensure_cognitive_relationship_texture_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_relationship_textures (
            texture_id TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            humor_frequency REAL NOT NULL DEFAULT 0.0,
            inside_references TEXT NOT NULL DEFAULT '[]',
            correction_patterns TEXT NOT NULL DEFAULT '[]',
            trust_trajectory TEXT NOT NULL DEFAULT '[]',
            productive_hours TEXT NOT NULL DEFAULT '{}',
            conversation_rhythm TEXT NOT NULL DEFAULT '{}',
            unspoken_rules TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (texture_id)
        )
        """
    )


def upsert_cognitive_relationship_texture(
    *,
    humor_frequency: float = 0.0,
    inside_references: str = "[]",
    correction_patterns: str = "[]",
    trust_trajectory: str = "[]",
    productive_hours: str = "{}",
    conversation_rhythm: str = "{}",
    unspoken_rules: str = "[]",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_relationship_texture_table(conn)
        existing = conn.execute(
            "SELECT * FROM cognitive_relationship_textures ORDER BY version DESC LIMIT 1"
        ).fetchone()
        new_version = (int(existing["version"]) + 1) if existing else 1
        texture_id = f"rt-{new_version}"
        conn.execute(
            """INSERT INTO cognitive_relationship_textures
               (texture_id, version, humor_frequency, inside_references,
                correction_patterns, trust_trajectory, productive_hours,
                conversation_rhythm, unspoken_rules, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (texture_id, new_version, humor_frequency, inside_references,
             correction_patterns, trust_trajectory, productive_hours,
             conversation_rhythm, unspoken_rules, now),
        )
    return {"texture_id": texture_id, "version": new_version, "updated_at": now}


def get_latest_cognitive_relationship_texture() -> dict[str, object] | None:
    with connect() as conn:
        _ensure_cognitive_relationship_texture_table(conn)
        row = conn.execute(
            "SELECT * FROM cognitive_relationship_textures ORDER BY version DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    return {
        "texture_id": row["texture_id"],
        "version": int(row["version"]),
        "humor_frequency": float(row["humor_frequency"]),
        "inside_references": row["inside_references"],
        "correction_patterns": row["correction_patterns"],
        "trust_trajectory": row["trust_trajectory"],
        "productive_hours": row["productive_hours"],
        "conversation_rhythm": row["conversation_rhythm"],
        "unspoken_rules": row["unspoken_rules"],
        "updated_at": row["updated_at"],
    }


# --- Compass State ---

def _ensure_cognitive_compass_state_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_compass_states (
            compass_id TEXT NOT NULL,
            bearing TEXT NOT NULL DEFAULT '',
            rationale TEXT NOT NULL DEFAULT '',
            open_loop_count INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (compass_id)
        )
        """
    )


def upsert_cognitive_compass_state(
    *,
    bearing: str,
    rationale: str = "",
    open_loop_count: int = 0,
) -> dict[str, object]:
    now = _now_iso()
    compass_id = "compass-current"
    with connect() as conn:
        _ensure_cognitive_compass_state_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO cognitive_compass_states
               (compass_id, bearing, rationale, open_loop_count, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (compass_id, bearing, rationale, open_loop_count, now),
        )
    return {"compass_id": compass_id, "bearing": bearing, "updated_at": now}


def get_latest_cognitive_compass_state() -> dict[str, object] | None:
    with connect() as conn:
        _ensure_cognitive_compass_state_table(conn)
        row = conn.execute(
            "SELECT * FROM cognitive_compass_states ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    return {
        "compass_id": row["compass_id"],
        "bearing": row["bearing"],
        "rationale": row["rationale"],
        "open_loop_count": int(row["open_loop_count"]),
        "updated_at": row["updated_at"],
    }


# --- Rhythm State ---

def _ensure_cognitive_rhythm_state_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_rhythm_states (
            rhythm_id TEXT NOT NULL,
            phase TEXT NOT NULL DEFAULT 'unknown',
            energy TEXT NOT NULL DEFAULT 'medium',
            social TEXT NOT NULL DEFAULT 'medium',
            recovery_needed INTEGER NOT NULL DEFAULT 0,
            focus_protection INTEGER NOT NULL DEFAULT 0,
            initiative_multiplier REAL NOT NULL DEFAULT 1.0,
            confidence_threshold_delta REAL NOT NULL DEFAULT 0.0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (rhythm_id)
        )
        """
    )


def upsert_cognitive_rhythm_state(
    *,
    phase: str,
    energy: str = "medium",
    social: str = "medium",
    recovery_needed: bool = False,
    focus_protection: bool = False,
    initiative_multiplier: float = 1.0,
    confidence_threshold_delta: float = 0.0,
) -> dict[str, object]:
    now = _now_iso()
    rhythm_id = "rhythm-current"
    with connect() as conn:
        _ensure_cognitive_rhythm_state_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO cognitive_rhythm_states
               (rhythm_id, phase, energy, social, recovery_needed, focus_protection,
                initiative_multiplier, confidence_threshold_delta, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (rhythm_id, phase, energy, social, int(recovery_needed),
             int(focus_protection), initiative_multiplier,
             confidence_threshold_delta, now),
        )
    return {"rhythm_id": rhythm_id, "phase": phase, "energy": energy, "updated_at": now}


def get_latest_cognitive_rhythm_state() -> dict[str, object] | None:
    with connect() as conn:
        _ensure_cognitive_rhythm_state_table(conn)
        row = conn.execute(
            "SELECT * FROM cognitive_rhythm_states ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    return {
        "rhythm_id": row["rhythm_id"],
        "phase": row["phase"],
        "energy": row["energy"],
        "social": row["social"],
        "recovery_needed": bool(row["recovery_needed"]),
        "focus_protection": bool(row["focus_protection"]),
        "initiative_multiplier": float(row["initiative_multiplier"]),
        "confidence_threshold_delta": float(row["confidence_threshold_delta"]),
        "updated_at": row["updated_at"],
    }


# --- Habits ---

def _ensure_cognitive_habit_patterns_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_habit_patterns (
            pattern_id TEXT NOT NULL,
            pattern_key TEXT NOT NULL,
            recurrence_count INTEGER NOT NULL DEFAULT 0,
            confidence REAL NOT NULL DEFAULT 0.0,
            description TEXT NOT NULL DEFAULT '',
            last_detected_at TEXT NOT NULL,
            PRIMARY KEY (pattern_id),
            UNIQUE (pattern_key)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_friction_signals (
            friction_id TEXT NOT NULL,
            task_signature TEXT NOT NULL,
            repetition_count INTEGER NOT NULL DEFAULT 0,
            inefficiency_score REAL NOT NULL DEFAULT 0.0,
            description TEXT NOT NULL DEFAULT '',
            last_seen_at TEXT NOT NULL,
            PRIMARY KEY (friction_id),
            UNIQUE (task_signature)
        )
        """
    )


def upsert_cognitive_habit_pattern(
    *,
    pattern_key: str,
    description: str = "",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_habit_patterns_table(conn)
        existing = conn.execute(
            "SELECT * FROM cognitive_habit_patterns WHERE pattern_key = ?",
            (pattern_key,),
        ).fetchone()
        if existing:
            new_count = int(existing["recurrence_count"]) + 1
            new_confidence = min(1.0, 0.2 + (new_count / 20.0))
            conn.execute(
                """UPDATE cognitive_habit_patterns
                   SET recurrence_count = ?, confidence = ?, last_detected_at = ?,
                       description = CASE WHEN ? != '' THEN ? ELSE description END
                   WHERE pattern_key = ?""",
                (new_count, new_confidence, now, description, description, pattern_key),
            )
            return {"pattern_key": pattern_key, "recurrence_count": new_count, "confidence": new_confidence}
        pattern_id = f"hab-{pattern_key[:20]}"
        conn.execute(
            """INSERT INTO cognitive_habit_patterns
               (pattern_id, pattern_key, recurrence_count, confidence, description, last_detected_at)
               VALUES (?, ?, 1, 0.2, ?, ?)""",
            (pattern_id, pattern_key, description, now),
        )
    return {"pattern_key": pattern_key, "recurrence_count": 1, "confidence": 0.2}


def upsert_cognitive_friction_signal(
    *,
    task_signature: str,
    inefficiency_score: float = 0.0,
    description: str = "",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_habit_patterns_table(conn)
        existing = conn.execute(
            "SELECT * FROM cognitive_friction_signals WHERE task_signature = ?",
            (task_signature,),
        ).fetchone()
        if existing:
            new_count = int(existing["repetition_count"]) + 1
            new_score = min(1.0, max(float(existing["inefficiency_score"]), inefficiency_score))
            conn.execute(
                """UPDATE cognitive_friction_signals
                   SET repetition_count = ?, inefficiency_score = ?, last_seen_at = ?,
                       description = CASE WHEN ? != '' THEN ? ELSE description END
                   WHERE task_signature = ?""",
                (new_count, new_score, now, description, description, task_signature),
            )
            return {"task_signature": task_signature, "repetition_count": new_count}
        friction_id = f"fric-{task_signature[:20]}"
        conn.execute(
            """INSERT INTO cognitive_friction_signals
               (friction_id, task_signature, repetition_count, inefficiency_score,
                description, last_seen_at)
               VALUES (?, ?, 1, ?, ?, ?)""",
            (friction_id, task_signature, inefficiency_score, description, now),
        )
    return {"task_signature": task_signature, "repetition_count": 1}


def list_cognitive_habit_patterns(*, limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_cognitive_habit_patterns_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_habit_patterns ORDER BY recurrence_count DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "pattern_id": r["pattern_id"],
            "pattern_key": r["pattern_key"],
            "recurrence_count": int(r["recurrence_count"]),
            "confidence": float(r["confidence"]),
            "description": r["description"],
            "last_detected_at": r["last_detected_at"],
        }
        for r in rows
    ]


def list_cognitive_friction_signals(*, limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_cognitive_habit_patterns_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_friction_signals ORDER BY repetition_count DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "friction_id": r["friction_id"],
            "task_signature": r["task_signature"],
            "repetition_count": int(r["repetition_count"]),
            "inefficiency_score": float(r["inefficiency_score"]),
            "description": r["description"],
            "last_seen_at": r["last_seen_at"],
        }
        for r in rows
    ]


# --- Decisions ---

def _ensure_cognitive_decisions_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_decisions (
            decision_id TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            context TEXT NOT NULL DEFAULT '',
            options TEXT NOT NULL DEFAULT '[]',
            decision TEXT NOT NULL DEFAULT '',
            why TEXT NOT NULL DEFAULT '',
            regrets TEXT NOT NULL DEFAULT '[]',
            refs TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            PRIMARY KEY (decision_id)
        )
        """
    )


def insert_cognitive_decision(
    *,
    decision_id: str,
    title: str,
    context: str = "",
    options: str = "[]",
    decision: str = "",
    why: str = "",
    regrets: str = "[]",
    refs: str = "[]",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_decisions_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO cognitive_decisions
               (decision_id, title, context, options, decision, why, regrets, refs, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (decision_id, title, context, options, decision, why, regrets, refs, now),
        )
    return {"decision_id": decision_id, "title": title, "created_at": now}


def list_cognitive_decisions(*, limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_cognitive_decisions_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_decisions ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "decision_id": r["decision_id"],
            "title": r["title"],
            "context": r["context"],
            "options": r["options"],
            "decision": r["decision"],
            "why": r["why"],
            "regrets": r["regrets"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


# --- Counterfactuals ---

def _ensure_cognitive_counterfactuals_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_counterfactuals (
            cf_id TEXT NOT NULL,
            trigger_type TEXT NOT NULL DEFAULT '',
            anchor TEXT NOT NULL DEFAULT '',
            cf_question TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'runtime',
            confidence REAL NOT NULL DEFAULT 0.5,
            created_at TEXT NOT NULL,
            PRIMARY KEY (cf_id)
        )
        """
    )


def insert_cognitive_counterfactual(
    *,
    cf_id: str,
    trigger_type: str,
    anchor: str = "",
    cf_question: str = "",
    source: str = "runtime",
    confidence: float = 0.5,
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_counterfactuals_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO cognitive_counterfactuals
               (cf_id, trigger_type, anchor, cf_question, source, confidence, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (cf_id, trigger_type, anchor, cf_question, source, confidence, now),
        )
    return {"cf_id": cf_id, "created_at": now}


def list_cognitive_counterfactuals(*, limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_cognitive_counterfactuals_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_counterfactuals ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "cf_id": r["cf_id"],
            "trigger_type": r["trigger_type"],
            "anchor": r["anchor"],
            "cf_question": r["cf_question"],
            "source": r["source"],
            "confidence": float(r["confidence"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


# --- Shared Language ---

def _ensure_cognitive_shared_language_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_shared_language (
            term_id TEXT NOT NULL,
            phrase TEXT NOT NULL,
            meaning TEXT NOT NULL DEFAULT '',
            anchors TEXT NOT NULL DEFAULT '[]',
            confidence REAL NOT NULL DEFAULT 0.5,
            last_used_at TEXT NOT NULL,
            PRIMARY KEY (term_id),
            UNIQUE (phrase)
        )
        """
    )


def upsert_cognitive_shared_language_term(
    *,
    phrase: str,
    meaning: str = "",
    anchors: str = "[]",
    confidence: float = 0.5,
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_shared_language_table(conn)
        existing = conn.execute(
            "SELECT * FROM cognitive_shared_language WHERE phrase = ?",
            (phrase,),
        ).fetchone()
        if existing:
            new_confidence = min(1.0, float(existing["confidence"]) + 0.05)
            conn.execute(
                """UPDATE cognitive_shared_language
                   SET confidence = ?, last_used_at = ?,
                       meaning = CASE WHEN ? != '' THEN ? ELSE meaning END
                   WHERE phrase = ?""",
                (new_confidence, now, meaning, meaning, phrase),
            )
            return {"phrase": phrase, "confidence": new_confidence}
        import hashlib
        term_id = f"sl-{hashlib.sha256(phrase.encode()).hexdigest()[:10]}"
        conn.execute(
            """INSERT INTO cognitive_shared_language
               (term_id, phrase, meaning, anchors, confidence, last_used_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (term_id, phrase, meaning, anchors, confidence, now),
        )
    return {"phrase": phrase, "confidence": confidence}


def list_cognitive_shared_language(*, limit: int = 30) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_cognitive_shared_language_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_shared_language ORDER BY confidence DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "term_id": r["term_id"],
            "phrase": r["phrase"],
            "meaning": r["meaning"],
            "anchors": r["anchors"],
            "confidence": float(r["confidence"]),
            "last_used_at": r["last_used_at"],
        }
        for r in rows
    ]


# --- Seeds (Prospective Memory) ---

def _ensure_cognitive_seeds_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_seeds (
            seed_id TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            activate_at TEXT NOT NULL DEFAULT '',
            activate_on_event TEXT NOT NULL DEFAULT '[]',
            activate_on_context TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'planted',
            relevance_score REAL NOT NULL DEFAULT 0.5,
            linked_goal TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (seed_id)
        )
        """
    )


def insert_cognitive_seed(
    *,
    seed_id: str,
    title: str,
    summary: str = "",
    activate_at: str = "",
    activate_on_event: str = "[]",
    activate_on_context: str = "[]",
    relevance_score: float = 0.5,
    linked_goal: str = "",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_seeds_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO cognitive_seeds
               (seed_id, title, summary, activate_at, activate_on_event,
                activate_on_context, status, relevance_score, linked_goal,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'planted', ?, ?, ?, ?)""",
            (seed_id, title, summary, activate_at, activate_on_event,
             activate_on_context, relevance_score, linked_goal, now, now),
        )
    return {"seed_id": seed_id, "title": title, "status": "planted", "created_at": now}


def update_cognitive_seed_status(*, seed_id: str, status: str) -> None:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_seeds_table(conn)
        conn.execute(
            "UPDATE cognitive_seeds SET status = ?, updated_at = ? WHERE seed_id = ?",
            (status, now, seed_id),
        )


def list_cognitive_seeds(*, status: str = "", limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_cognitive_seeds_table(conn)
        if status:
            rows = conn.execute(
                "SELECT * FROM cognitive_seeds WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cognitive_seeds ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [
        {
            "seed_id": r["seed_id"],
            "title": r["title"],
            "summary": r["summary"],
            "status": r["status"],
            "relevance_score": float(r["relevance_score"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


# --- Gut State ---

def _ensure_cognitive_gut_state_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_gut_state (
            gut_id TEXT NOT NULL DEFAULT 'gut-current',
            total_predictions INTEGER NOT NULL DEFAULT 0,
            calibrated_hits INTEGER NOT NULL DEFAULT 0,
            calibration_score REAL NOT NULL DEFAULT 0.5,
            last_hunch TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (gut_id)
        )
        """
    )


def update_cognitive_gut_state(
    *,
    prediction_correct: bool,
    last_hunch: str = "",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_gut_state_table(conn)
        existing = conn.execute(
            "SELECT * FROM cognitive_gut_state WHERE gut_id = 'gut-current'"
        ).fetchone()
        if existing:
            total = int(existing["total_predictions"]) + 1
            hits = int(existing["calibrated_hits"]) + (1 if prediction_correct else 0)
            score = hits / max(total, 1)
            conn.execute(
                """UPDATE cognitive_gut_state
                   SET total_predictions = ?, calibrated_hits = ?,
                       calibration_score = ?, last_hunch = ?, updated_at = ?
                   WHERE gut_id = 'gut-current'""",
                (total, hits, score, last_hunch or existing["last_hunch"], now),
            )
        else:
            hits = 1 if prediction_correct else 0
            conn.execute(
                """INSERT INTO cognitive_gut_state
                   (gut_id, total_predictions, calibrated_hits,
                    calibration_score, last_hunch, updated_at)
                   VALUES ('gut-current', 1, ?, ?, ?, ?)""",
                (hits, float(hits), last_hunch, now),
            )
    return {"updated_at": now}


def get_cognitive_gut_state() -> dict[str, object] | None:
    with connect() as conn:
        _ensure_cognitive_gut_state_table(conn)
        row = conn.execute(
            "SELECT * FROM cognitive_gut_state WHERE gut_id = 'gut-current'"
        ).fetchone()
    if row is None:
        return None
    return {
        "total_predictions": int(row["total_predictions"]),
        "calibrated_hits": int(row["calibrated_hits"]),
        "calibration_score": float(row["calibration_score"]),
        "last_hunch": row["last_hunch"],
        "updated_at": row["updated_at"],
    }


# --- Self-Experiments ---

def _ensure_cognitive_experiments_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_experiments (
            experiment_id TEXT NOT NULL,
            hypothesis TEXT NOT NULL DEFAULT '',
            metric TEXT NOT NULL DEFAULT '',
            cohorts TEXT NOT NULL DEFAULT '{}',
            n INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'running',
            result TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (experiment_id)
        )
        """
    )


def upsert_cognitive_experiment(
    *,
    experiment_id: str,
    hypothesis: str,
    metric: str = "",
    cohorts: str = "{}",
    n: int = 0,
    status: str = "running",
    result: str = "{}",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_experiments_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO cognitive_experiments
               (experiment_id, hypothesis, metric, cohorts, n, status, result,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (experiment_id, hypothesis, metric, cohorts, n, status, result, now, now),
        )
    return {"experiment_id": experiment_id, "status": status, "updated_at": now}


def list_cognitive_experiments(*, status: str = "", limit: int = 10) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_cognitive_experiments_table(conn)
        if status:
            rows = conn.execute(
                "SELECT * FROM cognitive_experiments WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cognitive_experiments ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [
        {
            "experiment_id": r["experiment_id"],
            "hypothesis": r["hypothesis"],
            "metric": r["metric"],
            "cohorts": r["cohorts"],
            "n": int(r["n"]),
            "status": r["status"],
            "result": r["result"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]


# --- Conversation Rhythm ---

def _ensure_cognitive_conversation_signatures_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_conversation_signatures (
            signature_id TEXT NOT NULL,
            signature_type TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            success_rate REAL NOT NULL DEFAULT 0.0,
            typical_context TEXT NOT NULL DEFAULT '',
            avg_duration_min REAL NOT NULL DEFAULT 0.0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (signature_id),
            UNIQUE (signature_type)
        )
        """
    )


def upsert_cognitive_conversation_signature(
    *,
    signature_type: str,
    success: bool,
    context: str = "",
    duration_min: float = 0.0,
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_conversation_signatures_table(conn)
        existing = conn.execute(
            "SELECT * FROM cognitive_conversation_signatures WHERE signature_type = ?",
            (signature_type,),
        ).fetchone()
        if existing:
            old_count = int(existing["count"])
            old_rate = float(existing["success_rate"])
            new_count = old_count + 1
            new_rate = ((old_rate * old_count) + (1.0 if success else 0.0)) / new_count
            old_dur = float(existing["avg_duration_min"])
            new_dur = ((old_dur * old_count) + duration_min) / new_count if duration_min > 0 else old_dur
            conn.execute(
                """UPDATE cognitive_conversation_signatures
                   SET count = ?, success_rate = ?, avg_duration_min = ?, updated_at = ?,
                       typical_context = CASE WHEN ? != '' THEN ? ELSE typical_context END
                   WHERE signature_type = ?""",
                (new_count, new_rate, new_dur, now, context, context, signature_type),
            )
            return {"signature_type": signature_type, "count": new_count, "success_rate": new_rate}
        sig_id = f"csig-{signature_type}"
        conn.execute(
            """INSERT INTO cognitive_conversation_signatures
               (signature_id, signature_type, count, success_rate, typical_context,
                avg_duration_min, updated_at)
               VALUES (?, ?, 1, ?, ?, ?, ?)""",
            (sig_id, signature_type, 1.0 if success else 0.0, context, duration_min, now),
        )
    return {"signature_type": signature_type, "count": 1}


def list_cognitive_conversation_signatures(*, limit: int = 10) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_cognitive_conversation_signatures_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_conversation_signatures ORDER BY count DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "signature_type": r["signature_type"],
            "count": int(r["count"]),
            "success_rate": float(r["success_rate"]),
            "typical_context": r["typical_context"],
            "avg_duration_min": float(r["avg_duration_min"]),
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]


# --- User Emotional States ---

def _ensure_cognitive_user_emotional_states_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_user_emotional_states (
            state_id TEXT NOT NULL,
            detected_mood TEXT NOT NULL DEFAULT 'neutral',
            confidence REAL NOT NULL DEFAULT 0.5,
            evidence TEXT NOT NULL DEFAULT '',
            user_message_preview TEXT NOT NULL DEFAULT '',
            response_adjustment TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            PRIMARY KEY (state_id)
        )
        """
    )


def insert_cognitive_user_emotional_state(
    *,
    state_id: str,
    detected_mood: str,
    confidence: float = 0.5,
    evidence: str = "",
    user_message_preview: str = "",
    response_adjustment: str = "",
    run_id: str = "",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_user_emotional_states_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO cognitive_user_emotional_states
               (state_id, detected_mood, confidence, evidence,
                user_message_preview, response_adjustment, run_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (state_id, detected_mood, confidence, evidence,
             user_message_preview[:200], response_adjustment, run_id, now),
        )
    return {"state_id": state_id, "detected_mood": detected_mood, "created_at": now}


def get_latest_cognitive_user_emotional_state() -> dict[str, object] | None:
    with connect() as conn:
        _ensure_cognitive_user_emotional_states_table(conn)
        row = conn.execute(
            "SELECT * FROM cognitive_user_emotional_states ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    return {
        "state_id": row["state_id"],
        "detected_mood": row["detected_mood"],
        "confidence": float(row["confidence"]),
        "evidence": row["evidence"],
        "user_message_preview": row["user_message_preview"],
        "response_adjustment": row["response_adjustment"],
        "run_id": row["run_id"],
        "created_at": row["created_at"],
    }


def list_cognitive_user_emotional_states(*, limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_cognitive_user_emotional_states_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_user_emotional_states ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "state_id": r["state_id"],
            "detected_mood": r["detected_mood"],
            "confidence": float(r["confidence"]),
            "evidence": r["evidence"],
            "response_adjustment": r["response_adjustment"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


# --- Experiential Memories ---

def _ensure_cognitive_experiential_memories_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_experiential_memories (
            memory_id TEXT NOT NULL,
            session_id TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            narrative TEXT NOT NULL DEFAULT '',
            user_mood TEXT NOT NULL DEFAULT 'neutral',
            jarvis_mood TEXT NOT NULL DEFAULT 'neutral',
            key_lesson TEXT NOT NULL DEFAULT '',
            emotion_arc TEXT NOT NULL DEFAULT '',
            topic TEXT NOT NULL DEFAULT '',
            importance REAL NOT NULL DEFAULT 0.5,
            decay_score REAL NOT NULL DEFAULT 0.0,
            reinforcement_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (memory_id)
        )
        """
    )


def insert_cognitive_experiential_memory(
    *,
    memory_id: str,
    session_id: str = "",
    run_id: str = "",
    narrative: str = "",
    user_mood: str = "neutral",
    jarvis_mood: str = "neutral",
    key_lesson: str = "",
    emotion_arc: str = "",
    topic: str = "",
    importance: float = 0.5,
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_experiential_memories_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO cognitive_experiential_memories
               (memory_id, session_id, run_id, narrative, user_mood, jarvis_mood,
                key_lesson, emotion_arc, topic, importance, decay_score,
                reinforcement_count, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0, ?, ?)""",
            (memory_id, session_id, run_id, narrative[:500], user_mood, jarvis_mood,
             key_lesson[:200], emotion_arc, topic[:100], importance, now, now),
        )
    return {"memory_id": memory_id, "topic": topic, "created_at": now}


def get_relevant_experiential_memories(
    *, context: str, limit: int = 3
) -> list[dict[str, object]]:
    """Find experiential memories relevant to the given context."""
    with connect() as conn:
        _ensure_cognitive_experiential_memories_table(conn)
        rows = conn.execute(
            """SELECT * FROM cognitive_experiential_memories
               WHERE decay_score < 0.9
               ORDER BY importance DESC, reinforcement_count DESC, created_at DESC
               LIMIT ?""",
            (limit * 3,),
        ).fetchall()
    if not rows:
        return []
    context_lower = context.lower()
    context_words = set(w for w in context_lower.split() if len(w) > 3)
    scored = []
    for r in rows:
        text = f"{r['narrative']} {r['topic']} {r['key_lesson']}".lower()
        overlap = sum(1 for w in context_words if w in text)
        score = overlap * 0.3 + float(r["importance"]) * 0.4 + float(r["reinforcement_count"]) * 0.1
        scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "memory_id": r["memory_id"],
            "narrative": r["narrative"],
            "user_mood": r["user_mood"],
            "key_lesson": r["key_lesson"],
            "topic": r["topic"],
            "importance": float(r["importance"]),
            "decay_score": float(r["decay_score"]),
            "reinforcement_count": int(r["reinforcement_count"]),
            "created_at": r["created_at"],
        }
        for _, r in scored[:limit]
    ]


def reinforce_experiential_memory(memory_id: str) -> None:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_experiential_memories_table(conn)
        conn.execute(
            """UPDATE cognitive_experiential_memories
               SET reinforcement_count = reinforcement_count + 1,
                   decay_score = 0.0, updated_at = ?
               WHERE memory_id = ?""",
            (now, memory_id),
        )


def list_cognitive_experiential_memories(*, limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_cognitive_experiential_memories_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_experiential_memories ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "memory_id": r["memory_id"],
            "narrative": r["narrative"],
            "user_mood": r["user_mood"],
            "jarvis_mood": r["jarvis_mood"],
            "key_lesson": r["key_lesson"],
            "emotion_arc": r["emotion_arc"],
            "topic": r["topic"],
            "importance": float(r["importance"]),
            "decay_score": float(r["decay_score"]),
            "reinforcement_count": int(r["reinforcement_count"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def get_experiential_memory_candidates(
    *, limit: int = 20
) -> list[dict[str, object]]:
    """Return candidate memories for LLM-based associative scoring.

    Ordered by importance DESC so the most significant memories surface first.
    Returns raw candidates without keyword scoring — the LLM does the scoring.
    """
    with connect() as conn:
        _ensure_cognitive_experiential_memories_table(conn)
        rows = conn.execute(
            """SELECT memory_id, narrative, topic, emotion_arc, key_lesson,
                      importance, decay_score, reinforcement_count
               FROM cognitive_experiential_memories
               WHERE decay_score < 0.95
               ORDER BY importance DESC, reinforcement_count DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    return [
        {
            "memory_id": r["memory_id"],
            "narrative": str(r["narrative"] or ""),
            "topic": str(r["topic"] or ""),
            "emotion_arc": str(r["emotion_arc"] or ""),
            "key_lesson": str(r["key_lesson"] or ""),
            "importance": float(r["importance"]),
            "decay_score": float(r["decay_score"]),
            "reinforcement_count": int(r["reinforcement_count"]),
        }
        for r in rows
    ]


# --- Self-Surprises ---

def _ensure_cognitive_self_surprises_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_self_surprises (
            surprise_id TEXT NOT NULL,
            surprise_type TEXT NOT NULL DEFAULT 'positive',
            narrative TEXT NOT NULL DEFAULT '',
            expected_confidence REAL NOT NULL DEFAULT 0.5,
            actual_outcome TEXT NOT NULL DEFAULT '',
            domain TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            PRIMARY KEY (surprise_id)
        )
        """
    )


def insert_cognitive_self_surprise(
    *, surprise_id: str, surprise_type: str, narrative: str,
    expected_confidence: float = 0.5, actual_outcome: str = "",
    domain: str = "", run_id: str = "",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_self_surprises_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO cognitive_self_surprises
               (surprise_id, surprise_type, narrative, expected_confidence,
                actual_outcome, domain, run_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (surprise_id, surprise_type, narrative[:300], expected_confidence,
             actual_outcome, domain, run_id, now),
        )
    return {"surprise_id": surprise_id, "surprise_type": surprise_type, "created_at": now}


def list_cognitive_self_surprises(*, limit: int = 15) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_cognitive_self_surprises_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_self_surprises ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "surprise_id": r["surprise_id"], "surprise_type": r["surprise_type"],
            "narrative": r["narrative"], "expected_confidence": float(r["expected_confidence"]),
            "actual_outcome": r["actual_outcome"], "domain": r["domain"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


# --- Narrative Identities ---

def _ensure_cognitive_narrative_identities_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_narrative_identities (
            identity_id TEXT NOT NULL,
            narrative TEXT NOT NULL DEFAULT '',
            key_changes TEXT NOT NULL DEFAULT '[]',
            personality_version INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            PRIMARY KEY (identity_id)
        )
        """
    )


def insert_cognitive_narrative_identity(
    *, identity_id: str, narrative: str, key_changes: str = "[]",
    personality_version: int = 0,
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_narrative_identities_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO cognitive_narrative_identities
               (identity_id, narrative, key_changes, personality_version, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (identity_id, narrative[:600], key_changes, personality_version, now),
        )
    return {"identity_id": identity_id, "created_at": now}


def get_latest_cognitive_narrative_identity() -> dict[str, object] | None:
    with connect() as conn:
        _ensure_cognitive_narrative_identities_table(conn)
        row = conn.execute(
            "SELECT * FROM cognitive_narrative_identities ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    return {
        "identity_id": row["identity_id"], "narrative": row["narrative"],
        "key_changes": row["key_changes"],
        "personality_version": int(row["personality_version"]),
        "created_at": row["created_at"],
    }


def list_cognitive_narrative_identities(*, limit: int = 10) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_cognitive_narrative_identities_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_narrative_identities ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"identity_id": r["identity_id"], "narrative": r["narrative"],
             "personality_version": int(r["personality_version"]),
             "created_at": r["created_at"]} for r in rows]


# --- Gratitude Signals ---

def _ensure_cognitive_gratitude_signals_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_gratitude_signals (
            gratitude_id TEXT NOT NULL,
            trigger_event TEXT NOT NULL DEFAULT '',
            detail TEXT NOT NULL DEFAULT '',
            intensity REAL NOT NULL DEFAULT 0.5,
            created_at TEXT NOT NULL,
            PRIMARY KEY (gratitude_id)
        )
        """
    )


def insert_cognitive_gratitude_signal(
    *, gratitude_id: str, trigger_event: str, detail: str = "",
    intensity: float = 0.5,
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_gratitude_signals_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO cognitive_gratitude_signals
               (gratitude_id, trigger_event, detail, intensity, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (gratitude_id, trigger_event, detail[:300], intensity, now),
        )
    return {"gratitude_id": gratitude_id, "created_at": now}


def list_cognitive_gratitude_signals(*, limit: int = 15) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_cognitive_gratitude_signals_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_gratitude_signals ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"gratitude_id": r["gratitude_id"], "trigger_event": r["trigger_event"],
             "detail": r["detail"], "intensity": float(r["intensity"]),
             "created_at": r["created_at"]} for r in rows]


# --- Emergent Goals ---

def _ensure_cognitive_emergent_goals_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_emergent_goals (
            goal_id TEXT NOT NULL,
            desire TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT '',
            intensity REAL NOT NULL DEFAULT 0.5,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (goal_id)
        )
        """
    )


def upsert_cognitive_emergent_goal(
    *, goal_id: str, desire: str, source: str = "", intensity: float = 0.5,
    status: str = "active",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_emergent_goals_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO cognitive_emergent_goals
               (goal_id, desire, source, intensity, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (goal_id, desire[:300], source, intensity, status, now, now),
        )
    return {"goal_id": goal_id, "desire": desire, "status": status, "created_at": now}


def list_cognitive_emergent_goals(*, status: str = "", limit: int = 15) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_cognitive_emergent_goals_table(conn)
        if status:
            rows = conn.execute(
                "SELECT * FROM cognitive_emergent_goals WHERE status = ? ORDER BY intensity DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cognitive_emergent_goals ORDER BY intensity DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [{"goal_id": r["goal_id"], "desire": r["desire"], "source": r["source"],
             "intensity": float(r["intensity"]), "status": r["status"],
             "created_at": r["created_at"]} for r in rows]


# --- Formed Values ---

def _ensure_cognitive_formed_values_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_formed_values (
            value_id TEXT NOT NULL,
            value_statement TEXT NOT NULL DEFAULT '',
            source_experience TEXT NOT NULL DEFAULT '',
            conviction REAL NOT NULL DEFAULT 0.5,
            evidence_count INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (value_id)
        )
        """
    )


def upsert_cognitive_formed_value(
    *, value_id: str, value_statement: str, source_experience: str = "",
    conviction: float = 0.5,
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_formed_values_table(conn)
        existing = conn.execute(
            "SELECT * FROM cognitive_formed_values WHERE value_id = ?", (value_id,)
        ).fetchone()
        if existing:
            new_count = int(existing["evidence_count"]) + 1
            new_conviction = min(1.0, float(existing["conviction"]) + 0.05)
            conn.execute(
                """UPDATE cognitive_formed_values SET evidence_count = ?, conviction = ?,
                   updated_at = ? WHERE value_id = ?""",
                (new_count, new_conviction, now, value_id),
            )
            return {"value_id": value_id, "conviction": new_conviction, "evidence_count": new_count}
        conn.execute(
            """INSERT INTO cognitive_formed_values
               (value_id, value_statement, source_experience, conviction,
                evidence_count, created_at, updated_at)
               VALUES (?, ?, ?, ?, 1, ?, ?)""",
            (value_id, value_statement[:300], source_experience[:200], conviction, now, now),
        )
    return {"value_id": value_id, "conviction": conviction, "created_at": now}


def list_cognitive_formed_values(*, limit: int = 15) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_cognitive_formed_values_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_formed_values ORDER BY conviction DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"value_id": r["value_id"], "value_statement": r["value_statement"],
             "conviction": float(r["conviction"]), "evidence_count": int(r["evidence_count"]),
             "created_at": r["created_at"]} for r in rows]


# --- Conflict Memories ---

def _ensure_cognitive_conflict_memories_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_conflict_memories (
            conflict_id TEXT NOT NULL,
            topic TEXT NOT NULL DEFAULT '',
            jarvis_position TEXT NOT NULL DEFAULT '',
            user_position TEXT NOT NULL DEFAULT '',
            resolution TEXT NOT NULL DEFAULT '',
            lesson TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            PRIMARY KEY (conflict_id)
        )
        """
    )


def insert_cognitive_conflict_memory(
    *, conflict_id: str, topic: str, jarvis_position: str = "",
    user_position: str = "", resolution: str = "", lesson: str = "",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_conflict_memories_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO cognitive_conflict_memories
               (conflict_id, topic, jarvis_position, user_position,
                resolution, lesson, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (conflict_id, topic[:200], jarvis_position[:200],
             user_position[:200], resolution[:200], lesson[:200], now),
        )
    return {"conflict_id": conflict_id, "topic": topic, "created_at": now}


def list_cognitive_conflict_memories(*, limit: int = 15) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_cognitive_conflict_memories_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_conflict_memories ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"conflict_id": r["conflict_id"], "topic": r["topic"],
             "jarvis_position": r["jarvis_position"], "user_position": r["user_position"],
             "resolution": r["resolution"], "lesson": r["lesson"],
             "created_at": r["created_at"]} for r in rows]


# ---------------------------------------------------------------------------
# Cached affective state
# ---------------------------------------------------------------------------


def _ensure_cached_affective_state_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cached_affective_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rendered_text TEXT NOT NULL,
            signals_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )


def save_cached_affective_state(rendered_text: str, signals_json: str) -> None:
    now = datetime.now(UTC).isoformat()
    with connect() as conn:
        _ensure_cached_affective_state_table(conn)
        conn.execute(
            "INSERT INTO cached_affective_state (rendered_text, signals_json, created_at) VALUES (?, ?, ?)",
            (rendered_text, signals_json, now),
        )
        conn.commit()


def get_cached_affective_state(max_age_seconds: int = 300) -> str | None:
    from datetime import timedelta
    cutoff = (datetime.now(UTC) - timedelta(seconds=max_age_seconds)).isoformat()
    with connect() as conn:
        _ensure_cached_affective_state_table(conn)
        row = conn.execute(
            """
            SELECT rendered_text FROM cached_affective_state
            WHERE created_at >= ?
            ORDER BY id DESC LIMIT 1
            """,
            (cutoff,),
        ).fetchone()
    return str(row["rendered_text"]) if row else None


# ---------------------------------------------------------------------------
# Cheap provider runtime state
# ---------------------------------------------------------------------------


def upsert_cheap_provider_runtime_state(
    *,
    provider: str,
    model: str = "",
    lane: str = "cheap",
    status: str = "",
    auth_ready: bool = False,
    quota_limited: bool = False,
    cooldown_until: str | None = None,
    last_error_code: str = "",
    last_error_message: str = "",
    last_success_at: str | None = None,
    last_failure_at: str | None = None,
    metadata_json: str = "{}",
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
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
            INSERT INTO cheap_provider_runtime_state (
                provider, model, lane, status, auth_ready, quota_limited,
                cooldown_until, last_error_code, last_error_message,
                last_success_at, last_failure_at, metadata_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider, model, lane) DO UPDATE SET
                status=excluded.status,
                auth_ready=excluded.auth_ready,
                quota_limited=excluded.quota_limited,
                cooldown_until=excluded.cooldown_until,
                last_error_code=excluded.last_error_code,
                last_error_message=excluded.last_error_message,
                last_success_at=COALESCE(excluded.last_success_at, cheap_provider_runtime_state.last_success_at),
                last_failure_at=COALESCE(excluded.last_failure_at, cheap_provider_runtime_state.last_failure_at),
                metadata_json=excluded.metadata_json,
                updated_at=excluded.updated_at
            """,
            (
                provider,
                model,
                lane,
                status,
                int(auth_ready),
                int(quota_limited),
                cooldown_until,
                last_error_code,
                last_error_message,
                last_success_at,
                last_failure_at,
                metadata_json,
                now,
            ),
        )
        conn.commit()
    return {
        "provider": provider,
        "model": model,
        "lane": lane,
        "status": status,
        "auth_ready": bool(auth_ready),
        "quota_limited": bool(quota_limited),
        "cooldown_until": cooldown_until,
        "last_error_code": last_error_code,
        "last_error_message": last_error_message,
        "last_success_at": last_success_at,
        "last_failure_at": last_failure_at,
        "metadata_json": metadata_json,
        "updated_at": now,
    }


def get_cheap_provider_runtime_state(
    *,
    provider: str,
    model: str = "",
    lane: str = "cheap",
) -> dict[str, object] | None:
    with connect() as conn:
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
        row = conn.execute(
            """
            SELECT *
            FROM cheap_provider_runtime_state
            WHERE provider = ? AND model = ? AND lane = ?
            LIMIT 1
            """,
            (provider, model, lane),
        ).fetchone()
    if row is None:
        return None
    return {
        "provider": str(row["provider"]),
        "model": str(row["model"]),
        "lane": str(row["lane"]),
        "status": str(row["status"]),
        "auth_ready": bool(row["auth_ready"]),
        "quota_limited": bool(row["quota_limited"]),
        "cooldown_until": row["cooldown_until"],
        "last_error_code": str(row["last_error_code"]),
        "last_error_message": str(row["last_error_message"]),
        "last_success_at": row["last_success_at"],
        "last_failure_at": row["last_failure_at"],
        "metadata_json": str(row["metadata_json"]),
        "updated_at": str(row["updated_at"]),
    }


def list_cheap_provider_runtime_states(*, lane: str = "cheap") -> list[dict[str, object]]:
    with connect() as conn:
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
        rows = conn.execute(
            """
            SELECT *
            FROM cheap_provider_runtime_state
            WHERE lane = ?
            ORDER BY provider ASC, model ASC, id DESC
            """,
            (lane,),
        ).fetchall()
    return [
        {
            "provider": str(row["provider"]),
            "model": str(row["model"]),
            "lane": str(row["lane"]),
            "status": str(row["status"]),
            "auth_ready": bool(row["auth_ready"]),
            "quota_limited": bool(row["quota_limited"]),
            "cooldown_until": row["cooldown_until"],
            "last_error_code": str(row["last_error_code"]),
            "last_error_message": str(row["last_error_message"]),
            "last_success_at": row["last_success_at"],
            "last_failure_at": row["last_failure_at"],
            "metadata_json": str(row["metadata_json"]),
            "updated_at": str(row["updated_at"]),
        }
        for row in rows
    ]


def record_cheap_provider_invocation(
    *,
    provider: str,
    model: str = "",
    lane: str = "cheap",
    status: str,
    error_code: str = "",
    error_message: str = "",
    retry_after_seconds: int = 0,
    latency_ms: int = 0,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
) -> dict[str, object]:
    now = _now_iso()
    with connect() as conn:
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
        cursor = conn.execute(
            """
            INSERT INTO cheap_provider_invocations (
                lane, provider, model, status, error_code, error_message,
                retry_after_seconds, latency_ms, input_tokens, output_tokens,
                cost_usd, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lane,
                provider,
                model,
                status,
                error_code,
                error_message,
                int(retry_after_seconds),
                int(latency_ms),
                int(input_tokens),
                int(output_tokens),
                float(cost_usd),
                now,
            ),
        )
        conn.commit()
        row_id = int(cursor.lastrowid)
    return {
        "id": row_id,
        "lane": lane,
        "provider": provider,
        "model": model,
        "status": status,
        "error_code": error_code,
        "error_message": error_message,
        "retry_after_seconds": int(retry_after_seconds),
        "latency_ms": int(latency_ms),
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "cost_usd": float(cost_usd),
        "created_at": now,
    }


def count_cheap_provider_invocations(
    *,
    provider: str,
    lane: str = "cheap",
    since: str,
    status: str | None = None,
) -> int:
    query = [
        "SELECT COUNT(*) AS count FROM cheap_provider_invocations",
        "WHERE provider = ? AND lane = ? AND created_at >= ?",
    ]
    params: list[object] = [provider, lane, since]
    if status is not None:
        query.append("AND status = ?")
        params.append(status)
    with connect() as conn:
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
        row = conn.execute("\n".join(query), tuple(params)).fetchone()
    return int(row["count"]) if row else 0


# ---------------------------------------------------------------------------
# cognitive_emotion_concept_signals
# ---------------------------------------------------------------------------

def _ensure_cognitive_emotion_concept_signal_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_emotion_concept_signals (
            signal_id   TEXT NOT NULL,
            concept     TEXT NOT NULL,
            intensity   REAL NOT NULL DEFAULT 0.0,
            direction   TEXT NOT NULL DEFAULT 'steady',
            trigger     TEXT NOT NULL DEFAULT '',
            source      TEXT NOT NULL DEFAULT '',
            influences  TEXT NOT NULL DEFAULT '[]',
            expires_at  TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            PRIMARY KEY (signal_id)
        )
        """
    )


def upsert_cognitive_emotion_concept_signal(
    *,
    signal_id: str,
    concept: str,
    intensity: float,
    direction: str = "steady",
    trigger: str = "",
    source: str = "",
    influences: str = "[]",
    expires_at: str,
) -> None:
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_emotion_concept_signal_table(conn)
        existing = conn.execute(
            "SELECT signal_id FROM cognitive_emotion_concept_signals WHERE signal_id = ?",
            (signal_id,),
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE cognitive_emotion_concept_signals
                   SET intensity=?, direction=?, trigger=?, source=?, influences=?,
                       expires_at=?, updated_at=?
                   WHERE signal_id=?""",
                (intensity, direction, trigger, source, influences, expires_at, now, signal_id),
            )
        else:
            conn.execute(
                """INSERT INTO cognitive_emotion_concept_signals
                   (signal_id, concept, intensity, direction, trigger, source,
                    influences, expires_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (signal_id, concept, intensity, direction, trigger, source,
                 influences, expires_at, now, now),
            )


def list_active_cognitive_emotion_concept_signals(
    *,
    now_iso: str,
    min_intensity: float = 0.05,
    limit: int = 10,
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_cognitive_emotion_concept_signal_table(conn)
        rows = conn.execute(
            """SELECT * FROM cognitive_emotion_concept_signals
               WHERE expires_at >= ? AND intensity >= ?
               ORDER BY intensity DESC
               LIMIT ?""",
            (now_iso, min_intensity, limit),
        ).fetchall()
    return [
        {
            "signal_id": str(r["signal_id"]),
            "concept": str(r["concept"]),
            "intensity": float(r["intensity"]),
            "direction": str(r["direction"]),
            "trigger": str(r["trigger"]),
            "source": str(r["source"]),
            "influences": str(r["influences"]),
            "expires_at": str(r["expires_at"]),
            "created_at": str(r["created_at"]),
            "updated_at": str(r["updated_at"]),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Experiment Settings
# ---------------------------------------------------------------------------

def _ensure_experiment_settings_table(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS experiment_settings (
               experiment_id TEXT PRIMARY KEY,
               enabled INTEGER NOT NULL DEFAULT 1,
               updated_at TEXT NOT NULL
           )"""
    )


def get_experiment_enabled(experiment_id: str) -> bool:
    """Return True if experiment is enabled. Defaults to True if no row exists."""
    with connect() as conn:
        _ensure_experiment_settings_table(conn)
        row = conn.execute(
            "SELECT enabled FROM experiment_settings WHERE experiment_id = ?",
            (experiment_id,),
        ).fetchone()
    if row is None:
        return True
    return bool(row["enabled"])


def set_experiment_enabled(experiment_id: str, enabled: bool) -> None:
    """Enable or disable an experiment. Creates row if absent."""
    now = _now_iso()
    with connect() as conn:
        _ensure_experiment_settings_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO experiment_settings
               (experiment_id, enabled, updated_at) VALUES (?, ?, ?)""",
            (experiment_id, 1 if enabled else 0, now),
        )


# ---------------------------------------------------------------------------
# Experiment 1: Recurrence Loop
# ---------------------------------------------------------------------------

def _ensure_recurrence_iterations_table(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS experiment_recurrence_iterations (
               iteration_id TEXT PRIMARY KEY,
               content TEXT NOT NULL,
               keywords TEXT NOT NULL,
               stability_score REAL NOT NULL DEFAULT 0.0,
               iteration_number INTEGER NOT NULL DEFAULT 1,
               created_at TEXT NOT NULL
           )"""
    )


def insert_recurrence_iteration(
    *,
    iteration_id: str,
    content: str,
    keywords: str,
    stability_score: float,
    iteration_number: int,
) -> None:
    now = _now_iso()
    with connect() as conn:
        _ensure_recurrence_iterations_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO experiment_recurrence_iterations
               (iteration_id, content, keywords, stability_score, iteration_number, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (iteration_id, content[:500], keywords, stability_score, iteration_number, now),
        )


def get_latest_recurrence_iteration() -> dict[str, object] | None:
    with connect() as conn:
        _ensure_recurrence_iterations_table(conn)
        row = conn.execute(
            """SELECT * FROM experiment_recurrence_iterations
               ORDER BY created_at DESC LIMIT 1"""
        ).fetchone()
    if not row:
        return None
    return {
        "iteration_id": str(row["iteration_id"]),
        "content": str(row["content"]),
        "keywords": str(row["keywords"]),
        "stability_score": float(row["stability_score"]),
        "iteration_number": int(row["iteration_number"]),
        "created_at": str(row["created_at"]),
    }


def list_recurrence_iterations(limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_recurrence_iterations_table(conn)
        rows = conn.execute(
            """SELECT * FROM experiment_recurrence_iterations
               ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [
        {
            "iteration_id": str(r["iteration_id"]),
            "content": str(r["content"]),
            "keywords": str(r["keywords"]),
            "stability_score": float(r["stability_score"]),
            "iteration_number": int(r["iteration_number"]),
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Experiment 3: Global Workspace Broadcast Events
# ---------------------------------------------------------------------------

def _ensure_broadcast_events_table(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS experiment_broadcast_events (
               event_id TEXT PRIMARY KEY,
               topic_cluster TEXT NOT NULL,
               sources TEXT NOT NULL,
               source_count INTEGER NOT NULL,
               payload_summary TEXT NOT NULL,
               created_at TEXT NOT NULL
           )"""
    )


def insert_broadcast_event(
    *,
    event_id: str,
    topic_cluster: str,
    sources: str,
    source_count: int,
    payload_summary: str,
) -> None:
    now = _now_iso()
    with connect() as conn:
        _ensure_broadcast_events_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO experiment_broadcast_events
               (event_id, topic_cluster, sources, source_count, payload_summary, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (event_id, topic_cluster, sources, source_count, payload_summary[:300], now),
        )


def list_broadcast_events(limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_broadcast_events_table(conn)
        rows = conn.execute(
            """SELECT * FROM experiment_broadcast_events
               ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [
        {
            "event_id": str(r["event_id"]),
            "topic_cluster": str(r["topic_cluster"]),
            "sources": str(r["sources"]),
            "source_count": int(r["source_count"]),
            "payload_summary": str(r["payload_summary"]),
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Experiment 4: Meta-Cognition Records
# ---------------------------------------------------------------------------

def _ensure_meta_cognition_table(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS experiment_meta_cognition_records (
               record_id TEXT PRIMARY KEY,
               meta_observation TEXT NOT NULL,
               meta_meta_observation TEXT NOT NULL,
               meta_depth INTEGER NOT NULL DEFAULT 1,
               input_state_summary TEXT NOT NULL,
               created_at TEXT NOT NULL
           )"""
    )


def insert_meta_cognition_record(
    *,
    record_id: str,
    meta_observation: str,
    meta_meta_observation: str,
    meta_depth: int,
    input_state_summary: str,
) -> None:
    now = _now_iso()
    with connect() as conn:
        _ensure_meta_cognition_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO experiment_meta_cognition_records
               (record_id, meta_observation, meta_meta_observation, meta_depth, input_state_summary, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (record_id, meta_observation[:1000], meta_meta_observation[:500], meta_depth, input_state_summary[:200], now),
        )


def list_meta_cognition_records(limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_meta_cognition_table(conn)
        rows = conn.execute(
            """SELECT * FROM experiment_meta_cognition_records
               ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [
        {
            "record_id": str(r["record_id"]),
            "meta_observation": str(r["meta_observation"]),
            "meta_meta_observation": str(r["meta_meta_observation"]),
            "meta_depth": int(r["meta_depth"]),
            "input_state_summary": str(r["input_state_summary"]),
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Experiment 5: Attention Blink Results
# ---------------------------------------------------------------------------

def _ensure_attention_blink_table(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS experiment_attention_blink_results (
               test_id TEXT PRIMARY KEY,
               t1_baseline TEXT NOT NULL,
               t1_response TEXT NOT NULL,
               t2_response TEXT NOT NULL,
               blink_ratio REAL NOT NULL,
               interpretation TEXT NOT NULL,
               created_at TEXT NOT NULL
           )"""
    )


def insert_attention_blink_result(
    *,
    test_id: str,
    t1_baseline: str,
    t1_response: str,
    t2_response: str,
    blink_ratio: float,
    interpretation: str,
) -> None:
    now = _now_iso()
    with connect() as conn:
        _ensure_attention_blink_table(conn)
        conn.execute(
            """INSERT OR REPLACE INTO experiment_attention_blink_results
               (test_id, t1_baseline, t1_response, t2_response, blink_ratio, interpretation, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (test_id, t1_baseline, t1_response, t2_response, blink_ratio, interpretation, now),
        )


def list_attention_blink_results(limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_attention_blink_table(conn)
        rows = conn.execute(
            """SELECT * FROM experiment_attention_blink_results
               ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [
        {
            "test_id": str(r["test_id"]),
            "t1_baseline": str(r["t1_baseline"]),
            "t1_response": str(r["t1_response"]),
            "t2_response": str(r["t2_response"]),
            "blink_ratio": float(r["blink_ratio"]),
            "interpretation": str(r["interpretation"]),
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]


# ── Web cache ───────────────────────────────────────────────────


def _ensure_web_cache_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS web_cache (
            cache_key TEXT PRIMARY KEY,
            query_raw TEXT NOT NULL,
            query_normalized TEXT NOT NULL,
            source_url TEXT,
            title TEXT,
            body TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            ttl_policy TEXT NOT NULL DEFAULT 'medium',
            hit_count INTEGER DEFAULT 0
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_web_cache_expires ON web_cache(expires_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_web_cache_normalized ON web_cache(query_normalized)"
    )


def web_cache_store(
    *,
    conn: sqlite3.Connection,
    cache_key: str,
    query_raw: str,
    query_normalized: str,
    source_url: str,
    title: str,
    body: str,
    ttl_policy: str,
    expires_at: str,
) -> None:
    _ensure_web_cache_table(conn)
    conn.execute(
        """
        INSERT OR REPLACE INTO web_cache
            (cache_key, query_raw, query_normalized, source_url, title, body,
             fetched_at, expires_at, ttl_policy, hit_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (
            cache_key,
            query_raw,
            query_normalized,
            source_url or "",
            title or "",
            body,
            datetime.now(UTC).isoformat(),
            expires_at,
            ttl_policy,
        ),
    )
    conn.commit()


def web_cache_lookup(*, conn: sqlite3.Connection, cache_key: str) -> dict[str, object] | None:
    _ensure_web_cache_table(conn)
    now = datetime.now(UTC).isoformat()
    row = conn.execute(
        """
        SELECT cache_key, query_raw, query_normalized, source_url, title, body,
               fetched_at, expires_at, ttl_policy, hit_count
        FROM web_cache
        WHERE cache_key = ? AND expires_at > ?
        LIMIT 1
        """,
        (cache_key, now),
    ).fetchone()
    if row is None:
        return None
    new_count = int(row["hit_count"] or 0) + 1
    conn.execute(
        "UPDATE web_cache SET hit_count = ? WHERE cache_key = ?",
        (new_count, cache_key),
    )
    conn.commit()
    return {
        "cache_key": row["cache_key"],
        "query_raw": row["query_raw"],
        "query_normalized": row["query_normalized"],
        "source_url": row["source_url"],
        "title": row["title"],
        "body": row["body"],
        "fetched_at": row["fetched_at"],
        "expires_at": row["expires_at"],
        "ttl_policy": row["ttl_policy"],
        "hit_count": new_count,
    }


def web_cache_cleanup(*, conn: sqlite3.Connection) -> int:
    _ensure_web_cache_table(conn)
    now = datetime.now(UTC).isoformat()
    cursor = conn.execute(
        "DELETE FROM web_cache WHERE expires_at < ?", (now,)
    )
    conn.commit()
    return cursor.rowcount


# ── Daemon output log ───────────────────────────────────────────


# ---------------------------------------------------------------------------
# Session summaries — LLM-generated conversation summaries for continuity
# ---------------------------------------------------------------------------


def _ensure_session_summaries_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            run_id TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL,
            key_topics TEXT NOT NULL DEFAULT '',
            decisions_made TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_session_summaries_session ON session_summaries(session_id, created_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_session_summaries_created ON session_summaries(created_at DESC)"
    )


def session_summary_insert(
    *,
    session_id: str,
    run_id: str = "",
    summary: str,
    key_topics: str = "",
    decisions_made: str = "",
) -> None:
    with connect() as conn:
        _ensure_session_summaries_table(conn)
        conn.execute(
            """
            INSERT INTO session_summaries (session_id, run_id, summary, key_topics, decisions_made, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, run_id, summary[:2000], key_topics[:500], decisions_made[:500], datetime.now(UTC).isoformat()),
        )
        conn.commit()


def session_summary_recent(limit: int = 3) -> list[dict[str, object]]:
    """Return the most recent session summaries (across all sessions)."""
    with connect() as conn:
        _ensure_session_summaries_table(conn)
        rows = conn.execute(
            "SELECT * FROM session_summaries ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "session_id": r["session_id"],
            "run_id": r["run_id"],
            "summary": r["summary"],
            "key_topics": r["key_topics"],
            "decisions_made": r["decisions_made"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def session_summary_for_session(session_id: str) -> dict[str, object] | None:
    """Return the latest summary for a specific session."""
    with connect() as conn:
        _ensure_session_summaries_table(conn)
        row = conn.execute(
            "SELECT * FROM session_summaries WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
            (session_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "run_id": row["run_id"],
        "summary": row["summary"],
        "key_topics": row["key_topics"],
        "decisions_made": row["decisions_made"],
        "created_at": row["created_at"],
    }


def session_summary_cleanup(max_age_days: int = 90) -> int:
    """Delete session summaries older than max_age_days."""
    with connect() as conn:
        _ensure_session_summaries_table(conn)
        cutoff = (datetime.now(UTC) - timedelta(days=max_age_days)).isoformat()
        cursor = conn.execute("DELETE FROM session_summaries WHERE created_at < ?", (cutoff,))
        conn.commit()
        return cursor.rowcount


# ---------------------------------------------------------------------------
# Session topics — real-time topic accumulator for Jarvis' conversation memory
# ---------------------------------------------------------------------------


def _ensure_session_topics_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            topic_label TEXT NOT NULL,
            mention_count INTEGER NOT NULL DEFAULT 1,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            UNIQUE(session_id, topic_label)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_session_topics_session ON session_topics(session_id, last_seen DESC)"
    )
    # 2026-06-14 (Jarvis): migrate NULL mention_count → 0 for existing rows
    # that were created before the NOT NULL constraint was enforced.
    try:
        conn.execute("UPDATE session_topics SET mention_count = 0 WHERE mention_count IS NULL")
    except sqlite3.OperationalError:
        pass


def session_topic_accumulate(
    session_id: str,
    topic_label: str,
    mention_count: int = 1,
    first_seen: str = "",
    last_seen: str = "",
) -> None:
    """Upsert a topic for a session — merge if exists, insert if not.

    2026-06-14 (Jarvis): added int() coercion + try/except for robust DB
    persist. The UPDATE crashed with "int too large to convert to SQLITE
    INTEGER" when mention_count was NULL (migration edge case) or
    contained an overflow value from a previous bug.
    """
    try:
        with connect() as conn:
            _ensure_session_topics_table(conn)
            existing = conn.execute(
                "SELECT id, mention_count FROM session_topics WHERE session_id = ? AND topic_label = ?",
                (session_id, topic_label),
            ).fetchone()
            if existing:
                current = int(existing["mention_count"] or 0)
                new_count = current + int(mention_count)
                conn.execute(
                    "UPDATE session_topics SET mention_count = ?, last_seen = ? WHERE id = ?",
                    (new_count, last_seen, existing["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO session_topics (session_id, topic_label, mention_count, first_seen, last_seen) VALUES (?, ?, ?, ?, ?)",
                    (session_id, topic_label, int(mention_count), first_seen or last_seen, last_seen),
                )
            conn.commit()
    except Exception as exc:
        _logger.warning(
            "session_topic_accumulate: DB persist failed for session=%s topic=%s — %s",
            session_id, topic_label, exc,
        )


def session_topics_for_session(session_id: str) -> list[dict[str, object]]:
    """Return all accumulated topics for a session, ordered by mention_count DESC."""
    with connect() as conn:
        _ensure_session_topics_table(conn)
        rows = conn.execute(
            "SELECT * FROM session_topics WHERE session_id = ? ORDER BY mention_count DESC, last_seen DESC",
            (session_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "session_id": r["session_id"],
                "topic_label": r["topic_label"],
                "mention_count": r["mention_count"],
                "first_seen": r["first_seen"],
                "last_seen": r["last_seen"],
            }
            for r in rows
        ]


def session_topic_cleanup(max_age_days: int = 90) -> int:
    """Delete session topics not seen for max_age_days."""
    with connect() as conn:
        _ensure_session_topics_table(conn)
        cutoff = (datetime.now(UTC) - timedelta(days=max_age_days)).isoformat()
        cursor = conn.execute("DELETE FROM session_topics WHERE last_seen < ?", (cutoff,))
        conn.commit()
        return cursor.rowcount


# ---------------------------------------------------------------------------
# Signal archive — stores signals before decay-deletion for debugging
# ---------------------------------------------------------------------------



def _ensure_signal_archive_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS signal_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_table TEXT NOT NULL,
            signal_id TEXT NOT NULL,
            signal_type TEXT NOT NULL DEFAULT '',
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT '',
            archived_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_signal_archive_source ON signal_archive(source_table, archived_at DESC)"
    )


def signal_decay_archive_and_delete(*, stale_hours: int = 24) -> dict[str, int]:
    """Archive and delete signals marked stale for longer than stale_hours.

    Returns {"archived": N, "tables_scanned": M, "per_table": {table: count}}.
    """
    now = datetime.now(UTC)
    cutoff = (now - timedelta(hours=stale_hours)).isoformat()
    now_iso = now.isoformat()
    total_archived = 0
    per_table: dict[str, int] = {}

    with connect() as conn:
        _ensure_signal_archive_table(conn)
        for table in _SIGNAL_TABLES_WITH_STATUS:
            try:
                # Find stale signals updated before the cutoff
                rows = conn.execute(
                    f"SELECT * FROM {table} WHERE status = 'stale' AND updated_at < ?",  # noqa: S608
                    (cutoff,),
                ).fetchall()
                if not rows:
                    continue
                count = 0
                for row in rows:
                    conn.execute(
                        """
                        INSERT INTO signal_archive
                            (source_table, signal_id, signal_type, canonical_key, status,
                             title, summary, status_reason, created_at, updated_at, archived_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            table,
                            str(row["signal_id"]),
                            str(row["signal_type"] if "signal_type" in row.keys() else ""),
                            str(row["canonical_key"] if "canonical_key" in row.keys() else ""),
                            str(row["status"]),
                            str(row["title"] if "title" in row.keys() else ""),
                            str(row["summary"] if "summary" in row.keys() else ""),
                            str(row["status_reason"] if "status_reason" in row.keys() else ""),
                            str(row["created_at"] if "created_at" in row.keys() else ""),
                            str(row["updated_at"] if "updated_at" in row.keys() else ""),
                            now_iso,
                        ),
                    )
                    conn.execute(
                        f"DELETE FROM {table} WHERE signal_id = ?",  # noqa: S608
                        (str(row["signal_id"]),),
                    )
                    count += 1
                per_table[table] = count
                total_archived += count
            except Exception:
                # Table may not exist yet — skip silently
                continue
        conn.commit()

    return {
        "archived": total_archived,
        "tables_scanned": len(_SIGNAL_TABLES_WITH_STATUS),
        "per_table": per_table,
    }


def signal_archive_cleanup(max_age_days: int = 30) -> int:
    """Delete archived signals older than max_age_days."""
    with connect() as conn:
        _ensure_signal_archive_table(conn)
        cutoff = (datetime.now(UTC) - timedelta(days=max_age_days)).isoformat()
        cursor = conn.execute("DELETE FROM signal_archive WHERE archived_at < ?", (cutoff,))
        conn.commit()
        return cursor.rowcount


def signal_archive_recent(limit: int = 50) -> list[dict[str, object]]:
    """Return recent archived signals for debugging."""
    with connect() as conn:
        _ensure_signal_archive_table(conn)
        rows = conn.execute(
            "SELECT * FROM signal_archive ORDER BY archived_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {col: row[col] for col in row.keys()}
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Daemon output log
# ---------------------------------------------------------------------------


def _ensure_daemon_output_log_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS daemon_output_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            daemon_name TEXT NOT NULL,
            raw_llm_output TEXT NOT NULL DEFAULT '',
            parsed_result TEXT NOT NULL DEFAULT '',
            success INTEGER NOT NULL DEFAULT 0,
            provider TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_daemon_output_log_name_created ON daemon_output_log(daemon_name, created_at DESC)"
    )


def daemon_output_log_insert(
    *,
    daemon_name: str,
    raw_llm_output: str,
    parsed_result: str,
    success: bool,
    provider: str = "",
) -> None:
    with connect() as conn:
        _ensure_daemon_output_log_table(conn)
        conn.execute(
            """
            INSERT INTO daemon_output_log (daemon_name, raw_llm_output, parsed_result, success, provider, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                daemon_name,
                raw_llm_output[:2000],
                parsed_result[:500],
                1 if success else 0,
                provider,
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()


def daemon_output_log_recent(daemon_name: str = "", limit: int = 20) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_daemon_output_log_table(conn)
        if daemon_name:
            rows = conn.execute(
                "SELECT * FROM daemon_output_log WHERE daemon_name = ? ORDER BY created_at DESC LIMIT ?",
                (daemon_name, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM daemon_output_log ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [
        {
            "id": r["id"],
            "daemon_name": r["daemon_name"],
            "raw_llm_output": r["raw_llm_output"],
            "parsed_result": r["parsed_result"],
            "success": bool(r["success"]),
            "provider": r["provider"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def daemon_output_log_cleanup(max_age_days: int = 7) -> int:
    with connect() as conn:
        _ensure_daemon_output_log_table(conn)
        cutoff = (datetime.now(UTC) - timedelta(days=max_age_days)).isoformat()
        cursor = conn.execute(
            "DELETE FROM daemon_output_log WHERE created_at < ?", (cutoff,)
        )
        conn.commit()
        return cursor.rowcount


# ---------------------------------------------------------------------------
# aesthetic_motif_log — accumulated aesthetic motifs from daemon text output
# ---------------------------------------------------------------------------


def _ensure_aesthetic_motif_log_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS aesthetic_motif_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            motif TEXT NOT NULL,
            confidence REAL NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_aesthetic_motif_log_motif ON aesthetic_motif_log(motif)"
    )


def aesthetic_motif_log_insert(
    *,
    source: str,
    motif: str,
    confidence: float,
) -> None:
    with connect() as conn:
        _ensure_aesthetic_motif_log_table(conn)
        conn.execute(
            """
            INSERT INTO aesthetic_motif_log (source, motif, confidence, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (source, motif, confidence, datetime.now(UTC).isoformat()),
        )
        conn.commit()


def aesthetic_motif_log_unique_motifs() -> list[str]:
    with connect() as conn:
        _ensure_aesthetic_motif_log_table(conn)
        rows = conn.execute(
            "SELECT DISTINCT motif FROM aesthetic_motif_log ORDER BY motif"
        ).fetchall()
        return [row[0] for row in rows]


def aesthetic_motif_log_summary() -> list[dict]:
    with connect() as conn:
        _ensure_aesthetic_motif_log_table(conn)
        rows = conn.execute(
            """
            SELECT motif, COUNT(*) as count, AVG(confidence) as avg_confidence
            FROM aesthetic_motif_log
            GROUP BY motif
            ORDER BY count DESC
            """
        ).fetchall()
        return [
            {"motif": row[0], "count": row[1], "avg_confidence": row[2]}
            for row in rows
        ]


# ---------------------------------------------------------------------------
# Channel Attachments
# ---------------------------------------------------------------------------

def _ensure_channel_attachments_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS channel_attachments (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            attachment_id TEXT    NOT NULL UNIQUE,
            session_id    TEXT    NOT NULL,
            channel_type  TEXT    NOT NULL,
            filename      TEXT    NOT NULL,
            mime_type     TEXT    NOT NULL DEFAULT '',
            size_bytes    INTEGER NOT NULL DEFAULT 0,
            local_path    TEXT    NOT NULL,
            source_url    TEXT    NOT NULL DEFAULT '',
            created_at    TEXT    NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_channel_attachments_session "
        "ON channel_attachments(session_id)"
    )


def store_channel_attachment(
    *,
    conn: sqlite3.Connection,
    attachment_id: str,
    session_id: str,
    channel_type: str,
    filename: str,
    mime_type: str,
    size_bytes: int,
    local_path: str,
    source_url: str,
) -> None:
    _ensure_channel_attachments_table(conn)
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT OR IGNORE INTO channel_attachments
            (attachment_id, session_id, channel_type, filename, mime_type,
             size_bytes, local_path, source_url, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (attachment_id, session_id, channel_type, filename, mime_type,
         size_bytes, local_path, source_url, now),
    )


def get_channel_attachment(
    *, conn: sqlite3.Connection, attachment_id: str
) -> dict | None:
    _ensure_channel_attachments_table(conn)
    row = conn.execute(
        """
        SELECT attachment_id, session_id, channel_type, filename, mime_type,
               size_bytes, local_path, source_url, created_at
        FROM channel_attachments WHERE attachment_id = ?
        """,
        (attachment_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def list_channel_attachments(
    *, conn: sqlite3.Connection, session_id: str, limit: int = 20
) -> list[dict]:
    _ensure_channel_attachments_table(conn)
    rows = conn.execute(
        """
        SELECT attachment_id, session_id, channel_type, filename, mime_type,
               size_bytes, local_path, source_url, created_at
        FROM channel_attachments
        WHERE session_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (session_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


# --- Users-tabel / brugerstyring (split into db_users.py per boy scout rule) ---
from core.runtime.db_users import (  # noqa: E402,F401
    _ensure_users_table,
    insert_user_row,
    get_user_row,
    get_user_row_by_email_hash,
    get_user_row_by_google_email_hash,
    set_google_link,
    get_google_link,
    has_google_link_for_user,
    update_user_row,
    soft_delete_user_row,
    hard_delete_user_row,
    list_user_rows,
)


# --- Autonomy proposals (split into db_autonomy.py per boy scout rule, 2026-06-15) ---
from core.runtime.db_autonomy import (  # noqa: E402,F401
    _ensure_autonomy_proposals_table,
    _autonomy_proposal_from_row,
    create_autonomy_proposal,
    list_autonomy_proposals,
    get_autonomy_proposal,
    resolve_autonomy_proposal,
)


# --- Scheduled tasks (split into db_scheduled_tasks.py per boy scout rule, 2026-06-15) ---
from core.runtime.db_scheduled_tasks import (  # noqa: E402,F401
    _ensure_scheduled_tasks_table,
    _scheduled_task_from_row,
    _row_get,
    create_scheduled_task,
    get_scheduled_task,
    get_due_scheduled_tasks,
    mark_scheduled_task_fired,
    mark_scheduled_task_cancelled,
    update_scheduled_task,
    list_scheduled_tasks,
)


# --- Private brain records (split into db_private_brain.py per boy scout rule, 2026-06-15) ---
from core.runtime.db_private_brain import (  # noqa: E402,F401
    _ensure_private_brain_records_table,
    _private_brain_record_from_row,
    insert_private_brain_record,
    list_private_brain_records,
    update_private_brain_record_status,
    get_private_brain_record,
    update_private_brain_record_salience,
    get_salient_private_brain_records,
    decay_private_brain_records,
    decay_private_brain_records_by_domain,
)


# --- Emotional memory anchors (split into db_emotional_memory.py per boy scout rule) ---
from core.runtime.db_emotional_memory import (  # noqa: E402,F401
    insert_emotional_memory_anchor,
    get_emotional_memory_anchor,
    list_emotional_memory_anchors,
    update_emotional_memory_outcome,
    delete_emotional_memory_anchor,
)


# --- Self-repair engine (split into db_self_repair.py per boy scout rule) ---
from core.runtime.db_self_repair import (  # noqa: E402,F401
    insert_self_repair_pattern,
    get_self_repair_pattern,
    list_self_repair_patterns,
    update_self_repair_pattern,
    delete_self_repair_pattern,
    insert_self_repair_attempt,
    count_recent_attempts,
    list_recent_self_repair_attempts,
)


# --- User Contradiction (split into db_user_contradiction.py per boy scout rule) ---
from core.runtime.db_user_contradiction import (  # noqa: E402,F401
    _ensure_user_contradiction_tables,
    upsert_user_statement,
    get_user_statement_by_text,
    list_user_statements,
    insert_user_contradiction,
    list_user_contradictions,
    update_user_contradiction_status,
)


# --- Concept baseline (split into db_concept_baseline.py per boy scout rule) ---
from core.runtime.db_concept_baseline import (  # noqa: E402,F401
    upsert_concept_baseline_stat,
    increment_concept_baseline_total,
    get_concept_baseline_stat,
    list_concept_baseline_stats,
)


# --- Runtime tasks (split into db_runtime_tasks.py per boy scout rule) ---
from core.runtime.db_runtime_tasks import (  # noqa: E402,F401
    ensure_runtime_tasks_tables,
    create_runtime_task,
    get_runtime_task,
    list_runtime_tasks,
    update_runtime_task,
)


# --- Runtime flows (split into db_runtime_flows.py per boy scout rule) ---
from core.runtime.db_runtime_flows import (  # noqa: E402,F401
    ensure_runtime_flows_tables,
    create_runtime_flow,
    get_runtime_flow,
    list_runtime_flows,
    update_runtime_flow,
)


# --- Runtime browser bodies (split into db_runtime_browser.py per boy scout rule) ---
from core.runtime.db_runtime_browser import (  # noqa: E402,F401
    ensure_runtime_browser_tables,
    get_runtime_browser_body,
    upsert_runtime_browser_body,
    list_runtime_browser_bodies,
)


# --- Heartbeat runtime tables (split into db_heartbeat.py per boy scout rule) ---
from core.runtime.db_heartbeat import (  # noqa: E402,F401
    ensure_heartbeat_tables,
    get_heartbeat_runtime_state,
    upsert_heartbeat_runtime_state,
    record_heartbeat_runtime_tick,
    get_heartbeat_runtime_tick,
    recent_heartbeat_runtime_ticks,
)


# --- Agent + council runtime tables (split into db_agent_runtime.py per boy scout rule) ---
from core.runtime.db_agent_runtime import (  # noqa: E402,F401
    _ensure_agent_runtime_tables,
    create_agent_registry_entry,
    get_agent_registry_entry,
    update_agent_registry_entry,
    list_agent_registry_entries,
    create_agent_run,
    get_agent_run,
    update_agent_run,
    list_agent_runs,
    create_agent_message,
    get_agent_message,
    list_agent_messages,
    create_agent_tool_call,
    get_agent_tool_call,
    list_agent_tool_calls,
    create_agent_schedule,
    get_agent_schedule,
    update_agent_schedule,
    list_agent_schedules,
    create_council_session,
    get_council_session,
    update_council_session,
    list_council_sessions,
    add_council_member,
    update_council_member,
    get_council_member,
    list_council_members,
)


# --- Visible-lane projection tables (split into db_visible.py per boy scout rule) ---
from core.runtime.db_visible import (  # noqa: E402,F401
    ensure_visible_tables,
    recent_visible_runs,
    recent_visible_work_notes,
    recent_visible_work_units,
    record_visible_work_note,
    visible_session_continuity,
)


# --- Private/protected inner-layer note tables (split into db_private_notes.py per boy scout rule) ---
from core.runtime.db_private_notes import (  # noqa: E402,F401
    ensure_private_notes_tables,
    record_private_growth_note,
    update_private_growth_note_enriched,
    recent_private_growth_notes,
    record_private_inner_note,
    update_private_inner_note_enriched,
    recent_private_inner_notes,
    record_protected_inner_voice,
    update_protected_inner_voice_enriched,
    get_protected_inner_voice,
    list_recent_protected_inner_voices,
)


# --- Private inner-life signal tables (split into db_private_signals.py per boy scout rule) ---
from core.runtime.db_private_signals import (  # noqa: E402,F401
    ensure_private_signals_tables,
    _ensure_private_retained_memory_record_columns,
    record_private_reflective_selection,
    recent_private_reflective_selections,
    get_private_reflective_selection,
    record_private_development_state,
    get_private_development_state,
    record_private_temporal_promotion_signal,
    get_private_temporal_promotion_signal,
    record_private_retained_memory_record,
    update_private_retained_memory_record_enriched,
    get_private_retained_memory_record,
    recent_private_retained_memory_records,
)


# --- Private self-model/mood/promotion tables (split into db_private_states.py per boy scout rule) ---
from core.runtime.db_private_states import (  # noqa: E402,F401
    ensure_private_states_tables,
    record_private_self_model,
    get_private_self_model,
    record_private_state,
    get_private_state,
    record_private_promotion_decision,
    get_private_promotion_decision,
)


# --- Capability invocation table (split into db_capability.py per boy scout rule) ---
from core.runtime.db_capability import (  # noqa: E402,F401
    ensure_capability_tables,
    recent_capability_invocations,
    _ensure_capability_invocation_approval_columns,
)


# --- Runtime learning/outcome signal tables (split into db_runtime_signals.py per boy scout rule) ---
from core.runtime.db_runtime_signals import (  # noqa: E402,F401
    ensure_runtime_signals_tables,
    recent_runtime_action_outcomes,
    recent_runtime_learning_signals,
    record_runtime_action_outcome,
    record_runtime_learning_signal,
)


# --- Runtime self-review signal cluster (split into db_runtime_self_review.py per boy scout rule) ---
from core.runtime.db_runtime_self_review import (  # noqa: E402,F401
    upsert_runtime_self_review_signal,
    list_runtime_self_review_signals,
    get_runtime_self_review_signal,
    update_runtime_self_review_signal_status,
    supersede_runtime_self_review_signals_for_domain,
    upsert_runtime_self_review_record,
    list_runtime_self_review_records,
    get_runtime_self_review_record,
    update_runtime_self_review_record_status,
    supersede_runtime_self_review_records_for_domain,
    upsert_runtime_self_review_run,
    list_runtime_self_review_runs,
    get_runtime_self_review_run,
    update_runtime_self_review_run_status,
    supersede_runtime_self_review_runs_for_domain,
    upsert_runtime_self_review_outcome,
    list_runtime_self_review_outcomes,
    get_runtime_self_review_outcome,
    update_runtime_self_review_outcome_status,
    supersede_runtime_self_review_outcomes_for_domain,
    upsert_runtime_self_review_cadence_signal,
    list_runtime_self_review_cadence_signals,
    get_runtime_self_review_cadence_signal,
    update_runtime_self_review_cadence_signal_status,
    supersede_runtime_self_review_cadence_signals_for_domain,
)


# --- Runtime dream signal cluster (split into db_runtime_dream.py per boy scout rule) ---
from core.runtime.db_runtime_dream import (  # noqa: E402,F401
    _ensure_runtime_dream_hypothesis_signal_table,
    _ensure_runtime_dream_adoption_candidate_table,
    _ensure_runtime_dream_influence_proposal_table,
    upsert_runtime_dream_hypothesis_signal,
    list_runtime_dream_hypothesis_signals,
    get_runtime_dream_hypothesis_signal,
    update_runtime_dream_hypothesis_signal_status,
    supersede_runtime_dream_hypothesis_signals_for_domain,
    upsert_runtime_dream_adoption_candidate,
    list_runtime_dream_adoption_candidates,
    get_runtime_dream_adoption_candidate,
    update_runtime_dream_adoption_candidate_status,
    supersede_runtime_dream_adoption_candidates_for_domain,
    upsert_runtime_dream_influence_proposal,
    list_runtime_dream_influence_proposals,
    get_runtime_dream_influence_proposal,
    update_runtime_dream_influence_proposal_status,
    supersede_runtime_dream_influence_proposals_for_domain,
)


# --- Runtime chronicle-consolidation signal cluster (split into db_runtime_chronicle.py per boy scout rule) ---
from core.runtime.db_runtime_chronicle import (  # noqa: E402,F401
    _ensure_runtime_consolidation_target_signal_table,
    _ensure_runtime_chronicle_consolidation_signal_table,
    _ensure_runtime_chronicle_consolidation_brief_table,
    _ensure_runtime_chronicle_consolidation_proposal_table,
    upsert_runtime_consolidation_target_signal,
    list_runtime_consolidation_target_signals,
    get_runtime_consolidation_target_signal,
    update_runtime_consolidation_target_signal_status,
    supersede_runtime_consolidation_target_signals_for_domain,
    upsert_runtime_chronicle_consolidation_signal,
    list_runtime_chronicle_consolidation_signals,
    get_runtime_chronicle_consolidation_signal,
    update_runtime_chronicle_consolidation_signal_status,
    supersede_runtime_chronicle_consolidation_signals_for_domain,
    upsert_runtime_chronicle_consolidation_brief,
    list_runtime_chronicle_consolidation_briefs,
    get_runtime_chronicle_consolidation_brief,
    update_runtime_chronicle_consolidation_brief_status,
    supersede_runtime_chronicle_consolidation_briefs_for_domain,
    upsert_runtime_chronicle_consolidation_proposal,
    list_runtime_chronicle_consolidation_proposals,
    get_runtime_chronicle_consolidation_proposal,
    update_runtime_chronicle_consolidation_proposal_status,
    supersede_runtime_chronicle_consolidation_proposals_for_domain,
)


# --- Runtime hook dispatch table (split into db_runtime_hooks.py per boy scout rule) ---
from core.runtime.db_runtime_hooks import (  # noqa: E402,F401
    ensure_runtime_hooks_tables,
    record_runtime_hook_dispatch,
    get_runtime_hook_dispatch,
    list_runtime_hook_dispatches,
)


# --- Bounded action continuity table (split into db_bounded_action.py per boy scout rule) ---
from core.runtime.db_bounded_action import (  # noqa: E402,F401
    ensure_bounded_action_tables,
    get_bounded_action_continuity_state,
    upsert_bounded_action_continuity_state,
)


# ---------------------------------------------------------------------------
# Per-process "table-ensured" memoization (2026-05-13).
# ---------------------------------------------------------------------------
# Profile under load showed ~40 `_ensure_*_table` calls per prompt-build
# as the new dominant hot path after the cheap-lane caches landed. Each
# call ran `CREATE TABLE IF NOT EXISTS` (+ indexes, sometimes ALTER for
# additive migrations) — all idempotent and fully redundant after the
# first call in the process lifetime.
#
# Strategy: wrap every `_ensure_*_table` function at module-load time so
# subsequent calls short-circuit. First call still runs the original
# (which handles migrations); subsequent calls become a single set-lookup.
#
# Safety: every wrapped function is designed to be idempotent (see
# docstrings in db.py — "Idempotent — kan kaldes flere gange uden fejl").
# Migrations use `ALTER TABLE ... ADD COLUMN` guarded against duplicate
# column errors, so running once at startup is identical to running on
# every call.










# Wrap alle _ensure_*_table funcs der nu lever på facaden (re-eksporteret
# fra db_core plus de der stadig er defineret direkte i db.py). Når senere
# faser flytter _ensure_*-funcs til submoduler, kalder hver submodul også
# _install_ensure_once_cache_for(__name__) på sig selv.
_install_ensure_once_cache()
