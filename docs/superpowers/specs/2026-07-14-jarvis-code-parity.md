---
status: spec v2 — udkast til review (14. jul 2026). Grundet i et 5-agent research-sweep +
        6-linse råds-review (completeness · stabilitets-adversary · sikkerhed · Jarvis-integration ·
        sekvensering · operator-UX), begge verificeret mod kildekode. + Claudes egen introspektion.
formål: Gør jarvis-code til Jarvis' klient-ejede agentiske harness med FULD Claude-Code-paritet i
        kapabilitet, INTERAKTION og stabilitet — så Jarvis arbejder som Claude — og bliver derefter
        det DELTE substrat som jarvis-desk (code mode) migrerer til.
kilder: research wf_866d6701-3c4 · råd wf_6cb587c2-cc1 · Claude-introspektion ·
        2026-07-13-claude-orchestration-reference.md · streaming-production-grade-spec.md.
        VIGTIGT: research = LÆRING af mønstre; vi kopierer INGENS kode — vi bygger vores eget.
review: self-review + 6-linse råds-review INTEGRERET (v2). Integrations-log nederst.
---

# jarvis-code — fuld Claude-Code-paritet (kapabilitet · interaktion · stabilitet)

## 0. Nordstjerne + kerne-lektien

**Nordstjerne:** giv Jarvis den samme agentiske arbejdsmåde som Claude Code giver Claude, så
**stabilt** at det kan blive det delte substrat for jarvis-desk code mode. Bjørn: "gøre Jarvis lige
så stabil som dig."

**Paritet spænder tre lag** (rådet fandt at v1 kun dækkede det ene):
- **Orkestrering** — loop, tools, dispatch, baggrund, memory, skills, hooks. (v1 dækkede dette.)
- **Input/interaktion** — multimodal input, extended-thinking-replay, miljø-kontekst, mid-run
  styring, prompt-caching, budget-lofter, session-resume/fork, harness-adfærdskontrakt. (v1 MISSEDE dette.)
- **Governance/sikkerhed** — sandbox-realitet, untrusted-content-fencing, egress, per-bruger-isolation,
  subagent-privilegier, skill/MCP-supply-chain. (v1 behandlede sikkerhed som ÉN spande; det er et helt trussels-lag.)

**Kerne-lektien:** kapabilitet og stabilitet er IKKE separate. Jarvis' måneder-lange meta-bug =
*runtimen accepterer en brækket tur som et gyldigt "færdigt" svar*. jarvis-code dræbte cutoff på
TRANSPORT-niveau (korte bundne steps) men re-importerer den på LOOP-niveau. **Tier 0 (stabilitet)
bygges FØRST.** Og — kritisk korrektion fra rådet — Tier 0 må dække **partiel** (ikke-tom men afkortet)
completion, ikke kun tom.

## 1. Nuværende tilstand (jarvis-code v0.4.0, ~8.7k LOC)

**Stærk kerne (behold):** klient-ejet loop (`repl_ptk.py::_turn_worker` → `POST /v1/agent/step`, server
returnerer tool_calls, klient eksekverer 8 lokale tools LOKALT ellers forwarder til `/v1/tools/execute`);
5 approval-modes; live diff/undo; per-tur turn_id; API-reconnect m. backoff; cache-stabil tool-ordning;
fail-safe katalog; MCP (stdio); 7 hooks; cutoff-robust stepping (non-stream fallback).

**Fire arkitektur-problemer (verificeret):**
1. **3 overlappende UIs** (repl_ptk default 1734L · tui.py legacy · repl.py linear) — MCP/hooks/
   compaction/concurrent-tools wired KUN i linear repl.py, ikke i default. Feature-huller + drift.
2. **"Blind lane"** — `agent_loop.py` har nul `record_cost`, nul nerve, ingen `note_empty_completion`. Central er blind.
3. **Cutoff re-åbnet på loop-niveau** — silent-empty + partiel-completion + ubundet kontekst + ucappede tool-results.
4. **Multi-bruger-blocker** — `/v1/agent/step` læser INTET user_id og hardkoder `name="default"` (Bjørns
   workspace) + "du lever i Bjørns terminal" for ALLE kaldere. Twin-ruten `/v1/tools/execute` ER scopet
   (SEC#154 Finding A/B); agent/step er det IKKE. §6-migrationen lækker Bjørns identitet+memory til hver bruger.

## 2. Prærekvisit — inkrementel loop-konsolidering (IKKE big-bang)

Rådet: v1's "konsolidér 3 UIs" er en front-loaded big-bang som INTET Tier 0-kontrakt kræver. I stedet:
1. Erklær `repl_ptk` kanonisk; **frys `repl.py` som reference (slet ikke)**; behold `tui.py` som `--legacy`.
2. **Udskil repl_ptk's tur-loop til sit eget UI-frie modul** (`jc_agent_loop`) — Boy Scout + dette ER
   substrat-ekstraktionen (§6). Tier 0-kontrakterne bygges i dét modul, ikke i UI-filen.
3. Port MCP/hooks/compaction/concurrent-tools ind i det delte modul løbende, ikke som forudsætning.

## 3. Paritets-matrix (tiers). Status: has/partial/missing. [C]=klient-repo · [S]=server jarvis-v2.

### TIER 0 — Stabilitetskontrakter (BYGGES FØRST)

| # | Kontrakt | Status | Byg |
|---|---|---|---|
| A1 [C] | Terminal-garanti; behandl ALDRIG tom+ingen-tool_calls som færdig; aldrig split tool_use/result-par | partial | Klient-guard + server syntetisk `done` |
| A2 [C/S] | **Empty-detektion + ét bundet resend + tvungen slut-syntese** + **commit user-turn FØR step** (i dag droppes user-turen også ved tom respons) | missing | ÉT non-thinking resend; max_rounds→tving prosa-runde |
| A3 [C] | Kontekst-fit **round-atomisk** — dropper (assistant-m-tool_calls + ALLE dens tool_results) SAMLET; tæller tool_calls-argument-bytes | missing | **Genbrug IKKE model_context.fit_messages_to_window as-is** (tool-pair-blind, under-tæller → orphan-par→400). Reimplementér round-atomisk klient-side |
| A4 [C] | Uniform cap på ALLE tool-resultater (inkl. MCP) → spild til disk m. **synlig** "truncated N"-markør; **redigér secrets ud af spill-fil** | missing | Klient-side før append |
| A5 [C] | Degenerations/gentagelses-guard (ciffer-normaliseret) | missing | Spejl stream_degeneration-logik klient-side |
| A6 [C/S] | **Partiel-completion** — plumb `finish_reason` gennem iterator→done-SSE→klient; `length`/`content_filter`/null-uden-terminal = IKKE-terminal → fortsæt/resync (ikke accepter afkortet svar) | missing | **Rådets #1 residual-hul** — kernen af cutoff-familien |
| A7 [C] | **Round-atomicitet** — én tool_result pr. tool_call GARANTERET selv ved exception/cancel; ugyldige/partielle tool-args → typet `{status:error}` ikke `{}`-coercion | missing | Gør runden til en transaktion |
| A8 [C] | Forwarded (ikke-lokale) tool-fejl → typet `tool_result{status:error}` for det tool_call_id, ALDRIG raise der dræber turen | missing | try/except om route_tool_call/execute_native_tool (i dag raise_for_status dræber hele turen) |
| O1 [S] | Struktureret konvolut `{status,tokens_in,tokens_out,cost_usd,duration_ms,tool_calls,result}` + `record_cost` (m. user_id) + nerve + `note_empty_completion` — fjern blind lane | missing | Server agent_loop.py |
| O2 [C/S] | Loud typede fejl (BLOCKED/NEEDS_CONTEXT/DONE_WITH_CONCERNS) + return-or-stop; 502→classify_failure | partial | |
| O3 [C/S] | Per-step retry m. jitter + circuit-breaker/failover; **tool-idempotens ved retry** (gen-kør ikke tools hvis side-effekt landede); **model/tokenizer-konsistens inden for en tur** (ingen mid-tur-failover der skifter model) | partial | |
| O4 [C] | Idle/stall-watchdog (betingelses-baseret, aldrig destruktiv `wait_for`-cancel) | partial | |

### TIER 1 — Kerne-agentiske kapabiliteter

| # | Kapabilitet | Status | Byg |
|---|---|---|---|
| C [C/S] | **Subagent/dispatch** — **KORREKTION (rådet): server-siden er ALLEREDE BYGGET** (agent_runtime_base/spawn/council, agent_dispatch, central_convene_judge, subagent_digest; dispatch-ref DEL 4.4: "skal ikke BYGGES; skal aktiveres" — flag `agent_tools_enabled` OFF). | server=has/off, klient=missing | AKTIVÉR server-dispatch; klient tilføjer kun den LOKALE executor + render. Subagent ARVER Tier 0-kontrakten (bundne runder, resend, watchdog, wall-clock) + STRIKTESTE af forælder/egen mode (aldrig eskalér) |
| D [C] | Baggrunds-tasks + polling | missing | run_in_background bash (handle) + BashOutput/Kill; fjern 120s blocking-cap; gen-invokér ved state-ændring |
| M [C] | TodoWrite | missing | In-session store + tool + footer-render |
| E [C/S] | Memory — (1) projekt-memory altid injiceret (2) compaction-afledt session-summary | missing | + genbrug Jarvis' memory via MCP (per-bruger-scopet, §Sikkerhed) |

### TIER 1½ — Input/interaktion (rådet: helt fraværende i v1)

| # | Kapabilitet | Byg |
|---|---|---|
| R [C/S] | **Multimodal input** (billeder/screenshots) — step-content = array af typede blokke (text/image), ikke str-coercion (agent_loop.py:~355); read_file base64/media-type-gren; composer paste. **Load-bearing for Jarvis** ([[feedback_verify_visual_before_done]] "SE UI før færdig") |
| S [C] | **Extended-thinking/reasoning-replay** — bevar reasoning_content på tværs af tool-runder (m. pairing-invariant); tænk-budget-direktiv (think/+Nk). Test 3+ runde deepseek/copilot-loop ([[reference_copilot_followup_thinking_bug]]) |
| T [S] | **Miljø-blok** i system-prompt — `<env>`: cwd, git branch/status, OS/platform, dato, seneste commits (klient sender; server injicerer) |
| U [C] | **Mid-run styring** — Esc = kooperativ interrupt (≠ Ctrl-C abort): stop efter nuværende tool, behold tur-kontekst, åbn composer → korrektion injiceres som user-besked ved næste boundary. Kø typet input under kørsel (droppes i dag) |
| V [C/S] | **Prompt-caching-kontrakt** — cache_control-breakpoints: (a) system+identitet (b) tools-katalog (c) stabil samtale-prefix; TTL; interaktion m. tier-skift (none/identity/full) + compaction |
| W [C/S] | **Budget-lofter** — per-run token/USD-loft der HALTER loopet m. typet BLOCKED('budget') + fortsæt-tilbud; "+Nk"-grant. (I dag kun max_rounds=60, intet spend-loft) |
| X [C/S] | **Session resume/continue/FORK** — reconcilér klient --continue/--session m. server /session; fork (findes ikke). Distinkt fra memory-E |
| Y [S] | **Harness-adfærdskontrakt** i system-prompt — koncis/ingen preamble-postamble, comment-disciplin, proaktivitets-grænser, refuse-with-alternative, verify-before-done. (Det der får CC til at føles stabilt) |
| +[C] | @-fil-mentions/autocomplete i composer · /clear kontekst-reset · Read-pagination (offset/limit, linje-cap som CC's 2000) · MultiEdit atomisk fler-redigering · per-subagent model-valg · 429 Retry-After-header · SubagentStop/Notification-hooks |

### TIER 2 — Skill-system (Bjørns fokus, §4) · TIER 3 — Governance/UX · TIER 4 — Hærdning

- **Tier 2 (F):** REUSE Jarvis' eksisterende skill-motor; tilføj 3 trigger-brikker (§4).
- **Tier 3:** to-akse permissions (§Sikkerhed) · first-class plan-mode (kollapsér plan ind i approval-akse, ét sandheds-punkt, Shift+Tab-cycle) · hooks→gate-ledger (**klient/server-split: forwarded tools defererer til server `check_brain_write_allowed`; ingen dobbelt-gate**) · slash-unify (/cost /model /compact /tools /mcp /hooks — mangler i default-UI) · MCP HTTP/SSE (+ trust, §Sikkerhed) · UX (§Operator).
- **Tier 4:** multi-strategi fuzzy edit · bundet selv-korrektions-loop (≤3, struktureret lint/test-feedback) · checkpoint/rollback (git-commit pr. edit-runde) · provider-XML-tool-fallback ([[reference_gemini_ollama_toolcall_400]]) · per-tool telemetri→eventbus · ægte WebSearch (de-dupliker web_fetch/scrape) · OS-sandbox (se §Sikkerhed — flyttet FREM fra "senere").

## 4. Skill-systemet (reuse, ikke genopbyg)

**Jarvis HAR et komplet skill-system:** `skill_engine.py` (loader/registry, RLock) · `skill_engine_tools.py`
(semantisk matcher) · `skill_gate_tool.py` (`skill_gate` pre-action-gate, globalt reg. simple_tools.py:1776,
kill-switch, fail-open) · `gate_skill.py` (sikkerheds-scan) · **64 skills** i `~/.jarvis-v2/skills/` (15
superpowers; SKILL.md-parser tolererer name+description → superpowers KOMPATIBLE).

**Ubrugt af én grund — triggeren mangler.** Byg (reuse motoren):
1. Injicér available-skills-katalog i jarvis-code system-prompt (`_skill_catalog()` → list_skills() name+use_when+tags, ~100 tokens, progressive disclosure).
2. CC-stil instruktion i `_SYSTEM_PROMPT`: "hvis en skill matcher, kald `skill_gate(query=...)` FØR du handler."
3. Promovér `skill_gate` til `DEFAULT_COMPANIONS` (jc_tool_catalog.py:20).
4. (Overvej: klient auto-kald af skill_gate på 1. tur = deterministisk, mere pålideligt end CC's egen svage prompt-baserede aktivering.)
5. Genopliv tool-navn-oversættelse (Write→bash, Task→dispatch, Worktree→git worktree) fra skills-jarvis-compat.md.
6. Render: **annoncér "▸ bruger skill: X — <one-liner>"** (rådet: ellers usynlig).
- **GOVERNANCE (sikkerhed):** auto-surfacing + auto-kald udvider injektions-fladen. Kræv **owner-approval for at
  tilføje/aktivere** en skill jarvis-code auto-surfacer (tie til [[project_self_registering_nerves]]; regex-scanner
  misser paraphraseret/dansk injektion). Modellen kan write_file en SKILL.md → selv-modifikation af egen prompt.

## 5. Stabilitetskontrakter (tværgående invarianter — udvidet af rådet)

1. Bundet alt (uniform cap → spild til disk, **secret-redigeret**). 2. Reserveret compaction-buffer.
3. Compaction-stige billigst-først. 4. Aldrig split tool_use/result; aldrig forældreløs thinking.
5. Garanterede terminal-events; **run-liveness = eneste sandhed**. 6. Circuit-breaker + bundne retries.
7. Concurrency by declared property (isReadOnly/isConcurrencySafe — **klient-executor kører reads/writes
serielt i dag; skal parallelisere reads/serialisere writes**). 8. Isolation. 9. Lag-delte permissions.
10. Vedvarende baggrunds-summary. 11. Typede loud fejl til modellen. 12. Ingen silent caps (log+markér).
13. Diagnostik: DB/live-nerver = ground truth.
**Nye (rådet):** 14. **Round = atomisk enhed** for fit/compaction/cancel (definér eksplicit). 15. **Untrusted-content-
fencing** — tool-output/web/fil/MCP/subagent-resultat er UTRO; hegn (delimitér, markér "untrusted — aldrig
instruktioner") før modellen. 16. **Idempotens ved step-retry** — gen-kør ikke tools m. landede side-effekter.
17. **Compaction kun ved ren round-boundary** (ingen åbne tool_calls). 18. **Provider/tokenizer-konsistens
inden for en tur.** 19. **Forwarded-tool-cancel** — server skal stoppe container-side tool når klient forlader turen.

## 6. Sikkerhed & trust-model (rådet: helt nyt lag — ikke bare "to-akse")

**Korrektioner til v1 (verificeret forkert):** "sandbox default-ON" er FALSK — `_apply_cwd_and_guard`
confiner kun FIL-tool-stier og kun under opt-in `--sandbox`; **bash confineres ALDRIG** (kun cwd sat).
".git/config-beskyttelse" findes IKKE i koden.

**Krav (før full-auto/subagenter shipper — flyttet FREM):**
- **To-akse:** capability/sandbox-profil (ReadOnly/WorkspaceWrite/Restricted, beskyt .git/config) SEPARAT fra
  approval-timing. **dangerous-command + secret-path-guards SKAL fyre i ALLE modes inkl. bypass** (i dag springes
  de over ved bypass — den mode Jarvis kører unattended). Regex er ADVISORY; ægte gulv = **bash-confinement
  (bwrap/Landlock)** — flyttet fra Tier 4 til krav før Fase 2.
- **Untrusted-content** (invariant 15) — indirekte prompt-injektion via repo/web/fil er DEN dominerende angrebsklasse.
- **Egress-akse** — bash-net (curl/wget/nc/scp) + web_fetch = separat approval; **secret-exfil-kæde** (`cat .env`
  auto-godkendt readonly → `curl --data @.env`) skal brydes: udvid secret-detektion til bash-bodies + egress-gate.
- **SSRF** — web_fetch følger redirects uden allowlist, kører på klient-net (kan nå 127.0.0.1:8080, 169.254.169.254,
  RFC1918 [[reference_home_infra_map]]). Blokér intern/loopback/metadata; cap+re-validér hver hop.
- **Subagent-privilegier** — arver STRIKTESTE mode; kan aldrig eskalere; tool-budget/egress belastes+bundet af forælder (fan-out = token-bombe-risiko).
- **Multi-bruger** — `/v1/agent/step` SKAL resolve identitet/workspace/rolle fra autentificeret kalder (ContextVar
  auth-middleware sætter allerede), ikke hardkode Bjørn. **bypass/full-auto = owner-only server-side.** Per-bruger
  session-store + quota-gate ([[project_api_hardening_quota_tokens]] §20-22). `record_cost` + user_id.
- **Skill/MCP-supply-chain** — owner-approval for skills (§4); MCP-server-allowlist + binær-pinning (TOFU) før HTTP/SSE.
- **Audit-trail** — per-bruger/per-tool eksekverings-log (hvem kørte hvilken bash/write) distinkt fra cost-nerve.
- **ANSI-injektion** — sanitér tool-output før TUI-render (spoofede approval-prompts).

## 7. Operator-UX (rådet: nyt afsnit)

Mid-run styring (Esc, §U) · **diff VED approval-tid** (dry-run FØR gate; i dag vises diff kun EFTER kørsel — approve-blind)
· approval-timeout/auto-deny (unattended deadlock i dag: Event.wait uden timeout) · kumulativ session-cost + budget-loft-advarsel
· "context remaining før compaction"-indikator · **skill-annoncering** · live per-subagent-progress + inspicér transcript ·
completion/attention-notifikation (bell/ntfy/desk-push for autonome runs) · Ctrl-C dobbelt-tap-bekræftelse · keyboard-discoverability.

## 8. Migrations-sti → desk

- Byg Tier 0-1½ som **UI-frit delt substrat** (`jc_agent_loop`-modul, §2) — repl_ptk + desk konsumerer samme kerne.
- **BLOCKER (rådet):** per-bruger-scoping af `/v1/agent/step` + record_cost + session-store SKAL være på plads FØR
  desk-migration (ellers lækker Bjørns identitet/memory/kvote). Dette er prærekvisit, ikke "senere".
- Prove-then-migrate: desk starter når substratet passerer acceptance (§9). Desk = wire substrat + kanaler ind, ikke genopbyg.

## 9. Acceptance — "færdig nok til at migrere" (rådet: gør målbar)

1. **Fault-injection-harness (mock-provider):** injicér tom content · mid-stream cutoff · length-truncation ·
   tool_use-uden-result · degenerativ repetition · ugyldige tool-args · forwarded-tool-500. **Assertér:** hver
   giver recovered svar ELLER typet BLOCKED (aldrig silent/hængt); loopet emitterer ALTID terminal-konvolut;
   kontekst+tool-results capper synligt; ingen orphan-par. **Numerisk bar:** 0 silent-empty, 0 hæng, 0 orphan-400
   over N=100 injicerede runder. Regressions-tests committed (pyproject testpaths findes).
2. **Ægte fler-trins dev-opgave e2e** i jarvis-code: læs→(skill matcher→skill_gate)→planlæg→dispatch subagent→
   redigér→test→husk — samme flow som Claude, uden hæng/cutoff/fabrikation.
3. **Ikke blind lane:** hvert step synligt i Central (status/usage/duration/nerver/user_id).
4. **Sikkerheds-gulv:** bash-confinement + untrusted-fencing + egress-gate aktive; multi-bruger-scoping på agent/step.

## 10. Sekvensering (rådet: split repo + inkrementel)

Tag hvert item **[C]klient / [S]server**. jarvis-code kan **IKKE importere core.*** — hver "reuse" siger HVOR den kører
(klient-reimplementering vs server-kald).
- **Fase 0 [S] server Tier-0-lite FØRST (lav risiko, live API):** cost_usd i _stream_step done + record_cost + nerve +
  note_empty_completion + finish_reason-plumbing + user_id-scoping af agent/step. Fjerner blind lane + multi-bruger-blocker.
- **Fase 0.5 [C]:** udskil repl_ptk tur-loop → `jc_agent_loop`-modul (substrat-frø).
- **Fase 1 [C] Tier 0:** A1-A8 (partiel-completion, round-atomicitet, tool-pair-aware fit, forwarded-error-typing, cap, degeneration).
- **Fase 2 [C/S]:** AKTIVÉR dispatch (server allerede bygget) + klient-executor · baggrund/polling · todos · memory · **bash-sandbox+egress (sikkerhedsgulv FØR autonomi)**.
- **Fase 3 [C]:** skill-trigger (3 brikker).
- **Fase 4 [C/S]:** input/interaktion (multimodal · thinking-replay · env · steering · caching · budget · resume/fork · adfærdskontrakt).
- **Fase 5:** governance/UX + hærdning.
- **Fase 6:** acceptance-harness → migrations-trigger → desk.
**Riskeste antagelse (rådet):** at klient-side reuse af server-core er muligt — det er det ikke (ingen import); planlæg reimplementering.

## 11. Åbne beslutninger (til Bjørn)

1. **Server Tier-0-lite på LIVE api nu** (Fase 0) — ok at røre agent_loop.py på produktion med tests, eller separat staging?
2. **bash-sandbox-gulv:** bwrap/Landlock FØR Fase 2 (rådet stærkt anbefaler; kernel xanmod/DKMS — kræver kernel-support-tjek).
3. **Skill-trigger:** prompt-instruktion (model beslutter) vs. klient auto-kald (deterministisk). Rådet: auto-kald mere pålideligt.
4. **Multimodal-prioritet:** nu (Fase 4) eller tidligere — givet "SE UI før færdig" er det load-bearing for Jarvis' egen honesty-stack?
5. **Desk-multi-bruger-scoping** som Fase 0-blocker: enig i at det ER en prærekvisit, ikke "senere"?

---
## Integrations-log (v1 → v2, fra 6-linse råd)
- **Rettede fejl:** "sandbox default-ON" (falsk) · ".git-beskyttelse findes" (falsk) · "byg dispatch" → dispatch er
  ALLEREDE bygget server-side (aktivér) · "reuse core.*" → klient kan ikke importere (reimplementér).
- **Nye lag:** Tier 1½ input/interaktion (R-Y+) · §6 sikkerhed/trust-model · §7 operator-UX · multi-bruger-scoping som §6-blocker.
- **Hærdede kontrakter:** A6 partiel-completion/finish_reason (rådets #1 residual) · A3 round-atomisk fit (ikke reuse tool-pair-blind) ·
  A7 round-atomicitet · A8 forwarded-error-typing · invarianter 14-19.
- **Målbar acceptance:** fault-injection-harness + numerisk bar + regressions-tests.
- **Sekvensering:** split [C]/[S]; server Tier-0-lite først; inkrementel UI; sikkerhedsgulv før autonomi.
