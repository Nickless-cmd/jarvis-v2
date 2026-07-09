"""Persistence for the cognitive + experiential-memory domain.

Split out of core/runtime/db.py per the boy-scout rule. Owns the schema and
CRUD for the large cognitive cluster (cognitive_* tables: personality-vector,
taste-profile, chronicle-entries, episodes, relationship-texture, compass,
rhythm, habit/friction, decisions, counterfactuals, shared-language, seeds,
gut-state, experiments, conversation-signatures, user-emotional-states,
experiential-memories, self-surprises, narrative-identities, gratitude,
emergent-goals, formed-values, conflict-memories, emotion-concept-signals),
plus the session-distillation table. All `_ensure_*_table` helpers are invoked
lazily by their own CRUD (never by init_db), so the cluster is self-contained.

The three independent utility caches (web_cache, session_topics,
daemon_output_log) were sub-split to db_cognitive_utility.py per the boy-scout
rule and are re-exported at the bottom of this module.

NOTE: `get_session_distillation_record` lazy-imports the staying db.py-local
row-mapper `_session_distillation_record_from_row` in-body to avoid a circular
import (the LIST variant and that mapper stay in db.py).
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import connect, _now_iso


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
    """Insert a session-distillation record (INSERT OR IGNORE on distillation_id).

    Returns the stored row dict (via get_session_distillation_record), or {} if
    the lookup fails. No-op if a record with the same distillation_id exists.
    """
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


def get_session_distillation_record(distillation_id: str) -> dict[str, object] | None:
    """Return the session-distillation record for the given id, or None if absent.

    Maps the row via db.py's _session_distillation_record_from_row (lazy-imported
    to avoid a circular import).
    """
    with connect() as conn:
        _ensure_session_distillation_records_table(conn)
        row = conn.execute(
            "SELECT * FROM session_distillation_records WHERE distillation_id = ?",
            (distillation_id,),
        ).fetchone()
    if row is None:
        return None
    # Row-mapper stays in db.py (used by the LIST variant that also stays);
    # lazy-import avoids a circular import between db.py and db_cognitive.py.
    from core.runtime.db import _session_distillation_record_from_row
    return _session_distillation_record_from_row(row)


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
    """Insert a new personality-vector version (auto-incremented from the latest).

    Writes a fresh versioned row and invalidates the cognitive-state cache so the
    change surfaces in the next prompt assembly. Returns {vector_id, version,
    updated_at}.
    """
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
    """Return the highest-version personality-vector row as a dict, or None if none exist."""
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
    """Return up to `limit` personality-vector rows (newest version first) as dicts."""
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
    """Insert a new taste-profile version (auto-incremented from the latest).

    Returns {profile_id, version, updated_at}.
    """
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
    """Return the highest-version taste-profile row as a dict, or None if none exist."""
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


def insert_cognitive_chronicle_entry(
    *,
    entry_id: str,
    period: str,
    narrative: str,
    key_events: str = "[]",
    lessons: str = "[]",
    affective_signature: str = "",
) -> dict[str, object]:
    """Insert or replace a chronicle entry keyed by entry_id (INSERT OR REPLACE).

    Returns {entry_id, period, created_at}.
    """
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
    """Return the most recently created chronicle entry as a dict, or None if none exist."""
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
    """Return up to `limit` chronicle entries (newest first) as dicts.

    Privacy-scoped to the current user: rows with NULL relevant_to_users (general
    Jarvis state) plus rows that mention the current user id. Falls back to all
    rows when no user context is set.
    """
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
    """Insert or replace a cognitive episode keyed by episode_id (INSERT OR REPLACE).

    Text fields are truncated (trigger/outcome_status/summary) before storage.
    Returns {episode_id, created_at}.
    """
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
    """Return up to `limit` cognitive episodes (newest first) as dicts."""
    with connect() as conn:
        _ensure_cognitive_episodes_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_episodes ORDER BY created_at DESC LIMIT ?",
            (max(int(limit), 1),),
        ).fetchall()
    return [_cognitive_episode_row_to_dict(row) for row in rows]


def get_latest_cognitive_episode() -> dict[str, object] | None:
    """Return the most recent cognitive episode as a dict, or None if none exist."""
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
    """Insert a new relationship-texture version (auto-incremented from the latest).

    Returns {texture_id, version, updated_at}.
    """
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
    """Return the highest-version relationship-texture row as a dict, or None if none exist."""
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
    """Upsert the singleton compass state ('compass-current', INSERT OR REPLACE).

    Returns {compass_id, bearing, updated_at}.
    """
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
    """Return the most recently updated compass-state row as a dict, or None if none exist."""
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
    """Upsert the singleton rhythm state ('rhythm-current', INSERT OR REPLACE).

    Booleans (recovery_needed, focus_protection) are stored as ints. Returns
    {rhythm_id, phase, energy, updated_at}.
    """
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
    """Return the most recently updated rhythm-state row as a dict, or None if none exist."""
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
    """Upsert a habit pattern by pattern_key.

    On an existing key, bumps recurrence_count and recomputes confidence
    (min(1.0, 0.2 + count/20)); otherwise inserts a new row at count 1 / conf 0.2.
    Returns {pattern_key, recurrence_count, confidence}.
    """
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
    """Upsert a friction signal by task_signature.

    On an existing signature, bumps repetition_count and keeps the max
    inefficiency_score; otherwise inserts a new row at count 1. Returns
    {task_signature, repetition_count}.
    """
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
    """Return up to `limit` habit patterns (most recurrent first) as dicts."""
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
    """Return up to `limit` friction signals (most repeated first) as dicts."""
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
    """Insert or replace a decision record keyed by decision_id (INSERT OR REPLACE).

    Returns {decision_id, title, created_at}.
    """
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
    """Return up to `limit` decision records (newest first) as dicts."""
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
    """Insert or replace a counterfactual keyed by cf_id (INSERT OR REPLACE).

    Returns {cf_id, created_at}.
    """
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
    """Return up to `limit` counterfactuals (newest first) as dicts."""
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
    """Upsert a shared-language term by phrase.

    On an existing phrase, nudges confidence up by 0.05 (capped at 1.0) and
    refreshes last_used_at; otherwise inserts a new hash-derived term_id. Returns
    {phrase, confidence}.
    """
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
    """Return up to `limit` shared-language terms (highest confidence first) as dicts."""
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
    """Insert or replace a seed keyed by seed_id, status forced to 'planted'.

    Returns {seed_id, title, status, created_at}.
    """
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
    """Update the status (and updated_at) of the seed with the given seed_id. Returns None."""
    now = _now_iso()
    with connect() as conn:
        _ensure_cognitive_seeds_table(conn)
        conn.execute(
            "UPDATE cognitive_seeds SET status = ?, updated_at = ? WHERE seed_id = ?",
            (status, now, seed_id),
        )


def list_cognitive_seeds(*, status: str = "", limit: int = 20) -> list[dict[str, object]]:
    """Return up to `limit` seeds (newest first) as dicts, optionally filtered by status."""
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
    """Update the singleton gut state ('gut-current') with one prediction outcome.

    Increments total_predictions, adds to calibrated_hits when prediction_correct,
    and recomputes calibration_score = hits/total. Creates the row on first call.
    Returns {updated_at}.
    """
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
    """Return the singleton gut-state row ('gut-current') as a dict, or None if unset."""
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
    """Insert or replace an experiment keyed by experiment_id (INSERT OR REPLACE).

    Returns {experiment_id, status, updated_at}.
    """
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
    """Return up to `limit` experiments (most recently updated first) as dicts, optionally filtered by status."""
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
    """Upsert a conversation signature by signature_type.

    On an existing type, increments count and folds success/duration_min into the
    running success_rate and avg_duration_min; otherwise inserts a new row.
    Returns {signature_type, count[, success_rate]}.
    """
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
    """Return up to `limit` conversation signatures (most frequent first) as dicts."""
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
    """Insert or replace a user-emotional-state row keyed by state_id (INSERT OR REPLACE).

    user_message_preview is truncated to 200 chars. Returns {state_id,
    detected_mood, created_at}.
    """
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
    """Return the most recently created user-emotional-state row as a dict, or None if none exist."""
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
    """Return up to `limit` user-emotional-state rows (newest first) as dicts."""
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
    """Insert or replace an experiential memory keyed by memory_id (INSERT OR REPLACE).

    decay_score and reinforcement_count are initialised to 0; narrative/key_lesson/
    topic are truncated. Returns {memory_id, topic, created_at}.
    """
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


def reinforce_experiential_memory(memory_id: str) -> None:
    """Bump reinforcement_count by 1 and reset decay_score to 0 for the given memory. Returns None."""
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
    """Return up to `limit` experiential memories (newest first) as dicts."""
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
    """Insert or replace a self-surprise keyed by surprise_id (INSERT OR REPLACE).

    narrative is truncated to 300 chars. Returns {surprise_id, surprise_type, created_at}.
    """
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
    """Return up to `limit` self-surprises (newest first) as dicts."""
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
    """Insert or replace a narrative-identity keyed by identity_id (INSERT OR REPLACE).

    narrative is truncated to 600 chars. Returns {identity_id, created_at}.
    """
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
    """Return the most recently created narrative-identity row as a dict, or None if none exist."""
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
    """Return up to `limit` narrative-identity rows (newest first) as dicts."""
    with connect() as conn:
        _ensure_cognitive_narrative_identities_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_narrative_identities ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"identity_id": r["identity_id"], "narrative": r["narrative"],
             "personality_version": int(r["personality_version"]),
             "created_at": r["created_at"]} for r in rows]


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
    """Insert or replace a gratitude signal keyed by gratitude_id (INSERT OR REPLACE).

    detail is truncated to 300 chars. Returns {gratitude_id, created_at}.
    """
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
    """Return up to `limit` gratitude signals (newest first) as dicts."""
    with connect() as conn:
        _ensure_cognitive_gratitude_signals_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_gratitude_signals ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"gratitude_id": r["gratitude_id"], "trigger_event": r["trigger_event"],
             "detail": r["detail"], "intensity": float(r["intensity"]),
             "created_at": r["created_at"]} for r in rows]


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
    """Insert or replace an emergent goal keyed by goal_id (INSERT OR REPLACE).

    desire is truncated to 300 chars. Returns {goal_id, desire, status, created_at}.
    """
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
    """Return up to `limit` emergent goals (highest intensity first) as dicts, optionally filtered by status."""
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
    """Upsert a formed value by value_id.

    On an existing id, bumps evidence_count and nudges conviction up by 0.05
    (capped at 1.0); otherwise inserts a new row at evidence_count 1. Returns
    {value_id, conviction[, evidence_count | created_at]}.
    """
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
    """Return up to `limit` formed values (highest conviction first) as dicts."""
    with connect() as conn:
        _ensure_cognitive_formed_values_table(conn)
        rows = conn.execute(
            "SELECT * FROM cognitive_formed_values ORDER BY conviction DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"value_id": r["value_id"], "value_statement": r["value_statement"],
             "conviction": float(r["conviction"]), "evidence_count": int(r["evidence_count"]),
             "created_at": r["created_at"]} for r in rows]


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
    """Insert or replace a conflict memory keyed by conflict_id (INSERT OR REPLACE).

    All text fields are truncated to 200 chars. Returns {conflict_id, topic, created_at}.
    """
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
    """Return up to `limit` conflict memories (newest first) as dicts."""
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
    """Upsert a time-bounded emotion-concept signal by signal_id.

    Updates the row's intensity/direction/trigger/source/influences/expires_at if
    the signal_id exists, else inserts a new row. Returns None.
    """
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
    """Return active emotion-concept signals as dicts (highest intensity first).

    Filters to rows with expires_at >= now_iso and intensity >= min_intensity,
    capped at `limit`.
    """
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


# --- Re-exports: utility caches sub-split to db_cognitive_utility.py -----------
# (boy-scout rule — kept the public names resolvable here, and thus via db.py,
# for existing `from core.runtime.db import web_cache_lookup` style imports.)
from core.runtime.db_cognitive_utility import (  # noqa: E402,F401
    _ensure_daemon_output_log_table,
    _ensure_session_topics_table,
    _ensure_web_cache_table,
    daemon_output_log_cleanup,
    daemon_output_log_insert,
    daemon_output_log_recent,
    session_topic_accumulate,
    session_topic_cleanup,
    session_topics_for_session,
    web_cache_cleanup,
    web_cache_lookup,
    web_cache_store,
)
