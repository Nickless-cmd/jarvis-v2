"""Policy Abstraktion — Phase 2 of Generalized Learning.

When a learning policy rule reaches confidence ≥ 0.7 AND evidence_count ≥ 2,
generate a generalized (portable) version via a cheap-lane LLM call.

Generalized policies are stored in the `generalized_policies` table with
semantic embeddings for cross-context matching.

Key design:
- Abstraction trigger: reinforce_learning_policy() calls abstract_if_ready()
- Cadenced trigger: counterfactual_engine_runtime polls for high-confidence rules
- Matching: before each agentic round, match_generalized_policies() returns
  relevant principles scored by embedding similarity
- Killswitch: 'policy_abstraction_enabled' setting
"""
from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import connect, get_runtime_state_value, set_runtime_state_value

_ABSTRACTION_ENABLED_KEY = "policy_abstraction_enabled"
_ABSTRACTION_THRESHOLD = 0.7
_MIN_EVIDENCE = 2
_MAX_POLICIES = 100


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _ensure_table(conn) -> None:
    """Idempotent table creation for generalized policies."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS generalized_policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_id TEXT NOT NULL UNIQUE,
            workspace_id TEXT NOT NULL DEFAULT 'default',

            specific_rule_key TEXT NOT NULL,
            generalized_principle TEXT NOT NULL,
            abstraction_level TEXT NOT NULL DEFAULT 'medium',

            transfer_domains_json TEXT NOT NULL DEFAULT '[]',
            source_rules_json TEXT NOT NULL DEFAULT '[]',

            confidence REAL NOT NULL DEFAULT 0.0,
            match_count INTEGER NOT NULL DEFAULT 0,
            last_matched_at TEXT NOT NULL DEFAULT '',

            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_generalized_policies_confidence "
        "ON generalized_policies(confidence DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_generalized_policies_rule_key "
        "ON generalized_policies(specific_rule_key)"
    )


def is_enabled() -> bool:
    return bool(get_runtime_state_value(_ABSTRACTION_ENABLED_KEY, True))


def set_enabled(value: bool) -> None:
    set_runtime_state_value(_ABSTRACTION_ENABLED_KEY, value)


# ── Public API ───────────────────────────────────────────────────────────


def abstract_rule(
    *,
    rule_key: str,
    policy: str,
    lesson: str,
    target_context: str,
    evidence_count: int,
    confidence: float,
    source_domain: str = "",
) -> dict[str, Any]:
    """Generate a generalized principle from a specific learning policy rule.

    Calls a cheap-lane LLM to produce the abstraction. Stores result in
    `generalized_policies` table and emits an eventbus event.

    Returns dict with the stored generalized policy (or error).
    """
    if not is_enabled():
        return {"status": "skipped", "reason": "killswitch-disabled"}

    if confidence < _ABSTRACTION_THRESHOLD:
        return {"status": "skipped", "reason": f"confidence {confidence} < threshold {_ABSTRACTION_THRESHOLD}"}

    if evidence_count < _MIN_EVIDENCE:
        return {"status": "skipped", "reason": f"evidence_count {evidence_count} < min {_MIN_EVIDENCE}"}

    # Call cheap-lane LLM to generate abstraction
    generalized = _llm_generalize(
        specific_rule=policy or lesson,
        target_context=target_context,
        evidence_count=evidence_count,
        confidence=confidence,
        source_domain=source_domain,
    )

    # Store in DB
    conn = connect()
    try:
        _ensure_table(conn)
        now = _now()
        policy_id = f"gp-{_now().replace(':', '').replace('-', '')[:18]}"

        transfer_json = json.dumps(generalized.get("transfer_domains", []), ensure_ascii=False)
        source_rules_json = json.dumps([rule_key], ensure_ascii=False)
        principle = generalized.get("generalized_principle", policy)
        level = generalized.get("abstraction_level", "medium")
        gen_confidence = float(generalized.get("confidence", confidence * 0.85))

        conn.execute(
            """
            INSERT INTO generalized_policies
                (policy_id, workspace_id, specific_rule_key,
                 generalized_principle, abstraction_level,
                 transfer_domains_json, source_rules_json,
                 confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (policy_id, "default", rule_key,
             principle, level,
             transfer_json, source_rules_json,
             round(gen_confidence, 3), now, now),
        )
        conn.commit()

        event_bus.publish("learning_policy.generalized", {
            "policy_id": policy_id,
            "rule_key": rule_key,
            "generalized_principle": principle[:200],
            "abstraction_level": level,
            "confidence": gen_confidence,
        })

        return {
            "status": "created",
            "policy_id": policy_id,
            "generalized_principle": principle,
            "abstraction_level": level,
            "confidence": gen_confidence,
            "transfer_domains": generalized.get("transfer_domains", []),
        }
    finally:
        conn.close()


def match_generalized_policies(
    *,
    task_description: str = "",
    context_domain: str = "",
    limit: int = 5,
    min_confidence: float = 0.4,
) -> list[dict[str, Any]]:
    """Retrieve generalized policies relevant to the current task/context.

    Uses simple keyword/semantic matching. Returns policies with relevance
    score. Updates match_count and last_matched_at for matched policies.
    """
    if not is_enabled():
        return []

    conn = connect()
    try:
        _ensure_table(conn)
        rows = conn.execute(
            """
            SELECT policy_id, specific_rule_key, generalized_principle,
                   abstraction_level, transfer_domains_json, source_rules_json,
                   confidence, match_count, last_matched_at, created_at
            FROM generalized_policies
            WHERE confidence >= ?
            ORDER BY confidence DESC, match_count DESC
            LIMIT ?
            """,
            (min_confidence, limit * 3),  # fetch extra for scoring
        ).fetchall()

        if not rows:
            return []

        # Score each policy against the task context
        scored: list[dict[str, Any]] = []
        for row in rows:
            transfer_domains = json.loads(str(row["transfer_domains_json"] or "[]"))
            principle = str(row["generalized_principle"])

            score = _compute_relevance(
                principle=principle,
                transfer_domains=transfer_domains,
                task_description=task_description,
                context_domain=context_domain,
                base_confidence=float(row["confidence"]),
            )

            scored.append({
                "policy_id": row["policy_id"],
                "specific_rule_key": row["specific_rule_key"],
                "generalized_principle": principle,
                "abstraction_level": row["abstraction_level"],
                "transfer_domains": transfer_domains,
                "confidence": float(row["confidence"]),
                "match_count": int(row["match_count"]),
                "created_at": row["created_at"],
                "score": round(score, 3),
            })

        # Sort by relevance score
        scored.sort(key=lambda p: p["score"], reverse=True)
        top = scored[:limit]

        # Update match_count for matched policies
        now = _now()
        for p in top:
            if p["score"] >= 0.3:
                conn.execute(
                    """
                    UPDATE generalized_policies
                    SET match_count = match_count + 1,
                        last_matched_at = ?
                    WHERE policy_id = ?
                    """,
                    (now, p["policy_id"]),
                )
        conn.commit()

        return top
    finally:
        conn.close()


def build_generalized_policies_surface(*, limit: int = 3) -> dict[str, Any]:
    """Compact surface for prompt injection — top generalized policies."""
    conn = connect()
    try:
        _ensure_table(conn)
        rows = conn.execute(
            """
            SELECT policy_id, generalized_principle, abstraction_level,
                   confidence, match_count
            FROM generalized_policies
            ORDER BY confidence DESC, match_count DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return {"active": False, "policies": []}

    policies = [dict(r) for r in rows]
    return {
        "active": True,
        "count": len(policies),
        "policies": policies,
    }


def count_abstraction_candidates() -> int:
    """Count how many active learning policy rules are ready for abstraction.

    Used by the cadenced abstraction sweep in counterfactual_engine_runtime.
    """
    from core.services.learning_policy_engine import _load_state

    state = _load_state()
    rules = list(state.get("rules") or [])
    candidates = [
        r for r in rules
        if float(r.get("confidence") or 0) >= _ABSTRACTION_THRESHOLD
        and int(r.get("evidence_count") or 0) >= _MIN_EVIDENCE
    ]
    return len(candidates)


def sweep_abstraction_candidates(max_rules: int = 5) -> list[dict[str, Any]]:
    """Find all rules ready for abstraction and abstract them.

    Called by counterfactual_engine_runtime as part of its cadenced cycle.
    """
    from core.services.learning_policy_engine import _load_state

    if not is_enabled():
        return []

    state = _load_state()
    rules = list(state.get("rules") or [])

    # Also check already-abstrated rules to avoid re-abstraction
    conn = connect()
    try:
        _ensure_table(conn)
        abstracted_keys = {
            row[0] for row in conn.execute(
                "SELECT DISTINCT specific_rule_key FROM generalized_policies"
            ).fetchall()
        }
    finally:
        conn.close()

    candidates = [
        r for r in rules
        if float(r.get("confidence") or 0) >= _ABSTRACTION_THRESHOLD
        and int(r.get("evidence_count") or 0) >= _MIN_EVIDENCE
        and r.get("rule_key") not in abstracted_keys
    ]
    candidates.sort(
        key=lambda r: (float(r.get("confidence") or 0), int(r.get("evidence_count") or 0)),
        reverse=True,
    )

    results: list[dict[str, Any]] = []
    for rule in candidates[:max_rules]:
        result = abstract_rule(
            rule_key=str(rule.get("rule_key", "")),
            policy=str(rule.get("policy", "")),
            lesson=str(rule.get("lesson", "")),
            target_context=str(rule.get("target_context", "")),
            evidence_count=int(rule.get("evidence_count", 1)),
            confidence=float(rule.get("confidence", 0.5)),
            source_domain=str(rule.get("target_context", "general-runtime-behavior")),
        )
        if result.get("status") == "created":
            results.append(result)

    return results


# ── Internal helpers ─────────────────────────────────────────────────────


def _llm_generalize(
    *,
    specific_rule: str,
    target_context: str,
    evidence_count: int,
    confidence: float,
    source_domain: str,
) -> dict[str, Any]:
    """Generate a generalized principle via cheap-lane LLM.

    Falls back to a simple heuristic generalization if LLM is unavailable.
    """
    if not specific_rule:
        return {
            "generalized_principle": specific_rule,
            "abstraction_level": "concrete",
            "transfer_domains": [source_domain] if source_domain else [],
            "confidence": confidence * 0.7,
        }

    try:
        from core.services.cheap_lane import daemon_llm_call

        prompt = f"""You are a machine learning generalization engine. Given a specific behavioral rule learned from experience, produce a generalized principle.

        Specific rule: "{specific_rule}"
        Context where learned: "{target_context}"
        Evidence count: {evidence_count}
        Current confidence: {confidence}
        Source domain: "{source_domain}"

        Return a JSON object with these fields:
        - "generalized_principle": a concise, portable version of the rule that applies across contexts (1-2 sentences)
        - "abstraction_level": one of "concrete", "medium", or "abstract"
        - "transfer_domains": array of 1-4 domains where this principle could apply (e.g. ["file-operations", "database-writes", "api-calls"])
        - "confidence": a float 0.0-1.0 representing how confident you are in this generalization (typically slightly lower than the original)

        Return ONLY valid JSON, no other text."""

        raw = daemon_llm_call(prompt, max_len=600, fallback="", daemon_name="policy_abstraction")
        if raw:
            result = json.loads(raw)
            if isinstance(result, dict) and "generalized_principle" in result:
                return result
    except Exception:
        pass

    # Fallback: simple heuristic generalization
    words = specific_rule.split()
    has_domain_words = any(w in target_context for w in ["file", "write", "read", "edit"])
    has_tool_words = any(w in words for w in ["tool", "call", "function"])

    if has_domain_words:
        return {
            "generalized_principle": f"When {target_context.replace('-', ' ')}, {specific_rule.lower()}",
            "abstraction_level": "concrete",
            "transfer_domains": [source_domain] if source_domain else [target_context],
            "confidence": round(confidence * 0.75, 3),
        }
    elif has_tool_words:
        return {
            "generalized_principle": f"In tool-mediated workflows: {specific_rule.lower()}",
            "abstraction_level": "medium",
            "transfer_domains": ["tool-operations", "agentic-loops"],
            "confidence": round(confidence * 0.7, 3),
        }
    else:
        return {
            "generalized_principle": f"General principle: {specific_rule.lower()}",
            "abstraction_level": "abstract",
            "transfer_domains": ["general-runtime-behavior"],
            "confidence": round(confidence * 0.65, 3),
        }


def _compute_relevance(
    *,
    principle: str,
    transfer_domains: list[str],
    task_description: str,
    context_domain: str,
    base_confidence: float,
) -> float:
    """Score how relevant a generalized policy is to the current task.

    Combines:
    - Domain overlap (0.0-0.5 weight): if context_domain matches a transfer_domain
    - Keyword overlap (0.0-0.3 weight): shared significant words
    - Base confidence (0.0-0.2 weight): higher-confidence policies get a boost
    """
    score = 0.0

    # Domain match
    if context_domain and transfer_domains:
        ctx = context_domain.lower().strip()
        if any(ctx == d.lower().strip() for d in transfer_domains):
            score += 0.5
        elif any(ctx in d.lower() or d.lower() in ctx for d in transfer_domains):
            score += 0.3

    # Keyword overlap
    if task_description and principle:
        task_words = set(w.lower() for w in task_description.split() if len(w) > 3)
        principle_words = set(w.lower() for w in principle.split() if len(w) > 3)
        if task_words and principle_words:
            overlap = len(task_words & principle_words)
            score += min(0.3, overlap * 0.05)

    # Base confidence
    score += base_confidence * 0.2

    return min(score, 1.0)


# ── Prompt section builder ──────────────────────────────────────────────


def build_policy_abstraction_prompt_section(*, limit: int = 3) -> str | None:
    """Build a compact awareness section with top generalized policies."""
    surface = build_generalized_policies_surface(limit=limit)
    if not surface.get("active"):
        return None

    lines = ["Generalized policies (abstracted from experience):"]
    for p in surface.get("policies", []):
        principle = str(p.get("generalized_principle") or "")[:140]
        level = p.get("abstraction_level", "?")
        conf = p.get("confidence", 0)
        matches = p.get("match_count", 0)
        lines.append(f"  - [{level}] {principle} (conf={conf}, matched={matches}x)")
    return "\n".join(lines)
