"""Schema layer for core.runtime.db — init_db + all _ensure_*/_migrate_* helpers.

Udskilt fra db.py (Fase 2 batch 7, behavior-preserving) så db.py bliver et
rent re-eksport-hub. init_db() er startup-schema-orkestratoren: den opretter
alle tabeller og kalder ~117 _ensure_*/_migrate_*-funcs. Nogle af dem er
defineret her (flyttet sammen med init_db); andre lever i leaf-db_*-moduler og
importeres nedenfor, så init_db's bare-name-kald resolver.

Import-regel: db_schema importerer KUN fra db_core + leaf db_*-moduler (som selv
kun importerer db_core). db_schema importerer ALDRIG fra core.runtime.db —
db.py re-eksporterer FRA db_schema, så en modsat-rettet import ville skabe cyklus.

Split-historik: docs/superpowers/specs/2026-05-15-db-split-design.md
"""
from __future__ import annotations

import logging as _logging
import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from core.runtime.db_core import connect, _install_ensure_once_cache_for

_logger = _logging.getLogger("uvicorn.error")

# === Cross-module _ensure_*/_migrate_*-funcs som init_db kalder ved bare navn ===
# Disse er defineret i leaf-db_*-moduler (kun db_core-afhængige → ingen cyklus).
# Bruges af init_db via bare navn, derfor F401-undertrykt.
#
# NB: db_users og db_user_contradiction importerer selv `connect` fra
# core.runtime.db (ikke db_core) — hvis vi importerer dem her på modul-niveau,
# opstår en cyklus når db_schema importeres FØR db.py er færdig-initialiseret.
# Derfor importeres deres to ensures lazily inde i init_db (samme mønster som de
# øvrige inline-imports i init_db). De resterende moduler afhænger kun af db_core.
from core.runtime.db_autonomy import _ensure_autonomy_proposals_table  # noqa: E402,F401
from core.runtime.db_scheduled_tasks import _ensure_scheduled_tasks_table  # noqa: E402,F401
from core.runtime.db_capability_approval import (  # noqa: E402,F401
    _ensure_capability_approval_request_columns,
)
from core.runtime.db_runtime_self import (  # noqa: E402,F401
    _ensure_runtime_self_model_signal_table,
    _ensure_runtime_self_narrative_continuity_signal_table,
    _ensure_runtime_selfhood_proposal_table,
)
from core.runtime.db_runtime_private import (  # noqa: E402,F401
    _ensure_runtime_private_initiative_tension_signal_table,
    _ensure_runtime_private_inner_interplay_signal_table,
    _ensure_runtime_private_inner_note_signal_table,
    _ensure_runtime_private_state_snapshot_table,
    _ensure_runtime_private_temporal_curiosity_state_table,
    _ensure_runtime_private_temporal_promotion_signal_table,
)
from core.runtime.db_runtime_initiatives import _ensure_runtime_initiatives_table  # noqa: E402,F401
from core.runtime.db_runtime_chronicle import (  # noqa: E402,F401
    _ensure_runtime_chronicle_consolidation_brief_table,
    _ensure_runtime_chronicle_consolidation_proposal_table,
    _ensure_runtime_chronicle_consolidation_signal_table,
    _ensure_runtime_consolidation_target_signal_table,
)
from core.runtime.db_runtime_temporal_memory_signals import (  # noqa: E402,F401
    _ensure_runtime_memory_md_update_proposal_table,
    _ensure_runtime_regulation_homeostasis_signal_table,
    _ensure_runtime_release_marker_signal_table,
    _ensure_runtime_remembered_fact_signal_table,
    _ensure_runtime_selective_forgetting_candidate_table,
    _ensure_runtime_temperament_tendency_signal_table,
)
from core.runtime.db_runtime_executive_signals import (  # noqa: E402,F401
    _ensure_runtime_autonomy_pressure_signal_table,
    _ensure_runtime_development_focus_table,
    _ensure_runtime_goal_signal_table,
    _ensure_runtime_proactive_loop_lifecycle_signal_table,
    _ensure_runtime_proactive_question_gate_table,
)
from core.runtime.db_runtime_cognition_signals import (  # noqa: E402,F401
    _ensure_runtime_executive_contradiction_signal_table,
    _ensure_runtime_meaning_significance_signal_table,
    _ensure_runtime_metabolism_state_signal_table,
)
from core.runtime.db_runtime_relational_signals import (  # noqa: E402,F401
    _ensure_runtime_attachment_topology_signal_table,
    _ensure_runtime_inner_visible_support_signal_table,
    _ensure_runtime_loyalty_gradient_signal_table,
    _ensure_runtime_relation_continuity_signal_table,
    _ensure_runtime_relation_state_signal_table,
    _ensure_runtime_user_understanding_signal_table,
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
        from core.runtime.db_users import _ensure_users_table
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
        from core.runtime.db_user_contradiction import _ensure_user_contradiction_tables
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
        _ensure_chat_messages_content_json_column(conn)
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


def _ensure_chat_messages_content_json_column(conn: sqlite3.Connection) -> None:
    """Add chat_messages.content_json column. Idempotent.

    Kanonisk struktureret content-array (text/tool_use/tool_result) pr. besked;
    NULL = gammel besked (serve-on-read rekonstruerer). Nullable → ingen backfill.
    """
    cols = [
        r[1] for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()
    ]
    if "content_json" not in cols:
        conn.execute("ALTER TABLE chat_messages ADD COLUMN content_json TEXT")


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


# Wrap _ensure_*_table-funcs defineret HER med once-cache, så init_db's
# bare-name-kald bruger de cachede wrappers (samme adfærd som da init_db
# levede i db.py og _install_ensure_once_cache() wrappede db.py-namespace).
# Allerede-wrappede funcs (importeret fra andre submoduler) springes over.
_install_ensure_once_cache_for("core.runtime.db_schema")

