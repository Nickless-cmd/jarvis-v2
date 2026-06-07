# Lag 1 — Credit Assignment Design

**Formål:** Lukke feedback-loopet mellem en beslutning og dens faktiske outcome.
Ingen flere heuristiske energy-level scores. Reelle data.

---

## 1. Hvad er problemet?

| Lag | Status |
|-----|--------|
| **Lag 2 (EMA-drift)** | ✅ Live — monitorerer om stemmen driver over tid |
| **Lag 1 (credit assignment)** | ❌ DB + daemon-hook findes, **men `record_choice()` kaldes aldrig** for reelle beslutninger |

Konkret:
- `_estimate_credit_score()` bruger energy-level heuristik (3.0 ± signal-støj)
- Meta-reflection daemonen scanner efter `kind="prompt_variant"` — men ingen prompt-varianter registreres
- `aesthetic_taste_daemon.record_choice()` logger mode/style, ikke beslutninger
- **Ingen beslutning bliver nogensinde evalueret på sit faktiske outcome**

---

## 2. Decision kinds — hvad skal trackes?

### Phase 1 (implementer nu) — 3 decision kinds

| Kind | Eksempel | Instrumenteringspunkt |
|------|----------|-----------------------|
| **`provider_routing`** | "deepseek via OpenRouter vs direkte vs Ollama" | `select_cheap_lane_target()` + `resolve_role_model()` |
| **`model_tier`** | "fast vs reasoning vs deep" | `classify_reasoning_tier()` |
| **`response_style`** | "kort/direkte vs lang/reflekterende" | Før hvert svar (i tool-execution layer) |

### Phase 2 (næste) — 2 decision kinds

| Kind | Eksempel | Instrumenteringspunkt |
|------|----------|-----------------------|
| **`tool_path`** | "search vs read vs spawn agent" | Før tool-selection i ReAct loop |
| **`priority`** | "user-task vs proactive vs wakeup" | heartbeat `_phase1_rule_based_decision()` |

---

## 3. Hvornår er outcome klart? (outcome horizon)

| Decision kind | Horizon | Signal | 
|---------------|---------|--------|
| `provider_routing` | **Inden for 1 turn** | Lykkedes kaldet? (status=ok vs error/timeout) |
| `model_tier` | **Inden for 3 turns** | Krævede det korrektion? Var svaret brugbart? |
| `response_style` | **Brugerens næste besked** | Engagement-signal (tak/viderefør vs korrektion/afbrud) |
| `tool_path` (Phase 2) | **Ved task completion** | Blev opgaven løst med færrest steps? |
| `priority` (Phase 2) | **Ved session-end / timeout** | Blev noget vigtigt forsømt? |

---

## 4. Scoring model — fra heuristik til outcome-based

### 4.1 Nuværende (skal erstattes)

```python
def _estimate_credit_score(decision, cross_snapshot):
    score = 3.0  # altid neutral
    # tilfældige ±1 baseret på concurrent energy level
    ...
```

Dette **måler ikke outcome**. Det måler korreleret støj.

### 4.2 Ny model

Hver outcome har **en primær scorer** og **0-2 boostere**:

```
outcome_score = primary * 0.6 + booster_1 * 0.25 + booster_2 * 0.15
```

**Provider routing — primary scorer:**

| Udfald | Score |
|--------|-------|
| `status=ok` + latency < 2s | 5.0 |
| `status=ok` + latency 2-5s | 4.0 |
| `status=ok` + latency > 5s | 3.0 |
| `status=error` + auto-failover worked | 2.5 |
| `status=error` + no fallback | 1.0 |

Booster: `cost_per_token < median` → +0.5

**Model tier — primary scorer:**

| Udfald | Score |
|--------|-------|
| Tier korrekt (ingen bruger-korrektion, task completed) | 4.0 |
| Tier for høj (over-engineered, spildte tokens) → next turn var "bare gør X" | 2.0 |
| Tier for lav (missede nuance, måtte gøres om) | 1.5 |
| Tier skiftet midlertidigt (auto-eskalation) | 3.5 |

Booster: `task_completion_detected` (goal advancement) → +1.0

**Response style — primary scorer:**

| Udfald | Score |
|--------|-------|
| Bruger svarer med engagement (tak, smiles, uddybning) | 4.5 |
| Bruger fortsætter uden reaktion på stil | 3.5 |
| Bruger korrigerer / afbryder / ignorerer | 1.5 |
| Bruger beder om kortere/længere svar | 2.0 |

Booster: `stil matcher brugerens egen stil` → +0.5

---

## 5. Implementation

### 5.1 Nye funktioner i `db_credit_assignment.py`

```python
def score_provider_outcome(decision_id: str, result: dict) -> dict:
    """Score a provider_routing decision based on actual call result."""
    status = result.get("status", "error")
    latency = result.get("latency_ms", 99999)
    
    if status == "ok":
        if latency < 2000:  primary = 5.0
        elif latency < 5000: primary = 4.0
        else:                primary = 3.0
    else:
        if result.get("fallback_used"): primary = 2.5
        else:                           primary = 1.0
    
    booster = 0.0
    cost = result.get("cost_per_token", 0)
    if cost and cost < _get_median_cost():
        booster = 0.5
    
    return link_outcome_to_decision(
        decision_id=decision_id,
        credit_score=primary + booster,
        rationale=f"provider: {status}, latency={latency}ms, cost_booster={booster}",
        evidence_summary=json.dumps({"latency_ms": latency, "cost": cost, "status": status}),
    )


def score_tier_outcome(decision_id: str, tier_result: dict, next_turns: list[dict]) -> dict:
    """Score a model_tier decision after observing subsequent turns."""
    ...


def score_response_outcome(decision_id: str, user_reply: str) -> dict:
    """Score a response_style decision based on user engagement."""
    ...
```

### 5.2 Instrumentering — hvor kaldes `record_choice()`?

**Provider routing** — i `cheap_provider_runtime.py`:

```python
# Før kald:
choice_id = record_choice(
    kind="provider_routing",
    title=f"Vælg provider for {task_kind}",
    options=[p["name"] for p in healthy_providers],
    decision=selected_provider,
    why=f"priority={reason}, health={health_score}",
)

# Efter kald:
score_provider_outcome(choice_id, result)
```

**Model tier** — i `reasoning_classifier.py` kald-stedet:

```python
choice_id = record_choice(
    kind="model_tier",
    title=f"Reasoning tier for: {message[:60]}",
    options=["fast", "reasoning", "deep"],
    decision=tier,
    why=", ".join(signals),
)
# Score efter N turns via en callback
```

**Response style** — i `heartbeat_runtime.py` eller tool-execution:

```python
choice_id = record_choice(
    kind="response_style",
    title="Svar-stil",
    options=["short_direct", "elaborate", "technical"],
    decision=chosen_style,
    why=f"tone={tone_signal}, complexity={complexity}",
)
```

### 5.3 Outcome hooks — hvornår scores beslutningen?

| Decision kind | Score-hook | Trigger |
|---------------|------------|---------|
| provider_routing | **Synkront** — lige efter kaldet | `execute_cheap_lane` returnerer |
| model_tier | **Asynkront** — N turns senere | Ny `user_message` eventbus hook |
| response_style | **Asynkront** — brugerens næste besked | `user_message` eventbus hook |

### 5.4 Meta-reflection daemon — opdatering

Erstat `_estimate_credit_score()` med:

```python
def _check_outcomes(cross_snapshot: dict) -> dict:
    """Scan for pending outcomes (decisions with no outcome_aggregate).
    
    For provider_routing: already scored synchronously, nothing to do.
    For model_tier + response_style: check if enough turns have passed
    to evaluate outcome, then call score_*_outcome().
    """
    unreviewed = list_unreviewed_decisions(kind="model_tier", limit=5)
    for dec in unreviewed:
        # Check if N turns have passed since decision was made
        turns_since = _count_turns_since(dec["created_at"])
        if turns_since >= 3:
            score_tier_outcome(dec["decision_id"], ...)
    
    unreviewed_style = list_unreviewed_decisions(kind="response_style", limit=5)
    for dec in unreviewed_style:
        next_user = _get_next_user_message_after(dec["created_at"])
        if next_user:
            score_response_outcome(dec["decision_id"], next_user["text"])
```

---

## 6. Success-kriterier

| Kriterie | Måling |
|----------|--------|
| `record_choice()` kaldes for ≥1 real decision kind | Count i DB efter 24h ≥ 10 |
| Outcome scores ≠ 3.0 konstant | Standard deviation over 10 scores ≥ 0.5 |
| Meta-reflection daemon scorer IKKE med heuristik længere | Tjek: ingen `_estimate_credit_score()` kald |
| Mindst én beslutning har `outcome_aggregate` < 2.0 eller > 4.0 | Query: `SELECT outcome_aggregate FROM cognitive_decisions` |

---

## 7. Ikke i scope (endnu)

- Lag 1 for `tool_path` og `priority` (Phase 2)
- Automatisk justering af adfærd baseret på outcome (det er Lag 3)
- Visualisering af credit trends (kommer når data er der)
