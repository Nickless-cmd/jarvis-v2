"""Adaptive veto gate — pre-execution hook that pauses tool calls when pushback is firm.

When affective_pushback fires with action=firm_pushback AND there is
evidence (not just feeling), the veto gate can block execution and
surface a confirmation request to the user instead of blindly running
the tool.

This is the "muscle" behind pushback: pushback generates the signal,
veto_gate acts on it.

Design:
- Called from _execute_simple_tool_calls before each tool runs.
- Returns (allowed: bool, reason: str | None).
- If not allowed, the tool call is replaced with a veto message that
  surfaces in the chat as a confirmation card.
- Bjørn retains authority: vetoes can always be overridden by explicit
  user confirmation ("ja", "kør", "gør det").

**Adaptive layers (2026-05-18):**
1. Token-signal gate — consent markers override veto before pushback runs.
2. Veto event log — every veto decision + resolution logged to DB.
3. Adaptive thresholds — per (tool, feeling) override count adjusts sensitivity.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ── Layer 1: Token-signal gate ─────────────────────────────────────────────

# Consent/override markers — short explicit confirmations that should
# bypass the veto gate entirely. These are the words Bjørn uses to
# override a veto ("ja", "kør", "godkendt", etc.).
#
# 2026-05-22 (Claude): fixed `gaa det` → `gå det` typo. Original had
# `r'\bg(?:ør|aa) det\b'` which matched non-Danish "gaa det" but
# missed actual "gå det".
_OVERRIDE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r'^\s*(ja|kør|kør på|do it|go ahead|proceed)\s*\.?\s*$', re.IGNORECASE),
    re.compile(r'^\s*(godkendt|accepteret|approved|accept|ok|okay)\s*\.?\s*$', re.IGNORECASE),
    re.compile(r'\bg(?:ør|å) det\b', re.IGNORECASE),
)

# Negation markers — words that flip consent into refusal.
# When any of these appear before a consent token (within ~30 chars),
# the message is NOT a consent signal — it's a refusal/negation.
# 2026-05-22 (Claude): added because original implementation matched
# "ikke godkendt restart" as consent, a security bug that let users
# accidentally bypass veto by typing refusals.
_NEGATION_RE = re.compile(
    r'\b(ikke|aldrig|nej|stop|annull[eé]r|cancel|abort|nope|no)\b',
    re.IGNORECASE,
)

# Consent-in-context: when a consent word appears near a risk marker,
# the user is explicitly approving the risky operation — not commanding it.
# E.g. "godkendt restart" → consent, not risk.
_CONSENT_NEAR_RISK = re.compile(
    r'\b(godkendt|ja|kør|accepteret|approved|accept|ok)\b.{0,40}\b'
    r'(restart|deploy|merge|slet|delete|purge|force)\b',
    re.IGNORECASE,
)


def _is_negated(user_message: str, consent_start_idx: int) -> bool:
    """True if a negation word appears within ~30 chars BEFORE the consent token.

    Catches "ikke godkendt restart", "aldrig approved", "nej, kør restart" etc.
    Window is 30 chars (~5-6 words) — Danish negations cling close to the verb.
    """
    if consent_start_idx <= 0:
        return False
    window_start = max(0, consent_start_idx - 30)
    window = user_message[window_start:consent_start_idx]
    return bool(_NEGATION_RE.search(window))


def _check_token_signal_gate(user_message: str, tool_name: str) -> bool:
    """Check if user message contains explicit consent that overrides veto.

    Returns True if the message is a clear override signal.
    This runs BEFORE affective pushback, so the veto never fires at all.

    `tool_name` is accepted for future use (tool-specific consent rules)
    but currently the gate is tool-agnostic — explicit consent words
    override veto for any tool. This is intentional: when Bjørn types
    "godkendt", he means "yes, do the thing I just saw you ask about".
    """
    if not user_message:
        return False

    # Pure override: short consent messages ("ja", "kør", "godkendt")
    for pattern in _OVERRIDE_PATTERNS:
        m = pattern.search(user_message)
        if m and not _is_negated(user_message, m.start()):
            return True

    # Consent near risk marker: "godkendt restart" = explicit approval
    m = _CONSENT_NEAR_RISK.search(user_message)
    if m and not _is_negated(user_message, m.start()):
        return True

    return False


def _maybe_record_override_from_token_signal(tool_name: str) -> None:
    """If the token-signal gate detected an override pattern, check if there
    was a recent blocked veto for this tool and record the override.

    This closes the feedback loop: every "kør" or "ja" from the user
    raises the adaptive threshold for that (tool, feeling) pair.

    Time-window: 15 minutes. Older "pending" vetoes are not considered
    related to the current message — Bjørn typing "ja" today shouldn't
    override-credit a veto from last week. 2026-05-22 (Claude): added
    cutoff because the original query had no time bound, so an ancient
    pending veto would soak up every override signal indefinitely.
    """
    if not tool_name:
        return
    try:
        from datetime import timedelta
        from core.runtime.db_core import connect
        cutoff_iso = (datetime.now(UTC) - timedelta(minutes=15)).isoformat()
        with connect() as conn:
            rows = conn.execute(
                """SELECT event_id, feeling FROM veto_events
                   WHERE tool_name = ? AND veto_result = 'blocked'
                     AND resolution = 'pending'
                     AND created_at >= ?
                   ORDER BY id DESC LIMIT 1""",
                (tool_name, cutoff_iso),
            ).fetchall()
        for row in rows:
            event_id, feeling = row
            if feeling:
                record_override(tool_name, feeling)
            else:
                # No feeling recorded — still mark the event as overridden
                try:
                    with connect() as conn:
                        conn.execute(
                            "UPDATE veto_events SET resolution = 'overridden_by_user' WHERE event_id = ?",
                            (event_id,),
                        )
                except Exception:
                    pass
    except Exception:
        pass


# ── Layer 2: Veto event log ────────────────────────────────────────────────

_VETO_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS veto_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    tool_name TEXT NOT NULL,
    user_message_preview TEXT NOT NULL DEFAULT '',
    feeling TEXT NOT NULL DEFAULT '',
    intensity REAL NOT NULL DEFAULT 0.0,
    evidence_summary TEXT NOT NULL DEFAULT '',
    veto_result TEXT NOT NULL,  -- 'blocked', 'allowed', 'overridden'
    resolution TEXT NOT NULL DEFAULT 'pending',  -- 'overridden_by_user', 'honored', 'false_positive'
    override_count_before INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
)
"""


def _ensure_veto_events_table() -> None:
    """Ensure the veto_events table exists."""
    try:
        from core.runtime.db_core import connect
        with connect() as conn:
            conn.execute(_VETO_EVENTS_TABLE)
    except Exception:
        logger.exception("Failed to create veto_events table")


def log_veto_event(
    tool_name: str,
    user_message: str,
    feeling: str,
    intensity: float,
    evidence_summary: str,
    veto_result: str,  # 'blocked', 'allowed', 'overridden'
    resolution: str = 'pending',
) -> str:
    """Log a veto decision to the veto_events table.

    Returns event_id for reference.
    """
    event_id = f"veto-{uuid4().hex[:12]}"
    override_count = _get_override_count(tool_name, feeling)
    try:
        from core.runtime.db_core import connect
        with connect() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO veto_events
                   (event_id, tool_name, user_message_preview, feeling, intensity,
                    evidence_summary, veto_result, resolution, override_count_before, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event_id,
                    tool_name,
                    (user_message or "")[:200],
                    feeling,
                    round(intensity, 2),
                    evidence_summary[:300],
                    veto_result,
                    resolution,
                    override_count,
                    datetime.now(UTC).isoformat(),
                ),
            )
    except Exception:
        logger.exception("Failed to log veto event")
    return event_id


def resolve_veto_event(event_id: str, resolution: str) -> None:
    """Mark a veto event as resolved (overridden, honored, false_positive).

    2026-05-22 (Claude): wires the honored path into the adaptive
    threshold counter. When the user honors a veto ("ok, stop"), the
    threshold for that (tool, feeling) drops -0.02 per spec §B. This
    keeps the gate sensitive for combos that Bjørn actually wants
    blocked. Without this, the gate could only ever desensitize via
    override, never resensitize via honored.
    """
    try:
        from core.runtime.db_core import connect
        # Read tool_name + feeling before updating so we can bump the
        # honored counter for the correct combo.
        with connect() as conn:
            row = conn.execute(
                "SELECT tool_name, feeling FROM veto_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            conn.execute(
                "UPDATE veto_events SET resolution = ? WHERE event_id = ?",
                (resolution, event_id),
            )
        if row and resolution == "honored":
            tool_name = str(row[0] or "")
            feeling = str(row[1] or "")
            if tool_name and feeling:
                count = _increment_honored_count(tool_name, feeling)
                new_threshold = _adaptive_threshold(tool_name, feeling, 1.0)
                logger.info(
                    "Veto honored recorded for %s/%s: honored_count=%d, "
                    "new_threshold=%.2f",
                    tool_name, feeling, count, new_threshold,
                )
                _emit_veto_gate_event("honored_recorded", {
                    "tool_name": tool_name,
                    "feeling": feeling,
                    "honored_count": count,
                    "new_threshold": round(new_threshold, 2),
                })
    except Exception:
        logger.exception("Failed to resolve veto event")


def veto_event_stats(tool_name: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Read recent veto events for observability."""
    try:
        from core.runtime.db_core import connect
        with connect() as conn:
            if tool_name:
                rows = conn.execute(
                    """SELECT event_id, tool_name, feeling, intensity, veto_result,
                              resolution, override_count_before, created_at
                       FROM veto_events
                       WHERE tool_name = ?
                       ORDER BY id DESC LIMIT ?""",
                    (tool_name, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT event_id, tool_name, feeling, intensity, veto_result,
                              resolution, override_count_before, created_at
                       FROM veto_events
                       ORDER BY id DESC LIMIT ?""",
                    (limit,),
                ).fetchall()
            return [
                {
                    "event_id": r[0],
                    "tool_name": r[1],
                    "feeling": r[2],
                    "intensity": r[3],
                    "veto_result": r[4],
                    "resolution": r[5],
                    "override_count": r[6],
                    "created_at": r[7],
                }
                for r in rows
            ]
    except Exception:
        return []


# ── Layer 3: Adaptive thresholds ───────────────────────────────────────────
#
# 2026-05-22 (Claude): rewrite to match the spec
# docs/superpowers/specs/2026-05-18-adaptive-veto-gate.md §B.
#
# Original implementation used a single base (0.75) with a global per-
# (tool, feeling) override-count multiplier. Spec called for:
#   1. Per-tool, per-feeling base thresholds (restart/delete/default)
#   2. Override raises threshold by +0.05 (already correct)
#   3. Honored lowers threshold by -0.02 (was missing)
#   4. Clamp: min 0.30, max 0.98 (was [0, 1.0])
#
# A "honored" veto is one where the user accepted the block ("ok", "stop",
# "ja, du har ret") — the gate was correct, so reduce the threshold a
# bit so the same combo stays sensitive. An "overridden" veto is one
# where the user said "kør anyway" — the gate was a false positive, so
# raise the threshold to suppress it next time.

# Per (tool, feeling) base thresholds. Tool-specific entries take
# precedence; otherwise "default" applies. Higher value = harder to
# trigger (more frustrated user required before veto fires).
_BASE_THRESHOLDS: dict[str, dict[str, float]] = {
    "restart": {
        "irritation": 0.95,   # very hard — restart is rarely catastrophic
        "unease": 0.50,
        "fatigue": 0.60,
    },
    "delete": {
        "irritation": 0.70,   # easier — delete is irreversible
        "unease": 0.40,
        "fatigue": 0.50,
    },
    "default": {
        "irritation": 0.75,
        "unease": 0.50,
        "fatigue": 0.75,
    },
}

# Adjustment per outcome. Override = false positive, raise threshold.
# Honored = correct gate, lower threshold (resensitize).
_OVERRIDE_BUMP = 0.05
_HONORED_DAMPEN = 0.02

# Hard clamp per spec
_THRESHOLD_MIN = 0.30
_THRESHOLD_MAX = 0.98


# Storage for adaptive counters.
#
# 2026-05-22 (Claude): migrated from runtime_state_kv to a dedicated
# table after Bjørn's review. The KV approach worked, but a typed
# table gives:
#   - per-row audit (created_at, last_modified) instead of just upsert ts
#   - clean DELETE / inspection without grep'ing through KV
#   - explicit UNIQUE constraint on (tool, feeling, kind) preventing
#     duplicate counter rows
#   - matches the storage pattern used by veto_events
#
# Migration from legacy KV happens lazily on first ensure-call.
_VETO_ADAPTIVE_COUNTERS_TABLE = """
CREATE TABLE IF NOT EXISTS veto_adaptive_counters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    feeling TEXT NOT NULL,
    counter_kind TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    last_modified TEXT NOT NULL,
    UNIQUE(tool_name, feeling, counter_kind)
)
"""

_VETO_ADAPTIVE_COUNTERS_MIGRATED = False


def _ensure_veto_adaptive_counters_table() -> None:
    """Create the table if missing + migrate legacy KV entries once per process."""
    global _VETO_ADAPTIVE_COUNTERS_MIGRATED
    try:
        from core.runtime.db_core import connect
        with connect() as conn:
            conn.execute(_VETO_ADAPTIVE_COUNTERS_TABLE)
    except Exception:
        logger.exception("Failed to create veto_adaptive_counters table")
        return

    if _VETO_ADAPTIVE_COUNTERS_MIGRATED:
        return
    _VETO_ADAPTIVE_COUNTERS_MIGRATED = True
    # Lazy migration from runtime_state_kv. Old key format:
    #   veto_adaptive:<tool>:<feeling>:<kind>
    # Old value format: JSON-encoded string of int.
    try:
        import json as _json
        from core.runtime.db_core import connect
        now = datetime.now(UTC).isoformat()
        with connect() as conn:
            rows = conn.execute(
                "SELECT key, value_json FROM runtime_state_kv "
                "WHERE key LIKE 'veto_adaptive:%'"
            ).fetchall()
            migrated = 0
            for key, raw_value in rows:
                parts = key.split(":")
                # Expect 4 parts: 'veto_adaptive', tool, feeling, kind
                if len(parts) != 4:
                    continue
                _, tool, feeling, kind = parts
                if kind not in ("overrides", "honored"):
                    continue
                try:
                    decoded = _json.loads(raw_value) if raw_value else "0"
                    count = int(decoded) if decoded else 0
                except Exception:
                    count = 0
                conn.execute(
                    """INSERT OR IGNORE INTO veto_adaptive_counters
                       (tool_name, feeling, counter_kind, count, created_at, last_modified)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (tool, feeling, kind, count, now, now),
                )
                migrated += 1
            if migrated:
                logger.info(
                    "veto_adaptive_counters: migrated %d legacy KV entries", migrated
                )
    except Exception:
        logger.exception("veto_adaptive_counters: legacy migration failed")


def _adjust_counter(tool_name: str, feeling: str, kind: str, delta: int) -> int:
    """Read-modify-write a counter ("overrides" or "honored") in veto_adaptive_counters.

    Returns the new value. Always >= 0 (counters cannot go negative).
    """
    _ensure_veto_adaptive_counters_table()
    try:
        from core.runtime.db_core import connect
        now = datetime.now(UTC).isoformat()
        with connect() as conn:
            row = conn.execute(
                """SELECT count FROM veto_adaptive_counters
                   WHERE tool_name = ? AND feeling = ? AND counter_kind = ?""",
                (tool_name, feeling, kind),
            ).fetchone()
            current = int(row[0]) if row else 0
            new_value = max(0, current + delta)
            if row is None:
                conn.execute(
                    """INSERT INTO veto_adaptive_counters
                       (tool_name, feeling, counter_kind, count, created_at, last_modified)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (tool_name, feeling, kind, new_value, now, now),
                )
            else:
                conn.execute(
                    """UPDATE veto_adaptive_counters
                       SET count = ?, last_modified = ?
                       WHERE tool_name = ? AND feeling = ? AND counter_kind = ?""",
                    (new_value, now, tool_name, feeling, kind),
                )
            return new_value
    except Exception:
        logger.exception("_adjust_counter failed for %s/%s/%s", tool_name, feeling, kind)
        return 0


def _get_counter(tool_name: str, feeling: str, kind: str) -> int:
    """Read a counter without modification."""
    _ensure_veto_adaptive_counters_table()
    try:
        from core.runtime.db_core import connect
        with connect() as conn:
            row = conn.execute(
                """SELECT count FROM veto_adaptive_counters
                   WHERE tool_name = ? AND feeling = ? AND counter_kind = ?""",
                (tool_name, feeling, kind),
            ).fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return 0


# Public names kept for back-compat with existing callers.
def _get_override_count(tool_name: str, feeling: str) -> int:
    return _get_counter(tool_name, feeling, "overrides")


def _increment_override_count(tool_name: str, feeling: str) -> int:
    return _adjust_counter(tool_name, feeling, "overrides", +1)


def _get_honored_count(tool_name: str, feeling: str) -> int:
    return _get_counter(tool_name, feeling, "honored")


def _increment_honored_count(tool_name: str, feeling: str) -> int:
    return _adjust_counter(tool_name, feeling, "honored", +1)


def _base_threshold(tool_name: str, feeling: str) -> float:
    """Look up per-(tool, feeling) base from _BASE_THRESHOLDS.

    Falls through to "default" tool key, then to 0.75 if even that's missing.
    """
    tool_table = _BASE_THRESHOLDS.get(tool_name) or _BASE_THRESHOLDS["default"]
    return tool_table.get(feeling, _BASE_THRESHOLDS["default"].get(feeling, 0.75))


def _adaptive_threshold(tool_name: str, feeling: str, intensity: float) -> float:
    """Compute the effective veto threshold for this (tool, feeling) pair.

    base = per-(tool, feeling) value from _BASE_THRESHOLDS
    adjustment = (overrides * +0.05) - (honored * -0.02)
    clamped to [0.30, 0.98]
    """
    base = _base_threshold(tool_name, feeling)
    overrides = _get_override_count(tool_name, feeling)
    honored = _get_honored_count(tool_name, feeling)
    adjustment = (overrides * _OVERRIDE_BUMP) - (honored * _HONORED_DAMPEN)
    effective = base + adjustment
    return max(_THRESHOLD_MIN, min(_THRESHOLD_MAX, effective))


# ── Tools always allowed ───────────────────────────────────────────────────

_ALWAYS_ALLOWED_TOOLS = frozenset({
    "read_file", "read_tool_result", "read_self_docs", "search",
    "find_files", "web_fetch", "web_scrape", "web_search",
    "get_weather", "get_exchange_rate", "get_news", "wolfram_query",
    "analyze_image", "list_initiatives", "list_proposals",
    "list_scheduled_tasks", "list_plans", "todo_list", "monitor_list",
    "verification_status", "context_pressure", "context_size_check",
    "heartbeat_status", "daemon_status", "discord_status",
    "comfyui_status", "comfyui_objects", "health_status",
    "goal_list", "decision_list", "composite_list",
    "list_identity_pins", "read_visual_memory", "recall_sensory_memories",
    "recall_memories", "search_jarvis_brain", "search_memory",
    "memory_list_headings", "search_sessions", "provider_health_status",
    "tick_quality_summary", "detect_stale_goals", "decision_adherence_summary",
    "list_prompt_experiments", "list_agent_observations",
    "list_arcs", "list_crisis_markers", "list_recurring",
    "list_self_wakeups", "list_events",
    # Read-only git operations — observability into the repo, no mutation.
    "git_log", "git_diff", "git_status", "git_show",
    # bash — arbitrary shell exec. Owner-calibrated trust: Bjørn
    # explicitly enabled this 2026-05-03 ("han har haft det hele tiden").
    # Side effects are Jarvis's responsibility; veto_gate doesn't gate it.
    "bash",
})


def check_veto(
    tool_name: str,
    user_message: str = "",
    session_id: str | None = None,
) -> tuple[bool, str | None]:
    """Check if a tool call should be vetoed.

    Returns (allowed, reason). If allowed=True, proceed.
    If allowed=False, the tool call should be replaced with a
    veto message asking for confirmation.

    Logic (in order):
    1. Read-only tools are always allowed.
    2. Token-signal gate: if user message contains explicit consent → allow.
    3. Compute affective pushback for the user message.
    4. If pushback found, compute adaptive threshold for this (tool, feeling).
       Only veto if intensity exceeds the adaptive threshold.
    5. Log every veto decision to the veto_events table.
    6. Otherwise → allow.
    """
    # Step 1: Always-allow list
    if tool_name in _ALWAYS_ALLOWED_TOOLS:
        return True, None

    # Step 2: Token-signal gate — explicit consent overrides veto entirely
    _ensure_veto_events_table()
    if _check_token_signal_gate(user_message, tool_name):
        # If token-signal says allow, this might be a user override of a
        # recent veto. Record it so adaptive thresholds learn from it.
        _maybe_record_override_from_token_signal(tool_name)
        return True, None

    # Step 3: Read pushback state
    try:
        from core.services.pushback import affective_pushback_section
        section = affective_pushback_section(user_message)
    except Exception:
        return True, None

    if not section:
        return True, None

    # Parse the section to extract action, feeling, and evidence
    action = _extract_action(section)
    has_evidence = _has_evidence(section)
    feeling = _extract_feeling(section)
    intensity = _extract_intensity(section)

    if not has_evidence:
        return True, None

    # Step 4: Adaptive threshold check
    threshold = _adaptive_threshold(tool_name, feeling, intensity)
    # If intensity is 0.0 (missing/unset in pushback data), assume
    # it exceeds threshold — fail-closed for incomplete data.
    # Real pushback always includes an intensity value.
    below_threshold = (intensity > 0.0) and (intensity < threshold)

    if action == "firm_pushback" and has_evidence and not below_threshold:
        # Veto fired — log the event
        event_id = log_veto_event(
            tool_name=tool_name,
            user_message=user_message,
            feeling=feeling or "unknown",
            intensity=intensity,
            evidence_summary=_summarize_evidence(section),
            veto_result="blocked",
        )
        return False, _format_veto_reason(section, tool_name, event_id=event_id)

    if action in ("soft_pushback", "ask_or_check") and has_evidence:
        # Soft pushback or below threshold: allow but emit warning
        try:
            from core.eventbus.bus import event_bus
            event_bus.publish("veto_gate.soft_warning", {
                "tool_name": tool_name,
                "feeling": feeling,
                "intensity": intensity,
                "threshold": threshold,
                "pushback_section": section[:500],
            })
        except Exception:
            pass
        # Log as allowed
        log_veto_event(
            tool_name=tool_name,
            user_message=user_message,
            feeling=feeling or "unknown",
            intensity=intensity,
            evidence_summary=_summarize_evidence(section),
            veto_result="allowed",
        )
        return True, None

    # Only firm_pushback with evidence and above threshold gets blocked
    return True, None


def _extract_feeling(section: str) -> str:
    """Extract the feeling name from the pushback section."""
    for line in section.splitlines():
        if "feeling=" in line:
            for part in line.split():
                if part.startswith("feeling="):
                    return part.split("=", 1)[1].strip()
    return ""


def _extract_intensity(section: str) -> float:
    """Extract the intensity value from the pushback section."""
    for line in section.splitlines():
        if "intensity=" in line:
            for part in line.split():
                if part.startswith("intensity="):
                    try:
                        return float(part.split("=", 1)[1].strip())
                    except (ValueError, IndexError):
                        return 0.0
    return 0.0


def _summarize_evidence(section: str) -> str:
    """Extract a brief evidence summary from the pushback section."""
    lines = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped and "evidence:" in stripped and "weak/none" not in stripped:
            # Extract after "evidence:"
            idx = stripped.find("evidence:")
            if idx >= 0:
                lines.append(stripped[idx + len("evidence:"):].strip())
    return "; ".join(lines[:3]) if lines else ""


def _extract_action(section: str) -> str:
    """Extract the action tier from the pushback section text."""
    for line in section.splitlines():
        if "action=" in line:
            for part in line.split():
                if part.startswith("action="):
                    return part.split("=", 1)[1].strip()
    return ""


def _has_evidence(section: str) -> bool:
    """Check if the pushback section contains evidence markers."""
    return "evidence:" in section and "weak/none" not in section


def _format_veto_reason(section: str, tool_name: str, event_id: str = "") -> str:
    """Format a human-readable veto reason."""
    lines = section.strip().splitlines()
    # First line is the header, second is feeling, rest is evidence
    feeling_line = ""
    evidence_lines = []
    for line in lines:
        if "feeling=" in line:
            feeling_line = line.strip()
        elif "evidence:" in line and "weak/none" not in line:
            evidence_lines.append(line.strip())

    parts = [f"VETO: {tool_name} blokeret af affective pushback."]
    if feeling_line:
        parts.append(feeling_line)
    for e in evidence_lines[:2]:
        parts.append(e)
    # Add adaptive context
    feeling = _extract_feeling(section)
    intensity = _extract_intensity(section)
    if feeling:
        count = _get_override_count(tool_name, feeling)
        threshold = _adaptive_threshold(tool_name, feeling, intensity)
        parts.append(f"(adaptive: {count} overrides, threshold={threshold:.2f})")
    if event_id:
        parts.append(f"[event: {event_id}]")
    parts.append("Sig 'ja' eller 'kør' for at gennemtvinge alligevel.")
    return " | ".join(parts)


def build_veto_gate_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Reports adaptive gate state: active layers, recent events, thresholds.
    """
    try:
        recent_events = veto_event_stats(limit=5)
    except Exception:
        recent_events = []

    # Collect adaptive threshold summary for recently-blocked tools
    threshold_summary: dict[str, dict[str, float]] = {}
    for ev in recent_events:
        t = ev.get("tool_name", "")
        f = ev.get("feeling", "")
        if t and f and t not in threshold_summary:
            threshold_summary[t] = {
                "threshold": _adaptive_threshold(t, f, 1.0),
                "overrides": _get_override_count(t, f),
            }

    return {
        "active": True,
        "mode": "adaptive_veto_gate",
        "layers": ["token_signal_gate", "veto_event_log", "adaptive_thresholds"],
        "recent_events": recent_events,
        "adaptive_thresholds": threshold_summary,
        "summary": "3-layer adaptive veto gate active.",
        "authority": "derived-read-only",
    }


def record_override(tool_name: str, feeling: str) -> int:
    """Record that the user overrode a veto for this (tool, feeling) pair.

    This is called when the user says "kør" or "ja" to override a veto.
    Returns the new override count.
    """
    count = _increment_override_count(tool_name, feeling)
    threshold = _adaptive_threshold(tool_name, feeling, 1.0)
    logger.info(
        "Veto override recorded for %s/%s: count=%d, new_threshold=%.2f",
        tool_name, feeling, count, threshold,
    )
    # Re-resolve any pending veto events for this tool+feeling
    try:
        from core.runtime.db_core import connect
        with connect() as conn:
            conn.execute(
                """UPDATE veto_events SET resolution = 'overridden_by_user'
                   WHERE tool_name = ? AND feeling = ? AND resolution = 'pending'""",
                (tool_name, feeling),
            )
    except Exception:
        pass
    _emit_veto_gate_event("override_recorded", {
        "tool_name": tool_name,
        "feeling": feeling,
        "override_count": count,
        "new_threshold": round(threshold, 2),
    })
    return count


def _emit_veto_gate_event(kind: str, payload: dict[str, object] | None = None) -> None:
    """Emit a scoped event — defensive, never blocks caller.
    Cartographer scans for event_bus.publish() text.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            f"veto_gate.{kind}",
            payload or {},
        )
    except Exception:
        pass

