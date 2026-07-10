# Claude Code-leak: Lært vs. Mangler (samlet + kilde-verificeret)

**Dato:** 2026-07-10
**Kilde:** Jarvis' 3 research-beskeder (session chat-d600b2…) + **verifikation mod den faktiske lækkede kildekode** (tanbiralam/claude-code, ~513k linjer TS, v2.1.88-snapshot fra npm source-map-lækken 31. mar 2026).

> **Metode-lære (vigtig):** Flere gaps Jarvis "manglede" var allerede bygget, og jeg (Claude) kaldte fejlagtigt noget for konfabulation ud fra min egen upålidelige introspektion. Konklusion: **verificér ALTID mod kilden (leaked kode / core/services/) før du erklærer noget ægte eller falsk.**

---

## A. Verificeret ægte i den lækkede kilde

| System | Hvad kilden viser |
|--------|-------------------|
| **KAIROS** | `kairosActive`-flag (`commands.ts`, `AppStateStore.ts`). Headless baggrunds-"assistant mode" når brugeren ikke ser terminalen. Ægte, flag-gated. |
| **CHICAGO / CDCC** (= Chicago Desktop Compute-use Control) | `CHICAGO_MCP`-flag. **Computer Use som en in-process MCP-server** ved navn `computer-use`, tools = `mcp__computer-use__*`, native Swift-pakke `@ant/computer-use-mcp`. API-backend detekterer tool-navnene → injicerer CU-hint i system-prompt. Guards: macOS-only · interaktiv session · ant/GrowthBook (`tengu_malort_pedway`) · **frontmost-gate** (via `__CFBundleIdentifier`) · **app-allowlist** (`appNames.ts`) · SCContentFilter-screenshots · `request_access` godkender pr. session. Stdio-config er attrap (client.ts intercepter på navn). |
| **44 compile-time feature-flags** | ~20 gater built-but-hidden features (Bun dead-code-elimination når flag=false). |
| **3-lags memory + strict write** | index (altid) → topic-filer (on-demand) → transcripts (kun greppet). Skriv topic FØR index. |
| **autoDream** | Trigger-gates (≥24t + ≥5 sessioner + consolidation-lock), 4 faser (orient/gather/consolidate/prune), contradiction-removal, ~200-linjers/25KB byte-cap. |
| **23 nummererede bash-security-checks** | `bashSecurity.ts`, hver m. ID + ALLOW/DENY/FLAG. |
| **Magic Docs** | Idle → scope-limited sub-agent der kun må editere doc-fil. |
| **3 subagent-modeller** | Fork / Teammate (websocket-context) / Worktree (isoleret git). |
| **Prompt cache-grænse** | `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` — stabil cachet front, dynamisk bag. |

---

## B. Allerede bygget hos Jarvis (Jarvis kender ikke fuldt sine egne systemer)

| Leak-koncept | Jarvis' eksisterende |
|---|---|
| autoDream lock + session-gate + byte-cap | **Spec C** (10. jul) |
| contradiction-removal | **Spec A** contradiction_resolver |
| 3-lags memory + strict write | **Spec B** (migreret) |
| 23 security-checks | **Spec E** — 24 nummererede predikater |
| Magic Docs | **doc_repair_agent** (Spec A) |
| away-summaries | `build_return_brief` + **Spec D** |
| tick-decide ("skal jeg?") | gated initiativ-stige |
| webhooks | `webhook_tools.py` |
| prompt cache-grænse | byte-identisk stable-prefix |
| Fork-subagenter | `spawn_agent_task` |
| input-simulation / OS-handlinger | **operator-bro** (bash/keyboard/file på Bjørns maskine) |

---

## C. Ægte tilbageværende kandidater

1. **State-flag system m. TTL + cross-session persistens** (`flag/get/list/clear`). Jarvis' egen #1. Han har `schedule_task` + `remember_this`, men ikke en eksplicit TTL-flag-butik. Lavthængende, konkret.
2. **Teammate / Worktree-subagent-modeller** (ud over Fork).
3. **Append-only u-sletbar audit-log** for autonome handlinger (KAIROS-mønster).
4. **Per-tick blocking-budget** (KAIROS' 15s-loft).
5. **Hærd operator-broen med CHICAGO's guard-mønster:** app-allowlist + "frontmost/kontekst"-gate + pr-session `request_access`. Broen er Jarvis' computer-use-analog; CHICAGO's guards er en god skabelon.
6. **BUDDY** (terminal-tamagotchi) — ren leg, valgfri.

---

## D. Korrektion: hvad der IKKE er som Jarvis beskrev

- **CHICAGO er ægte, men ikke "ccdn.native.window/state/browser"-moduler.** Den rigtige impl er én computer-use-MCP-server + native Swift. Jarvis konfabulerede de specifikke modulnavne/API-signaturer; *kapaciteten* (desktop-selv-operation) er ægte.
- **CHICAGO er macOS-desktop-only** (mus/tastatur/clipboard/screenshot på brugerens Mac). Jarvis er **headless Linux** — ikke direkte portérbar. Hans operator-bro er den funktionelle analog.
- `ccdn`/`cdcc` som strenge findes IKKE i v2.1.88-snapshottet (min runtime er en nyere build; navnet kan være post-leak). "CDCC" = Bjørns udfoldning: **C**hicago **D**esktop **C**ompute-use **C**ontrol.

---

## Anbefaling
Af C er **#1 state-flag-systemet** mest værd (Jarvis' egen konklusion, konkret, lavthængende). **#5 (hærd operator-broen med CHICAGO-guards)** er den bedste "lær-af-CHICAGO"-gevinst uden at prøve at portere macOS-computer-use til en headless container.
