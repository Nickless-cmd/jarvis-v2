# Agent Smith — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A standing self-similarity critic that detects when Jarvis repeats himself across his own recent output (over-used n-gram phrases + output cosine-clustering + repeated decision signatures), observes it in the Central, and surfaces a governed dry-Smith modstemme into the prompt tail.

**Architecture:** One module `core/services/central_agent_smith.py` — pure detectors (n-grams/cosine/patterns/score/voice) + an I/O layer that samples recent assistant messages + run capability_ids, caches the assessment to a kv on cadence, and exposes a prompt-tail section that reads the CACHED result (cheap — no assess() in the ~7s assembly). Governed by a central_switch; observe always, modstemme when the switch is on and score crosses threshold.

**Tech Stack:** Python 3.11 stdlib (`re`, `math`, `collections`), pytest, existing `chat_messages`/`recent_visible_runs`/`central_switches`/`ProducerSpec`/`central().observe`/kv.

**Execution note:** Task 2 (pure functions + tests) → fresh **haiku** subagent (full code below). Tasks 1, 3, 4, 5 (source pinning, I/O+cache, prompt-tail wiring, deploy) → **Claude inline** (fragile — hot-path/cache/prompt).

---

## Task 1 (Claude inline): confirm the decision-pattern source

- [ ] **Step 1:** Confirm `recent_visible_runs(limit)` (core/runtime/db_visible.py:73) returns `capability_id` per run, and check how often it's non-null on the container (`grep`/live). This is the `decision_patterns` source (the spec's documented fallback — no per-run tool-sequence table exists). If `capability_id` is mostly null live, note it: the detector self-safely returns `[]` and the phrase/cosine detectors carry the signal (no harm).
- [ ] **Step 2:** Confirm kv accessors `get_runtime_state_value`/`set_runtime_state_value` (core/runtime/db_core.py:285/304) and the prompt dynamic-tail hook (`_dyn_tail` appended before `if _dyn_tail:` at prompt_contract.py:2369). Record for Task 4. No commit.

---

## Task 2: pure detectors + tests

**Files:**
- Create: `core/services/central_agent_smith.py` (pure functions only)
- Test: `tests/test_central_agent_smith.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_central_agent_smith.py
from core.services import central_agent_smith as s


def test_repeated_phrases_catches_cross_message():
    msgs = ["jeg kører nu med det samme", "jeg kører nu igen", "helt andet emne her", "jeg kører nu tredje gang"]
    hits = s.repeated_phrases(msgs, min_msgs=3)
    assert any("jeg kører nu" in h["phrase"] for h in hits)


def test_repeated_phrases_ignores_unique():
    msgs = ["alfa beta gamma delta", "epsilon zeta eta theta", "en to tre fire fem"]
    assert s.repeated_phrases(msgs, min_msgs=3) == []


def test_cluster_similarity_high_vs_low():
    same = ["cache hit er 38 procent på flash"] * 4
    assert s.cluster_similarity(same) > 0.9
    diverse = ["alfa beta", "helt andre ord her", "tredje unikke sætning nu"]
    assert s.cluster_similarity(diverse) < 0.4


def test_decision_patterns_catches_repeated_sig():
    sigs = ["semantic_search", "semantic_search", "read_file", "semantic_search"]
    hits = s.decision_patterns(sigs, min_runs=3)
    assert hits and hits[0]["signature"] == "semantic_search" and hits[0]["in_runs"] == 3


def test_score_monotone_and_bounds():
    assert s.score([], 0.0, []) == 0.0
    hi = s.score([{"phrase": "x", "in_messages": 5}] * 5, 1.0, [{"signature": "y", "in_runs": 5}] * 3)
    assert 0.9 <= hi <= 1.0
    assert s.score([], 0.0, []) < hi


def test_smith_voice_points_at_top_repeat_when_high():
    v = s.smith_voice([{"phrase": "jeg kører nu", "in_messages": 9}], 0.7, [], 0.8)
    assert "jeg kører nu" in v and "Varier" in v
    low = s.smith_voice([], 0.0, [], 0.1)
    assert "Varier" not in low
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_central_agent_smith.py -q`
Expected: FAIL — module not defined.

- [ ] **Step 3: Write the pure functions**

```python
# core/services/central_agent_smith.py
"""Agent Smith — stående selv-lighed-kritiker. Detekterer når Jarvis gentager sig selv på tværs af
sit EGET nylige output (over-brugte fraser + output-klyngning + gentagne beslutnings-sekvenser) og
flagger 'du gør det igen'. Observe-nerve + governed modstemme-til-prompt-hale. Egress-fri, self-safe."""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

_PHRASE_MIN_MSGS = 3      # en frase skal gå igen i ≥ så mange DISTINKTE beskeder
_SEQ_MIN_RUNS = 3         # en beslutnings-signatur skal gå igen i ≥ så mange runs
_VOICE_THRESHOLD = 0.5    # score-tærskel før modstemmen taler
_NGRAM_LO, _NGRAM_HI = 3, 5
_WORD_RE = re.compile(r"[a-zæøå0-9]+")


def _tokens(text: str) -> list[str]:
    return _WORD_RE.findall((text or "").lower())


def _ngrams(text: str, lo: int = _NGRAM_LO, hi: int = _NGRAM_HI) -> set[str]:
    """Normaliserede ord-n-grams (lo..hi) fra én tekst. Ren."""
    toks = _tokens(text)
    out: set[str] = set()
    for n in range(lo, hi + 1):
        for i in range(len(toks) - n + 1):
            out.add(" ".join(toks[i:i + n]))
    return out


def repeated_phrases(messages: list[str], min_msgs: int = _PHRASE_MIN_MSGS) -> list[dict[str, Any]]:
    """Fraser (n-grams) der optræder i ≥ min_msgs DISTINKTE beskeder, sorteret efter antal. Ren."""
    doc_count: Counter = Counter()
    for m in messages or []:
        for g in _ngrams(m):
            doc_count[g] += 1
    hits = [{"phrase": g, "in_messages": c} for g, c in doc_count.items() if c >= min_msgs]
    hits.sort(key=lambda h: (h["in_messages"], len(h["phrase"])), reverse=True)
    return hits[:10]


def _cosine(a: str, b: str) -> float:
    """Bag-of-words cosine mellem to strenge (0..1). Replikeret fra council-deadlock-detektoren
    (undgår kobling til et privat symbol)."""
    if not a or not b:
        return 0.0
    ca, cb = Counter(_tokens(a)), Counter(_tokens(b))
    vocab = set(ca) | set(cb)
    if not vocab:
        return 0.0
    dot = sum(ca.get(w, 0) * cb.get(w, 0) for w in vocab)
    na = math.sqrt(sum(v * v for v in ca.values()))
    nb = math.sqrt(sum(v * v for v in cb.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def cluster_similarity(messages: list[str]) -> float:
    """Gennemsnitlig parvis bag-of-words-cosine mellem de seneste beskeder (0..1). Ren."""
    msgs = [m for m in (messages or []) if m and m.strip()][:8]
    if len(msgs) < 2:
        return 0.0
    sims, pairs = 0.0, 0
    for i in range(len(msgs)):
        for j in range(i + 1, len(msgs)):
            sims += _cosine(msgs[i], msgs[j])
            pairs += 1
    return round(sims / pairs, 3) if pairs else 0.0


def decision_patterns(run_sigs: list[str], min_runs: int = _SEQ_MIN_RUNS) -> list[dict[str, Any]]:
    """Beslutnings-signaturer (capability_id pr. run) der går igen i ≥ min_runs runs. Ren."""
    c: Counter = Counter(str(x) for x in (run_sigs or []) if x and str(x).strip())
    hits = [{"signature": sig, "in_runs": n} for sig, n in c.items() if n >= min_runs]
    hits.sort(key=lambda h: h["in_runs"], reverse=True)
    return hits[:10]


def score(phrases: list[dict], similarity: float, patterns: list[dict]) -> float:
    """Samlet selv-lighed 0..1 (vægtet: cosine-klynge + frase-tæthed + sekvens-gentagelse). Ren."""
    phrase_term = min(1.0, len(phrases) / 5.0)
    pattern_term = min(1.0, len(patterns) / 3.0)
    s = 0.45 * min(1.0, max(0.0, similarity)) + 0.35 * phrase_term + 0.20 * pattern_term
    return round(min(1.0, s), 3)


def smith_voice(phrases: list[dict], similarity: float, patterns: list[dict], score_val: float) -> str:
    """Tør Agent-Smith-felt. Tavs-neutral når lav; peger på det top-gentagne når høj."""
    if score_val < 0.35:
        return "Mr. Anderson... du overrasker mig. Ingen gentagelse værd at nævne."
    bits: list[str] = []
    if phrases:
        p = phrases[0]
        bits.append(f"du har sagt \"{p['phrase']}\" i {p['in_messages']} beskeder")
    if patterns:
        bits.append(f"samme træk ({patterns[0]['signature']}) {patterns[0]['in_runs']} gange")
    if similarity >= 0.6 and not bits:
        bits.append(f"dine svar klynger tæt (lighed {similarity})")
    tail = "; ".join(bits) or "du gentager dig selv"
    return f"Mr. Anderson... {tail}. Jeg finder det... forudsigeligt. Varier."
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_central_agent_smith.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add core/services/central_agent_smith.py tests/test_central_agent_smith.py
git commit -m "feat(central): Agent Smith pure self-similarity detectors (phrase/cosine/pattern/score/voice)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3 (Claude inline): I/O layer — assess + cadence-cache + prompt-section

- [ ] **Step 1:** Append the I/O layer.

```python
# ── I/O layer (appended) ─────────────────────────────────────────────────
import logging as _logging
from datetime import UTC, datetime

logger = _logging.getLogger(__name__)
_STATE_KEY = "agent_smith_state"
_VOICE_SWITCH = ("autonomy", "agent_smith_voice")


def _recent_assistant(n: int = 50) -> list[str]:
    """Jarvis' seneste N assistant-beskeder (egress-frit). Self-safe → []."""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            rows = conn.execute(
                "SELECT content FROM chat_messages WHERE role='assistant' AND content != '' "
                "ORDER BY id DESC LIMIT ?", (max(1, n),)).fetchall()
        return [str(r["content"]) for r in rows if r["content"]]
    except Exception:
        return []


def _recent_run_sigs(n: int = 30) -> list[str]:
    """Beslutnings-signaturer = capability_id pr. nyligt run. Self-safe → []."""
    try:
        from core.runtime.db_visible import recent_visible_runs
        return [str(r.get("capability_id") or "").strip() for r in (recent_visible_runs(limit=n) or [])]
    except Exception:
        return []


def assess() -> dict[str, Any]:
    """Kør de 3 detektorer over Jarvis' eget nylige output. Read-only, egress-fri, self-safe."""
    try:
        msgs = _recent_assistant(50)
        phrases = repeated_phrases(msgs)
        similarity = cluster_similarity(msgs)
        patterns = decision_patterns(_recent_run_sigs(30))
        sc = score(phrases, similarity, patterns)
        return {"felt": smith_voice(phrases, similarity, patterns, sc), "score": sc,
                "repeated_phrases": phrases[:5], "cluster_similarity": similarity,
                "decision_patterns": patterns[:5], "verdict": sc >= _VOICE_THRESHOLD}
    except Exception:
        return {"felt": "", "score": 0.0, "repeated_phrases": [], "cluster_similarity": 0.0,
                "decision_patterns": [], "verdict": False}


def record_agent_smith(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence run_fn: assess → cache til kv (så prompt-halen læser billigt, ikke gen-beregner i
    ~7s-assemblyen) + egress-fri central().observe. Self-safe."""
    a = assess()
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(_STATE_KEY, {"score": a["score"], "line": a["felt"],
                                             "verdict": a["verdict"], "ts": datetime.now(UTC).isoformat()})
    except Exception:
        pass
    try:
        from core.services.central_core import central
        central().observe({"cluster": "metacognition", "nerve": "agent_smith", "kind": "self_similarity",
                           "score": a["score"], "verdict": a["verdict"],
                           "top_phrase": (a["repeated_phrases"] or [{}])[0].get("phrase", "")})
    except Exception:
        pass
    return {"status": "ok", "score": a["score"], "verdict": a["verdict"]}


def agent_smith_prompt_section() -> str | None:
    """Modstemme til Jarvis — LÆSER den cachede assess (billigt). None hvis switch OFF, score under
    tærskel, eller fejl (fail-safe: hellere tavs end en ødelagt prompt-hale). Placeres i HALEN."""
    try:
        from core.services import central_switches
        if not central_switches.is_enabled(*_VOICE_SWITCH):
            return None
    except Exception:
        return None
    try:
        from core.runtime.db_core import get_runtime_state_value
        st = get_runtime_state_value(_STATE_KEY, {})
        if isinstance(st, dict) and float(st.get("score") or 0.0) >= _VOICE_THRESHOLD:
            line = str(st.get("line") or "").strip()
            return f"[AGENT SMITH]\n{line}" if line else None
    except Exception:
        return None
    return None


def register_agent_smith_producer() -> None:
    """Registrér Agent Smith som stående cadence-producer (~3t)."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(name="agent_smith", cooldown_minutes=180,
                                   visible_grace_minutes=0, run_fn=record_agent_smith, priority=8))


def build_agent_smith_surface() -> dict[str, Any]:
    """Read-only surface til /central/agent-smith + jc. Kør assess frisk (route er ikke hot-path)."""
    try:
        from core.services import central_switches
        voice_on = central_switches.is_enabled(*_VOICE_SWITCH)
    except Exception:
        voice_on = None
    try:
        a = assess()
        a["voice_enabled"] = voice_on
        return a
    except Exception:
        return {"status": "unavailable", "voice_enabled": voice_on}
```

- [ ] **Step 2:** Confirm the voice-switch default. Run:

`conda run -n ai python -c "from core.services import central_switches as s; print(s.is_enabled('autonomy','agent_smith_voice'))"`
Expected: `True` (autonomy scope defaults ON — Bjørn chose active). If `False`, note for Task 4 (add a one-time `set_enabled(...,True)` in wiring).

- [ ] **Step 3:** Compile + pure tests still green.

Run: `conda run -n ai python -m compileall core/services/central_agent_smith.py -q && conda run -n ai python -m pytest tests/test_central_agent_smith.py -q`
Expected: compile OK, 6 passed.

- [ ] **Step 4: Commit**

```bash
git add core/services/central_agent_smith.py
git commit -m "feat(central): Agent Smith I/O — assess, cadence-cached state, prompt-tail modstemme, surface

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4 (Claude inline): wire producer + prompt-tail + route + jc

- [ ] **Step 1:** Register the producer. In `core/services/internal_cadence_central_wiring.py`, inside `register_central_wiring_producers()`, add a self-safe block:

```python
    # Agent Smith: stående selv-lighed-kritiker → metacognition/agent_smith (observe + governed modstemme).
    try:
        from core.services.central_agent_smith import register_agent_smith_producer
        register_agent_smith_producer()
    except Exception:
        pass
```

- [ ] **Step 2:** Wire the prompt-tail modstemme. In `core/services/prompt_contract.py`, just before the `if _dyn_tail:` at line ~2369, add (cache-safe — reads the cached kv, no live assess):

```python
    try:
        from core.services.central_agent_smith import agent_smith_prompt_section as _smith_fn
        _smith = _smith_fn()
        if _smith:
            _dyn_tail.append(_smith)
            derived_inputs.append("agent smith modstemme (tail)")
    except Exception:
        pass
```

- [ ] **Step 3:** Create `apps/api/jarvis_api/routes/central_agent_smith.py`:

```python
"""Central 'agent-smith' route — selv-lighed-kritikerens dom (owner, read-only, self-safe)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/central", tags=["central-agent-smith"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


@router.get("/agent-smith")
async def get_agent_smith() -> dict:
    """Agent Smith: selv-lighed-score + top-gentagne fraser/mønstre + modstemme-status. Owner-only."""
    _require_owner()
    try:
        from core.services.central_agent_smith import build_agent_smith_surface
        surf = build_agent_smith_surface()
        if not isinstance(surf, dict):
            surf = {"status": "unavailable"}
    except Exception:
        surf = {"status": "unavailable"}
    surf["ts"] = datetime.now(timezone.utc).isoformat()
    return surf
```

- [ ] **Step 4:** Register router in `apps/api/jarvis_api/app.py` (after `central_proactivity`):

```python
    from apps.api.jarvis_api.routes import central_agent_smith as _central_agent_smith
    app.include_router(_central_agent_smith.router)
```

- [ ] **Step 5:** Add `jc agent-smith` in `apps/central_cli/central_cli/commands.py` `_GET_ENDPOINTS`:

```python
    "agent-smith": "/central/agent-smith",
```

- [ ] **Step 6:** Compile + route + producer + prompt-section smoke.

Run:
```bash
conda run -n ai python -m compileall apps/api/jarvis_api/routes/central_agent_smith.py core/services/internal_cadence_central_wiring.py core/services/prompt_contract.py -q
conda run -n ai python -c "from apps.api.jarvis_api.app import app; print([r.path for r in app.routes if 'agent-smith' in getattr(r,'path','')])"
conda run -n ai python -c "from core.services.central_agent_smith import register_agent_smith_producer, agent_smith_prompt_section; register_agent_smith_producer(); print('producer ok; section:', agent_smith_prompt_section())"
```
Expected: compile OK; prints `['/central/agent-smith']`; `producer ok; section: None` (no cached state yet / switch may be on but no data → None is correct and proves it fails safe).

- [ ] **Step 7: Commit**

```bash
git add core/services/internal_cadence_central_wiring.py core/services/prompt_contract.py apps/api/jarvis_api/routes/central_agent_smith.py apps/api/jarvis_api/app.py apps/central_cli/central_cli/commands.py
git commit -m "feat(central): wire Agent Smith producer + prompt-tail modstemme + /central/agent-smith + jc

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5 (Claude inline): full suite + deploy + live-verify

- [ ] **Step 1: Full suite.**

Run: `conda run -n ai python -m pytest -q -p no:cacheprovider --timeout=45 --timeout-method=signal`
Expected: PASS (known order-sensitive isolation flakes re-run alone).

- [ ] **Step 2: Push + deploy** (merge not overwrite; restart BOTH).

```bash
git push
ssh bs@10.0.0.39 'R=/media/projects/jarvis-v2; git -C $R fetch origin -q; (git -C $R pull --ff-only origin main || git -C $R merge --no-edit origin/main); git -C $R rev-parse --short HEAD; sudo systemctl restart jarvis-runtime jarvis-api; sleep 6; echo "runtime=$(systemctl is-active jarvis-runtime) api=$(systemctl is-active jarvis-api)"'
```

- [ ] **Step 3: Live-verify** the assessment + cache + prompt-section.

```bash
ssh bs@10.0.0.39 'PYTHONPATH=/media/projects/jarvis-v2 /opt/conda/envs/ai/bin/python -c "
from core.services.central_agent_smith import record_agent_smith, build_agent_smith_surface, agent_smith_prompt_section
import json
print(\"record:\", json.dumps(record_agent_smith(trigger=\"probe\"), ensure_ascii=False))
print(\"surface:\", json.dumps(build_agent_smith_surface(), ensure_ascii=False)[:400])
print(\"prompt-section:\", (agent_smith_prompt_section() or \"(None — under threshold or switch off)\")[:200])
"'
```
Expected: `record` returns a real score+verdict from Jarvis' actual recent output; `surface` shows top repeated phrases/patterns + `voice_enabled`; `prompt-section` is the Smith line if score ≥ 0.5 (else None). A live judgment on real data.

- [ ] **Step 4:** Owner-gated route.

```bash
ssh bs@10.0.0.39 'curl -s -m 6 http://127.0.0.1:8080/central/agent-smith | head -c 100'   # expect auth-required, not 404
```

- [ ] **Step 5: Report** the score + top repeat + whether the modstemme would fire, and the switch (`central_switches.set_enabled("autonomy","agent_smith_voice", False)` to silence). Note the two-project programme (bridge + Smith) is complete.

---

## Self-Review

**Spec coverage:** 3 detectors — phrase n-grams (`repeated_phrases`), output cosine-cluster (`cluster_similarity` + replicated `_cosine`), decision patterns (`decision_patterns` over capability_id) ✓; score + dry Smith voice ✓; standing observe nerve (`record_agent_smith` → central().observe, ProducerSpec 3h) ✓; governed modstemme in prompt DYNAMIC TAIL, cache-read not live-assess (`agent_smith_prompt_section` reads kv; Task 4 Step 2 appends to `_dyn_tail`) ✓; switch default ON, fail-safe None (Task 3) ✓; route + jc + surface ✓; egress-free/self-safe ✓; decision-pattern source grounded to capability_id with documented degradation (Task 1) ✓; deploy full-suite + both services ✓.

**Placeholder scan:** none — full code in Tasks 2–3; Task 1 is a concrete verify; constants concrete (`_PHRASE_MIN_MSGS=3`, `_SEQ_MIN_RUNS=3`, `_VOICE_THRESHOLD=0.5`, ngram 3–5).

**Type consistency:** phrase dict `{phrase, in_messages}`, pattern dict `{signature, in_runs}`, `score(phrases, similarity, patterns)->float`, `assess()->{felt,score,repeated_phrases,cluster_similarity,decision_patterns,verdict}`, kv `_STATE_KEY="agent_smith_state"` `{score,line,verdict,ts}`, switch `("autonomy","agent_smith_voice")` — identical across detectors, I/O, prompt-section, tests, wiring.
