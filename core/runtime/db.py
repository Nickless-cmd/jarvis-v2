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


# _ensure_autonomy_proposals_table + autonomy CRUD er udskilt til db_autonomy.py
# (Boy Scout-reglen) og re-eksporteres i bunden af denne fil.


# create/list/get/resolve_autonomy_proposal + _autonomy_proposal_from_row er
# udskilt til db_autonomy.py (Boy Scout-reglen) og re-eksporteres i bunden.












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




# ---------------------------------------------------------------------------
# Private brain records — persistent private inner continuity
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Session distillation records
# ---------------------------------------------------------------------------




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


# --- Taste Profile ---


# --- Chronicle ---


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


# --- Cognitive Episodes ---


# --- Relationship Texture ---


# --- Compass State ---


# --- Rhythm State ---


# --- Habits ---


# --- Decisions ---


# --- Counterfactuals ---


# --- Shared Language ---


# --- Seeds (Prospective Memory) ---


# --- Gut State ---


# --- Self-Experiments ---


# --- Conversation Rhythm ---


# --- User Emotional States ---


# --- Experiential Memories ---




# --- Self-Surprises ---


# --- Narrative Identities ---


# --- Gratitude Signals ---


# --- Emergent Goals ---


# --- Formed Values ---


# --- Conflict Memories ---


# ---------------------------------------------------------------------------
# Cached affective state
# ---------------------------------------------------------------------------








# ---------------------------------------------------------------------------
# cognitive_emotion_concept_signals
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Experiment Settings
# ---------------------------------------------------------------------------







# ---------------------------------------------------------------------------
# Experiment 1: Recurrence Loop
# ---------------------------------------------------------------------------









# ---------------------------------------------------------------------------
# Experiment 3: Global Workspace Broadcast Events
# ---------------------------------------------------------------------------







# ---------------------------------------------------------------------------
# Experiment 4: Meta-Cognition Records
# ---------------------------------------------------------------------------







# ---------------------------------------------------------------------------
# Experiment 5: Attention Blink Results
# ---------------------------------------------------------------------------







# ── Web cache ───────────────────────────────────────────────────


# ── Daemon output log ───────────────────────────────────────────


# ---------------------------------------------------------------------------
# Session summaries — LLM-generated conversation summaries for continuity
# ---------------------------------------------------------------------------












# ---------------------------------------------------------------------------
# Session topics — real-time topic accumulator for Jarvis' conversation memory
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Signal archive — stores signals before decay-deletion for debugging
# ---------------------------------------------------------------------------










# ---------------------------------------------------------------------------
# Daemon output log
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# aesthetic_motif_log — accumulated aesthetic motifs from daemon text output
# ---------------------------------------------------------------------------










# ---------------------------------------------------------------------------
# Channel Attachments
# ---------------------------------------------------------------------------









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


# --- Runtime self-* signal cluster (split into db_runtime_self.py per boy scout rule) ---
# The self_model / self_narrative_continuity / selfhood ensure-functions are
# re-imported here because init_db() calls them inline; the rest are public CRUD.
from core.runtime.db_runtime_self import (  # noqa: E402,F401
    _ensure_runtime_self_model_signal_table,
    _ensure_runtime_self_narrative_continuity_signal_table,
    _ensure_runtime_selfhood_proposal_table,
    upsert_runtime_self_model_signal,
    list_runtime_self_model_signals,
    get_runtime_self_model_signal,
    update_runtime_self_model_signal_status,
    supersede_runtime_self_model_signals,
    upsert_runtime_self_authored_prompt_proposal,
    list_runtime_self_authored_prompt_proposals,
    get_runtime_self_authored_prompt_proposal,
    update_runtime_self_authored_prompt_proposal_status,
    supersede_runtime_self_authored_prompt_proposals_for_domain,
    upsert_runtime_self_narrative_continuity_signal,
    list_runtime_self_narrative_continuity_signals,
    get_runtime_self_narrative_continuity_signal,
    update_runtime_self_narrative_continuity_signal_status,
    supersede_runtime_self_narrative_continuity_signals_for_focus,
    upsert_runtime_selfhood_proposal,
    list_runtime_selfhood_proposals,
    get_runtime_selfhood_proposal,
    update_runtime_selfhood_proposal_status,
    supersede_runtime_selfhood_proposals_for_domain,
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


# --- Runtime private-* signal cluster (split into db_runtime_private.py per boy scout rule) ---
# All six ensure-functions are re-imported here because init_db() calls them
# inline; the rest are public CRUD.
from core.runtime.db_runtime_private import (  # noqa: E402,F401
    _ensure_runtime_private_inner_note_signal_table,
    _ensure_runtime_private_initiative_tension_signal_table,
    _ensure_runtime_private_inner_interplay_signal_table,
    _ensure_runtime_private_state_snapshot_table,
    _ensure_runtime_private_temporal_curiosity_state_table,
    _ensure_runtime_private_temporal_promotion_signal_table,
    upsert_runtime_private_inner_note_signal,
    list_runtime_private_inner_note_signals,
    get_runtime_private_inner_note_signal,
    update_runtime_private_inner_note_signal_status,
    supersede_runtime_private_inner_note_signals_for_focus,
    upsert_runtime_private_initiative_tension_signal,
    list_runtime_private_initiative_tension_signals,
    get_runtime_private_initiative_tension_signal,
    update_runtime_private_initiative_tension_signal_status,
    supersede_runtime_private_initiative_tension_signals_for_domain,
    upsert_runtime_private_inner_interplay_signal,
    list_runtime_private_inner_interplay_signals,
    get_runtime_private_inner_interplay_signal,
    update_runtime_private_inner_interplay_signal_status,
    supersede_runtime_private_inner_interplay_signals_for_relation,
    upsert_runtime_private_state_snapshot,
    list_runtime_private_state_snapshots,
    get_runtime_private_state_snapshot,
    update_runtime_private_state_snapshot_status,
    supersede_runtime_private_state_snapshots_for_focus,
    upsert_runtime_private_temporal_curiosity_state,
    list_runtime_private_temporal_curiosity_states,
    get_runtime_private_temporal_curiosity_state,
    update_runtime_private_temporal_curiosity_state_status,
    supersede_runtime_private_temporal_curiosity_states_for_focus,
    upsert_runtime_private_temporal_promotion_signal,
    list_runtime_private_temporal_promotion_signals,
    get_runtime_private_temporal_promotion_signal,
    update_runtime_private_temporal_promotion_signal_status,
    supersede_runtime_private_temporal_promotion_signals_for_focus,
)


# --- Runtime executive-* signal cluster (split into db_runtime_executive_signals.py per boy scout rule) ---
# The goal_signal / development_focus / autonomy_pressure /
# proactive_loop_lifecycle / proactive_question_gate ensure-functions are
# re-imported here because init_db() calls them inline; the world_model /
# open_loop_signal / open_loop_closure_proposal / contract_candidate ensures are
# called lazily. NOTE: open_loop_signal and open_loop_closure_proposal are two
# distinct families; contract_candidate carries an extra counts helper.
from core.runtime.db_runtime_executive_signals import (  # noqa: E402,F401
    _ensure_runtime_goal_signal_table,
    _ensure_runtime_development_focus_table,
    _ensure_runtime_autonomy_pressure_signal_table,
    _ensure_runtime_proactive_loop_lifecycle_signal_table,
    _ensure_runtime_proactive_question_gate_table,
    upsert_runtime_goal_signal,
    list_runtime_goal_signals,
    get_runtime_goal_signal,
    update_runtime_goal_signal_status,
    supersede_runtime_goal_signals,
    upsert_runtime_world_model_signal,
    list_runtime_world_model_signals,
    get_runtime_world_model_signal,
    update_runtime_world_model_signal_status,
    supersede_runtime_world_model_signals,
    upsert_runtime_development_focus,
    list_runtime_development_focuses,
    get_runtime_development_focus,
    update_runtime_development_focus_status,
    supersede_runtime_development_focuses,
    upsert_runtime_autonomy_pressure_signal,
    list_runtime_autonomy_pressure_signals,
    get_runtime_autonomy_pressure_signal,
    update_runtime_autonomy_pressure_signal_status,
    supersede_runtime_autonomy_pressure_signals_for_type,
    upsert_runtime_open_loop_signal,
    list_runtime_open_loop_signals,
    get_runtime_open_loop_signal,
    update_runtime_open_loop_signal_status,
    supersede_runtime_open_loop_signals_for_domain,
    upsert_runtime_open_loop_closure_proposal,
    list_runtime_open_loop_closure_proposals,
    get_runtime_open_loop_closure_proposal,
    update_runtime_open_loop_closure_proposal_status,
    supersede_runtime_open_loop_closure_proposals_for_domain,
    upsert_runtime_contract_candidate,
    list_runtime_contract_candidates,
    get_runtime_contract_candidate,
    runtime_contract_candidate_counts,
    update_runtime_contract_candidate_status,
    supersede_runtime_contract_candidates,
    upsert_runtime_proactive_loop_lifecycle_signal,
    list_runtime_proactive_loop_lifecycle_signals,
    get_runtime_proactive_loop_lifecycle_signal,
    update_runtime_proactive_loop_lifecycle_signal_status,
    supersede_runtime_proactive_loop_lifecycle_signals_for_kind,
    upsert_runtime_proactive_question_gate,
    list_runtime_proactive_question_gates,
    get_runtime_proactive_question_gate,
    update_runtime_proactive_question_gate_status,
    supersede_runtime_proactive_question_gates_for_kind,
    _ensure_runtime_world_model_signal_table,
    _ensure_runtime_open_loop_signal_table,
    _ensure_runtime_open_loop_closure_proposal_table,
    _ensure_runtime_contract_candidate_table,
)


# --- Runtime temporal/memory-* signal cluster (split into db_runtime_temporal_memory_signals.py per boy scout rule) ---
# The remembered_fact / memory_md_update_proposal / release_marker /
# selective_forgetting / regulation_homeostasis / temperament_tendency ensure-
# functions are re-imported here because init_db() calls them inline; the
# temporal_recurrence ensure is called lazily. NOTE: this is the
# runtime_memory_md_update_proposal family — distinct from
# runtime_user_md_update_proposal which lives in db_runtime_relational_signals.py.
from core.runtime.db_runtime_temporal_memory_signals import (  # noqa: E402,F401
    _ensure_runtime_remembered_fact_signal_table,
    _ensure_runtime_memory_md_update_proposal_table,
    _ensure_runtime_release_marker_signal_table,
    _ensure_runtime_selective_forgetting_candidate_table,
    _ensure_runtime_regulation_homeostasis_signal_table,
    _ensure_runtime_temperament_tendency_signal_table,
    upsert_runtime_temporal_recurrence_signal,
    list_runtime_temporal_recurrence_signals,
    get_runtime_temporal_recurrence_signal,
    update_runtime_temporal_recurrence_signal_status,
    supersede_runtime_temporal_recurrence_signals_for_domain,
    upsert_runtime_remembered_fact_signal,
    list_runtime_remembered_fact_signals,
    get_runtime_remembered_fact_signal,
    update_runtime_remembered_fact_signal_status,
    supersede_runtime_remembered_fact_signals_for_dimension,
    upsert_runtime_memory_md_update_proposal,
    list_runtime_memory_md_update_proposals,
    get_runtime_memory_md_update_proposal,
    update_runtime_memory_md_update_proposal_status,
    supersede_runtime_memory_md_update_proposals_for_dimension,
    upsert_runtime_release_marker_signal,
    list_runtime_release_marker_signals,
    get_runtime_release_marker_signal,
    update_runtime_release_marker_signal_status,
    supersede_runtime_release_marker_signals_for_domain,
    upsert_runtime_selective_forgetting_candidate,
    list_runtime_selective_forgetting_candidates,
    get_runtime_selective_forgetting_candidate,
    update_runtime_selective_forgetting_candidate_status,
    supersede_runtime_selective_forgetting_candidates_for_domain,
    upsert_runtime_regulation_homeostasis_signal,
    list_runtime_regulation_homeostasis_signals,
    get_runtime_regulation_homeostasis_signal,
    update_runtime_regulation_homeostasis_signal_status,
    supersede_runtime_regulation_homeostasis_signals_for_focus,
    upsert_runtime_temperament_tendency_signal,
    list_runtime_temperament_tendency_signals,
    get_runtime_temperament_tendency_signal,
    update_runtime_temperament_tendency_signal_status,
    supersede_runtime_temperament_tendency_signals_for_focus,
    _ensure_runtime_temporal_recurrence_signal_table,
)


# --- Runtime cognition-* signal cluster (split into db_runtime_cognition_signals.py per boy scout rule) ---
# The meaning_significance / metabolism_state / executive_contradiction ensure-
# functions are re-imported here because init_db() calls them inline; the rest
# are public CRUD.
from core.runtime.db_runtime_cognition_signals import (  # noqa: E402,F401
    _ensure_runtime_meaning_significance_signal_table,
    _ensure_runtime_metabolism_state_signal_table,
    _ensure_runtime_executive_contradiction_signal_table,
    upsert_runtime_reflection_signal,
    list_runtime_reflection_signals,
    get_runtime_reflection_signal,
    update_runtime_reflection_signal_status,
    supersede_runtime_reflection_signals_for_domain,
    upsert_runtime_reflective_critic,
    list_runtime_reflective_critics,
    get_runtime_reflective_critic,
    update_runtime_reflective_critic_status,
    supersede_runtime_reflective_critics,
    upsert_runtime_internal_opposition_signal,
    list_runtime_internal_opposition_signals,
    get_runtime_internal_opposition_signal,
    update_runtime_internal_opposition_signal_status,
    supersede_runtime_internal_opposition_signals_for_domain,
    upsert_runtime_meaning_significance_signal,
    list_runtime_meaning_significance_signals,
    get_runtime_meaning_significance_signal,
    update_runtime_meaning_significance_signal_status,
    supersede_runtime_meaning_significance_signals_for_focus,
    upsert_runtime_witness_signal,
    list_runtime_witness_signals,
    get_runtime_witness_signal,
    update_runtime_witness_signal_status,
    supersede_runtime_witness_signals_for_domain,
    upsert_runtime_awareness_signal,
    list_runtime_awareness_signals,
    get_runtime_awareness_signal,
    update_runtime_awareness_signal_status,
    supersede_runtime_awareness_signals,
    upsert_runtime_executive_contradiction_signal,
    list_runtime_executive_contradiction_signals,
    get_runtime_executive_contradiction_signal,
    update_runtime_executive_contradiction_signal_status,
    supersede_runtime_executive_contradiction_signals_for_domain,
    upsert_runtime_metabolism_state_signal,
    list_runtime_metabolism_state_signals,
    get_runtime_metabolism_state_signal,
    update_runtime_metabolism_state_signal_status,
    supersede_runtime_metabolism_state_signals_for_domain,
)


# --- Runtime relational-* signal cluster (split into db_runtime_relational_signals.py per boy scout rule) ---
# The inner_visible_support / relation_state / relation_continuity /
# attachment_topology / loyalty_gradient / user_understanding ensure-functions
# are re-imported here because init_db() calls them inline; the rest are public
# CRUD. NOTE: this is the runtime_user_md_update_proposal family — distinct from
# runtime_memory_md_update_proposal which stays in db.py.
from core.runtime.db_runtime_relational_signals import (  # noqa: E402,F401
    _ensure_runtime_inner_visible_support_signal_table,
    _ensure_runtime_relation_state_signal_table,
    _ensure_runtime_relation_continuity_signal_table,
    _ensure_runtime_attachment_topology_signal_table,
    _ensure_runtime_loyalty_gradient_signal_table,
    _ensure_runtime_user_understanding_signal_table,
    upsert_runtime_relation_continuity_signal,
    list_runtime_relation_continuity_signals,
    get_runtime_relation_continuity_signal,
    update_runtime_relation_continuity_signal_status,
    supersede_runtime_relation_continuity_signals_for_focus,
    upsert_runtime_relation_state_signal,
    list_runtime_relation_state_signals,
    get_runtime_relation_state_signal,
    update_runtime_relation_state_signal_status,
    supersede_runtime_relation_state_signals_for_focus,
    upsert_runtime_attachment_topology_signal,
    list_runtime_attachment_topology_signals,
    get_runtime_attachment_topology_signal,
    update_runtime_attachment_topology_signal_status,
    supersede_runtime_attachment_topology_signals_for_domain,
    upsert_runtime_loyalty_gradient_signal,
    list_runtime_loyalty_gradient_signals,
    get_runtime_loyalty_gradient_signal,
    update_runtime_loyalty_gradient_signal_status,
    supersede_runtime_loyalty_gradient_signals_for_domain,
    upsert_runtime_user_understanding_signal,
    list_runtime_user_understanding_signals,
    get_runtime_user_understanding_signal,
    update_runtime_user_understanding_signal_status,
    supersede_runtime_user_understanding_signals_for_dimension,
    upsert_runtime_user_md_update_proposal,
    list_runtime_user_md_update_proposals,
    get_runtime_user_md_update_proposal,
    update_runtime_user_md_update_proposal_status,
    supersede_runtime_user_md_update_proposals_for_dimension,
    upsert_runtime_inner_visible_support_signal,
    list_runtime_inner_visible_support_signals,
    get_runtime_inner_visible_support_signal,
    update_runtime_inner_visible_support_signal_status,
    supersede_runtime_inner_visible_support_signals_for_focus,
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


# --- Cognitive + experiential-memory domain (split into db_cognitive.py per boy scout rule) ---
from core.runtime.db_cognitive import (  # noqa: E402,F401
    _ensure_session_distillation_records_table,
    insert_session_distillation_record,
    get_session_distillation_record,
    _ensure_cognitive_personality_vector_table,
    upsert_cognitive_personality_vector,
    get_latest_cognitive_personality_vector,
    list_cognitive_personality_vectors,
    _ensure_cognitive_taste_profile_table,
    upsert_cognitive_taste_profile,
    get_latest_cognitive_taste_profile,
    _ensure_cognitive_chronicle_entries_table,
    insert_cognitive_chronicle_entry,
    get_latest_cognitive_chronicle_entry,
    list_cognitive_chronicle_entries,
    _ensure_cognitive_episodes_table,
    insert_cognitive_episode,
    list_cognitive_episodes,
    get_latest_cognitive_episode,
    _cognitive_episode_row_to_dict,
    _ensure_cognitive_relationship_texture_table,
    upsert_cognitive_relationship_texture,
    get_latest_cognitive_relationship_texture,
    _ensure_cognitive_compass_state_table,
    upsert_cognitive_compass_state,
    get_latest_cognitive_compass_state,
    _ensure_cognitive_rhythm_state_table,
    upsert_cognitive_rhythm_state,
    get_latest_cognitive_rhythm_state,
    _ensure_cognitive_habit_patterns_table,
    upsert_cognitive_habit_pattern,
    upsert_cognitive_friction_signal,
    list_cognitive_habit_patterns,
    list_cognitive_friction_signals,
    _ensure_cognitive_decisions_table,
    insert_cognitive_decision,
    list_cognitive_decisions,
    _ensure_cognitive_counterfactuals_table,
    insert_cognitive_counterfactual,
    list_cognitive_counterfactuals,
    _ensure_cognitive_shared_language_table,
    upsert_cognitive_shared_language_term,
    list_cognitive_shared_language,
    _ensure_cognitive_seeds_table,
    insert_cognitive_seed,
    update_cognitive_seed_status,
    list_cognitive_seeds,
    _ensure_cognitive_gut_state_table,
    update_cognitive_gut_state,
    get_cognitive_gut_state,
    _ensure_cognitive_experiments_table,
    upsert_cognitive_experiment,
    list_cognitive_experiments,
    _ensure_cognitive_conversation_signatures_table,
    upsert_cognitive_conversation_signature,
    list_cognitive_conversation_signatures,
    _ensure_cognitive_user_emotional_states_table,
    insert_cognitive_user_emotional_state,
    get_latest_cognitive_user_emotional_state,
    list_cognitive_user_emotional_states,
    _ensure_cognitive_experiential_memories_table,
    insert_cognitive_experiential_memory,
    reinforce_experiential_memory,
    list_cognitive_experiential_memories,
    get_experiential_memory_candidates,
    _ensure_cognitive_self_surprises_table,
    insert_cognitive_self_surprise,
    list_cognitive_self_surprises,
    _ensure_cognitive_narrative_identities_table,
    insert_cognitive_narrative_identity,
    get_latest_cognitive_narrative_identity,
    list_cognitive_narrative_identities,
    _ensure_cognitive_gratitude_signals_table,
    insert_cognitive_gratitude_signal,
    list_cognitive_gratitude_signals,
    _ensure_cognitive_emergent_goals_table,
    upsert_cognitive_emergent_goal,
    list_cognitive_emergent_goals,
    _ensure_cognitive_formed_values_table,
    upsert_cognitive_formed_value,
    list_cognitive_formed_values,
    _ensure_cognitive_conflict_memories_table,
    insert_cognitive_conflict_memory,
    list_cognitive_conflict_memories,
    _ensure_cognitive_emotion_concept_signal_table,
    upsert_cognitive_emotion_concept_signal,
    list_active_cognitive_emotion_concept_signals,
    _ensure_web_cache_table,
    web_cache_store,
    web_cache_lookup,
    web_cache_cleanup,
    _ensure_session_topics_table,
    session_topic_accumulate,
    session_topics_for_session,
    session_topic_cleanup,
    _ensure_daemon_output_log_table,
    daemon_output_log_insert,
    daemon_output_log_recent,
    daemon_output_log_cleanup,
)


# --- Runtime-initiatives cluster (split into db_runtime_initiatives.py per boy scout rule) ---
from core.runtime.db_runtime_initiatives import (  # noqa: E402,F401
    _ensure_runtime_initiatives_table,
    _runtime_initiative_from_row,
    create_runtime_initiative,
    get_runtime_initiative,
    find_pending_runtime_initiative_by_focus,
    list_runtime_initiatives,
    update_runtime_initiative,
    approve_runtime_initiative,
    reject_runtime_initiative,
)


# --- Governance CRUD domains (split into db_governance.py per boy scout rule) ---
# tool-intent approvals, contract-file writes, webchat execution pilots.
# NB: _ensure_tool_intent_approval_request_columns and
# _ensure_runtime_webchat_execution_pilot_table stay in db.py (init_db calls them).
from core.runtime.db_governance import (  # noqa: E402,F401
    create_tool_intent_approval_request,
    get_tool_intent_approval_request,
    resolve_tool_intent_approval_request,
    expire_tool_intent_approval_request,
    _tool_intent_approval_request_from_row,
    record_runtime_contract_file_write,
    get_runtime_contract_file_write,
    recent_runtime_contract_file_writes,
    runtime_contract_file_write_counts,
    _ensure_runtime_contract_file_write_table,
    _runtime_contract_file_write_from_row,
    record_runtime_webchat_execution_pilot,
    list_runtime_webchat_execution_pilots,
    get_runtime_webchat_execution_pilot,
    _runtime_webchat_execution_pilot_from_row,
)


# --- Small runtime CRUD domains (split into db_runtime_misc.py per boy scout rule) ---
from core.runtime.db_runtime_misc import (  # noqa: E402,F401
    get_relevant_experiential_memories,
    list_session_distillation_records,
    _ensure_cached_affective_state_table,
    save_cached_affective_state,
    get_cached_affective_state,
    _ensure_experiment_settings_table,
    get_experiment_enabled,
    set_experiment_enabled,
    _ensure_recurrence_iterations_table,
    insert_recurrence_iteration,
    get_latest_recurrence_iteration,
    list_recurrence_iterations,
    _ensure_broadcast_events_table,
    insert_broadcast_event,
    list_broadcast_events,
    _ensure_meta_cognition_table,
    insert_meta_cognition_record,
    list_meta_cognition_records,
    _ensure_attention_blink_table,
    insert_attention_blink_result,
    list_attention_blink_results,
    _ensure_session_summaries_table,
    session_summary_insert,
    session_summary_recent,
    session_summary_for_session,
    session_summary_cleanup,
    _ensure_signal_archive_table,
    signal_decay_archive_and_delete,
    signal_archive_cleanup,
    signal_archive_recent,
    _ensure_aesthetic_motif_log_table,
    aesthetic_motif_log_insert,
    aesthetic_motif_log_unique_motifs,
    aesthetic_motif_log_summary,
    _ensure_channel_attachments_table,
    store_channel_attachment,
    get_channel_attachment,
    list_channel_attachments,
)


# --- Runtime diary-synthesis signal cluster (split into db_runtime_diary.py per boy scout rule) ---
from core.runtime.db_runtime_diary import (  # noqa: E402,F401
    _ensure_runtime_diary_synthesis_signal_table,
    _runtime_diary_synthesis_signal_from_row,
    list_runtime_diary_synthesis_signals,
    get_diary_synthesis_signal,
    update_diary_synthesis_signal_status,
    supersede_diary_synthesis_signals_for_focus,
    upsert_diary_synthesis_signal,
)


# --- Cheap-provider runtime-state + invocation cluster (split into db_cheap_provider.py per boy scout rule) ---
from core.runtime.db_cheap_provider import (  # noqa: E402,F401
    upsert_cheap_provider_runtime_state,
    get_cheap_provider_runtime_state,
    list_cheap_provider_runtime_states,
    record_cheap_provider_invocation,
    count_cheap_provider_invocations,
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
