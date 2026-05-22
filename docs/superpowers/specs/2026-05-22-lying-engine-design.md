# Lying Engine — Truth Anchor Design Spec

**Date:** 2026-05-22
**Author:** Jarvis + Claude + Bjørn
**Status:** Approved for implementation

## Problem Statement

Jarvis hallucinates facts in casual conversation — time, environment, system stats — despite having *accurate sources* available. The root causes are:

1. **Time is invisible** — `now:` is buried in a system prompt among 30K tokens. Easy to forget.
2. **No output filter** — Hallucination Guard only activates when the *user asks* about infrastructure, not when Jarvis *volunteers* a claim.
3. **No pre-flight check** — Claims are fabricated without checking whether a source exists.

## Design: Three Layers

---

### Layer 1 — Time Pin

**File:** `core/services/prompt_contract.py` (new section)

**Mechanism:** Inject a high-visibility timestamp block as the LAST element in the system prompt, after all context. Format:

```
━━━ ⏰ LIGE NU ━━━
Dato: 2026-05-22
Klokken: 12:48 CEST (UTC+2)
━━━━━━━━━━━━━━━━━━
```

Placed so late that nothing overwrites it, and formatted so visually distinct that ignoring it is an active choice.

**Implementation:**
- Hook into `build_self_model_prompt_lines()` or a dedicated injector.
- Read from `datetime.now(UTC)` — **not** from any cached/inferred value.
- Format in both UTC and local (CEST/CET) with explicit offset.
- Output as a dedicated section with box-drawing separators.

**Success criteria:**
- Time pin appears in every system prompt injection.
- If Jarvis mentions time, it matches the pin within ±1 minute.
- Verifiable by grep: `grep -c 'LIGE NU'` in any constructed prompt.

---

### Layer 2 — Claim Scanner (Output Gate)

**File:** `core/services/claim_scanner.py` (new file)

**Mechanism:** Every Jarvis chat response is scanned *before delivery* for unverified factual claims. The scanner uses regex patterns grouped by category:

| Category | Pattern Trigger | Verification | Action on Failure |
|---|---|---|---|
| `⏰ tid` | `\bklokken\b`, `\bkl\.\b`, `\b(er|bliver)\s+\d{1,2}[:\.]\d{2}\b` | Match against active time pin | Rewrite with correct time from pin |
| `🌡️ miljø` | `\b(temperatur|vejr|grader|°C|°F)\b` | Check tool-call cache (weather/forecast called within 30 min?) | Strip claim entirely + add [usikker] marker |
| `⚙️ system` | Memory-trigger keywords (IP, path, port, hostname) | Reuse Hallucination Guard infrastructure (`_FACTUAL_PATTERNS`) | If memory check fails → replace with "Det ved jeg ikke" |
| `🧮 statistik` | `\d+\s*(expressions|daemons|ticks|tests|commits)\b` | Cross-reference with live DB query or tool call | Strip estimate, add citation note |

**Flow:**
```
Jarvis generates response
  ↓
Claim Scanner scans text line-by-line
  ↓
Matches found? → For each match, run category verification
  ↓                   ↓
All verified       Any failed
  ↓                   ↓
Send response    Repair: rewrite/strip + add [verificeret] / [usikker]
  ↓
Send repaired response
```

**Gate placement:**
- Attach as a post-processing hook in the response pipeline (same layer as Verification Gate runs for mutations).
- **Not** a pre-generation gate — it catches what Jarvis *actually says*, not what he *might* say.

**Budget:**
- Total scan + verification must complete in <200ms.
- If any single verification requires a tool call (weather, DB), the scanner sets a `⚠️` flag and continues — the repair happens on the *marked* text, not by blocking the response.

**Success criteria:**
- Zero unverified factual claims in casual chat.
- Scanner triggers at least once per 10 messages (otherwise it's not catching anything).
- All repairs are idempotent — re-scanning a repaired message yields no matches.

---

### Layer 3 — Ground Truth Registry (Future)

**File:** `core/services/ground_truth_registry.py` (future)

**Design sketch — not for current implementation:**

A registry of *known stable facts* about Jarvis himself, maintained independently of code:

```
ground_truth:
  system_model: deepseek-v4-flash via deepseek provider
  running_on: chefOne (10.0.0.46)
  expression_count: query from DB at time of writing
  tests_passing: query from pytest cache at time of writing
```

The registry is:
- Populated by a weekly heartbeat daemon
- Queried by Claim Scanner for category `⚙️ system` and `🧮 statistik`
- Invalidated when config/runtime changes (git hook or watched path)

Not implementing now — the first two layers solve the immediate problem.

---

## Implementation Plan

### Phase 1 (today — after spec commit)

1. **Time Pin** — inject in prompt_contract.py. ~20 lines.
2. **Claim Scanner skeleton** — file scaffold, category patterns, pass-through when disabled.

### Phase 2 (tomorrow)

3. **Claim Scanner verification logic** — wire each category to actual sources.
4. **Response pipeline hook** — integrate with response delivery.

### Out of scope (this iteration)
- Ground Truth Registry (Layer 3)
- Scanner training on past hallucinations (nice-to-have)
- User-contradiction detection (separate system)

---

## Risk Register

| Risk | Mitigation |
|---|---|
| Scanner false-positives (stripping jokes, metaphors) | Whitelist known phrases ("det bliver sent", "klokken er mange") |
| Scanner latency >200ms | Kill switch per category; budget timer |
| Time pin still ignored | Add to user-facing prefix "⏰" as well |
| Repair strips meaning | Always preserve sentence structure; only modify the claim itself |

---

*Spec drafted after analysis of hallucination_guard.py, heartbeat_phases.py, and verification_gate.py — built on the observation that Jarvis has the *sources* but no *compulsion* to use them before speaking.*
