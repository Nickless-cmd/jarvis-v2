# Thought-to-Action Proposals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Jarvis' thought stream generate action proposals — non-destructive proposals surface immediately in MC, destructive ones require explicit user approval before anything happens.

**Architecture:** Two new Python modules. `proposal_classifier.py` is a pure function that detects action impulses in Danish/English text and scores their destructiveness using pattern matching. `thought_action_proposal_daemon.py` holds module-level proposal state (pending queue, resolved history), receives fragments from the heartbeat, classifies them, and exposes a resolve endpoint. MC gets two new HTTP endpoints (GET list + POST resolve) and OperationsTab gets a `ThoughtProposalsPanel` above the existing AutonomyProposalsPanel.

**Tech Stack:** Python 3.11+, FastAPI, re (stdlib), React, lucide-react.

---

## File Map

| File | Action |
|------|--------|
| `apps/api/jarvis_api/services/proposal_classifier.py` | Create |
| `apps/api/jarvis_api/services/thought_action_proposal_daemon.py` | Create |
| `tests/test_proposal_classifier.py` | Create |
| `tests/test_thought_action_proposal_daemon.py` | Create |
| `core/eventbus/events.py` | Modify — add `"thought_action_proposal"` |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Modify — inject after thought_stream block (line 1766) |
| `apps/api/jarvis_api/routes/mission_control.py` | Modify — add GET + POST endpoints |
| `apps/ui/src/lib/adapters.js` | Modify — normalize + fetch + return |
| `apps/ui/src/components/mission-control/OperationsTab.jsx` | Modify — add ThoughtProposalsPanel |

---

## Task 1: proposal_classifier.py (TDD)

**Files:**
- Create: `apps/api/jarvis_api/services/proposal_classifier.py`
- Create: `tests/test_proposal_classifier.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_proposal_classifier.py`:

```python
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.api.jarvis_api.services.proposal_classifier import classify_fragment


def test_no_action_in_plain_fragment():
    """Fragment without action language returns has_action=False."""
    result = classify_fragment("Mørket udenfor er stille. Lyset er slukket.")
    assert result["has_action"] is False


def test_detects_danish_action_language():
    """Fragment with 'vil gerne' triggers action detection."""
    result = classify_fragment("Det er interessant — jeg vil gerne undersøge hvad brugeren tænker om det.")
    assert result["has_action"] is True
    assert result["action_description"] != ""


def test_detects_english_action_language():
    """Fragment with 'I could' triggers action detection."""
    result = classify_fragment("This feels incomplete. I could look into it more deeply.")
    assert result["has_action"] is True


def test_non_destructive_score_below_threshold():
    """Research/ask actions score below 0.5 destructive."""
    result = classify_fragment("Lyst til at spørge brugeren om hans mening om det her emne.")
    assert result["has_action"] is True
    assert result["destructive_score"] < 0.5
    assert result["proposal_type"] == "non_destructive"


def test_destructive_keywords_raise_score():
    """Fragment mentioning deletion scores above 0.5."""
    result = classify_fragment("Måske burde jeg slette de gamle logfiler og rydde op.")
    assert result["has_action"] is True
    assert result["destructive_score"] >= 0.5
    assert result["proposal_type"] == "needs_approval"


def test_destructive_english_keywords():
    """Fragment mentioning 'delete' scores above 0.5."""
    result = classify_fragment("I want to delete the old cache files to free up space.")
    assert result["has_action"] is True
    assert result["destructive_score"] >= 0.5
    assert result["proposal_type"] == "needs_approval"


def test_action_description_is_non_empty_when_action_found():
    """When has_action is True, action_description must be a non-empty string."""
    result = classify_fragment("Jeg vil gerne prøve at skrive en note om det her.")
    assert result["has_action"] is True
    assert isinstance(result["action_description"], str)
    assert len(result["action_description"]) > 0


def test_result_keys_always_present():
    """classify_fragment always returns all required keys."""
    result = classify_fragment("Bare en tanke om ingenting.")
    assert set(result.keys()) >= {"has_action", "action_description", "destructive_score", "proposal_type", "destructive_reason"}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && pytest tests/test_proposal_classifier.py -v
```

Expected: `ModuleNotFoundError: No module named 'apps.api.jarvis_api.services.proposal_classifier'`

- [ ] **Step 3: Implement proposal_classifier.py**

Create `apps/api/jarvis_api/services/proposal_classifier.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && pytest tests/test_proposal_classifier.py -v
```

Expected: 8/8 PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/proposal_classifier.py tests/test_proposal_classifier.py
git commit -m "feat: add proposal_classifier for detecting action impulses in thought fragments"
```

---

## Task 2: thought_action_proposal_daemon.py (TDD)

**Files:**
- Create: `apps/api/jarvis_api/services/thought_action_proposal_daemon.py`
- Create: `tests/test_thought_action_proposal_daemon.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_thought_action_proposal_daemon.py`:

```python
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
import apps.api.jarvis_api.services.thought_action_proposal_daemon as tap


def _reset():
    tap._pending_proposals.clear()
    tap._resolved_proposals.clear()
    tap._last_classified_fragment = ""


def test_no_proposal_for_non_action_fragment():
    """Fragment without action language produces no proposal."""
    _reset()
    with patch("apps.api.jarvis_api.services.thought_action_proposal_daemon.classify_fragment",
               return_value={"has_action": False, "action_description": "", "destructive_score": 0.0,
                             "proposal_type": "non_destructive", "destructive_reason": ""}):
        result = tap.tick_thought_action_proposal_daemon("Bare en rolig tanke.")
    assert result["generated"] is False
    assert len(tap._pending_proposals) == 0


def test_proposal_created_for_action_fragment():
    """Fragment with action language creates a pending proposal."""
    _reset()
    with patch("apps.api.jarvis_api.services.thought_action_proposal_daemon.classify_fragment",
               return_value={"has_action": True, "action_description": "research",
                             "destructive_score": 0.0, "proposal_type": "non_destructive",
                             "destructive_reason": ""}):
        result = tap.tick_thought_action_proposal_daemon("Vil gerne undersøge det nærmere.")
    assert result["generated"] is True
    assert len(tap._pending_proposals) == 1
    assert tap._pending_proposals[0]["status"] == "pending"
    assert tap._pending_proposals[0]["proposal_type"] == "non_destructive"


def test_same_fragment_not_classified_twice():
    """Identical fragment is not re-classified if already processed."""
    _reset()
    fragment = "Vil gerne undersøge det."
    tap._last_classified_fragment = fragment
    with patch("apps.api.jarvis_api.services.thought_action_proposal_daemon.classify_fragment") as mock_cls:
        tap.tick_thought_action_proposal_daemon(fragment)
    mock_cls.assert_not_called()


def test_pending_proposals_capped_at_10():
    """Pending proposal queue is capped at 10 items."""
    _reset()
    tap._pending_proposals[:] = [
        {"id": f"p{i}", "fragment_excerpt": "x", "action_description": "research",
         "proposal_type": "non_destructive", "status": "pending", "created_at": "2026-01-01T00:00:00"}
        for i in range(10)
    ]
    with patch("apps.api.jarvis_api.services.thought_action_proposal_daemon.classify_fragment",
               return_value={"has_action": True, "action_description": "research",
                             "destructive_score": 0.0, "proposal_type": "non_destructive",
                             "destructive_reason": ""}):
        tap.tick_thought_action_proposal_daemon("En ny handling.")
    assert len(tap._pending_proposals) == 10


def test_resolve_proposal_approve():
    """Approving a proposal moves it from pending to resolved."""
    _reset()
    tap._pending_proposals.append({
        "id": "test-id-1",
        "fragment_excerpt": "Vil gerne undersøge.",
        "action_description": "research",
        "proposal_type": "non_destructive",
        "status": "pending",
        "created_at": "2026-01-01T00:00:00",
    })
    result = tap.resolve_proposal("test-id-1", "approved")
    assert result is True
    assert len(tap._pending_proposals) == 0
    assert tap._resolved_proposals[0]["status"] == "approved"


def test_resolve_proposal_dismiss():
    """Dismissing a proposal moves it from pending to resolved with dismissed status."""
    _reset()
    tap._pending_proposals.append({
        "id": "test-id-2",
        "fragment_excerpt": "Slet de gamle filer.",
        "action_description": "slet/fjern",
        "proposal_type": "needs_approval",
        "status": "pending",
        "created_at": "2026-01-01T00:00:00",
    })
    result = tap.resolve_proposal("test-id-2", "dismissed")
    assert result is True
    assert tap._resolved_proposals[0]["status"] == "dismissed"


def test_resolve_unknown_id_returns_false():
    """Resolving a non-existent proposal ID returns False."""
    _reset()
    result = tap.resolve_proposal("nonexistent", "approved")
    assert result is False


def test_build_surface_structure():
    """build_proposal_surface returns expected keys."""
    _reset()
    surface = tap.build_proposal_surface()
    assert "pending_proposals" in surface
    assert "resolved_proposals" in surface
    assert "pending_count" in surface
    assert "needs_approval_count" in surface
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && pytest tests/test_thought_action_proposal_daemon.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement thought_action_proposal_daemon.py**

Create `apps/api/jarvis_api/services/thought_action_proposal_daemon.py`:

```python
"""Thought-action proposal daemon — turns action impulses in thought stream into MC proposals."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from apps.api.jarvis_api.services.proposal_classifier import classify_fragment

_MAX_PENDING = 10
_MAX_RESOLVED = 20

_pending_proposals: list[dict] = []
_resolved_proposals: list[dict] = []
_last_classified_fragment: str = ""


def tick_thought_action_proposal_daemon(fragment: str) -> dict[str, object]:
    """Classify fragment and create a proposal if an action impulse is detected."""
    global _last_classified_fragment

    if not fragment or fragment == _last_classified_fragment:
        return {"generated": False}

    _last_classified_fragment = fragment
    classification = classify_fragment(fragment)

    if not classification["has_action"]:
        return {"generated": False}

    # Drop if pending queue is full
    pending_non_approval = [p for p in _pending_proposals if p["proposal_type"] == "non_destructive"]
    pending_approval = [p for p in _pending_proposals if p["proposal_type"] == "needs_approval"]

    # Hard cap: never exceed _MAX_PENDING total
    if len(_pending_proposals) >= _MAX_PENDING:
        return {"generated": False}

    proposal = {
        "id": f"tap-{uuid4().hex[:12]}",
        "fragment_excerpt": fragment[:120],
        "action_description": classification["action_description"],
        "proposal_type": classification["proposal_type"],
        "destructive_score": classification["destructive_score"],
        "destructive_reason": classification["destructive_reason"],
        "status": "pending",
        "created_at": datetime.now(UTC).isoformat(),
    }
    _pending_proposals.append(proposal)

    try:
        insert_private_brain_record(
            record_id=f"pb-tap-{uuid4().hex[:12]}",
            record_type="thought-action-proposal",
            layer="private_brain",
            session_id="",
            run_id=f"tap-daemon-{uuid4().hex[:12]}",
            focus="handlingsimpuls",
            summary=classification["action_description"],
            detail=f"fragment={fragment[:80]} type={classification['proposal_type']}",
            source_signals="thought-action-proposal-daemon:heartbeat",
            confidence="low",
            created_at=proposal["created_at"],
        )
    except Exception:
        pass

    try:
        event_bus.publish(
            "thought_action_proposal.created",
            {
                "proposal_id": proposal["id"],
                "proposal_type": proposal["proposal_type"],
                "action_description": proposal["action_description"],
            },
        )
    except Exception:
        pass

    return {"generated": True, "proposal": proposal}


def resolve_proposal(proposal_id: str, decision: str) -> bool:
    """Move a proposal from pending to resolved. decision: 'approved' | 'dismissed'."""
    global _pending_proposals, _resolved_proposals

    for i, p in enumerate(_pending_proposals):
        if p["id"] == proposal_id:
            resolved = {**p, "status": decision, "resolved_at": datetime.now(UTC).isoformat()}
            _pending_proposals.pop(i)
            _resolved_proposals.insert(0, resolved)
            if len(_resolved_proposals) > _MAX_RESOLVED:
                _resolved_proposals = _resolved_proposals[:_MAX_RESOLVED]
            try:
                event_bus.publish(
                    "thought_action_proposal.resolved",
                    {"proposal_id": proposal_id, "decision": decision},
                )
            except Exception:
                pass
            return True

    return False


def get_pending_proposals() -> list[dict]:
    return list(_pending_proposals)


def build_proposal_surface() -> dict:
    return {
        "pending_proposals": list(_pending_proposals),
        "resolved_proposals": _resolved_proposals[:10],
        "pending_count": len(_pending_proposals),
        "needs_approval_count": sum(
            1 for p in _pending_proposals if p["proposal_type"] == "needs_approval"
        ),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && pytest tests/test_thought_action_proposal_daemon.py -v
```

Expected: 8/8 PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/thought_action_proposal_daemon.py tests/test_thought_action_proposal_daemon.py
git commit -m "feat: add thought_action_proposal_daemon — turns thought impulses into MC proposals"
```

---

## Task 3: Backend integration

**Files:**
- Modify: `core/eventbus/events.py`
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py` (after line 1766)
- Modify: `apps/api/jarvis_api/routes/mission_control.py`

- [ ] **Step 1: Add eventbus family**

In `core/eventbus/events.py`, add `"thought_action_proposal"` after `"thought_stream"`:

```python
    "thought_stream",
    "thought_action_proposal",
```

- [ ] **Step 2: Add heartbeat injection**

In `apps/api/jarvis_api/services/heartbeat_runtime.py`, after the thought-stream block (after the `except Exception: pass` at line 1766), add:

```python
    # Thought-action proposals
    try:
        from apps.api.jarvis_api.services.thought_action_proposal_daemon import (
            tick_thought_action_proposal_daemon,
            get_pending_proposals,
        )
        from apps.api.jarvis_api.services.thought_stream_daemon import get_latest_thought_fragment as _get_ts_fragment
        _ts_fragment = _get_ts_fragment()
        if _ts_fragment:
            tick_thought_action_proposal_daemon(_ts_fragment)
        _pending = get_pending_proposals()
        if _pending:
            inputs_present.append(f"handlingsforslag: {len(_pending)} afventer")
    except Exception:
        pass
```

- [ ] **Step 3: Add MC endpoints**

In `apps/api/jarvis_api/routes/mission_control.py`, after the `/thought-stream` endpoint, add:

```python

@router.get("/thought-proposals")
def mc_thought_proposals() -> dict:
    """Return pending and resolved thought-action proposals."""
    from apps.api.jarvis_api.services.thought_action_proposal_daemon import build_proposal_surface
    return build_proposal_surface()


@router.post("/thought-proposals/{proposal_id}/resolve")
def mc_resolve_thought_proposal(proposal_id: str, body: dict) -> dict:
    """Approve or dismiss a thought-action proposal. Body: {decision: 'approved'|'dismissed'}"""
    from apps.api.jarvis_api.services.thought_action_proposal_daemon import resolve_proposal
    decision = str(body.get("decision") or "dismissed")
    if decision not in ("approved", "dismissed"):
        return {"ok": False, "error": "decision must be 'approved' or 'dismissed'"}
    ok = resolve_proposal(proposal_id, decision)
    return {"ok": ok}
```

- [ ] **Step 4: Verify Python syntax**

```bash
conda activate ai && python -m compileall core/eventbus/events.py apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/routes/mission_control.py
```

Expected: `Compiling ... ok` for all files, no errors.

- [ ] **Step 5: Commit**

```bash
git add core/eventbus/events.py apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/routes/mission_control.py
git commit -m "feat: wire thought-action proposals into eventbus, heartbeat, and MC endpoints"
```

---

## Task 4: Frontend — adapters.js + OperationsTab

**Files:**
- Modify: `apps/ui/src/lib/adapters.js`
- Modify: `apps/ui/src/components/mission-control/OperationsTab.jsx`

- [ ] **Step 1: Add normalize function to adapters.js**

In `apps/ui/src/lib/adapters.js`, after `normalizeThoughtStream` (search for `function normalizeThoughtStream`), add:

```javascript
function normalizeThoughtProposals(raw) {
  if (!raw || typeof raw !== 'object') return null
  return {
    pendingProposals: Array.isArray(raw.pending_proposals)
      ? raw.pending_proposals.map(p => ({
          id: p.id || '',
          fragmentExcerpt: p.fragment_excerpt || '',
          actionDescription: p.action_description || '',
          proposalType: p.proposal_type || 'non_destructive',
          destructiveScore: p.destructive_score ?? 0,
          destructiveReason: p.destructive_reason || '',
          status: p.status || 'pending',
          createdAt: p.created_at || '',
        }))
      : [],
    resolvedProposals: Array.isArray(raw.resolved_proposals)
      ? raw.resolved_proposals.map(p => ({
          id: p.id || '',
          actionDescription: p.action_description || '',
          proposalType: p.proposal_type || 'non_destructive',
          status: p.status || 'dismissed',
          resolvedAt: p.resolved_at || '',
        }))
      : [],
    pendingCount: raw.pending_count ?? 0,
    needsApprovalCount: raw.needs_approval_count ?? 0,
  }
}
```

- [ ] **Step 2: Add fetch + destructure + return field**

Find the Promise.all destructuring in `getMissionControlJarvis()` (search for `thoughtStreamPayload`). Add `thoughtProposalsPayload` at the end of both the destructuring and the array:

Old destructuring:
```javascript
    const [..., thoughtStreamPayload] = await Promise.all([
      ...
      requestJson('/mc/thought-stream').catch(() => null),
    ])
```

New (add at end of both lines):
```javascript
    const [..., thoughtStreamPayload, thoughtProposalsPayload] = await Promise.all([
      ...
      requestJson('/mc/thought-stream').catch(() => null),
      requestJson('/mc/thought-proposals').catch(() => null),
    ])
```

In the return object, after `thoughtStream: normalizeThoughtStream(...)`, add:
```javascript
      thoughtProposals: normalizeThoughtProposals(thoughtProposalsPayload || null),
```

- [ ] **Step 3: Add ThoughtProposalsPanel to OperationsTab.jsx**

In `apps/ui/src/components/mission-control/OperationsTab.jsx`:

**a) Add imports** at the top (add to existing import line):

```javascript
import { Lightbulb, CheckCircle, XCircle, AlertTriangle } from 'lucide-react'
```

**b) Add the panel component** before `export function OperationsTab`:

```jsx
function ThoughtProposalsPanel({ proposals, onResolve }) {
  if (!proposals) return null
  const { pendingProposals, resolvedProposals, needsApprovalCount } = proposals

  if (pendingProposals.length === 0 && resolvedProposals.length === 0) {
    return (
      <div style={s({ fontSize: 11, color: T.text3, padding: '8px 0' })}>
        Ingen handlingsforslag endnu — tankestrømmen genererer dem løbende.
      </div>
    )
  }

  return (
    <div>
      {pendingProposals.length > 0 && (
        <div style={s({ marginBottom: 12 })}>
          {needsApprovalCount > 0 && (
            <div style={s({ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 8, fontSize: 10, color: T.amber })}>
              <AlertTriangle size={11} />
              <span>{needsApprovalCount} kræver approval</span>
            </div>
          )}
          {pendingProposals.map(p => (
            <div key={p.id} style={s({
              border: `1px solid ${p.proposalType === 'needs_approval' ? T.amber + '50' : T.border0}`,
              borderRadius: 8,
              padding: '8px 10px',
              marginBottom: 6,
              background: T.bgRaised,
            })}>
              <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 })}>
                <div style={s({ flex: 1, minWidth: 0 })}>
                  <div style={s({ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 })}>
                    <Lightbulb size={11} color={p.proposalType === 'needs_approval' ? T.amber : T.text3} />
                    <span style={s({ fontSize: 10, fontWeight: 600, color: p.proposalType === 'needs_approval' ? T.amber : T.text2 })}>
                      {p.actionDescription}
                    </span>
                    {p.proposalType === 'needs_approval' && (
                      <StatusBadge status="approval" />
                    )}
                  </div>
                  <div style={s({ fontSize: 10, color: T.text3, fontStyle: 'italic', lineHeight: 1.4 })}>
                    "{p.fragmentExcerpt.length > 80 ? p.fragmentExcerpt.slice(0, 80) + '…' : p.fragmentExcerpt}"
                  </div>
                </div>
                <div style={s({ display: 'flex', gap: 4, flexShrink: 0 })}>
                  <button
                    onClick={() => onResolve(p.id, 'approved')}
                    title="Godkend"
                    style={s({ background: 'none', border: 'none', cursor: 'pointer', color: T.green, padding: 2 })}
                  >
                    <CheckCircle size={14} />
                  </button>
                  <button
                    onClick={() => onResolve(p.id, 'dismissed')}
                    title="Afvis"
                    style={s({ background: 'none', border: 'none', cursor: 'pointer', color: T.text3, padding: 2 })}
                  >
                    <XCircle size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      {resolvedProposals.length > 0 && (
        <details>
          <summary style={s({ fontSize: 10, color: T.text3, cursor: 'pointer' })}>
            Seneste {resolvedProposals.length} løste forslag
          </summary>
          <div style={s({ marginTop: 6 })}>
            {resolvedProposals.map(p => (
              <div key={p.id} style={s({ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: `1px solid ${T.border0}`, fontSize: 10 })}>
                <span style={s({ color: T.text3 })}>{p.actionDescription}</span>
                <span style={s({ color: p.status === 'approved' ? T.green : T.text3 })}>{p.status}</span>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  )
}
```

**c) Add props and panel to OperationsTab**

Find `export function OperationsTab({` (line 205). Add `thoughtProposals` and `onResolveThoughtProposal` to the props destructuring:

```javascript
export function OperationsTab({
  data,
  selection,
  onSelectionChange,
  onOpenRun,
  onOpenSession,
  onOpenApproval,
  onOpenItem,
  onToolIntentAction,
  toolIntentActionBusy,
  toolIntentActionError,
  thoughtProposals,
  onResolveThoughtProposal,
}) {
```

Find the return block where `<AutonomyProposalsPanel />` is rendered (line 258). Add `ThoughtProposalsPanel` in a new article immediately before it:

```jsx
  return (
    <div className="mc-tab-page">
      <section className="mc-section-grid mc-operations-grid">
        <article className="support-card" id="thought-proposals" style={{ gridColumn: '1 / -1' }}>
          <div className="panel-header">
            <div>
              <h3>Handlingsforslag</h3>
              <p className="muted">Jarvis' tanker der indeholder handlingsimpulser</p>
            </div>
          </div>
          <ThoughtProposalsPanel
            proposals={thoughtProposals}
            onResolve={onResolveThoughtProposal || (() => {})}
          />
        </article>

        <article className="support-card" id="autonomy-proposals" style={{ gridColumn: '1 / -1' }}>
          <AutonomyProposalsPanel />
        </article>
```

- [ ] **Step 4: Wire props in MissionControlPage.jsx**

Find where `<OperationsTab` is rendered in `apps/ui/src/app/MissionControlPage.jsx`. Add the two new props. First find the existing call:

```bash
grep -n "OperationsTab" apps/ui/src/app/MissionControlPage.jsx
```

Then read those lines and add:
```jsx
        thoughtProposals={data?.thoughtProposals || null}
        onResolveThoughtProposal={async (id, decision) => {
          try {
            await fetch(`/mc/thought-proposals/${id}/resolve`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ decision }),
            })
            refresh()
          } catch (_) {}
        }}
```

Note: `refresh` is the data-refresh function already used in MissionControlPage — check the existing pattern for how other actions call refresh after a POST (e.g. `onToolIntentAction`).

- [ ] **Step 5: Verify all tests still pass**

```bash
conda activate ai && pytest tests/test_proposal_classifier.py tests/test_thought_action_proposal_daemon.py -v
```

Expected: 16/16 PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/ui/src/lib/adapters.js apps/ui/src/components/mission-control/OperationsTab.jsx apps/ui/src/app/MissionControlPage.jsx
git commit -m "feat: add ThoughtProposalsPanel in OperationsTab — Jarvis can propose actions from thought stream"
```

---

## Self-Review

**Spec coverage:**

| Requirement | Task |
|-------------|------|
| Thought fragments analyzed for action impulses | Task 1 (classifier) |
| Pattern-based destructive keyword detection | Task 1 |
| `non_destructive` vs `needs_approval` classification | Task 1 + 2 |
| Pending proposal queue (max 10) | Task 2 |
| Same fragment not classified twice | Task 2 |
| `resolve_proposal(id, decision)` | Task 2 |
| `insert_private_brain_record` on creation | Task 2 |
| Eventbus `thought_action_proposal.created` / `.resolved` | Task 2 + 3 |
| `"thought_action_proposal"` in ALLOWED_EVENT_FAMILIES | Task 3 |
| Heartbeat injection after thought_stream | Task 3 |
| `GET /mc/thought-proposals` endpoint | Task 3 |
| `POST /mc/thought-proposals/{id}/resolve` endpoint | Task 3 |
| adapters.js normalize + fetch + return | Task 4 |
| OperationsTab ThoughtProposalsPanel | Task 4 |
| Approve/dismiss buttons in UI | Task 4 |
| Destructive proposals visually flagged (amber) | Task 4 |

**Placeholder scan:** Ingen placeholders. Al kode er komplet.

**Type consistency:** `proposal_type` er `"non_destructive"` | `"needs_approval"` i classifier, daemon, og UI normalization — konsistent. `status` er `"pending"` | `"approved"` | `"dismissed"` — konsistent i daemon og UI.

**Step 4 note:** `refresh` i MissionControlPage — søg efter `onToolIntentAction` implementationen i samme fil for at finde det korrekte refresh-kald-mønster, og følg det.
