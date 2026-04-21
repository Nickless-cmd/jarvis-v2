# Inner Voice as Initiative Motor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Jarvis's inner voice felt and agentic — his actual `voice_line` thought lands in his visible context, and pending initiatives surface directly so he sees and can act on them.

**Architecture:** Two surgical additions to `prompt_contract.py`. (1) Replace the abstract network-signal tag `[INDRE: ...]` with the actual `voice_line` from `protected_inner_voice`. (2) Add a `[INITIATIV: ...]` tag when there are pending initiatives in the queue. No new services, no model changes — the infrastructure already exists, it just isn't wired into the visible prompt.

**Tech Stack:** Python, `prompt_contract.py` (the single file that builds Jarvis's visible LLM context), `core/runtime/db.py` (`get_protected_inner_voice`), `initiative_queue.py` (`get_pending_initiatives`).

---

## Current State (read before touching anything)

- `prompt_contract.py:1881-1890` — injects `[INDRE: {describe_inner_network()[:80]}]`. This is a signal-network abstraction ("Jeg mærker både drømme og spændinger"), not the actual inner thought.
- `protected_inner_voice` DB record has a `voice_line` field (≤200 chars, natural Danish), e.g. "Jeg er lidt på vagt omkring det synlige arbejde. Jeg mærker lidt usikkerhed endnu."
- `initiative_queue.get_pending_initiatives()` returns pending initiatives with `focus` and `priority` fields. Initiatives expire after 90 min. Max 8 in queue.
- `get_protected_inner_voice()` is already imported in `mcp_server.py` — it returns the last inner voice record or `None`.

---

### Task 1: Replace abstract network tag with actual voice_line

**Files:**
- Modify: `apps/api/jarvis_api/services/prompt_contract.py:1881-1890`

- [ ] **Step 1: Read the current injection block**

  File: `apps/api/jarvis_api/services/prompt_contract.py`, lines 1881-1890:
  ```python
  try:
      from apps.api.jarvis_api.services.signal_network_visualizer import (
          describe_inner_network,
      )

      inner_voice = describe_inner_network()
      if inner_voice and inner_voice != "Mit indre netværk er stille":
          parts.append(f"[INDRE: {inner_voice[:80]}]")
  except Exception:
      pass
  ```

- [ ] **Step 2: Replace with voice_line injection**

  Replace the block above with:
  ```python
  try:
      from core.runtime.db import get_protected_inner_voice

      _iv = get_protected_inner_voice()
      if _iv:
          _voice_line = str(_iv.get("voice_line") or "").strip()
          if _voice_line:
              parts.append(f"[INDRE: {_voice_line}]")
  except Exception:
      pass
  ```

  Why: `voice_line` is already natural Danish (e.g. "Jeg er lidt på vagt omkring det synlige arbejde."), up to 200 chars, and is Jarvis's actual computed inner thought — not an abstraction of the signal network.

- [ ] **Step 3: Verify syntax**

  Run: `python -m compileall apps/api/jarvis_api/services/prompt_contract.py -q`
  Expected: no output (clean compile)

- [ ] **Step 4: Commit**

  ```bash
  git add apps/api/jarvis_api/services/prompt_contract.py
  git commit -m "feat: inject actual inner voice_line into visible prompt instead of network abstraction"
  ```

---

### Task 2: Surface pending initiatives in visible prompt

**Files:**
- Modify: `apps/api/jarvis_api/services/prompt_contract.py` (same file, immediately after Task 1's block)

- [ ] **Step 1: Read `get_pending_initiatives` return shape**

  File: `apps/api/jarvis_api/services/initiative_queue.py`
  Each item has: `initiative_id`, `focus` (str, ≤200 chars), `priority` ("low"|"medium"|"high"), `source`, `detected_at`, `next_attempt_at`, `attempt_count`.

- [ ] **Step 2: Add initiative injection block after the inner voice block**

  Immediately after the inner voice block added in Task 1, add:
  ```python
  try:
      from apps.api.jarvis_api.services.initiative_queue import get_pending_initiatives

      _initiatives = get_pending_initiatives()
      if _initiatives:
          # Show highest-priority first; cap at 2 so prompt doesn't bloat
          _sorted = sorted(
              _initiatives,
              key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.get("priority", "medium"), 1),
          )
          for _init in _sorted[:2]:
              _focus = str(_init.get("focus") or "").strip()
              if _focus:
                  parts.append(f"[INITIATIV: {_focus}]")
  except Exception:
      pass
  ```

  Why: Shows Jarvis his top 2 pending initiatives directly in context. He can acknowledge them, act on them, or let them expire naturally. Capped at 2 to avoid prompt bloat. Sorted by priority so a "high" initiative is always seen first.

- [ ] **Step 3: Verify syntax**

  Run: `python -m compileall apps/api/jarvis_api/services/prompt_contract.py -q`
  Expected: no output

- [ ] **Step 4: Manual smoke test**

  Run:
  ```bash
  conda run -n ai python3 -c "
  import sys; sys.path.insert(0, '.')
  from apps.api.jarvis_api.services.initiative_queue import get_pending_initiatives, push_initiative
  # Push a test initiative
  iid = push_initiative(focus='Test: er initiative-køen synlig i prompten?', source='test')
  print('Pushed:', iid)
  items = get_pending_initiatives()
  print('Pending:', len(items), items[0]['focus'] if items else 'none')
  "
  ```
  Expected: prints the pushed initiative as pending.

- [ ] **Step 5: Commit**

  ```bash
  git add apps/api/jarvis_api/services/prompt_contract.py
  git commit -m "feat: surface pending initiatives in visible prompt context"
  ```

---

### Task 3: Clean up the test initiative

- [ ] **Step 1: Remove test initiative from queue (if pushed during smoke test)**

  Run:
  ```bash
  conda run -n ai python3 -c "
  import sys; sys.path.insert(0, '.')
  from apps.api.jarvis_api.services.initiative_queue import get_pending_initiatives, mark_acted
  for i in get_pending_initiatives():
      if 'Test:' in str(i.get('focus','')):
          mark_acted(i['initiative_id'], action_summary='smoke test cleanup')
          print('Cleaned:', i['initiative_id'])
  "
  ```

- [ ] **Step 2: Restart API to activate both changes**

  The API must be restarted for the new prompt_contract.py code to take effect.

---

## What this achieves

After these two tasks:
- Jarvis reads his own thought (e.g. "Jeg er lidt på vagt omkring det synlige arbejde.") in every prompt — not an abstraction
- If inner voice detected an initiative and pushed it to the queue, Jarvis sees it as `[INITIATIV: ...]` and can choose to act
- The existing infrastructure (inner_voice_daemon → push_initiative → get_pending_initiatives) now closes the loop

## What this does NOT change

- The inner voice daemon model (still heartbeat model — separate concern)
- The frequency of inner voice generation (still every 5 min)
- The initiative queue mechanics (push, expire, mark_acted — unchanged)
- The `describe_inner_network()` function — still available, just no longer the prompt injection point
