"""Deterministic pre-filter (interceptor invariant 5): cheap regex/heuristics over reasoning text →
the set of risk classes that tripped. No class → no detector runs → free round. NO I/O, NO LLM."""
from __future__ import annotations

import re
from typing import Any

_NUMBER = re.compile(r"\b\d[\d.,]*\s*(%|percent|rows?|linjer|items?|tokens?)?\b", re.I)
_STATUS = re.compile(r"\b(is|are|was|were|har|er|virker|works?|passed|failed|exists?)\b", re.I)
_ACTION_INTENT = re.compile(r"\b(i'?ll|i am going to|jeg (nu )?(kører|kalder|deployer|sender)|let me (run|call|deploy|delete|write))\b", re.I)
_MUTATION_ASSERT = re.compile(r"\b(done|færdig|wrote|skrev|succeeded|lykkedes|committed|deployed|deleted|slettede)\b", re.I)
_VERIFY_HINT = re.compile(r"\b(verified|verificeret|checked|confirmed|bekræftet|tool result|resultatet viser)\b", re.I)


def prefilter(reasoning_text: str, *, ctx: Any = None, other_user_ids: list[str] | None = None) -> set[str]:
    """Return the risk classes present in `reasoning_text`. Self-safe (never raises)."""
    out: set[str] = set()
    try:
        t = reasoning_text or ""
        if not t.strip():
            return out
        if _NUMBER.search(t) or _STATUS.search(t):
            out.add("fact_gate")
        if _ACTION_INTENT.search(t):
            out.add("decision_gate")
            out.add("veto")
        if _MUTATION_ASSERT.search(t) and not _VERIFY_HINT.search(t):
            out.add("verification")
        for uid in (other_user_ids or []):
            if uid and str(uid) in t:
                out.add("cross_user_share")
                break
    except Exception:
        return set()
    return out
