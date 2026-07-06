"""Ground-truth injection and freshness checking for context compaction.

Lag A: Collects verifiable facts (git SHA, commit log, key-file checks)
before compaction so the LLM doesn't have to guess whether something
exists or not.

Lag B: Stamps each compact marker with the git SHA at creation time,
enabling staleness detection without re-validation.

Usage:
    from core.context.compact_ground_truth import (
        collect_compact_ground_truth,
        format_ground_truth_block,
        get_current_git_sha,
        check_compact_marker_freshness,
    )

    # Before compaction:
    gt = collect_compact_ground_truth()
    prompt = format_ground_truth_block(gt) + original_prompt

    # After compaction, when storing marker:
    sha = get_current_git_sha()
    store_compact_marker(session_id, text, git_sha=sha)

    # Later, when reading marker:
    freshness = check_compact_marker_freshness(stored_sha)
"""
from __future__ import annotations

import logging
import subprocess
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REPO_DIR = Path("/media/projects/jarvis-v2")

# Key files to verify existence of — these are frequently claimed "missing"
# by compaction LLMs even when they're committed and live.
KEY_FILES: list[str] = [
    "core/runtime/db_credit_assignment.py",
    "core/services/chat_sessions.py",
    "core/services/heartbeat_runtime.py",
    "core/services/identity_composer.py",
    "core/context/auto_compact.py",
    "core/context/session_compact.py",
    "core/context/compact_llm.py",
    "core/context/run_compact.py",
    "core/tools/wake_word_tool.py",
    "core/tools/speak_tool.py",
    "core/tools/smart_compact_tools.py",
]


def get_current_git_sha() -> str:
    """Get the current git HEAD SHA of the Jarvis repo. Returns empty string on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=REPO_DIR, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception as exc:
        logger.warning("compact_ground_truth: git rev-parse failed: %s", exc)
        return ""


def get_commit_count_since(start_sha: str | None = None) -> int | None:
    """Count commits between start_sha and HEAD. Returns None if start_sha is empty or unknown."""
    if not start_sha:
        return None
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", f"{start_sha}..HEAD"],
            capture_output=True, text=True, cwd=REPO_DIR, timeout=5,
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
        return None
    except Exception:
        return None


def get_recent_commit_log(since: str | None = None, count: int = 30) -> str:
    """Get recent git log as oneline. Optionally since an ISO timestamp.

    Returns empty string on failure.
    """
    try:
        cmd = ["git", "log", "--oneline", f"-{count}"]
        if since:
            cmd.insert(2, f"--since={since}")
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=REPO_DIR, timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception as exc:
        logger.warning("compact_ground_truth: git log failed: %s", exc)
        return ""


def check_key_files(key_files: list[str] | None = None) -> dict[str, str]:
    """Check existence of key files. Returns dict of {relative_path: 'exists'|'missing'}."""
    checked = key_files or KEY_FILES
    result: dict[str, str] = {}
    for rel in checked:
        path = REPO_DIR / rel
        result[rel] = "exists" if path.exists() else "missing"
    return result


def check_cognitive_decisions_count() -> int | None:
    """Return count of cognitive_decision records in DB, or None on failure."""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM cognitive_decisions"
            ).fetchone()
            return int(row[0]) if row else None
    except Exception:
        return None


def collect_compact_ground_truth(session_id: str | None = None) -> dict[str, Any]:
    """Collect ground-truth data before compaction.

    Returns a dict with:
      - current_git_sha: str
      - recent_commits: str (git log --oneline -30)
      - key_files: dict[str, str]
      - cognitive_decisions_count: int | None
      - collected_at: str (ISO timestamp)

    If session_id is provided, also fetches session_created_at for
    `--since` filtering of git log.
    """
    sha = get_current_git_sha()

    # Try to get session timestamp for granular git log
    session_since: str | None = None
    if session_id:
        try:
            from core.services.chat_sessions import get_chat_session
            info = get_chat_session(session_id)
            if info and info.get("created_at"):
                session_since = info["created_at"]
        except Exception:
            pass

    return {
        "current_git_sha": sha,
        "recent_commits": get_recent_commit_log(since=session_since),
        "key_files": check_key_files(),
        "cognitive_decisions_count": check_cognitive_decisions_count(),
        "collected_at": datetime.now(UTC).isoformat(),
    }


def format_ground_truth_block(gt: dict[str, Any]) -> str:
    """Format a ground-truth dict into a human-readable block for prompt injection."""
    lines: list[str] = [
        "=== GROUND TRUTH (verifiable facts) ===",
        f"Current git HEAD: {gt.get('current_git_sha', '?')}",
        f"Collected at: {gt.get('collected_at', '?')}",
        "",
    ]

    commits = gt.get("recent_commits", "")
    if commits:
        lines.append(f"Commits (session-related):\n{commits}")
        lines.append("")

    files = gt.get("key_files", {})
    if files:
        lines.append("Key files:")
        for rel, status in sorted(files.items()):
            lines.append(f"  [{status.upper()}] {rel}")
        lines.append("")

    dec_count = gt.get("cognitive_decisions_count")
    if dec_count is not None:
        lines.append(f"cognitive_decisions records in DB: {dec_count}")
    else:
        lines.append("cognitive_decisions table: not accessible")

    lines.append("=== END GROUND TRUTH ===")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────
# Lag C: Post-compact validation — detect hallucinated claims
# ──────────────────────────────────────────────────────────────────────

HALLUCINATION_PATTERNS: list[tuple[str, str]] = [
    # (Danish_pattern, English_pattern)
    ("ikke implementeret", "not implemented"),
    ("mangler", "missing"),
    ("åbent", "open"),
    ("klar til design", "ready for design"),
    ("skal bygges", "needs to be built"),
    ("endnu ikke", "not yet"),
    ("venter på", "waiting for"),
    ("ikke påbegyndt", "not started"),
    ("findes ikke", "does not exist"),
    ("manglende", "lacking"),
]


def _parse_compact_claims(marker_text: str) -> list[dict[str, str]]:
    """Extract suspicious claims from a compact marker text.

    Returns a list of dicts with:
      - pattern: the matched pattern text
      - context: ~80 chars surrounding the match
      - claim_type: 'missing_file' | 'missing_feature' | 'unimplemented'
    """
    from core.context.token_estimate import estimate_tokens
    import re

    claims: list[dict[str, str]] = []
    lower_text = marker_text.lower()

    for da_pat, en_pat in HALLUCINATION_PATTERNS:
        # Try both patterns
        for pat in (da_pat, en_pat):
            if pat not in lower_text:
                continue
            # Find each occurrence
            start = 0
            while True:
                idx = lower_text.find(pat, start)
                if idx == -1:
                    break

                # Grab surrounding context (~80 chars)
                ctx_start = max(0, idx - 60)
                ctx_end = min(len(marker_text), idx + len(pat) + 60)
                context = marker_text[ctx_start:ctx_end].replace("\n", " ").strip()

                # Classify the claim type
                claim_type = "unimplemented"
                # Check if it mentions a file / code thing
                if any(w in context.lower() for w in
                       (".py", ".ts", ".js", ".md", "file", "modul", "service", "tool")):
                    claim_type = "missing_file"
                elif any(w in context.lower() for w in
                         ("funktion", "feature", "kommando", "command", "daemon")):
                    claim_type = "missing_feature"

                claims.append({
                    "pattern": pat,
                    "context": context[:120],
                    "claim_type": claim_type,
                })
                start = idx + 1

    # Deduplicate by (pattern, context_prefix) — same pattern + same context = duplicate
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for c in claims:
        key = f"{c['pattern']}|{c['context'][:60]}"
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def _check_claim_against_ground_truth(
    claim: dict[str, str],
    ground_truth: dict[str, Any],
) -> dict[str, Any]:
    """Check a single claim against ground truth. Returns verification result.

    Returns:
        {
            "pattern": str,
            "context": str,
            "verified_false": bool,   # True = claim contradicts ground truth
            "evidence": str,          # Why it's verified false
            "confidence": str,        # "high" | "medium" | "low"
        }
    """
    ctx = claim["context"]
    result = {
        "pattern": claim["pattern"],
        "context": ctx,
        "verified_false": False,
        "evidence": "",
        "confidence": "low",
    }

    # Check 1: Does any KEY_FILE name appear in the context next to a "missing" claim?
    for rel_path in (ground_truth.get("key_files") or {}):
        filename = rel_path.split("/")[-1]  # e.g. "db_credit_assignment.py"
        if filename.replace(".py", "") in ctx or filename.replace("_", " ") in ctx:
            actual_status = ground_truth["key_files"].get(rel_path, "unknown")
            if actual_status == "exists":
                result["verified_false"] = True
                result["evidence"] = (
                    f"Claim mentions '{filename}' as missing/unimplemented, "
                    f"but file exists at {rel_path}"
                )
                result["confidence"] = "high"
                return result
            elif actual_status == "missing":
                result["verified_false"] = False
                result["evidence"] = f"File {rel_path} is indeed missing"
                result["confidence"] = "high"
                return result

    # Check 2: Does the context match any commit message topic?
    commits = ground_truth.get("recent_commits", "")
    if commits:
        # Extract topic words from context (remove noise words)
        topic_words = [
            w for w in ctx.lower().split()
            if len(w) > 3 and w not in ("ikke", "med", "til", "det", "den", "der",
                                        "some", "thing", "this", "that", "with", "from")
        ]
        for word in topic_words:
            if word in commits.lower():
                result["verified_false"] = True
                result["evidence"] = (
                    f"Claim mentions '{word}' as unimplemented, but "
                    f"recent commits reference '{word}'"
                )
                result["confidence"] = "medium"
                return result

    # Check 3: Does it claim cognitive_decisions is missing when it exists?
    if claim["pattern"] in ("mangler", "missing", "findes ikke", "does not exist"):
        if "cognitive" in ctx.lower() or "beslutning" in ctx.lower():
            dec_count = ground_truth.get("cognitive_decisions_count")
            if dec_count is not None and dec_count > 0:
                result["verified_false"] = True
                result["evidence"] = (
                    f"Claim suggests cognitive_decisions is missing/unavailable, "
                    f"but DB has {dec_count} records"
                )
                result["confidence"] = "high"
                return result
            elif dec_count == 0:
                result["verified_false"] = False
                result["evidence"] = "cognitive_decisions table exists but is empty"
                result["confidence"] = "medium"
                return result

    return result


def _ensure_compaction_validation_table() -> None:
    """Create compaction_validation_failures table if it doesn't exist (Lag D prep)."""
    try:
        from core.runtime.db import connect as _connect
        with _connect() as _conn:
            _conn.execute(
                """
                CREATE TABLE IF NOT EXISTS compaction_validation_failures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    marker_id TEXT NOT NULL DEFAULT '',
                    failures_json TEXT NOT NULL DEFAULT '[]',
                    regenerated BOOLEAN NOT NULL DEFAULT 0,
                    new_marker_id TEXT NOT NULL DEFAULT '',
                    detected_at TEXT NOT NULL,
                    resolved_at TEXT
                )
                """
            )
    except Exception:
        pass


def _log_validation_failure(
    session_id: str,
    marker_id: str,
    failures: list[dict[str, Any]],
) -> int | None:
    """Log a validation failure to DB. Returns the row ID or None."""
    import json
    try:
        _ensure_compaction_validation_table()
        from core.runtime.db import connect as _connect
        with _connect() as _conn:
            _conn.execute(
                """
                INSERT INTO compaction_validation_failures
                    (session_id, marker_id, failures_json, detected_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    session_id,
                    marker_id,
                    json.dumps(failures, ensure_ascii=False),
                    datetime.now(UTC).isoformat(),
                ),
            )
            row_id = _conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        # Blind-spot #1 (6. jul): FØR landede fabrikeret-hukommelse-detektion KUN i denne
        # private tabel + logger.warning (som ikke engang rammer container-journalen) → Centralen
        # var blind for stille komprimerings-brud (roden til at auto-komprimering stoppede
        # ubemærket ~23. juni). Emit nu et METADATA-ONLY signal (§24.4: ingen rå claim/kontekst-
        # tekst — kun tællere) så Centralen ser når komprimering hallucinerer eller brydes.
        try:
            from core.eventbus.bus import event_bus
            _high = sum(1 for f in (failures or []) if (f or {}).get("confidence") == "high")
            event_bus.publish(
                "compaction.validation_failed",
                {
                    "session_id": session_id,
                    "marker_id": marker_id,
                    "failure_count": len(failures or []),
                    "high_confidence": _high,
                    "row_id": row_id,
                },
            )
        except Exception:
            pass
        return row_id
    except Exception as exc:
        logger.warning("compact_ground_truth: failed to log validation failure: %s", exc)
        return None


def validate_compact_marker(
    session_id: str,
    marker_text: str,
    marker_id: str = "",
    ground_truth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Post-compact validation of a compact marker against ground truth.

    Lag C: Parses the marker for hallucination patterns (claims that something
    is missing, not implemented, or open) and cross-references each against
    verifiable ground truth.

    If false claims are found, they're logged to the compaction_validation_failures
    table for later investigation and potential auto-regeneration.

    Returns a validation report dict:
        {
            "marker_id": str,
            "session_id": str,
            "checked_at": str (ISO),
            "total_suspicious_claims": int,
            "verified_false": int,          # claims that ARE hallucinated
            "verified_true": int,            # claims that are actually correct
            "inconclusive": int,             # can't verify either way
            "failures": [                    # only the verified_false ones
                { "pattern", "context", "evidence", "confidence" }
            ],
            "passed": bool,  # True if zero verified_false
            "logged": bool,   # True if failures were persisted to DB
        }
    """
    if not marker_text:
        return {
            "marker_id": marker_id,
            "session_id": session_id,
            "checked_at": datetime.now(UTC).isoformat(),
            "total_suspicious_claims": 0,
            "verified_false": 0,
            "verified_true": 0,
            "inconclusive": 0,
            "failures": [],
            "passed": True,
            "logged": False,
        }

    # Collect ground truth if not provided
    if ground_truth is None:
        ground_truth = collect_compact_ground_truth(session_id)

    # Parse claims
    claims = _parse_compact_claims(marker_text)

    # Check each claim
    verified_false: list[dict[str, Any]] = []
    verified_true_count = 0
    inconclusive_count = 0

    for claim in claims:
        result = _check_claim_against_ground_truth(claim, ground_truth)
        if result["verified_false"]:
            verified_false.append(result)
        elif result["confidence"] == "high":
            verified_true_count += 1
        else:
            inconclusive_count += 1

    # Log failures if any
    logged = False
    if verified_false:
        row_id = _log_validation_failure(session_id, marker_id, verified_false)
        logged = row_id is not None

    return {
        "marker_id": marker_id,
        "session_id": session_id,
        "checked_at": datetime.now(UTC).isoformat(),
        "total_suspicious_claims": len(claims),
        "verified_false": len(verified_false),
        "verified_true": verified_true_count,
        "inconclusive": inconclusive_count,
        "failures": verified_false,
        "passed": len(verified_false) == 0,
        "logged": logged,
    }


def auto_regenerate_compact_marker(
    session_id: str,
    original_marker_id: str = "",
) -> str | None:
    """Auto-regenerate a compact marker if post-compact validation failed.

    Injects the ground-truth block directly into the compaction prompt so the
    LLM has factual data and cannot hallucinate about missing files/features.

    Returns the new marker_id, or None on failure. If the original marker
    needs no correction, returns None without regenerating.
    """
    # Fetch current marker
    from core.services.chat_sessions import get_compact_marker_with_sha
    current_text, current_sha = get_compact_marker_with_sha(session_id)
    if not current_text:
        return None

    # Validate it first
    gt = collect_compact_ground_truth(session_id)
    report = validate_compact_marker(
        session_id, current_text,
        marker_id=original_marker_id,
        ground_truth=gt,
    )

    if report["passed"]:
        return None  # No correction needed

    logger.info(
        "auto_regenerate: session=%s has %d verified-false claims — regenerating",
        session_id, report["verified_false"],
    )

    # Build a corrected compact prompt with ground truth injected
    from core.context.compact_llm import call_compact_llm

    gt_block = format_ground_truth_block(gt)
    corrected_prompt = (
        ">>> CORRECTING PREVIOUS COMPACT MARKER\n"
        "The previous compact marker contained claims that contradict verifiable facts.\n"
        "Here are the verified facts — use them to produce an ACCURATE summary:\n\n"
        f"{gt_block}\n\n"
        "The previous (incorrect) marker was:\n"
        f"{current_text}\n\n"
        "---\n"
        "Rewrite the compact summary above, correcting any factual errors.\n"
        "Focus on actual session context. Be precise — don't speculate.\n"
        "Keep it under 300 words."
    )

    new_summary = call_compact_llm(corrected_prompt)
    if not new_summary or new_summary.startswith("[Kontekst komprimeret"):
        logger.warning("auto_regenerate: LLM returned fallback — keeping original")
        return None

    # Store the new marker
    from core.services.chat_sessions import store_compact_marker
    new_sha = get_current_git_sha()
    new_marker_id = store_compact_marker(session_id, new_summary, git_sha=new_sha)

    # Mark the original failure as resolved
    try:
        _ensure_compaction_validation_table()
        from core.runtime.db import connect as _connect
        with _connect() as _conn:
            _conn.execute(
                """
                UPDATE compaction_validation_failures
                SET regenerated = 1, new_marker_id = ?, resolved_at = ?
                WHERE session_id = ? AND marker_id = ? AND resolved_at IS NULL
                """,
                (new_marker_id, datetime.now(UTC).isoformat(), session_id, original_marker_id),
            )
    except Exception:
        pass

    logger.info(
        "auto_regenerate: session=%s regenerated marker %s",
        session_id, new_marker_id,
    )
    return new_marker_id


def get_validation_failures(session_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """Read recent compaction validation failures from DB.

    If session_id is given, filters to that session.
    Returns list of dicts sorted by detected_at DESC.
    """
    import json
    try:
        _ensure_compaction_validation_table()
        from core.runtime.db import connect as _connect
        with _connect() as _conn:
            if session_id:
                rows = _conn.execute(
                    """
                    SELECT * FROM compaction_validation_failures
                    WHERE session_id = ?
                    ORDER BY id DESC LIMIT ?
                    """,
                    (session_id, limit),
                ).fetchall()
            else:
                rows = _conn.execute(
                    """
                    SELECT * FROM compaction_validation_failures
                    ORDER BY id DESC LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [
            {
                "id": r["id"],
                "session_id": r["session_id"],
                "marker_id": r["marker_id"],
                "failures": json.loads(r["failures_json"]),
                "regenerated": bool(r["regenerated"]),
                "new_marker_id": r["new_marker_id"],
                "detected_at": r["detected_at"],
                "resolved_at": r["resolved_at"],
            }
            for r in rows
        ]
    except Exception as exc:
        logger.warning("compact_ground_truth: get_validation_failures failed: %s", exc)
        return []


def get_validation_failures_summary(session_id: str | None = None) -> dict[str, Any]:
    """Get a summary of validation failures for awareness / heartbeat."""
    failures = get_validation_failures(session_id)
    return {
        "total_failures": len(failures),
        "unresolved": sum(1 for f in failures if not f["resolved_at"]),
        "auto_regenerated": sum(1 for f in failures if f["regenerated"]),
        "latest": failures[0] if failures else None,
    }


def get_compact_marker_freshness(stored_sha: str | None) -> dict[str, Any]:
    """Check freshness of a stored compact marker against current git HEAD.

    Returns:
        {
            "stored_sha": str | None,
            "current_sha": str,
            "fresh": bool,          # True if SHAs match or stored_sha is empty
            "commits_since": int | None,   # None if can't compute
            "status": "fresh" | "stale" | "unknown",
        }
    """
    current = get_current_git_sha()
    if not stored_sha or not current:
        return {
            "stored_sha": stored_sha,
            "current_sha": current,
            "fresh": not stored_sha,  # no stored SHA = can't tell, treat as fresh
            "commits_since": None,
            "status": "unknown",
        }

    if stored_sha == current:
        return {
            "stored_sha": stored_sha,
            "current_sha": current,
            "fresh": True,
            "commits_since": 0,
            "status": "fresh",
        }

    commits = get_commit_count_since(stored_sha)
    return {
        "stored_sha": stored_sha,
        "current_sha": current,
        "fresh": False,
        "commits_since": commits,
        "status": "stale",
    }


# ──────────────────────────────────────────────────────────────────────
# Lag D: Self-healing compaction loop
# ──────────────────────────────────────────────────────────────────────

# Danish correction signal phrases — when the user says something like
# this while a compact marker claimed the opposite, it's a mismatch.
CORRECTION_SIGNAL_PHRASES: list[str] = [
    "det er da implementeret",
    "det findes allerede",
    "det virker",
    "det er bygget",
    "det har vi lavet",
    "det er lavet",
    "det er der",
    "det eksisterer",
    "det kører",
    "det er på plads",
    "allerede bygget",
    "allerede implementeret",
    "det er færdigt",
    "det er klar",
    "jo det gør",
    "det er ikke åbent",
    "det er ikke noget mangler",
    "det er ikke missing",
    "nej det er",
    "jo det er",
    "det er der jo",
]


def _extract_topic_words(text: str) -> set[str]:
    """Extract meaningful topic/noun words from a text, filtering noise."""
    import re

    noise: set[str] = {
        "det", "den", "til", "af", "at", "med", "fra", "på", "om",
        "er", "har", "var", "kan", "skal", "vil", "blev", "være",
        "the", "and", "for", "are", "has", "not", "but", "its",
        "bare", "lige", "også", "mere", "helt", "faktisk",
        "mangler", "missing", "implementeret", "implemented",
        "åbent", "open", "ikke", "not", "stadig", "still",
        "endnu", "yet", "bliver", "being", "været", "been",
        "blevet", "gøre", "do", "gør", "does", "gor",
        "din", "dit", "min", "mit", "jeg", "du", "han", "hun",
        "vi", "i", "de", "mig", "dig", "sig", "vores", "deres",
        "ja", "nej", "jo", "da", "bare", "godt", "fint", "ok",
    }

    words = re.findall(r'\b[a-zæøåA-ZÆØÅ]{3,}\b', text.lower())
    return {w for w in words if w not in noise}


def _check_user_message_against_marker(
    user_msg: str,
    marker_text: str,
    marker_failures: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Check if a user message corrects a compact marker's false claim.

    Returns a mismatch report dict if a correction is detected, or None.

    Report format:
        {
            "matched": True,
            "marker_topic_overlap": set[str],
            "failure_context": str | None,   # the specific failure context that matched
            "confidence": "high" | "medium",
        }
    """
    msg_lower = user_msg.lower()

    # Step 1: Check for correction signal phrases
    has_signal = any(phrase in msg_lower for phrase in CORRECTION_SIGNAL_PHRASES)
    if not has_signal:
        return None

    # Step 2: Extract topic words
    msg_words = _extract_topic_words(msg_lower)
    marker_words = _extract_topic_words(marker_text)
    overlap = msg_words & marker_words

    # Step 3: Cross-reference with known failures (high confidence match)
    if marker_failures:
        for failure in marker_failures:
            ctx = failure.get("context", "")
            ctx_words = _extract_topic_words(ctx)
            if msg_words & ctx_words:
                return {
                    "matched": True,
                    "marker_topic_overlap": overlap,
                    "failure_context": ctx[:120],
                    "confidence": "high",
                }

    # Step 4: Topic overlap alone (medium confidence)
    if overlap:
        return {
            "matched": True,
            "marker_topic_overlap": overlap,
            "failure_context": None,
            "confidence": "medium",
        }

    return None


def detect_compact_mismatch_in_chat(session_id: str) -> list[dict[str, Any]]:
    """Scan recent user messages for corrections contradicting the latest compact marker.

    Called during conversation to detect when the user implicitly corrects
    a hallucinated compact claim. If mismatches are found, auto-regeneration
    is triggered.

    Returns a list of mismatch reports (one per offending message).
    """
    from core.services.chat_sessions import get_compact_marker_with_sha, recent_chat_session_messages

    # Get latest marker
    marker_text, _marker_sha = get_compact_marker_with_sha(session_id)
    if not marker_text:
        return []

    # Get recent user messages (last 10)
    messages = recent_chat_session_messages(session_id, limit=10)
    user_msgs = [m for m in messages if m["role"] == "user"]

    # Get known failures for this session
    failures = get_validation_failures(session_id, limit=10)

    mismatches: list[dict[str, Any]] = []
    for msg in user_msgs:
        result = _check_user_message_against_marker(
            msg["content"], marker_text, failures,
        )
        if result:
            result["user_message"] = msg["content"][:200]
            mismatches.append(result)

    return mismatches


def resolve_stale_markers_on_load(session_id: str) -> str | None:
    """Boot-time check: auto-regenerate stale/unresolved compact markers.

    Called when a session loads. Checks:
      1. Are there unresolved validation failures for this session?
      2. Is the marker stale (commits since stored SHA)?

    If either is true, auto-regenerates the marker with ground truth injected.

    Returns the new marker_id if regeneration happened, None otherwise.
    """
    # Check unresolved failures
    failures = get_validation_failures(session_id, limit=5)
    unresolved = [f for f in failures if not f.get("resolved_at")]
    if not unresolved:
        return None  # no known failures — nothing to heal

    # Check freshness only if we have a stored SHA
    from core.services.chat_sessions import get_compact_marker_with_sha as _get_marker

    _text, _sha = _get_marker(session_id)
    if _sha:
        freshness = get_compact_marker_freshness(_sha)
        if freshness.get("fresh"):
            # Marker is fresh — no need to regenerate even if old failures exist
            # (they may have been superseded by a newer compaction)
            logger.debug(
                "resolve_stale: session=%s marker is fresh (SHA matches) — skipping",
                session_id,
            )
            return None

    # Auto-regenerate
    logger.info(
        "resolve_stale: session=%s has %d unresolved failures — auto-regenerating",
        session_id, len(unresolved),
    )
    # Find the marker_id of the most recent unresolved failure
    marker_id = unresolved[0].get("marker_id", "")
    return auto_regenerate_compact_marker(session_id, original_marker_id=marker_id)


def compact_healthcheck_daemon_tick() -> list[dict[str, Any]]:
    """Periodic healthcheck: scan all sessions with unresolved validation failures.

    Called by the heartbeat daemon (e.g. every 30 min). Iterates over all
    sessions that have unresolved compaction_validation_failures and attempts
    auto-regeneration.

    Returns a list of resolution reports.
    """
    attempts: list[dict[str, Any]] = []

    try:
        _ensure_compaction_validation_table()
        from core.runtime.db import connect as _connect

        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT session_id
                FROM compaction_validation_failures
                WHERE resolved_at IS NULL AND regenerated = 0
                """
            ).fetchall()
    except Exception as exc:
        logger.warning("compact_healthcheck: db query failed: %s", exc)
        return attempts

    for row in rows:
        session_id = str(row["session_id"])
        try:
            new_id = resolve_stale_markers_on_load(session_id)
            attempts.append({
                "session_id": session_id,
                "regenerated": new_id is not None,
                "new_marker_id": new_id or "",
                "checked_at": datetime.now(UTC).isoformat(),
            })
        except Exception as exc:
            logger.warning(
                "compact_healthcheck: failed to heal session %s: %s",
                session_id, exc,
            )
            attempts.append({
                "session_id": session_id,
                "regenerated": False,
                "error": str(exc),
                "checked_at": datetime.now(UTC).isoformat(),
            })

    if attempts:
        healed = sum(1 for a in attempts if a["regenerated"])
        logger.info(
            "compact_healthcheck: healed %d/%d sessions",
            healed, len(attempts),
        )

    return attempts
