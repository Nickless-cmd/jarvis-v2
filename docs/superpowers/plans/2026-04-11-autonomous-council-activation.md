# Autonomous Council Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis the ability to autonomously decide when to convene a council or run a devil's advocate check — triggered by his own judgment during tool use, governed by a user-configurable sensitivity threshold.

**Architecture:** A pattern-based decision weight classifier scores actions 1–4 without LLM overhead. Two new tools (`convene_council`, `quick_council_check`) let Jarvis call deliberation from within his own execution. A sensitivity config controls how aggressively Jarvis's system prompt encourages council use. Closed council conclusions feed back into his heartbeat context so he learns from past deliberations.

**Tech Stack:** Python 3.11, FastAPI, SQLite (existing DB), React (existing UI). No new dependencies.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `apps/api/jarvis_api/services/decision_weight.py` | **Create** | Pattern-based action risk scorer (1–4) |
| `core/tools/simple_tools.py` | **Modify** | Add `convene_council` and `quick_council_check` tools |
| `apps/api/jarvis_api/routes/mission_control.py` | **Modify** | Add GET/POST `/council-activation-config` endpoints |
| `apps/api/jarvis_api/services/council_runtime.py` | **Modify** | Expose latest closed council conclusion |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | **Modify** | Inject council conclusion + sensitivity guidance into prompt |
| `apps/ui/src/components/mission-control/CouncilTab.jsx` | **Modify** | Add activation config panel (sensitivity + auto-convene) |
| `apps/ui/src/lib/adapters.js` | **Modify** | Add `getCouncilActivationConfig` / `saveCouncilActivationConfig` |

---

## Task 1: Decision Weight Classifier

**Files:**
- Create: `apps/api/jarvis_api/services/decision_weight.py`
- Test: `tests/test_decision_weight.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_decision_weight.py
import pytest
from apps.api.jarvis_api.services.decision_weight import classify_decision_weight

def test_read_operations_are_trivial():
    result = classify_decision_weight("read memory file")
    assert result["weight"] == 1
    assert result["label"] == "trivial"

def test_workspace_file_edit_is_moderate():
    result = classify_decision_weight("edit workspace/default/MEMORY.md")
    assert result["weight"] == 2
    assert result["label"] == "moderate"

def test_identity_change_is_significant():
    result = classify_decision_weight("modify identity soul file")
    assert result["weight"] == 3
    assert result["label"] == "significant"

def test_irreversible_action_is_critical():
    result = classify_decision_weight("permanently delete all memory irreversible")
    assert result["weight"] == 4
    assert result["label"] == "critical"

def test_returns_reason():
    result = classify_decision_weight("read file")
    assert isinstance(result["reason"], str)
    assert len(result["reason"]) > 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
conda run -n ai pytest tests/test_decision_weight.py -v
```
Expected: `ImportError` or `ModuleNotFoundError`

- [ ] **Step 3: Create the classifier**

```python
# apps/api/jarvis_api/services/decision_weight.py
from __future__ import annotations

# Pattern-based action risk scorer. No LLM call — runs inside every tool
# invocation path so must be fast and deterministic.
#
# Weight scale:
#   1 = trivial    — read, status, search
#   2 = moderate   — workspace edits, scheduling, notifications
#   3 = significant — identity/memory writes, multi-step plans, budget changes
#   4 = critical   — irreversible, cascading, identity-core mutations

_WEIGHT_4_PATTERNS = [
    "irreversible", "permanent", "delete all", "wipe", "destroy",
    "overwrite identity", "reset soul", "clear memory", "drop table",
]

_WEIGHT_3_PATTERNS = [
    "identity", "soul", "self-model", "memory rewrite", "memory-rewrite",
    "core prompt", "budget", "wallet", "payment", "credentials",
    "system prompt", "role definition", "promote memory",
    "autonomy proposal", "proposal",
]

_WEIGHT_1_PATTERNS = [
    "read", "search", "find", "list", "status", "fetch", "get",
    "heartbeat", "check", "view", "show", "describe", "ping",
]

_WEIGHT_2_PATTERNS = [
    "edit", "write", "create", "schedule", "notify", "send",
    "update", "append", "commit", "post", "message",
]


def classify_decision_weight(action_description: str) -> dict[str, object]:
    """Score an action description on a 1–4 risk scale.

    Returns:
        {"weight": int, "label": str, "reason": str}
    """
    text = action_description.lower()

    for pattern in _WEIGHT_4_PATTERNS:
        if pattern in text:
            return {
                "weight": 4,
                "label": "critical",
                "reason": f"matches critical pattern: '{pattern}'",
            }

    for pattern in _WEIGHT_3_PATTERNS:
        if pattern in text:
            return {
                "weight": 3,
                "label": "significant",
                "reason": f"matches significant pattern: '{pattern}'",
            }

    for pattern in _WEIGHT_1_PATTERNS:
        if pattern in text:
            return {
                "weight": 1,
                "label": "trivial",
                "reason": f"matches trivial pattern: '{pattern}'",
            }

    for pattern in _WEIGHT_2_PATTERNS:
        if pattern in text:
            return {
                "weight": 2,
                "label": "moderate",
                "reason": f"matches moderate pattern: '{pattern}'",
            }

    return {
        "weight": 2,
        "label": "moderate",
        "reason": "no specific pattern matched — defaulting to moderate",
    }
```

- [ ] **Step 4: Run tests**

```bash
conda run -n ai pytest tests/test_decision_weight.py -v
```
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/decision_weight.py tests/test_decision_weight.py
git commit -m "feat: pattern-based decision weight classifier (1-4 risk scale)"
```

---

## Task 2: `convene_council` Tool

**Files:**
- Modify: `core/tools/simple_tools.py` (TOOL_DEFINITIONS list + _TOOL_HANDLERS dict)
- Test: `tests/test_convene_council_tool.py`

The tool creates a council session, runs one deliberation round synchronously, and returns the summary as a tool result — so Jarvis sees the council's conclusion in his own context window.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_convene_council_tool.py
from unittest.mock import patch, MagicMock
from core.tools.simple_tools import execute_tool

def test_convene_council_tool_registered():
    """Tool must exist in registry."""
    result = execute_tool("convene_council", {"topic": "test"})
    # Should not return "Unknown tool"
    assert result.get("status") != "error" or "Unknown tool" not in result.get("error", "")

def test_convene_council_returns_summary():
    mock_council = {
        "council_id": "council-abc",
        "summary": "Council recommends proceeding with caution.",
        "status": "closed",
        "members": [],
        "messages": [],
    }
    with patch(
        "core.tools.simple_tools._exec_convene_council",
        return_value={"status": "ok", "summary": mock_council["summary"], "council_id": "council-abc"},
    ):
        result = execute_tool("convene_council", {"topic": "should I do X?"})
        assert result["status"] == "ok"

def test_convene_council_requires_topic():
    result = execute_tool("convene_council", {})
    assert result["status"] == "error"
    assert "topic" in result["error"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
conda run -n ai pytest tests/test_convene_council_tool.py::test_convene_council_tool_registered -v
```
Expected: FAIL (tool not registered yet)

- [ ] **Step 3: Add tool definition to TOOL_DEFINITIONS**

In `core/tools/simple_tools.py`, find the end of the `TOOL_DEFINITIONS` list (around line 800 before it closes with `]`) and add:

```python
    {
        "type": "function",
        "function": {
            "name": "convene_council",
            "description": (
                "Convene a council of agents to deliberate on a decision or topic. "
                "Use this when facing a significant or complex decision that warrants "
                "multiple perspectives before acting. The council runs synchronously "
                "and returns a summary recommendation. "
                "Suitable for: identity changes, multi-step plans, ambiguous tradeoffs, "
                "actions with lasting consequences."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The decision or question to deliberate. Be specific.",
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "low=full deliberation, medium=4 roles, high=critic+planner only",
                    },
                    "roles": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional explicit role list. Omit to use sensitivity defaults.",
                    },
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "quick_council_check",
            "description": (
                "Run a single Devil's Advocate agent to stress-test a decision before acting. "
                "Faster and cheaper than a full council. Use this for moderate-risk decisions "
                "where you want a sanity check without full deliberation. "
                "Returns the objection raised (if any) and whether escalation to full council is recommended."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The action or decision you are about to take.",
                    },
                },
                "required": ["action"],
            },
        },
    },
```

- [ ] **Step 4: Add handler functions**

In `core/tools/simple_tools.py`, find a handler function near the bottom of the handlers section (before `_TOOL_HANDLERS` dict) and add:

```python
def _exec_convene_council(args: dict[str, Any]) -> dict[str, Any]:
    topic = str(args.get("topic") or "").strip()
    if not topic:
        return {"status": "error", "error": "topic is required"}
    urgency = str(args.get("urgency") or "medium")
    explicit_roles: list[str] = list(args.get("roles") or [])

    # Role selection based on urgency
    if explicit_roles:
        roles = explicit_roles
    elif urgency == "high":
        roles = ["critic", "planner"]
    elif urgency == "low":
        roles = ["planner", "critic", "researcher", "synthesizer", "devils_advocate"]
    else:  # medium
        roles = ["planner", "critic", "researcher", "synthesizer"]

    try:
        from apps.api.jarvis_api.services.agent_runtime import (
            create_council_session_runtime,
            run_council_round,
        )
        session = create_council_session_runtime(topic=topic, roles=roles)
        council_id = str(session.get("council_id") or "")
        if not council_id:
            return {"status": "error", "error": "failed to create council session"}
        result = run_council_round(council_id)
        summary = str(result.get("summary") or "No summary produced.")
        members = result.get("members") or []
        positions = [
            f"{m.get('role')}: {str(m.get('position_summary') or '')[:120]}"
            for m in members
        ]
        return {
            "status": "ok",
            "council_id": council_id,
            "summary": summary,
            "positions": positions,
            "member_count": len(members),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_quick_council_check(args: dict[str, Any]) -> dict[str, Any]:
    action = str(args.get("action") or "").strip()
    if not action:
        return {"status": "error", "error": "action is required"}

    try:
        from apps.api.jarvis_api.services.agent_runtime import spawn_agent_task
        result = spawn_agent_task(
            role="devils_advocate",
            goal=(
                f"Jarvis is about to take the following action:\n\n{action}\n\n"
                "Argue the strongest possible case AGAINST this action. "
                "Be specific. End your response with one of: "
                "ESCALATE (full council needed) or PROCEED (action seems defensible)."
            ),
            auto_execute=True,
            budget_tokens=2000,
        )
        text = ""
        messages = result.get("messages") or []
        for msg in reversed(messages):
            if str(msg.get("direction") or "") == "agent->jarvis":
                text = str(msg.get("content") or "")
                break
        escalate = "ESCALATE" in text.upper()
        return {
            "status": "ok",
            "objection": text[:600] if text else "No objection raised.",
            "escalate_to_council": escalate,
            "agent_id": str(result.get("agent_id") or ""),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
```

- [ ] **Step 5: Register in _TOOL_HANDLERS**

Find `_TOOL_HANDLERS` dict (around line 2290) and add before closing `}`:

```python
    "convene_council": _exec_convene_council,
    "quick_council_check": _exec_quick_council_check,
```

- [ ] **Step 6: Verify syntax**

```bash
conda run -n ai python -m py_compile core/tools/simple_tools.py && echo "OK"
```
Expected: `OK`

- [ ] **Step 7: Run tests**

```bash
conda run -n ai pytest tests/test_convene_council_tool.py -v
```
Expected: 3 tests PASS

- [ ] **Step 8: Commit**

```bash
git add core/tools/simple_tools.py tests/test_convene_council_tool.py
git commit -m "feat: convene_council and quick_council_check tools for Jarvis"
```

---

## Task 3: Council Activation Config

**Files:**
- Modify: `apps/api/jarvis_api/routes/mission_control.py` (two new endpoints)
- Test: `tests/test_council_activation_config.py`

Config shape saved to `~/.jarvis-v2/config/council_activation.json`:
```json
{
  "sensitivity": "balanced",
  "auto_convene": true
}
```

Sensitivity maps to thresholds:
- `"conservative"` → suggest council for weight ≥ 2
- `"balanced"` → suggest council for weight ≥ 3 (default)
- `"minimal"` → suggest council for weight ≥ 4 only

- [ ] **Step 1: Write the failing test**

```python
# tests/test_council_activation_config.py
import json
import pytest
from fastapi.testclient import TestClient
from apps.api.jarvis_api.app import app

client = TestClient(app)

def test_get_activation_config_returns_defaults(tmp_path, monkeypatch):
    """Returns defaults when no config file exists."""
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.mission_control.CONFIG_DIR",
        tmp_path,
    )
    resp = client.get("/mc/council-activation-config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sensitivity"] == "balanced"
    assert data["auto_convene"] is True

def test_save_and_reload_activation_config(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.mission_control.CONFIG_DIR",
        tmp_path,
    )
    resp = client.post(
        "/mc/council-activation-config",
        json={"sensitivity": "minimal", "auto_convene": False},
    )
    assert resp.status_code == 200
    assert resp.json()["sensitivity"] == "minimal"

    resp2 = client.get("/mc/council-activation-config")
    assert resp2.json()["sensitivity"] == "minimal"
    assert resp2.json()["auto_convene"] is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
conda run -n ai pytest tests/test_council_activation_config.py -v
```
Expected: FAIL (endpoints not found)

- [ ] **Step 3: Add endpoints to mission_control.py**

Find the two `council-model-config` endpoints added previously (around the `@router.get("/council-model-config")` block) and add the new endpoints directly below them:

```python
@router.get("/council-activation-config")
def mc_get_council_activation_config() -> dict:
    """Return council activation sensitivity config."""
    import json
    from core.runtime.config import CONFIG_DIR
    path = CONFIG_DIR / "council_activation.json"
    defaults = {"sensitivity": "balanced", "auto_convene": True}
    if path.exists():
        try:
            saved = json.loads(path.read_text())
            return {**defaults, **saved}
        except Exception:
            pass
    return defaults


@router.post("/council-activation-config")
def mc_set_council_activation_config(payload: dict) -> dict:
    """Persist council activation sensitivity config."""
    import json
    from core.runtime.config import CONFIG_DIR
    allowed_sensitivities = {"conservative", "balanced", "minimal"}
    sensitivity = str(payload.get("sensitivity") or "balanced")
    if sensitivity not in allowed_sensitivities:
        sensitivity = "balanced"
    auto_convene = bool(payload.get("auto_convene", True))
    config = {"sensitivity": sensitivity, "auto_convene": auto_convene}
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / "council_activation.json").write_text(json.dumps(config, indent=2))
    return {**config, "saved": True}
```

- [ ] **Step 4: Verify syntax**

```bash
conda run -n ai python -m py_compile apps/api/jarvis_api/routes/mission_control.py && echo "OK"
```
Expected: `OK`

- [ ] **Step 5: Run tests**

```bash
conda run -n ai pytest tests/test_council_activation_config.py -v
```
Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add apps/api/jarvis_api/routes/mission_control.py tests/test_council_activation_config.py
git commit -m "feat: council activation config endpoint (sensitivity + auto_convene)"
```

---

## Task 4: Council Conclusion Feedback to Jarvis's Context

**Files:**
- Modify: `apps/api/jarvis_api/services/council_runtime.py` (add `get_latest_council_conclusion`)
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py` (inject conclusion + sensitivity prompt guidance)
- Test: `tests/test_council_conclusion_feedback.py`

The goal: after a council closes, its conclusion is visible in Jarvis's heartbeat context on the next turn, so he knows what his last deliberation concluded.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_council_conclusion_feedback.py
from unittest.mock import patch, MagicMock
from apps.api.jarvis_api.services.council_runtime import get_latest_council_conclusion

def test_get_latest_council_conclusion_returns_none_when_no_closed_sessions():
    with patch(
        "apps.api.jarvis_api.services.council_runtime.list_council_sessions",
        return_value=[],
    ):
        result = get_latest_council_conclusion()
        assert result is None

def test_get_latest_council_conclusion_returns_most_recent_closed():
    fake_sessions = [
        {"council_id": "c1", "status": "closed", "topic": "Should I X?",
         "summary": "Council recommends caution.", "updated_at": "2026-04-11T20:00:00"},
        {"council_id": "c2", "status": "deliberating", "topic": "Y",
         "summary": "", "updated_at": "2026-04-11T21:00:00"},
    ]
    with patch(
        "apps.api.jarvis_api.services.council_runtime.list_council_sessions",
        return_value=fake_sessions,
    ):
        result = get_latest_council_conclusion()
        assert result is not None
        assert result["council_id"] == "c1"
        assert "caution" in result["summary"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
conda run -n ai pytest tests/test_council_conclusion_feedback.py -v
```
Expected: `ImportError` (function not yet defined)

- [ ] **Step 3: Add `get_latest_council_conclusion` to council_runtime.py**

Open `apps/api/jarvis_api/services/council_runtime.py`. At the top, verify `list_council_sessions` is imported (check existing imports — if not present, add it). Then append at the end of the file:

```python
def get_latest_council_conclusion() -> dict[str, object] | None:
    """Return the most recent closed council session summary, or None."""
    from core.runtime.db import list_council_sessions
    sessions = list_council_sessions(limit=20)
    closed = [s for s in sessions if str(s.get("status") or "") == "closed"]
    if not closed:
        return None
    # Sessions are ordered newest-first by list_council_sessions
    latest = closed[0]
    return {
        "council_id": str(latest.get("council_id") or ""),
        "topic": str(latest.get("topic") or ""),
        "summary": str(latest.get("summary") or ""),
        "updated_at": str(latest.get("updated_at") or ""),
        "mode": str(latest.get("mode") or "council"),
    }
```

- [ ] **Step 4: Run tests**

```bash
conda run -n ai pytest tests/test_council_conclusion_feedback.py -v
```
Expected: 2 tests PASS

- [ ] **Step 5: Inject conclusion + sensitivity guidance into heartbeat prompt**

In `apps/api/jarvis_api/services/heartbeat_runtime.py`, find the function `_build_inner_visible_prompt_context` or the section around line 1595–1614 where `council_state` is assembled into the context string.

Find this block (around line 1601–1614):
```python
    council_state = str(council_runtime.get("council_state") or "quiet")
    council_recommendation = str(council_runtime.get("recommendation") or "none")
    council_divergence = str(council_runtime.get("divergence_level") or "low")
    if council_state not in {"quiet", "held"} or council_recommendation not in {
        "none",
        "hold",
    }:
        inputs_present.append(
            f"council-runtime ({council_state}, recommend={council_recommendation}, divergence={council_divergence})"
        )
    else:
        inputs_absent.append("council-runtime")
```

Replace it with:

```python
    council_state = str(council_runtime.get("council_state") or "quiet")
    council_recommendation = str(council_runtime.get("recommendation") or "none")
    council_divergence = str(council_runtime.get("divergence_level") or "low")
    if council_state not in {"quiet", "held"} or council_recommendation not in {
        "none",
        "hold",
    }:
        inputs_present.append(
            f"council-runtime ({council_state}, recommend={council_recommendation}, divergence={council_divergence})"
        )
    else:
        inputs_absent.append("council-runtime")

    # Latest closed council conclusion
    try:
        from apps.api.jarvis_api.services.council_runtime import get_latest_council_conclusion
        from core.runtime.config import CONFIG_DIR
        import json as _json
        conclusion = get_latest_council_conclusion()
        if conclusion and conclusion.get("summary"):
            inputs_present.append(
                f"last-council ({conclusion['mode']}, topic={conclusion['topic'][:60]!r}): "
                f"{conclusion['summary'][:200]}"
            )
        # Sensitivity guidance
        _activation_path = CONFIG_DIR / "council_activation.json"
        _activation = {}
        if _activation_path.exists():
            try:
                _activation = _json.loads(_activation_path.read_text())
            except Exception:
                pass
        _sensitivity = str(_activation.get("sensitivity") or "balanced")
        _auto_convene = bool(_activation.get("auto_convene", True))
        if _auto_convene:
            _guidance = {
                "conservative": "Use convene_council for any non-trivial decision. Use quick_council_check before most actions.",
                "balanced": "Use convene_council for significant decisions (identity, memory rewrites, multi-step plans). Use quick_council_check for uncertain moderate actions.",
                "minimal": "Use convene_council only for critical or irreversible decisions.",
            }.get(_sensitivity, "")
            if _guidance:
                inputs_present.append(f"council-guidance ({_sensitivity}): {_guidance}")
    except Exception:
        pass
```

- [ ] **Step 6: Verify syntax**

```bash
conda run -n ai python -m py_compile apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/services/council_runtime.py && echo "OK"
```
Expected: `OK`

- [ ] **Step 7: Run all tests**

```bash
conda run -n ai pytest tests/test_council_conclusion_feedback.py tests/test_decision_weight.py tests/test_convene_council_tool.py -v
```
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add apps/api/jarvis_api/services/council_runtime.py apps/api/jarvis_api/services/heartbeat_runtime.py tests/test_council_conclusion_feedback.py
git commit -m "feat: council conclusion feedback loop + sensitivity guidance in Jarvis context"
```

---

## Task 5: MC UI — Council Activation Config Panel

**Files:**
- Modify: `apps/ui/src/lib/adapters.js`
- Modify: `apps/ui/src/components/mission-control/CouncilTab.jsx`

Adds a compact "Council Activation" section to CouncilTab with:
- Sensitivity selector: `conservative | balanced | minimal`
- Auto-convene toggle

- [ ] **Step 1: Add adapter methods to adapters.js**

Find the `saveCouncilModelConfig` method (added previously) and add directly after it:

```javascript
  async getCouncilActivationConfig() {
    return requestJson('/mc/council-activation-config')
  },

  async saveCouncilActivationConfig(config) {
    return requestJson('/mc/council-activation-config', {
      method: 'POST',
      body: JSON.stringify(config),
    })
  },
```

- [ ] **Step 2: Add activation config state to CouncilTab**

In `CouncilTab.jsx`, find the state declarations block (the `useState` section) and add after `configSaved`:

```javascript
  const [activation, setActivation] = useState({ sensitivity: 'balanced', auto_convene: true })
  const [activationSaving, setActivationSaving] = useState(false)
  const [activationSaved, setActivationSaved] = useState(false)
```

- [ ] **Step 3: Load activation config in the existing config useEffect**

In `CouncilTab.jsx`, find the `loadConfig` async function inside the second `useEffect` (the one that calls `backend.getCouncilModelConfig()`). At the start of `loadConfig`, add a parallel fetch:

```javascript
      const [cfg, sel, activationCfg] = await Promise.all([
        backend.getCouncilModelConfig(),
        backend.getShell().catch(() => null),
        backend.getCouncilActivationConfig().catch(() => null),
      ])
```

Then after loading `configDraft`, add:
```javascript
      if (activationCfg) {
        setActivation({
          sensitivity: activationCfg.sensitivity || 'balanced',
          auto_convene: activationCfg.auto_convene !== false,
        })
      }
```

(Remove the old `Promise.all([cfg, sel])` line and replace with the three-way version above.)

- [ ] **Step 4: Add save handler for activation config**

Add this function after `handleSaveConfig`:

```javascript
  async function handleSaveActivation() {
    if (activationSaving) return
    setActivationSaving(true)
    try {
      await backend.saveCouncilActivationConfig(activation)
      setActivationSaved(true)
      setTimeout(() => setActivationSaved(false), 2000)
    } finally {
      setActivationSaving(false)
    }
  }
```

- [ ] **Step 5: Add UI section**

In `CouncilTab.jsx` JSX, find the `<Section title="Council Model Config"` block. Add a new section directly above it:

```jsx
      <Section title="Council Activation" description="Styrer hvornår Jarvis bruger council og quick_council_check autonomt">
        <div style={s({ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' })}>
          <div style={s({ display: 'flex', alignItems: 'center', gap: 8 })}>
            <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>sensitivitet</span>
            <select
              value={activation.sensitivity}
              onChange={(e) => setActivation((prev) => ({ ...prev, sensitivity: e.target.value }))}
              style={s({ borderRadius: 6, border: `1px solid ${T.border0}`, background: T.bgBase, color: T.text1, padding: '4px 8px', ...mono, fontSize: 9 })}
            >
              <option value="conservative">conservative — tjek alt over trivielt</option>
              <option value="balanced">balanced — tjek ved vigtige beslutninger</option>
              <option value="minimal">minimal — kun kritiske handlinger</option>
            </select>
          </div>
          <label style={s({ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', ...mono, fontSize: 9, color: T.text2 })}>
            <input
              type="checkbox"
              checked={activation.auto_convene}
              onChange={(e) => setActivation((prev) => ({ ...prev, auto_convene: e.target.checked }))}
              style={{ accentColor: T.accent }}
            />
            auto-convene aktivt
          </label>
          <button
            onClick={handleSaveActivation}
            disabled={activationSaving}
            style={s({ borderRadius: 8, border: `1px solid ${activationSaved ? T.green : T.border0}`, background: activationSaved ? `${T.green}22` : T.bgBase, color: T.text2, padding: '5px 12px', cursor: 'pointer', ...mono, fontSize: 9 })}
          >
            {activationSaved ? 'gemt ✓' : 'gem'}
          </button>
        </div>
      </Section>
```

- [ ] **Step 6: Build and verify**

```bash
cd apps/ui && npm run build 2>&1 | tail -5
```
Expected: `✓ built in X.XXs`

- [ ] **Step 7: Restart service**

```bash
sudo systemctl restart jarvis-api && sleep 2 && systemctl is-active jarvis-api
```
Expected: `active`

- [ ] **Step 8: Smoke test the new endpoints**

```bash
curl -s http://localhost/mc/council-activation-config | python3 -m json.tool
curl -s -X POST http://localhost/mc/council-activation-config \
  -H "Content-Type: application/json" \
  -d '{"sensitivity":"balanced","auto_convene":true}' | python3 -m json.tool
```
Expected: both return valid JSON with `sensitivity` and `auto_convene` fields.

- [ ] **Step 9: Commit**

```bash
git add apps/ui/src/lib/adapters.js apps/ui/src/components/mission-control/CouncilTab.jsx
git commit -m "feat: council activation config panel in MC CouncilTab"
```

---

## Task 6: Full Integration Smoke Test

- [ ] **Step 1: Run full test suite**

```bash
conda run -n ai pytest tests/test_decision_weight.py tests/test_convene_council_tool.py tests/test_council_activation_config.py tests/test_council_conclusion_feedback.py -v
```
Expected: all PASS

- [ ] **Step 2: Verify tools appear in Jarvis's tool list**

```bash
conda run -n ai python -c "
from core.tools.simple_tools import get_tool_definitions
names = [t['function']['name'] for t in get_tool_definitions()]
print('convene_council' in names, 'quick_council_check' in names)
"
```
Expected: `True True`

- [ ] **Step 3: Verify syntax across all modified files**

```bash
conda run -n ai python -m compileall core apps/api -q && echo "OK"
```
Expected: `OK`

- [ ] **Step 4: Restart and confirm active**

```bash
sudo systemctl restart jarvis-api && sleep 2 && systemctl is-active jarvis-api
```
Expected: `active`

- [ ] **Step 5: Final commit tag**

```bash
git commit --allow-empty -m "chore: autonomous council activation complete (tasks 1-5 integrated)"
```

---

## What This Delivers

After all tasks:

| Capability | How |
|---|---|
| Jarvis can call a council himself | `convene_council` tool in his toolset |
| Jarvis can run a quick sanity check | `quick_council_check` → single devil's advocate |
| Council only fires when decision warrants it | Sensitivity config in his system prompt guidance |
| Jarvis knows what his last council concluded | Injected in heartbeat context every turn |
| You control the threshold | MC Council tab → Activation panel |
| Truly critical paths always require council | Pattern-based weight 4 triggers via guidance |

**What stays Jarvis's:** He decides when to call council. The config shapes his guidance, not his constraints.
