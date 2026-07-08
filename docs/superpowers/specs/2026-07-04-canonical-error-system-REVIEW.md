---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Canonical Error System — FULD REVIEW + korrektioner (autoritativ)

**Dato:** 2026-07-04
**Reviewer:** Claude (Opus 4.8) — verificeret via 3 read-only agenter mod ægte kode
**Status:** Denne review er AUTORITATIV hvor den modsiger spec/audit/impl-plan. Læs den før implementering.

> **Kort:** Jarvis' retning er stærk og hans audit-linjenumre er præcise denne gang. MEN to ting skal rettes før implementering: (1) **byg PÅ den eksisterende Central-fejl-infrastruktur** (`central_error_envelope` findes ALLEREDE som canonical-repræsentation — undgå dobbelt-sandhed), og (2) **korrigér audit-tal + ét fejlkarakteriseret P0-item.**

---

## 1. Hvad Jarvis fik RIGTIGT (credit hvor det er fortjent)

- **Audit-linjenumre er næsten perfekte** — ingen hallucination denne gang (modsat tidligere audits). Alle desk-filer eksisterer, alle P0-linjer bekræftet undtagen én (§3). app.py's ~41 linjenumre er eksakte.
- **Retningen er rigtig:** teater-fallbacks er et reelt problem, "ingen stilhed"-princippet er sundt, faseinddeling P0→P1→P2 er fornuftig, self-review lukkede reelle huller (endpoint-kontrakt, nødfald, test-strategi).
- **`StreamError` i streamClient.ts ER et stærkt fundament** (verificeret: `ErrorCategory` + `retryable` + `statusCode` + `context` + `userMessage()`). Udvidelse med `kind`/`origin` er rigtig.
- **`gate_execution.py` ER et positivt eksempel** (verificeret: router fail-retninger gennem `central().decide` + `record_central_incident(kind=fail_open)`).

## 2. ARKITEKTONISK HOVEDKORREKTION — byg PÅ det eksisterende (undgå dobbelt-sandhed)

Spec'en foreslår NY `CanonicalError` + NY `central_error_conductor.py` + NY error-store. **~60-70% findes allerede og er kamp-testet.** CLAUDE.md's regel ("no dual truth", "Mission Control reads projections, does not invent a second truth") kræver at vi UDVIDER, ikke duplikerer:

| Spec-koncept | Findes ALLEREDE — byg på dette | Dobbelt-sandheds-risiko |
|---|---|---|
| `CanonicalError`-type/felter | **`core/services/central_error_envelope.py` → `ErrorEnvelope`** (code/severity/user_message/retryable/fix_hint/correlation_id/origin_cluster/detail + kode→dansk-`_MAP` + `to_client_event()` + `emit()`) | **HØJ** — to canonical dataclasses med divergerende felter+maps |
| `/internal/errors/report` receiver + klassifikation | **`central_anomaly.record_anomaly` + `_classify`** (modtager→klassificerer→dedup→eskalerer, allerede live via sys/threading/asyncio-hooks + log-handler) | **HØJ** — to klassifikatorer med to severity-skalaer |
| Incident-eskalering (§4.4) | **`db_central_incidents`** (`record_central_incident`/`bump_open_incident`/`resolve_*` — persistent, cross-proces, restart-overlevende) | **HØJ** — ny parallel error-tabel |
| `central().observe`-integration | allerede kontrakten `central_error_envelope.emit()` bruger | — |
| `ProviderFailoverHealer`/`LaneSwitchHealer` | **visible_runs failover-loop (:2731+) + `provider_circuit_breaker` + `heartbeat_provider_fallback`** (kill-switch-gated, per-provider breaker, én-failover-pr-tur, tools re-eksekveres IKKE) | **MEDIUM/HØJ** — to failover-stier der racer på samme breaker |
| `CircuitResetHealer` | **`central_switches.CircuitBreaker`** (per-nerve + per-provider) | MEDIUM |
| Rate-limit/recursion-guard (§9) | **`central_anomaly` cooldown + reentrancy-guard + `_SKIP_PREFIXES`** | MEDIUM |
| Desk unified rendering (§5.2) | **`ErrorEnvelope.to_client_event()`** (allerede ét klient-format for desk/companion/UI) | — |

**GENUINT NYT + værd at bygge (intet eksisterende):**
1. **Healer-registret + healing-actions** (backoff-retry-orkestrering, daemon-restart, syslogd-restart) — dette findes IKKE.
2. **Desk-UI:** `ErrorCard`, system-health-chip, transparency-log — findes IKKE.
3. **`except Exception: pass`-audit-oprydningen** — den mekaniske migration.

**Revideret Fase 0** (afløser impl-plan §5 Fase 0): (a) UDVID `ErrorEnvelope` med `kind`-taxonomi + `recoverable` + `scope` (rør IKKE de eksisterende felter). (b) `/internal/errors/report` = TYND adapter der kalder `central_anomaly.record_anomaly` + `central().observe` — ikke en ny pipeline. (c) Eskaleringer → `db_central_incidents`. (d) Byg healer-registret som det eneste ægte nye backend-stykke.

## 3. AUDIT-KORREKTIONER (verificeret mod kode)

**Tal-rettelser (impl-plan §5 bygger på forkerte tal):**
| Fil | Audit/plan sagde | VERIFICERET | Konsekvens |
|---|---|---|---|
| `visible_runs.py` | "35+ except:" | **134 `except: pass`** (270 total) | STØRSTE oprydnings-mål, ikke central.py. 4× undertalt. Skrøbelig fil → yderst konservativ, `severity: debug` først. |
| `heartbeat_runtime.py` | "hundredvis" | **139 `except: pass`** (214 total) | "mange", ikke "hundredvis". |
| `central_private_observe.py` | "6 except: pass" | **3** (5 total) | Overtalt. |
| `central.py` | "10+" | **9** | Tæt nok. |
| `app.py` lifespan | "~43 wrapped i pass" | 41 handlers: **18 tavse `pass` + 23 `logger.warning`** | Kun 18 er tavse — de 23 logger allerede. |
| `chat.py` | "12 except: pass" | **12** ✅ eksakt | — |
| desk total | "~70 steder" | **~130+ swallow-sites** | Undertalt (sikker retning). |

**Fejlkarakteriseret P0-item (ville spilde arbejde):**
- **`Composer.tsx:186 _deepseekFallback` — FJERN fra P0/audit.** Det er IKKE fejl-slugning eller model-hack. Det er en hardcodet default model-dropdown-liste vist indtil provider-listen loader (`providers.length ? ... : _deepseekFallback`). Ingen `catch`, ingen fejl-sti. Hører i "UI-default-data", ikke fejl-håndtering. Provider-failover findes allerede i visible_runs (§2).

**Sti-rettelser:** `MissionControl.tsx`/`RunDetail.tsx` er i `components/cowork/missioncontrol/` (audit udelod undermappen).

## 4. TAXONOMI + ENUM-KONSISTENS (tre docs modsiger hinanden)

Reconcilér til ÉN kanonisk definition (audit + impl-plan brugte kinds/enums der ikke var i spec'en):

**Endpoint:** ÉT navn → **`POST /internal/errors/report`** (impl-plan's; spec'ens `/central/errors` og audit's `central.errors` udgår). Desk sender via backend-proxy `/api/internal/errors/report`.

**`severity`:** `debug | info | warning | error | critical` (tilføj `debug` — rate-limiting §9 brugte det allerede). MEN: `ErrorEnvelope` bruger i dag `info|warning|error|critical` → udvid dén, map `debug`→lavest.

**`recoverable`:** `auto | retry | user_action | degraded | permanent` (ikke `none`; `permanent` fra impl-plan). `known_benign` er IKKE en recoverable — det er en healing-udfalds-tilstand (auto-healet, vises kun i health, ikke chat).

**`kind`-taxonomi:** spec'ens ~27 + de manglende fra audit: `server.error`, `protocol.malformed`, `infra.git_unavailable`, `pfsense.syslogd_dead` (spec havde `infra.syslogd_dead` — vælg ÉN: `infra.syslogd_dead`). Impl-plan siger "37 kinds" — tæl den endelige liste og fastlås tallet ét sted. Map hver kind til `ErrorEnvelope._MAP` (udvid den eksisterende, lav ikke en ny).

**`origin`:** brug `{file, function}` — IKKE `file:linje` (linjer driver; audit demonstrerede det selv med "forældede linjenumre"-hullet).

## 5. YDERLIGERE REVIEW-NOTER

- **Egress/privatliv:** errors med `context: Record<string,unknown>` + fri `message` må respektere egress-membranen. Cross-proces/ekstern: kun skalarer + forud-godkendt user_message (som `ErrorEnvelope` allerede gør). Fri kontekst holdes owner-lokalt. Tilføj til spec.
- **`DaemonRestartHealer` (`systemctl restart`) er en SECURITY-handling** (root/sudo). Spec §11-Q3 har ret: SKAL gennem `gate_kernel` GateClass.SECURITY + `central_switches`-godkendelse. Auto-restart-loops er en reel risiko → circuit-breaker + max-attempts obligatorisk (ikke valgfrit).
- **Tidsestimater optimistiske:** "Fase 1: 1 dag" for at røre visible_runs (134 spots) + heartbeat (139) er urealistisk. De to filer er på Boy-Scout-listen og er kilden til hver cutoff-bug. Realistisk: en dedikeret, konservativ sprint med `severity: debug` + shadow-observation FØRST. Rør ikke 134 spots i én omgang.
- **Align med dagens nerver:** `self.cutoff`/`self.loop_lag` har ALLEREDE live nerver (`stream/cutoff_at_loop_lag`, `runtime/loop_lag_spike`, `loop/no_progress_finalize`, `hollow_promise`, `stream/dsml_tail_dropped`, `stream/provider_length_truncation`). Canonical-systemet skal MAPPE disse eksisterende nerver til kinds, ikke gen-emittere dem.

## 6. Anbefalet implementerings-rækkefølge (revideret)

1. **Fase 0 (foundation, byg PÅ eksisterende):** udvid `ErrorEnvelope` (kind/recoverable/scope + udvid `_MAP`); tynd `/internal/errors/report`-adapter over `central_anomaly`+`observe`; map dagens error-nerver → kinds. Tests: taxonomi-komplethed + adapter happy-path. **Ingen ny store, ingen ny conductor.**
2. **Fase 1 (healer-registret — det ægte nye):** `error_healers.py` med registry; delegér Provider/Lane til eksisterende visible_runs-failover; DaemonRestart bag SECURITY-gate; backoff/syslogd nyt. Tests pr. healer.
3. **Fase 2 (desk-UI):** udvid `StreamError` m. kind/origin; `useCanonicalError`-hook; `ErrorCard` + health-chip + transparency-log (forbrug `to_client_event()`).
4. **Fase 3 (audit-oprydning, konservativt):** start med de ~15 P0-desk-sites (verificeret) + de 18 tavse `pass` i app.py + gate_execution. visible_runs/heartbeat's 134+139 spots = separat, `debug`-severity-først, shadow-observeret sprint. IKKE bulk.

---

*Denne review er grounded i 3 read-only verifikationer mod ægte kode. Jarvis' arbejde er godt — rettelserne handler mest om at UNDGÅ at genopbygge 60-70% der allerede findes, plus én fejlkarakterisering og skæve tal. Retningen står.*
