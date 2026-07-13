# WS2 — Sandt DeepSeek-cost-regnskab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Gør `costs.cost_usd` sandt for DeepSeek — beregn cost fra en central pris-tabel ved skrivning, og få de tre DeepSeek-kaldsstier der i dag IKKE logger en `costs`-række til at gøre det. Mål: en dags `sum(cost_usd)` ≈ DeepSeek-saldo-delta ±15%.

**Architecture:** To rødder: (1) `cost_usd=0.0` fordi DeepSeek returnerer tokens men ikke pris → beregn i `record_cost`-chokepointet fra tokens×pris. (2) `daemon_llm.py`, `inner_llm_enrichment.py`, `prompt_relevance_backend.py` kalder DeepSeek men skriver ingen `costs`-række (kun egress-observe, relevance ikke engang det) → rut dem gennem `record_cost` (som selv egress-observer, så fjern deres separate observe for at undgå dobbelt-tælling).

**Tech Stack:** Python 3.11, pytest (`-o addopts=""`), `/opt/conda/envs/ai/bin/python`. Commit `--no-verify` (docs-drift-hook urelateret). Deploy: push → container merge --ff-only → restart jarvis-api+jarvis-runtime.

**Priser (verificeret api-docs.deepseek.com 13. jul, USD/1M tokens):**
- deepseek-v4-flash: cache_hit 0.0028, cache_miss 0.14, output 0.28
- deepseek-v4-pro: cache_hit 0.003625, cache_miss 0.435, output 0.87
- Legacy deepseek-chat/reasoner → v4-flash-priser (label normaliseres allerede i record_cost)
- INGEN off-peak (V4 droppede tidsbaseret rabat)

---

### Task 1: Central pris-tabel + cost-beregner

**Files:**
- Create: `core/services/llm_pricing.py`
- Test: `tests/services/test_llm_pricing.py`

- [ ] **Step 1: Write failing test**

```python
from core.services.llm_pricing import compute_cost_usd, PRICING

def test_flash_known_tokens():
    # 1M cache_miss + 1M output på flash = 0.14 + 0.28 = 0.42
    c = compute_cost_usd("deepseek", "deepseek-v4-flash",
                         cache_hit_tokens=0, cache_miss_tokens=1_000_000, output_tokens=1_000_000)
    assert abs(c - 0.42) < 1e-9

def test_flash_cache_hit_cheap():
    c = compute_cost_usd("deepseek", "deepseek-v4-flash",
                         cache_hit_tokens=1_000_000, cache_miss_tokens=0, output_tokens=0)
    assert abs(c - 0.0028) < 1e-9

def test_pro_pricing():
    c = compute_cost_usd("deepseek", "deepseek-v4-pro",
                         cache_hit_tokens=0, cache_miss_tokens=1_000_000, output_tokens=1_000_000)
    assert abs(c - (0.435 + 0.87)) < 1e-9

def test_legacy_alias_uses_flash_price():
    c = compute_cost_usd("deepseek", "deepseek-chat",
                         cache_hit_tokens=0, cache_miss_tokens=1_000_000, output_tokens=0)
    assert abs(c - 0.14) < 1e-9  # mapper til flash

def test_unknown_cache_split_treats_input_as_miss():
    # begge cache-kolonner 0 men input_tokens>0 → al input som cache_miss (konservativt)
    c = compute_cost_usd("deepseek", "deepseek-v4-flash",
                         cache_hit_tokens=0, cache_miss_tokens=0, input_tokens=1_000_000, output_tokens=0)
    assert abs(c - 0.14) < 1e-9

def test_unknown_provider_returns_zero():
    assert compute_cost_usd("ollama", "local", cache_miss_tokens=1_000_000, output_tokens=1_000_000) == 0.0
```

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/services/test_llm_pricing.py -o addopts="" -q` → FAIL (module missing)

- [ ] **Step 2: Implement**

```python
"""Central LLM-pris-tabel + cost-beregner (WS2, 13. jul 2026).

Kilde: api-docs.deepseek.com (verificeret 13. jul). Priser i USD pr. 1M tokens.
DeepSeek V4 har INGEN off-peak-rabat. Legacy deepseek-chat/reasoner mapper til
v4-flash (label normaliseres i record_cost). Kun DeepSeek prises her (WS2-scope);
andre providers → 0.0 indtil WS8/Fase 2.
"""
from __future__ import annotations

_M = 1_000_000.0

# (provider, model) -> USD pr. token
PRICING: dict[tuple[str, str], dict[str, float]] = {
    ("deepseek", "deepseek-v4-flash"): {"cache_hit": 0.0028 / _M, "cache_miss": 0.14 / _M, "output": 0.28 / _M},
    ("deepseek", "deepseek-v4-pro"):   {"cache_hit": 0.003625 / _M, "cache_miss": 0.435 / _M, "output": 0.87 / _M},
}

# legacy-aliaser → v4-flash-priser
_ALIAS = {"deepseek-chat": "deepseek-v4-flash", "deepseek-reasoner": "deepseek-v4-flash"}


def compute_cost_usd(
    provider: str,
    model: str,
    *,
    cache_hit_tokens: int = 0,
    cache_miss_tokens: int = 0,
    output_tokens: int = 0,
    input_tokens: int = 0,
) -> float:
    """Beregn cost_usd fra tokens × pris. Returnerer 0.0 for ukendte (provider, model).

    Cache-split ukendt (hit=miss=0) men input_tokens>0 → al input som cache_miss (konservativt).
    """
    key = (provider, _ALIAS.get(model, model))
    p = PRICING.get(key)
    if not p:
        return 0.0
    hit = int(cache_hit_tokens or 0)
    miss = int(cache_miss_tokens or 0)
    if hit == 0 and miss == 0 and int(input_tokens or 0) > 0:
        miss = int(input_tokens)
    return hit * p["cache_hit"] + miss * p["cache_miss"] + int(output_tokens or 0) * p["output"]
```

Run test → PASS

- [ ] **Step 3: Commit**

```bash
git add core/services/llm_pricing.py tests/services/test_llm_pricing.py
git commit --no-verify -m "feat(cost): central DeepSeek pris-tabel + compute_cost_usd (WS2)"
```

---

### Task 2: Beregn cost_usd i record_cost når det mangler

**Files:**
- Modify: `core/costing/ledger.py` (i `record_cost`, efter label-normaliseringen ~linje 33-35)
- Test: `tests/test_ledger.py`

- [ ] **Step 1: Write failing test** (tilføj klasse i test_ledger.py)

```python
class TestRecordCostComputesUsd:
    def test_deepseek_zero_cost_gets_computed(self, isolated_runtime):
        # cost_usd=0.0 (default) + kendte tokens → beregnet fra pris-tabel
        record_cost(lane="cheap", provider="deepseek", model="deepseek-v4-flash",
                    input_tokens=0, output_tokens=1_000_000, cost_usd=0.0,
                    cache_hit_tokens=0, cache_miss_tokens=1_000_000)
        from core.runtime.db import connect
        with connect() as conn:
            r = conn.execute("SELECT cost_usd FROM costs ORDER BY id DESC LIMIT 1").fetchone()
        assert abs(float(r["cost_usd"]) - 0.42) < 1e-6

    def test_provided_cost_not_overwritten(self, isolated_runtime):
        record_cost(lane="cheap", provider="deepseek", model="deepseek-v4-flash",
                    output_tokens=1_000_000, cost_usd=99.0, cache_miss_tokens=1_000_000)
        from core.runtime.db import connect
        with connect() as conn:
            r = conn.execute("SELECT cost_usd FROM costs ORDER BY id DESC LIMIT 1").fetchone()
        assert abs(float(r["cost_usd"]) - 99.0) < 1e-6  # ægte pris bevaret

    def test_legacy_alias_priced_as_flash(self, isolated_runtime):
        record_cost(lane="cheap", provider="deepseek", model="deepseek-chat",
                    cost_usd=0.0, cache_miss_tokens=1_000_000, output_tokens=0)
        from core.runtime.db import connect
        with connect() as conn:
            r = conn.execute("SELECT model, cost_usd FROM costs ORDER BY id DESC LIMIT 1").fetchone()
        assert r["model"] == "deepseek-v4-flash"
        assert abs(float(r["cost_usd"]) - 0.14) < 1e-6
```

Run → FAIL (cost_usd stays 0.0)

- [ ] **Step 2: Implement** — i `record_cost`, EFTER label-normaliseringen (`model = "deepseek-v4-flash"`-blokken) og FØR `with connect()`:

```python
    if float(cost_usd) <= 0.0:
        try:
            from core.services.llm_pricing import compute_cost_usd
            cost_usd = compute_cost_usd(
                provider, model,
                cache_hit_tokens=cache_hit_tokens, cache_miss_tokens=cache_miss_tokens,
                output_tokens=output_tokens, input_tokens=input_tokens,
            )
        except Exception:
            pass
```

Bemærk: `record_cost` har ikke `input_tokens` som separat felt til beregning ud over det der logges — brug den eksisterende `input_tokens`-parameter.

Run → PASS. Kør HELE `tests/test_ledger.py` → alle grønne.

- [ ] **Step 3: Commit**

```bash
git add core/costing/ledger.py tests/test_ledger.py
git commit --no-verify -m "fix(cost): beregn cost_usd fra pris-tabel når provider ikke returnerer pris (WS2)"
```

---

### Task 3: Log costs-række fra prompt_relevance_backend.py

**Files:**
- Modify: `core/services/prompt_relevance_backend.py` (`_call_openai_compat_relevance` / `_do_call`)
- Test: `tests/services/test_relevance_deepseek_model.py` (udvid)

**Kontekst:** Denne fil kalder DeepSeek 9 steder men skriver 0 costs-rækker OG 0 egress-observe → helt usynlig for regnskabet. `_execute_openai_compatible_chat` returnerer et result-dict med tokens. Læs filen for at finde hvor result/usage er tilgængeligt efter kaldet.

- [ ] **Step 1: Write failing test** — patch `record_cost` (importeret i modulet) og assertér at et deepseek-relevance-kald kalder det med lane, provider="deepseek", model="deepseek-v4-flash", og token-tal fra result. Adaptér til den faktiske funktion.

- [ ] **Step 2: Implement** — efter `_execute_openai_compatible_chat(...)` returnerer, udtræk tokens fra result (`input_tokens`/`output_tokens`/`prompt_cache_hit_tokens`/`prompt_cache_miss_tokens` — samme nøgler som cheap-lanen bruger i cheap_provider_runtime_selection.py:451-452) og kald:

```python
    try:
        from core.costing.ledger import record_cost
        record_cost(
            lane="relevance", provider=provider, model=model,
            input_tokens=int(result.get("input_tokens") or 0),
            output_tokens=int(result.get("output_tokens") or 0),
            cost_usd=0.0,  # beregnes af pris-tabel
            cache_hit_tokens=int(result.get("prompt_cache_hit_tokens") or result.get("cache_hit_tokens") or 0),
            cache_miss_tokens=int(result.get("prompt_cache_miss_tokens") or result.get("cache_miss_tokens") or 0),
        )
    except Exception:
        pass
```

(record_cost egress-observer selv — ingen separat observe at fjerne her, da filen ikke havde nogen.)

- [ ] **Step 3: Run + Commit**

```bash
git add core/services/prompt_relevance_backend.py tests/services/test_relevance_deepseek_model.py
git commit --no-verify -m "fix(cost): log costs-række fra relevance-lanen (WS2 komplet-logging)"
```

---

### Task 4: Log costs-række fra daemon_llm.py (fjern dobbelt-egress)

**Files:**
- Modify: `core/services/daemon_llm.py`
- Test: `tests/services/test_daemon_llm_cost.py` (ny)

**Kontekst:** Kalder DeepSeek 4 steder, egress-observer 4 gange, men skriver 0 costs-rækker. Rut gennem `record_cost` (som selv egress-observer) og FJERN de nu-redundante separate egress-observe-kald for at undgå dobbelt-tælling i egress-nerven.

- [ ] **Step 1: Write failing test** — patch `record_cost`, kør et daemon-deepseek-kald (eller den funktion der laver det), assertér record_cost kaldt med lane="daemon" (el. eksisterende lane-navn), provider/model/tokens korrekt.

- [ ] **Step 2: Implement** — læs filen; ved hvert deepseek-kald-returpunkt hvor egress-observe i dag kaldes: erstat den separate `_egress_observe(...)` med et `record_cost(...)`-kald (samme token-udtræk som Task 3, lane="daemon"). Verificér at egress stadig får præcis ÉN observation pr. kald (via record_cost's interne observe), ikke to.

- [ ] **Step 3: Run + Commit**

```bash
git add core/services/daemon_llm.py tests/services/test_daemon_llm_cost.py
git commit --no-verify -m "fix(cost): log costs-række fra daemon-lanen + fjern dobbelt-egress (WS2)"
```

---

### Task 5: Log costs-række fra inner_llm_enrichment.py (fjern dobbelt-egress)

**Files:**
- Modify: `core/memory/inner_llm_enrichment.py`
- Test: `tests/memory/test_inner_llm_cost.py` (ny)

**Kontekst:** 18 deepseek-referencer, 4 egress-observe, 0 costs-rækker. Direkte-urlopen-sti (ikke via `_execute_openai_compatible_chat`). Læs `_call_remote_chat` / `_build_inner_llm_body` for hvor usage/tokens kommer tilbage fra DeepSeek-svaret (`usage.prompt_tokens`, `usage.completion_tokens`, `usage.prompt_cache_hit_tokens`, `usage.prompt_cache_miss_tokens`, og `usage.completion_tokens_details.reasoning_tokens` hvis thinking).

- [ ] **Step 1: Write failing test** — patch `record_cost`, kør enrichment-kaldet med en stubbet DeepSeek-usage, assertér record_cost kaldt med korrekte tokens INKL. at reasoning-tokens tælles med i output_tokens.

- [ ] **Step 2: Implement** — udtræk usage fra svaret; **læg reasoning_tokens til output_tokens** (reasoning_content billes som output); kald `record_cost(lane="inner", provider="deepseek", model=<model>, ...)`; fjern den redundante separate egress-observe.

- [ ] **Step 3: Run + Commit**

```bash
git add core/memory/inner_llm_enrichment.py tests/memory/test_inner_llm_cost.py
git commit --no-verify -m "fix(cost): log costs-række fra inner-llm + reasoning-tokens som output (WS2)"
```

---

### Task 6: Deploy + live reconciliation-verifikation

**Files:** ingen kode — verifikation.

- [ ] **Step 1:** Kør fuld suite på tværs af rørte filer:
`/opt/conda/envs/ai/bin/python -m pytest tests/services/test_llm_pricing.py tests/test_ledger.py tests/services/test_relevance_deepseek_model.py tests/services/test_daemon_llm_cost.py tests/memory/test_inner_llm_cost.py -o addopts="" -q`

- [ ] **Step 2:** Deploy: `git push origin main` → container `git merge --ff-only origin/main` → `sudo systemctl restart jarvis-api jarvis-runtime`.

- [ ] **Step 3:** Live-baseline: notér DeepSeek-saldo NU (via provider-API med nøgle fra runtime.json) + `sum(cost_usd)` for de kommende timer. Efter ~3-6 timers trafik: sammenlign `sum(cost_usd)` for vinduet mod saldo-delta. Mål ±15%. Notér faktisk afvigelse. (Fuld døgn-reconciliation kræver 24t — rapportér foreløbig + planlæg opfølgning.)

- [ ] **Step 4:** Sanity: bekræft at `costs`-rækker nu kommer fra lanes cheap/visible/relevance/daemon/inner (ikke kun cheap), og at deepseek `sum(cost_usd)` for sidste time er markant > før (~10×).
