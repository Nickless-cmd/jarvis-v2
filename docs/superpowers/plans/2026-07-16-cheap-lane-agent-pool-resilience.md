# Cheap-lane + Agent-pool Resilience — Implementation Plan (rådskorrigeret)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development eller
> superpowers:executing-plans til at eksekvere task-for-task. Steps bruger checkbox (`- [ ]`).

**Goal:** Løft Jarvis' gratis LLM-kraft: auto-aktivér flere gratis-nøgle-konti (multi-profil),
lad cheap-lane-poolen overtage efter ollama på ALLE ikke-visible runs, og lær kvoter adaptivt —
så det autonome loop ikke bryder og degraderer pænt til floor. Visible (deepseek) urørt.

**Architecture:** Fundament-først. `BalancerSlot.slot_id` udvides til at bære `auth_profile`
(Fund #1) FØR alt andet, ellers kolliderer default+account2 på state/kvote. Multi-profil aktiveres
på BEGGE stier men den KANONISKE er selection-stien (`execute_cheap_lane_via_pool`, Bjørn-beslutning
B2). account2 er en LAVERE fallback-tier (B1 — aldrig round-robin på tværs af samme provider-konti,
ban-risiko). Adaptiv kvote-læring er sikret (Fund #4): kun på ægte quota-exhausted 429, med
korroboration, config-gulv og døgn-reset. Global leaky-bucket (Fund #5) før balanceren. Alle nye
adfærd flag-gated shadow-først (Fund #9).

**Spec:** docs/superpowers/specs/2026-07-16-cheap-lane-agent-pool-resilience.md

**Tech:** Python 3.11, `/opt/conda/envs/ai/bin/python -m pytest ... -o addopts=""`. Deploy: commit→
push origin→ container `git fetch && reset --hard origin/main`→ `sudo systemctl restart jarvis-runtime jarvis-api`.

---

## Re-baseline mod HEAD (16. jul — hvorfor planen skiftede form)

Målt, ikke antaget. Rådets Fund #10 bekræftet: **hele WS5 (config-fixes) er dødt** — gemini
(`gemini-flash-latest`), cloudflare (`{account_id}`-URL), ollamafreeapi (`base_url=""` by design)
er ALLEREDE korrekte; openrouter har ingen statisk `:free`-model (dynamisk). WS5 → én
live-verifikation (Task 17), nul kodeændring. **Allerede løst siden rådsmødet:** SQLite
daily-headroom (`_daily_used_from_db`), reliability-vægtning, static_models-injektion. **Reelt
tilbage:** Fund #1 (slot_id), WS1 (profil-scan mangler på begge stier), WS3 (fallback), Fund #5
(rate-cap), WS2 (adaptiv læring), plus B1-konflikt-fix (account2 = fallback-tier, ikke RR).

## Ground-truth ankre (verificeret via kodelæsning)
- `core/services/cheap_lane_balancer.py`: `BalancerSlot` (L19, har `auth_profile`-felt L23),
  `slot_id`=`f"{provider}::{model}"` (L30-31, **mangler auth_profile**), `SlotState` (L35, har
  `daily_use_count` L41 — de-facto dødt, headroom kommer fra SQLite), `_daily_used_from_db(provider)`
  (L250, tæller per-provider), `_compute_weight` (L294), `_register_failure` (L346), `_select_slot`
  (L457), `call_balanced` (L630), `build_slot_pool` (L855, læser kun provider_router.json).
- `core/services/cheap_provider_runtime_selection.py`: `execute_cheap_lane_via_pool` (L476, to
  exit-former: floor-return L498 + raise L545, begge emitter `runtime.cheap_lane_exhausted` L492/L540),
  `select_cheap_lane_target` (L390), `_configured_cheap_candidates` (L780, single-profil).
- `core/services/central_router_adapt.py`: `resolve_autonomous_model` (L289, hard-guard mod betalt
  deepseek L304), `_LIVE_FLAG="model_router_adapt_live_enabled"` (L26).
- `core/services/visible_runs.py`: autonom-seam = `stream_visible_model(...)`-kaldet (L1456) i
  `_pump_model_stream`, exception fanget L1465; `VisibleRun.autonomous` (L459) markerer autonome runs.
- `core/runtime/db_cheap_provider.py`: `record_cheap_provider_invocation` (L214),
  `count_cheap_provider_invocations` (L292) — tabellen `cheap_provider_invocations` (L232) har
  **ingen auth_profile-kolonne**.

---

## File Structure
- Modify: `core/services/cheap_lane_balancer.py` — slot_id (P0), profil-scan (P1), tier (P2), læring (P5)
- Modify: `core/services/cheap_provider_runtime_selection.py` — profil-scan (P1), fallback-indgang (P3)
- Create: `core/services/non_visible_fallback.py` — ollama→cheap-lane fallback-helper (P3)
- Create: `core/services/auth_profile_scan.py` — delt profil-scanner (P1)
- Create: `core/services/non_visible_rate_cap.py` — leaky-bucket (P4)
- Modify: `core/runtime/db_cheap_provider.py` — auth_profile-kolonne + filter (P0)
- Modify: `core/services/visible_runs.py` — wire autonom-seam gennem fallback (P3)
- Modify: `apps/api/jarvis_api/routes/cheap_balancer.py` — snapshot tolererer nyt slot_id (P0)
- Tests: `tests/test_cheap_lane_balancer.py`, `tests/test_cheap_provider_runtime_selection.py`,
  `tests/test_non_visible_fallback.py`, `tests/test_auth_profile_scan.py`,
  `tests/test_non_visible_rate_cap.py`, `tests/test_db_cheap_provider.py`

**Flag-navne (alle default OFF/shadow):** `cheap_pool_multiprofile_enabled`,
`non_visible_ollama_fallback_enabled`, `cheap_pool_adaptive_quota_enabled`,
`non_visible_rate_cap_enabled`.

---

## Fase P0 — Fundament: slot_id bærer auth_profile (Fund #1) — FØRST, blokerer alt

### Task 1: slot_id inkluderer auth_profile
**Files:** Modify `core/services/cheap_lane_balancer.py` (L30-31); Test `tests/test_cheap_lane_balancer.py`
- [ ] **Step 1:** Skriv fejlende test:
```python
def test_slot_id_includes_auth_profile():
    from core.services.cheap_lane_balancer import BalancerSlot
    a = BalancerSlot(provider="groq", model="x", auth_profile="default",
                     base_url="", rpm_limit=None, daily_limit=None, is_public_proxy=False)
    b = BalancerSlot(provider="groq", model="x", auth_profile="account2",
                     base_url="", rpm_limit=None, daily_limit=None, is_public_proxy=False)
    assert a.slot_id != b.slot_id
    assert a.slot_id == "groq::x::default"
    assert b.slot_id == "groq::x::account2"
```
- [ ] **Step 2:** Kør → FAIL (begge er `groq::x`).
- [ ] **Step 3:** Ret `slot_id` (L30-31) til `f"{self.provider}::{self.model}::{self.auth_profile or 'default'}"`.
  Ret også `build_slot_pool`'s `seen`-dedup (L906) og static-models-loopets `sid` (L924) til at
  bruge `slot.slot_id`/samme 3-delte nøgle (ikke `f"{provider}::{model}"`).
- [ ] **Step 4:** Kør → PASS.
- [ ] **Step 5:** Kør HELE `tests/test_cheap_lane_balancer.py` → fang eksisterende tests der hardkoder
  det 2-delte slot_id; opdatér dem til 3-delt. Commit.

### Task 2: cheap_provider_invocations får auth_profile-kolonne (per-profil-kvote)
**Files:** Modify `core/runtime/db_cheap_provider.py` (L214, L292); Test `tests/test_db_cheap_provider.py`
- [ ] **Step 1:** Skriv fejlende test:
```python
def test_count_filters_by_auth_profile(isolated_runtime):
    from core.runtime.db_cheap_provider import (
        record_cheap_provider_invocation, count_cheap_provider_invocations)
    record_cheap_provider_invocation(provider="groq", status="ok", auth_profile="default")
    record_cheap_provider_invocation(provider="groq", status="ok", auth_profile="account2")
    since = "1970-01-01"
    assert count_cheap_provider_invocations(provider="groq", since=since, auth_profile="default") == 1
    assert count_cheap_provider_invocations(provider="groq", since=since, auth_profile="account2") == 1
    # uden filter = begge (bagudkompat)
    assert count_cheap_provider_invocations(provider="groq", since=since) == 2
```
- [ ] **Step 2:** Kør → FAIL (`auth_profile` er ukendt kwarg).
- [ ] **Step 3:** Tilføj `auth_profile TEXT NOT NULL DEFAULT ''` i BEGGE `CREATE TABLE`-blokke
  (L232 + L310). Migration for eksisterende tabel: efter `CREATE TABLE IF NOT EXISTS`, kør
  `try: conn.execute("ALTER TABLE cheap_provider_invocations ADD COLUMN auth_profile TEXT NOT NULL DEFAULT ''") except Exception: pass`
  (idempotent — fejler tavst hvis kolonnen findes). Tilføj `auth_profile: str = ""` kwarg til
  `record_cheap_provider_invocation` (insert-kolonne + værdi) og til `count_cheap_provider_invocations`
  (`if auth_profile: query.append("AND auth_profile = ?"); params.append(auth_profile)`). Returnér
  `auth_profile` i record-dict'en.
- [ ] **Step 4:** Kør → PASS.
- [ ] **Step 5:** Commit.

### Task 3: _daily_used_from_db og invocation-recording er profil-bevidste
**Files:** Modify `core/services/cheap_lane_balancer.py` (L250-268), `core/services/cheap_provider_runtime_selection.py` (record-kald L234/L549/L1082); Test begge
- [ ] **Step 1:** Test `test_daily_headroom_is_per_profile`:
```python
def test_daily_used_from_db_per_profile(isolated_runtime):
    from core.runtime.db_cheap_provider import record_cheap_provider_invocation as rec
    from core.services import cheap_lane_balancer as bal
    for _ in range(3): rec(provider="groq", status="ok", auth_profile="default")
    rec(provider="groq", status="ok", auth_profile="account2")
    assert bal._daily_used_from_db("groq", "default") == 3
    assert bal._daily_used_from_db("groq", "account2") == 1
```
- [ ] **Step 2:** FAIL (`_daily_used_from_db` tager kun `provider`).
- [ ] **Step 3:** Udvid `_daily_used_from_db(provider, auth_profile="")` → send `auth_profile` til
  `count_cheap_provider_invocations`. `_daily_headroom_for(slot)` sender `slot.auth_profile`.
  I selection-stien: hvert `record_cheap_provider_invocation`-kald (L234/L549/L1082) sender den
  valgte kandidats `auth_profile`. **Bagudkompat:** tom `auth_profile` = uændret adfærd
  (tæller alle) → gamle rækker uden profil forsvinder ikke.
- [ ] **Step 4:** PASS.
- [ ] **Step 5:** Verificér snapshot/MC ikke brækker på 3-delt slot_id: kør
  `tests/` for `cheap_balancer`-route + `apps/api/jarvis_api/routes/cheap_balancer.py` importér-smoke.
  Ret `reset_slot`/`disable_slot`/`enable_slot` hvis de parser slot_id (de bruger den som opak
  nøgle → ingen ændring forventet). Commit.

---

## Fase P1 — Multi-profil auto-aktivering (WS1, kanonisk = selection-sti)

### Task 4: delt profil-scanner
**Files:** Create `core/services/auth_profile_scan.py`; Test `tests/test_auth_profile_scan.py`
- [ ] **Step 1:** Test:
```python
def test_scan_profiles_for_provider(tmp_path, monkeypatch):
    # byg auth/profiles/{default,account2}/providers/groq/state.json+credentials.json
    from core.services import auth_profile_scan as s
    monkeypatch.setattr(s, "_profiles_root", lambda: tmp_path)
    _make_ready(tmp_path, "default", "groq"); _make_ready(tmp_path, "account2", "groq")
    profs = s.ready_profiles_for("groq")
    assert set(profs) == {"default", "account2"}
def test_scan_skips_unready(tmp_path, monkeypatch):
    from core.services import auth_profile_scan as s
    monkeypatch.setattr(s, "_profiles_root", lambda: tmp_path)
    _make_ready(tmp_path, "default", "groq")  # kun default har gyldig cred
    assert s.ready_profiles_for("groq") == ["default"]
```
- [ ] **Step 2:** FAIL (modul findes ikke).
- [ ] **Step 3:** Implementér `_profiles_root()` (→ `~/.jarvis-v2/auth/profiles`, override via
  `JARVIS_CONFIG_DIR`-nær sti), `ready_profiles_for(provider) -> list[str]`: iterér profil-mapper,
  for hver kald `provider_auth_ready(provider=provider, auth_profile=profil)` (importér fra
  `cheap_provider_runtime_adapters`); returnér sorteret liste (default først). **Cache TTL 60s**
  (modul-global dict `{provider: (expiry, list)}`) så hot-path ikke rammer FS pr. kald.
  `default` altid først i listen (determinisme + tier-ordning i P2).
- [ ] **Step 4:** PASS.
- [ ] **Step 5:** Test `test_cache_ttl` (to hurtige kald → ét FS-scan via monkeypatch-tæller). Commit.

### Task 5: build_slot_pool danner slot pr. (provider, profil)
**Files:** Modify `core/services/cheap_lane_balancer.py::build_slot_pool` (L855); Test `tests/test_cheap_lane_balancer.py`
- [ ] **Step 1:** Test `test_build_slot_pool_multiprofile`:
```python
def test_build_slot_pool_includes_account2(monkeypatch):
    # router har groq (cheap); begge profiler ready
    monkeypatch.setattr(bal, "_router_enabled_models", lambda: [
        {"provider":"groq","model":"llama-x","enabled":True,"lane":"cheap","auth_profile":"default"}])
    monkeypatch.setattr("core.services.auth_profile_scan.ready_profiles_for",
                        lambda p: ["default","account2"] if p=="groq" else ["default"])
    monkeypatch.setattr(bal, "_credentials_ready", lambda p,a: True)
    ids = {s.slot_id for s in bal.build_slot_pool()}
    assert "groq::llama-x::default" in ids and "groq::llama-x::account2" in ids
```
- [ ] **Step 2:** FAIL (kun default-slot i dag).
- [ ] **Step 3:** Gate bag flag `cheap_pool_multiprofile_enabled` (default OFF → kun `default`,
  uændret). Når ON: for hver router-model OG hver static-model, erstat den enkelte
  `auth_profile`-værdi med et loop over `auth_profile_scan.ready_profiles_for(provider)`; dan én
  `BalancerSlot` pr. profil. Bevar `_EXCLUDED_PROVIDERS`/routable/paid-filtrene. Dedup på
  3-delt `slot_id`.
- [ ] **Step 4:** PASS (+ verificér OFF-sti uændret via `test_multiprofile_off_is_single`).
- [ ] **Step 5:** Commit.

### Task 6: _configured_cheap_candidates danner kandidat pr. profil (KANONISK sti, B2)
**Files:** Modify `core/services/cheap_provider_runtime_selection.py::_configured_cheap_candidates` (L780); Test `tests/test_cheap_provider_runtime_selection.py`
- [ ] **Step 1:** Test `test_candidates_multiprofile`: to profiler ready for groq → to kandidat-rækker
  (samme provider/model, forskellig `auth_profile`), begge når flag ON.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Samme mønster som Task 5, bag SAMME flag. For hver kandidat-provider: loop over
  `ready_profiles_for(provider)` → én kandidat-dict pr. profil med korrekt `auth_profile`. Behold
  eksisterende filtre (paid/proxy/quota). **Vigtigt:** dette er den sti alle forbrugere + agent-pool
  bruger — poolen forenes her (B2).
- [ ] **Step 4:** PASS (+ OFF-sti = single-profil uændret).
- [ ] **Step 5:** Commit.

### Task 7: keyless providers = én slot (ingen per-profil-dup)
**Files:** Modify begge stier; Test begge
- [ ] **Step 1:** Test at pollinations/ovhcloud/ollamafreeapi/arko (auth_kind="none") danner PRÆCIS
  én slot/kandidat (profil "default"), selv med flere profil-mapper.
- [ ] **Step 2:** FAIL (loop ville duplikere).
- [ ] **Step 3:** I begge loops: hvis `provider_auth_ready` er profil-uafhængig (keyless — tjek via
  en `_is_keyless(provider)`-helper i `auth_profile_scan`, baseret på `CHEAP_PROVIDER_DEFAULTS[p].auth_kind=="none"`
  eller provider i `_PUBLIC_PROXIES`) → tving `ready_profiles_for` til `["default"]`.
- [ ] **Step 4:** PASS. Commit.

---

## Fase P2 — Egress-adskillelse: account2 = ÆGTE parallel-tier via proxy (B1 løst af IP-adskillelse)

**Kontekst (bevist + hærdet 16.jul, se [[reference_expressvpn_egress_gateway]]):** to hærdede,
reboot-persistente egress-containere giver account2 en ANDEN egress-IP end default → B1's ban-risiko
(samme IP + skiftevis konti på samme provider) er VÆK → account2 kan round-robines LIGEVÆRDIGT med
default (~2× kapacitet), ikke kun lav-vægtet fallback. Egress-stier: **ct106 `http://10.0.0.45:8888`
= ExpressVPN** for 12 providers; **ct107 `http://10.0.0.46:8888` = HE-IPv6** for KUN groq (Cloudflare
blokerer groq-VPN-IP, men accepterer HE-IPv6). Alle 13 account2-providers dækket, egress-accept
empirisk bevist.

### Task 8: BalancerSlot.egress + egress-resolution
**Files:** Modify `core/services/cheap_lane_balancer.py` (BalancerSlot) + ny `core/services/egress_routing.py`; Test `tests/test_egress_routing.py`
- [ ] **Step 1:** Test `test_resolve_egress`:
```python
def test_resolve_egress():
    from core.services.egress_routing import resolve_egress
    assert resolve_egress("cohere", "default") == "home"
    assert resolve_egress("cohere", "account2") == "vpn"
    assert resolve_egress("groq", "account2") == "he6"   # groq-undtagelse (VPN blokeret)
    assert resolve_egress("groq", "default") == "home"
```
- [ ] **Step 2:** FAIL (modul findes ikke).
- [ ] **Step 3:** Ny `egress_routing.py`: `EGRESS_ROUTES` config (per-provider override; groq→he6),
  `PROXY_ENDPOINTS = {"vpn":"http://10.0.0.45:8888","he6":"http://10.0.0.46:8888","home":None}`
  (læs fra runtime-config m. disse som default). `resolve_egress(provider, auth_profile)`: default-
  profil → "home"; ikke-default (account2, account3…) → per-provider override el. "vpn". Tilføj
  `egress: str = "home"` felt til `BalancerSlot` (sat i build_slot_pool/candidates via resolve_egress).
- [ ] **Step 4:** PASS.
- [ ] **Step 5:** Commit.

### Task 8b: executor router pr. egress (proxy-injektion + leak-værn)
**Files:** Modify `core/services/cheap_provider_runtime_selection.py` (`_execute_provider_chat`) + balancer-kald; Test `tests/test_cheap_provider_runtime_selection.py`
- [ ] **Step 1:** Test `test_executor_sets_proxy_per_egress`:
```python
def test_proxy_injection(monkeypatch):
    from core.services import egress_routing as er
    seen = {}
    monkeypatch.setattr(mod, "_http_provider_call", lambda **k: seen.update(k) or {"text":"ok"})
    mod._execute_provider_chat(provider="cohere", model="m", auth_profile="account2",
                               egress="vpn", message="hej")
    assert seen["proxies"]["https"] == "http://10.0.0.45:8888"
def test_home_egress_no_proxy(monkeypatch):
    ... egress="home" -> seen.get("proxies") is None
def test_leak_guard(): # egress=vpn men proxy-endpoint mangler -> raise, ALDRIG hjemme-IP
    import pytest
    with pytest.raises(RuntimeError): mod._resolve_proxy("vpn", endpoints={})
```
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Executor slår `PROXY_ENDPOINTS[slot.egress]` op og sætter `proxies={"https":ep,"http":ep}`
  på HTTP-kaldet når egress != "home". **Leak-værn (Fund #6-analog):** hvis egress ∈ {vpn,he6} men
  endpoint mangler/tom → `raise RuntimeError` (aldrig fald til hjemme-IP med account2 — det ville
  korrelere kontiene). Gate bag `cheap_pool_multiprofile_enabled`.
- [ ] **Step 4:** PASS.
- [ ] **Step 5:** Selvhelbred: proxy-endpoint uNåelig (ConnectionError) → registrér som slot-failure
  (cooldown), IKKE crash; account2-slot falder ud, default fortsætter. Test. Commit.

### Task 8c: account2 = ligeværdig parallel RR-tier
**Files:** Modify `_compute_weight` (L294) + `_select_slot` (L457); Test `tests/test_cheap_lane_balancer.py`
- [ ] **Step 1:** Test `test_account2_equal_weight_rr`:
```python
def test_account2_parallel_rr(now=1000.0):
    sd = _slot("groq","x","default","home"); sa = _slot("groq","x","account2","he6")
    st = SlotState(slot_id="")
    # ligeværdig vægt (egress-adskillelse fjerner B1-risiko) → begge vælges over tid
    assert bal._compute_weight(sd, st, now) == bal._compute_weight(sa, st, now) > 0
```
- [ ] **Step 2:** FAIL hvis nogen tier-nedvægtning af account2 findes.
- [ ] **Step 3:** account2-slots får SAMME vægt-tier som default (INGEN `_TIER_WEIGHT`-nedvægtning —
  den gamle B1-fallback-idé udgår, egress-adskillelsen gør parallel kørsel sikker). RR/tie-break
  spreder mellem default+account2 på samme provider for jævn kvote-brug. **Bevar** leak-værnet fra
  Task 9 som den eneste sikkerhedsmekanisme.
- [ ] **Step 4:** PASS.
- [ ] **Step 5:** Test `test_account2_falls_out_if_proxy_down` (proxy nede → account2-slot cooldown,
  default bærer alene). Commit.

---

## Fase P3 — ollama → cheap-lane fallback for ikke-visible (WS3, rygraden)

### Task 9: fallback-helper (primary → cheap-pool → floor)
**Files:** Create `core/services/non_visible_fallback.py`; Test `tests/test_non_visible_fallback.py`
- [ ] **Step 1:** Test:
```python
def test_ollama_failure_falls_to_cheap_pool(monkeypatch):
    from core.services import non_visible_fallback as f
    monkeypatch.setattr(f, "execute_cheap_lane_via_pool",
                        lambda **k: {"text":"ok","lane":"cheap","provider":"groq"})
    def boom(**k): raise RuntimeError("quota")
    r = f.run_non_visible_with_fallback(message="hej", primary_call=boom, run_is_autonomous=True)
    assert r["lane"] == "cheap"
def test_visible_is_rejected():
    from core.services import non_visible_fallback as f
    import pytest
    with pytest.raises(AssertionError):
        f.run_non_visible_with_fallback(message="x", primary_call=lambda **k: {}, run_is_autonomous=False)
def test_pool_exhausted_returns_floor(monkeypatch):
    from core.services import non_visible_fallback as f
    monkeypatch.setattr(f, "execute_cheap_lane_via_pool",
                        lambda **k: (_ for _ in ()).throw(RuntimeError("all failed")))
    monkeypatch.setattr(f, "attempt_floor", lambda **k: {"text":"","lane":"floor"})
    r = f.run_non_visible_with_fallback(message="x", primary_call=lambda **k:(_ for _ in ()).throw(RuntimeError("q")),
                                        run_is_autonomous=True)
    assert r["lane"] == "floor"
```
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Implementér `run_non_visible_with_fallback(*, message, primary_call, run_is_autonomous, task_kind="default")`:
  - **Hård isolation-assertion (Fund #6):** `assert run_is_autonomous, "fallback må ALDRIG ramme visible lane"`.
  - Prøv `primary_call()` (ollama). Ved success → returnér.
  - Ved exception → gate `non_visible_ollama_fallback_enabled`; hvis OFF → re-raise (uændret).
    Hvis ON → `execute_cheap_lane_via_pool(message=message, task_kind=task_kind, lane="autonomous")`.
    **max_depth=1** (helperen kalder ALDRIG sig selv rekursivt). Håndtér BEGGE exit-former
    (Fund #7): pool returnerer floor-dict → returnér den; pool RAISER RuntimeError → fang og
    `return attempt_floor(message=message, lane="autonomous", reason="pool-exhausted")`.
  - Aldrig betalt deepseek (pool filtrerer paid; assert `result.get("provider") != "deepseek"`).
- [ ] **Step 4:** PASS (alle 3).
- [ ] **Step 5:** Commit.

### Task 10: wire autonom-seam gennem fallback-helperen
**Files:** Modify `core/services/visible_runs.py` (`_pump_model_stream`, L1456 kald / L1465 catch); Test `tests/test_visible_runs.py`
- [ ] **Step 1:** Test `test_autonomous_stream_failure_falls_to_cheap` (autonomt `VisibleRun`
  m. `provider="ollama"` hvor `stream_visible_model` kaster → run completer, status != "failed",
  fallback-helper kaldt) OG `test_visible_run_never_uses_fallback` (`autonomous=False` →
  helper aldrig kaldt, exception propagerer som før).
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** I `_pump_model_stream`: behold visible-stien uændret. NÅR `run.autonomous is True`
  OG `stream_visible_model` kaster (catch L1465): kald `run_non_visible_with_fallback(message=
  run.user_message, primary_call=<no-op der re-raiser den fangne exc>, run_is_autonomous=True,
  task_kind="autonomous")` og pump resultatets tekst ind i controller-strømmen. **Gate:** hele
  fallback-armen bag `non_visible_ollama_fallback_enabled` (OFF → nuværende re-raise-adfærd).
  Bevar `run.autonomous`-gaten som eneste indgang (IKKE lane-streng — Fund #6).
- [ ] **Step 4:** PASS.
- [ ] **Step 5:** Commit.

---

## Fase P4 — Global rate-cap på ikke-visible lane (Fund #5)

### Task 11: leaky-bucket før balanceren
**Files:** Create `core/services/non_visible_rate_cap.py`; Test `tests/test_non_visible_rate_cap.py`
- [ ] **Step 1:** Test:
```python
def test_rate_cap_blocks_burst(monkeypatch):
    from core.services import non_visible_rate_cap as rc
    monkeypatch.setattr(rc, "_now", lambda: 1000.0)
    rc.reset()
    allowed = [rc.allow(tokens=100) for _ in range(rc.REQ_PER_MIN + 5)]
    assert allowed.count(True) == rc.REQ_PER_MIN   # overskydende afvist
def test_rate_cap_refills(monkeypatch):
    from core.services import non_visible_rate_cap as rc
    t = {"v": 1000.0}; monkeypatch.setattr(rc, "_now", lambda: t["v"]); rc.reset()
    for _ in range(rc.REQ_PER_MIN): rc.allow(tokens=1)
    assert rc.allow(tokens=1) is False
    t["v"] += 61                                    # ét minut senere
    assert rc.allow(tokens=1) is True
```
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Implementér token-bucket: `REQ_PER_MIN` (fx 120) + `TOKENS_PER_DAY` (fx 5_000_000),
  modul-global state, `_now()` hookable, `allow(tokens) -> bool` (dekrementér begge buckets, refill
  lineært). `reset()` for tests. **Uafhængig af slot-health** — dette er et hårdt loft der forhindrer
  multi-profil+fallback i at forstærke runaway. Kald `allow()` i `run_non_visible_with_fallback`
  (Task 9) FØR pool-kaldet; ved False → `attempt_floor(reason="rate-capped")`. Gate
  `non_visible_rate_cap_enabled`.
- [ ] **Step 4:** PASS.
- [ ] **Step 5:** Commit.

---

## Fase P5 — Adaptiv kvote-læring (WS2, sikret pr. Fund #4)

### Task 12: SlotState lærer daily_observed KUN på ægte quota-429
**Files:** Modify `core/services/cheap_lane_balancer.py` (`SlotState` L35, `_register_failure` L346, state-persist); Test `tests/test_cheap_lane_balancer.py`
- [ ] **Step 1:** Test:
```python
def test_learns_only_on_quota_429():
    st = SlotState(slot_id="groq::x::default")
    # transient/rate 429 → lærer IKKE
    bal._register_failure(st, "429 rate limit", now=T, retry_after_s=2)
    assert st.daily_observed is None
    # ægte daily-quota-udtømt + korroboration (2. hændelse) → lærer
    bal._register_failure(st, "quota exhausted daily", now=T, retry_after_s=0, observed_used=40)
    bal._register_failure(st, "quota exhausted daily", now=T+1, retry_after_s=0, observed_used=40)
    assert st.daily_observed is not None and st.daily_observed <= 40
def test_config_floor_not_undercut():
    st = SlotState(slot_id="groq::x::default")
    for _ in range(2): bal._register_failure(st, "quota exhausted daily", now=T, observed_used=1, config_daily=100)
    assert st.daily_observed >= bal._DAILY_FLOOR_FRACTION * 100  # aldrig absurd-lavt fra én støj-hændelse
```
- [ ] **Step 2:** FAIL (felter/args findes ikke).
- [ ] **Step 3:** Tilføj `daily_observed: Optional[int] = None`, `last_429_at: Optional[float] = None`,
  `quota_429_count: int = 0` til `SlotState` (+ persist i `_state_to_dict`/`_state_from_dict`).
  Udvid `_register_failure(state, error_kind, *, now, retry_after_s=0, observed_used=None, config_daily=None)`:
  - Klassificér: kun når `error_kind` matcher quota-exhausted-mønster (`"quota"` + `"daily"`, IKKE
    `"rate"`/`"transient"`/`retry_after_s>0`) tælles det som quota-hændelse.
  - **Korroboration:** kræv `quota_429_count >= 2` inden `daily_observed` sættes (én transient
    dræber ikke en slot — Fund #4 "min()=envejs-skralde").
  - **Config-gulv:** `daily_observed = max(config_daily * _DAILY_FLOOR_FRACTION, min(daily_observed or ∞, observed_used))`
    (`_DAILY_FLOOR_FRACTION=0.5`). Bevar rate/transient → eksisterende breaker-sti uændret.
  - Gate hele lærings-armen bag `cheap_pool_adaptive_quota_enabled`.
- [ ] **Step 4:** PASS.
- [ ] **Step 5:** Test `test_daily_reset_clears_observed` (ved døgn-skift nulstilles `daily_observed`
  + `quota_429_count` → re-læres). Commit.

### Task 13: prædiktiv skip når intet hovedrum
**Files:** Modify `_daily_headroom_for` (L263) / `_compute_weight` (L294); Test samme
- [ ] **Step 1:** Test `test_predictive_skip`: slot hvor `_daily_used_from_db(provider, profil) >=
  daily_observed` → `_compute_weight` returnerer 0 UDEN prøv-og-fejl.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** `_daily_headroom_for` bruger `min(config daily_limit, state.daily_observed)` som
  effektivt loft når `daily_observed` er sat (og flag ON); `_compute_weight` = 0 når headroom ≤
  lille margin. Kræver `SlotState` tilgængelig i `_daily_headroom_for` (send state ind, eller
  slå op). Bevar OFF-sti = ren config-headroom.
- [ ] **Step 4:** PASS. Commit.

### Task 14: anti-jag — eskalér breaker + stale-markér
**Files:** Modify `_register_failure` (L346); Test samme
- [ ] **Step 1:** Test `test_repeated_quota_failures_stale`: N quota-fejl indenfor M min →
  `breaker_level` eskalerer (eksisterende 5→15→60 min) OG en `stale_until_daily_reset`-markering
  sættes → `_compute_weight`=0 til døgn-reset.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Tilføj `stale_until_daily_reset: bool = False`; sæt ved ≥3 quota-hændelser i vindue.
  `_compute_weight` returnerer 0 når sat. Ryddes ved døgn-reset (samme sti som Task 12 Step 5).
- [ ] **Step 4:** PASS. Commit.

---

## Fase P6 — Shadow/flag-gating verifikation (Fund #9)

### Task 15: alle nye adfærd er shadow-gated + observerbare
**Files:** Modify de fire nye/ændrede stier; Test tværgående
- [ ] **Step 1:** Test `test_all_flags_default_off`: med alle fire flag uset → (a) `build_slot_pool`
  = single-profil, (b) autonom stream-fejl re-raiser (ingen fallback), (c) ingen rate-cap,
  (d) ingen daily_observed-læring. Dvs. HEAD-adfærd bevaret bit-for-bit når intet er flippet.
- [ ] **Step 2:** FAIL hvis nogen sti ikke gater korrekt → ret.
- [ ] **Step 3:** Tilføj Central-observabilitet: hver ny beslutning (`profile_slot_added`,
  `non_visible_fallback_fired`, `rate_capped`, `quota_learned`) skrives via `_observe_central`
  (self-safe) så vi kan SE effekten i shadow før flip.
- [ ] **Step 4:** PASS.
- [ ] **Step 5:** Commit.

---

## Fase P7 — Acceptance + deploy + nøgle-aktivering

### Task 16: acceptance-harness (spec-scenarier 1-6)
**Files:** Test `tests/test_cheap_pool_resilience_acceptance.py` (isolated_runtime)
- [ ] Integration-tests: (1) alle default-slots for én provider i cooldown → autonomt kører videre
  på anden provider; (2) quota-429×N → proaktiv afprioritering + stale, ingen genforsøg i vindue;
  (3) ollama-kvote → autonomt run completer via cheap (ikke failed); (4) ny profil-nøgle drop →
  slot indenfor TTL; (5) visible uændret (deepseek) under alt; (6) `record_cost`=$0 for gratis
  fallbacks. **Plus WS4-verifikation:** agent-pool (dispatch) trækker fra samme selection-pool →
  arver multi-profil (test at agent-lane-kald ser account2-kandidater når flag ON). Commit.

### Task 17: deploy + flip + aktivér alle nøgler (bundler cache-fix-restart)
- [ ] **Step 1: WS5 live-verifikation (nul kodeændring):** på containeren, kør provider-sweep mod
  gemini/cloudflare/ollamafreeapi/openrouter → bekræft de stadig resolver (Fund #10: de var
  allerede korrekte; dette er en regressions-vagt, ikke en fix).
- [ ] **Step 2:** Deploy: commit alt → `git push origin` → container `git fetch && reset --hard
  origin/main` → `sudo systemctl restart jarvis-runtime jarvis-api`. Denne genstart aktiverer OGSÅ
  det allerede-committede cache-rapporterings-fix (7fb0811f) — én genstart, to leverancer.
- [ ] **Step 3:** Verificér på containeren FØR flip: `build_slot_pool` (med flag ON i shadow) viser
  default+account2-slots for de 9 arbejdsheste; ingen slot-kollision (3-delt slot_id).
- [ ] **Step 4: Gradvis flip** (shadow → on, én ad gangen, observér Central mellem hver):
  `cheap_pool_multiprofile_enabled` → `non_visible_rate_cap_enabled` → `non_visible_ollama_fallback_enabled`
  → `cheap_pool_adaptive_quota_enabled`. Rate-cap FØR fallback (loft før forstærker).
- [ ] **Step 5:** Bekræft autonome runs completer gratis; fjern evt. sambanova-plaster. Opdatér
  memory ([[project_cheap_lane_pool_resilience_round]] → live). Commit final state.

---

## Self-review note
Dæknings-gate: hvert rørt/nyt `core/`-modul har matchende `test_<modul>.py`. Ingen placeholders.
Rækkefølge fundament-først (P0 slot_id blokerer alt), derefter aktivering (P1), tier-sikkerhed (P2),
rygrad (P3), hårdt loft (P4), subtil læring sidst (P5), shadow-verifikation (P6), deploy (P7).
Rådets 10 fund adresseret: #1(P0 T1-3), #2(B2 i T6), #3(P0 T2-3 SQLite), #4(P5 T12 sikret læring),
#5(P4 T11 rate-cap), #6(P3 T9-10 run.autonomous-gate+assertion), #7(T9 begge exit-former+max_depth),
#8(seam pinned T10), #9(P6 T15 flag-gating), #10(WS5 droppet→T17 verifikation). B1-konflikt
LØST af egress-adskillelse (P2 T8-8c: bevist+hærdet VPN/IPv6-proxies → account2=ægte parallel-tier,
ikke fallback; leak-værn = eneste sikkerhedsmekanisme). Visible-lane-urørthed testet i
T9(assertion)+T16(5). Egress-infra: [[reference_expressvpn_egress_gateway]] (ct106 VPN, ct107 IPv6).
```