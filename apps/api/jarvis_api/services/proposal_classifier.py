"""Proposal classifier — detects action impulses in thought fragments and scores destructiveness."""
from __future__ import annotations

import re

# Danish + English patterns that signal an action impulse
_ACTION_PATTERNS = [
    r"\bvil\s+gerne\b",
    r"\blyst\s+til\s+at\b",
    r"\bburde\s+(?:måske\s+)?(?:jeg\s+)?",
    r"\bhvad\s+hvis\s+jeg\b",
    r"\bkunne\s+(?:måske\s+)?prøve\s+at\b",
    r"\bvil\s+undersøge\b",
    r"\btænker\s+på\s+at\b",
    r"\bprøve\s+at\b",
    r"\bgå\s+i\s+gang\s+med\b",
    r"\bi\s+could\b",
    r"\bi\s+want\s+to\b",
    r"\bi\s+should\b",
    r"\bmaybe\s+(?:i\s+could\s+)?try\b",
    r"\bwould\s+be\s+interesting\s+to\b",
    r"\bI\s+might\b",
]

# Keywords that indicate a destructive/irreversible action
_DESTRUCTIVE_PATTERNS = [
    r"\bslet\b",
    r"\bfjern\b",
    r"\boverskriv\b",
    r"\bnulstil\b",
    r"\breset\b",
    r"\bdrop\b",
    r"\btruncate\b",
    r"\bdelete\b",
    r"\bremove\b",
    r"\berase\b",
    r"\bwipe\b",
    r"\bpurge\b",
    r"\bpush\b",
    r"\bdeploy\b",
    r"\bformat\b",
    r"\brydde\s+op\b",
    r"\bslette\b",
    r"\bfjerne\b",
]

# Brief label for what kind of action the pattern implies
_ACTION_LABELS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bundersøge\b|\bresearch\b|\blook\s+into\b", re.I), "research"),
    (re.compile(r"\bspørge\s+brugeren\b|\bask\s+the\s+user\b|\bask\s+user\b", re.I), "spørg bruger"),
    (re.compile(r"\bskrive\b|\bwrite\b|\bnote\b", re.I), "skriv"),
    (re.compile(r"\brefaktor\b|\brefactor\b|\brydde\s+op\b|\bclean\s+up\b", re.I), "refaktor/oprydning"),
    (re.compile(r"\bslet\b|\bfjern\b|\bdelete\b|\bremove\b|\berase\b", re.I), "slet/fjern"),
    (re.compile(r"\bpush\b|\bdeploy\b", re.I), "deploy/push"),
    (re.compile(r"\bprøve\b|\btest\b|\btry\b", re.I), "forsøg"),
]


def classify_fragment(fragment: str) -> dict:
    """
    Classify a thought fragment for action impulses.

    Returns:
        has_action (bool): whether an action impulse was detected
        action_description (str): brief label for the implied action
        destructive_score (float): 0.0–1.0, higher = more destructive/irreversible
        proposal_type (str): "non_destructive" | "needs_approval"
        destructive_reason (str): which destructive keyword matched, or ""
    """
    text_lower = fragment.lower()

    # Check for action language
    has_action = any(
        re.search(pat, text_lower)
        for pat in _ACTION_PATTERNS
    )

    if not has_action:
        return {
            "has_action": False,
            "action_description": "",
            "destructive_score": 0.0,
            "proposal_type": "non_destructive",
            "destructive_reason": "",
        }

    # Derive action label
    action_description = "uspecificeret handling"
    for pattern, label in _ACTION_LABELS:
        if pattern.search(fragment):
            action_description = label
            break

    # Score destructiveness
    destructive_reason = ""
    destructive_score = 0.0
    for pat in _DESTRUCTIVE_PATTERNS:
        m = re.search(pat, text_lower)
        if m:
            destructive_score = 0.8
            destructive_reason = m.group(0).strip()
            break

    proposal_type = "needs_approval" if destructive_score >= 0.5 else "non_destructive"

    return {
        "has_action": True,
        "action_description": action_description,
        "destructive_score": destructive_score,
        "proposal_type": proposal_type,
        "destructive_reason": destructive_reason,
    }
